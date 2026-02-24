import sqlite3
import os
import json
import smtplib
from email.message import EmailMessage
from datetime import datetime
from fastapi import FastAPI, Request  # type: ignore
from pydantic import BaseModel  # type: ignore
from fastapi.responses import HTMLResponse, JSONResponse  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from fastapi.templating import Jinja2Templates  # type: ignore
from fastapi import HTTPException  # type: ignore
import hashlib

DB_FILE = "sura.db"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
# Set these as environment variables or update them directly to test!
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "san01aug@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "ebad pzks oixl uadc")

def send_real_email(to_email, subject, body_html):
    if SENDER_EMAIL == "your_gmail_address@gmail.com" or not SENDER_PASSWORD:
        print(f"Skipping REAL email to {to_email} because SENDER credentials are not set.")
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = f"SURA Connect <{SENDER_EMAIL}>"
        msg['To'] = to_email
        msg.set_content("Please enable HTML to view this message.")
        msg.add_alternative(body_html, subtype='html')

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"Real email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ngos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            email TEXT NOT NULL,
            contact TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant TEXT,
            contact TEXT,
            location TEXT,
            foodType TEXT,
            quantity INTEGER,
            expiry TEXT,
            email TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Pending',
            ngoAssigned TEXT DEFAULT 'Not yet Assigned',
            history TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("DROP TABLE IF EXISTS restaurants")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            contact TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)
    
    # Seed NGOs if empty
    cursor.execute("SELECT COUNT(*) FROM ngos")
    if cursor.fetchone()[0] == 0:
        ngos_data = [
            ("Helping Hands", "Tambaram", "sanjayn10827@gmail.com", "9876543210"),
            ("Smile Foundation", "Pallavaram", "sanjayeshwaran33@gmail.com", "9554862315"),
            ("Food for all", "Gundiy", "kaviyasanjay2017@gmail.com", "8777564354"),
            ("Hope Home", "Tambaram", "mathesh.4119@gmail.com", "6655884426"),
            ("Care & Share", "Tambaram", "v.k.sunanda12@gmail.com", "7765894159"),
        ]
        cursor.executemany("INSERT INTO ngos (name, location, email, contact) VALUES (?, ?, ?, ?)", ngos_data)
        
    conn.commit()
    conn.close()

def hash_psw(password: str) -> str:
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + '$' + pw_hash.hex()

def verify_psw(password: str, db_hash: str) -> bool:
    try:
        salt_hex, pw_hash_hex = db_hash.split('$')
        salt = bytes.fromhex(salt_hex)
        pw_hash = bytes.fromhex(pw_hash_hex)
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000) == pw_hash
    except Exception:
        return False

class RegisterRequest(BaseModel):
    name: str
    location: str
    email: str
    contact: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

init_db()

app = FastAPI()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

class DonationRequest(BaseModel):
    restaurant: str
    contact: str
    location: str
    foodType: str
    quantity: int
    expiry: str
    email: str
    notes: str = ""

def log_event(req_id, event, conn):
    cursor = conn.cursor()
    cursor.execute("SELECT history FROM requests WHERE id = ?", (req_id,))
    row = cursor.fetchone()
    if row:
        history = json.loads(row["history"])
        history.append({"time": datetime.now().isoformat(), "event": event})
        cursor.execute("UPDATE requests SET history = ? WHERE id = ?", (json.dumps(history), req_id))
        conn.commit()

@app.post("/api/donations")
def create_donation(req: DonationRequest, request: Request):
    base_url = str(request.base_url).rstrip("/")
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Save initial request (status: Pending)
    cursor.execute("""
        INSERT INTO requests 
        (restaurant, contact, location, foodType, quantity, expiry, email, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (req.restaurant, req.contact, req.location, req.foodType, req.quantity, req.expiry, req.email, req.notes))
    req_id = cursor.lastrowid
    conn.commit()
    
    # 2. Find matching NGO by location first
    cursor.execute("SELECT * FROM ngos WHERE location = ? LIMIT 1", (req.location,))
    ngo = cursor.fetchone()
    
    # Fallback to ANY NGO if exact location fails
    if not ngo:
        cursor.execute("SELECT * FROM ngos ORDER BY RANDOM() LIMIT 1")
        ngo = cursor.fetchone()
    
    if ngo:
        # Update row to waiting for response
        cursor.execute("UPDATE requests SET status = 'Waiting for Response', ngoAssigned = ? WHERE id = ?", (ngo["name"], req_id))
        conn.commit()
        
        ngo_name = ngo['name']
        request_data = req.dict()
        
        cursor.execute("SELECT name, location, email, contact FROM restaurants WHERE name = ?", (req.restaurant,))
        restaurant_info = cursor.fetchone()
        if restaurant_info:
            restaurant_info = dict(restaurant_info)
        else:
            restaurant_info = {"name": req.restaurant, "location": req.location, "email": req.email, "contact": req.contact}

        # Build pretty HTML Email
        email_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: #f8fafc; padding: 20px; text-align: center; border-bottom: 3px solid #16a34a;">
                <h1 style="color: #16a34a; margin: 0;">🍲 SURA Connect</h1>
                <p style="margin: 5px 0 0; color: #64748b;">Emergency Food Rescue Alert</p>
            </div>
            
            <div style="padding: 30px;">
                <h2 style="margin-top: 0; color: #0f172a;">New Food Pickup Assigned to {ngo_name}</h2>
                <p>Hello {ngo_name} Team,</p>
                <p>Our intelligent routing system has matched your NGO as the optimal responder for a new surplus food donation in your vicinity.</p>
                
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px; background: #f1f5f9; border-radius: 8px; overflow: hidden;">
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0; font-weight: bold; width: 35%;">Restaurant</td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0;">{restaurant_info.get('name')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">Location</td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0;">{restaurant_info.get('location')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">Food Type</td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0;">{request_data.get('foodType')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">Quantity</td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0;">{request_data.get('quantity')} meals</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">Expiry Priority</td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0; color: #dc2626; font-weight: bold;">{request_data.get('expiry')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">Contact Details</td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e2e8f0;">
                          Phone: {restaurant_info.get('contact')}<br/>
                          Email: {restaurant_info.get('email')}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; font-weight: bold;">Notes</td>
                        <td style="padding: 12px 15px;">{request_data.get('notes', 'None provided')}</td>
                    </tr>
                </table>
                <p>Please confirm your decision:</p>
                <div style="margin-top: 20px;">
                    <a href="{base_url}/api/respond?decision=accept&requestId={req_id}" 
                       style="background: #16a34a; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin-right: 10px;">✅ Accept Pickup</a>
                    <a href="{base_url}/api/respond?decision=decline&requestId={req_id}" 
                       style="background: #dc2626; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">❌ Decline</a>
                </div>
            </div>
        </div>
        """
        
        send_real_email(ngo["email"], "New Food Donation Request Assigned", email_html)
        email_content = f"Mock Email to {ngo['name']} ({ngo['email']}): New Request from {req.restaurant} for {req.quantity} meals. [Accept] or [Decline]"
        log_event(req_id, f"Email sent to NGO {ngo['name']} requesting pickup.", conn)
        status_msg = f"Request saved. Contacted NGO: {ngo['name']}"
    else:
        cursor.execute("UPDATE requests SET status = 'No NGO Available' WHERE id = ?", (req_id,))
        conn.commit()
        log_event(req_id, "No NGOs found in the requested location.", conn)
        status_msg = "Request saved, but no NGOs available in your area."
        email_content = None

    cursor.execute("SELECT * FROM requests WHERE id = ?", (req_id,))
    new_req = dict(cursor.fetchone())
    conn.close()
    
    return {"message": status_msg, "email_mock": email_content, "request": new_req}

@app.get("/api/restaurants")
def list_restaurants():
    conn = get_db()
    cursor = conn.cursor()
    # Don't return passwords
    cursor.execute("SELECT id, name, location, email, contact FROM restaurants ORDER BY name ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

@app.post("/api/register")
def register_restaurant(req: RegisterRequest):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Check if email exists
        cursor.execute("SELECT id FROM restaurants WHERE email = ?", (req.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
            
        hashed_password = hash_psw(req.password)
        cursor.execute(
            "INSERT INTO restaurants (name, location, email, contact, password) VALUES (?, ?, ?, ?, ?)",
            (req.name, req.location, req.email, req.contact, hashed_password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {"id": user_id, "name": req.name, "location": req.location, "email": req.email, "contact": req.contact, "role": "restaurant"}
    finally:
        conn.close()

@app.post("/api/login")
def login_restaurant(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM restaurants WHERE email = ?", (req.email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    user_dict = dict(user)
    if not verify_psw(req.password, user_dict["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # Return user details without password
    return {
        "id": user_dict["id"],
        "name": user_dict["name"],
        "location": user_dict["location"],
        "email": user_dict["email"],
        "contact": user_dict["contact"],
        "role": "restaurant"
    }

@app.get("/api/ngos")
def list_ngos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, location, email, contact FROM ngos ORDER BY name ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/donations")
def list_donations():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requests ORDER BY id DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    for row in rows:
        row["history"] = json.loads(row["history"])
    return rows

@app.get("/api/respond")
def handle_response(decision: str, requestId: int, request: Request):
    base_url = str(request.base_url).rstrip("/")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requests WHERE id = ?", (requestId,))
    req = cursor.fetchone()
    
    if not req:
        return {"error": "Request not found"}
        
    if req["status"] in ["Accepted"]:
        return {"message": "Request already processed."}
        
    current_ngo = req["ngoAssigned"]
    
    if decision == "accept":
        cursor.execute("UPDATE requests SET status = 'Accepted' WHERE id = ?", (requestId,))
        conn.commit()
        
        # Email Donor that it was accepted
        restaurant_email = req['email']

        # Fetch NGO info so the Restaurant has their contact details
        cursor.execute("SELECT name, email, contact FROM ngos WHERE name = ?", (req['ngoAssigned'],))
        ngo_row = cursor.fetchone()
        if ngo_row:
            ngo_details = dict(ngo_row)
        else:
            ngo_details = {"name": req['ngoAssigned'], "email": "Unknown", "contact": "Unknown"}
            
        
        email_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: #f8fafc; padding: 20px; text-align: center; border-bottom: 3px solid #16a34a;">
                <h1 style="color: #16a34a; margin: 0;">🍲 SURA Connect</h1>
                <p style="margin: 5px 0 0; color: #64748b;">Donation Status Update</p>
            </div>
            
            <div style="padding: 30px;">
                <h2 style="margin-top: 0; color: #0f172a;">Great News! Your Donation was Accepted!</h2>
                <p>Hello {req['restaurant']},</p>
                <p>The NGO <strong>{req['ngoAssigned']}</strong> has officially accepted your surplus food donation request!</p>
                
                <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #16a34a;">Pickup Details</h3>
                    <p><strong>Food:</strong> {req['foodType']} ({req['quantity']} meals)</p>
                    <p><strong>Location:</strong> {req['location']}</p>
                    <hr style="border: none; border-top: 1px solid #cbd5e1; margin: 10px 0;"/>
                    <h3 style="margin-top: 0; color: #0f172a;">NGO Contact Info</h3>
                    <p><strong>NGO:</strong> {ngo_details['name']}</p>
                    <p><strong>Phone:</strong> {ngo_details['contact']}</p>
                    <p><strong>Email:</strong> {ngo_details['email']}</p>
                </div>
                
                <p>Please ensure the food is packaged and ready for their volunteers to pick up before the expiry time.</p>
                <p style="color: #64748b; font-size: 14px; margin-top: 30px;">Thank you for your contribution to reducing food waste!</p>
            </div>
        </body>
        </html>
        """
        send_real_email(req["email"], f"Update on your Food Donation Request : {requestId}", email_html)
        
        log_event(requestId, f"Request ACCEPTED by NGO {current_ngo}.", conn)
        log_event(requestId, f"Email sent to Donor ({req['email']}) with pickup confirmation.", conn)
        msg = f"Successfully accepted by {current_ngo}."
        
    elif decision == "decline":
        # Find another NGO in the same location that hasn't declined yet
        cursor.execute("SELECT * FROM ngos WHERE location = ? AND name != ?", (req["location"], current_ngo))
        next_ngos = cursor.fetchall()
        
        # We need to pick one that hasn't been asked. For simplicity, pick the first one not in history.
        history = json.loads(req["history"])
        contacted_names = [ev["event"].split(" ")[4] for ev in history if "Email sent to NGO" in ev["event"]]
        
        next_ngo_data = {}
        for n in next_ngos:
            if n["name"] not in contacted_names:
                next_ngo_data = dict(n)
                break
                
        if next_ngo_data:
            cursor.execute("UPDATE requests SET status = 'Waiting for Response', ngoAssigned = ? WHERE id = ?", (next_ngo_data["name"], requestId))
            conn.commit()
            
            email_html = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; background: #f3f4f6;">
                <div style="max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px;">
                    <h2 style="color: #16a34a;"> SURA Connect - New Donation Request</h2>
                    <p>Hello <b>{next_ngo_data['name']}</b>,</p>
                    <p>A food donation request is available for pickup near you (Forwarded due to previous decline).</p>
                    <p><b>Restaurant:</b> {req['restaurant']}</p>
                    <p><b>Location:</b> {req['location']}</p>
                    <p><b>Quantity:</b> {req['quantity']} meals</p>
                    <div style="margin-top: 20px;">
                        <a href="{base_url}/api/respond?decision=accept&requestId={requestId}" 
                           style="background: #16a34a; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin-right: 10px;">✅ Accept Pickup</a>
                        <a href="{base_url}/api/respond?decision=decline&requestId={requestId}" 
                           style="background: #dc2626; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">❌ Decline</a>
                    </div>
                </div>
            </div>
            """
            send_real_email(next_ngo_data["email"], "New Food Donation Request - Please Respond", email_html)
            
            log_event(requestId, f"Request DECLINED by {current_ngo}. Forwarding to {next_ngo_data['name']}.", conn)
            log_event(requestId, f"Email sent to NGO {next_ngo_data['name']} requesting pickup.", conn)
            msg = f"Declined. Forwarded to {next_ngo_data['name']}."
        else:
            cursor.execute("UPDATE requests SET status = 'Declined - No NGOs left' WHERE id = ?", (requestId,))
            conn.commit()
            log_event(requestId, f"Request DECLINED by {current_ngo}. No more NGOs available in {req['location']}.", conn)
            log_event(requestId, f"Email sent to Donor ({req['email']}) that no NGOs are available.", conn)
            msg = f"Declined. No other NGOs available."
            msg = f"Declined. No other NGOs available."
            
    conn.close()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Response Recorded</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f3f4f6; margin: 0; }}
            .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }}
            .icon {{ font-size: 48px; margin-bottom: 20px; }}
            h1 {{ color: #111827; font-size: 24px; margin-bottom: 10px; }}
            p {{ color: #4b5563; line-height: 1.5; }}
            .btn {{ margin-top: 20px; display: inline-block; padding: 10px 20px; background: #16a34a; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">{'' if decision == 'accept' else ''}</div>
            <h1>Action Recorded successfully!</h1>
            <p>{msg}</p>
            <p>You can now safely close this window.</p>
            <a href="{base_url}" class="btn">View Live Dashboard</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/")
def get_index():
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

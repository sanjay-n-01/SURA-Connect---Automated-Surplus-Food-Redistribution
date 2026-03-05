# SURA Connect 🍲

SURA Connect is a web application designed to combat food waste by intelligently routing surplus food from restaurants to nearby NGOs exactly when they need it most.

## 🚀 Features
- **Restaurant Portal**: A secure portal for restaurants to specify the type and quantity of their surplus food, and request a pickup.
- **NGO Portal**: A secure portal for NGOs to log in, view live food donation requests in their area, and accept or decline pickups. NGOs can also make bulk food requests that are broadcasted to all local restaurants.
- **Intelligent Routing**: The backend automatically assigns the food donation to the most optimal NGO based on location, and falls back to other NGOs if declined.
- **Automated Email Notifications**: Real-time email alerts are sent to NGOs to request a pickup, and confirmation emails are sent back to the restaurant containing the NGO's contact details once accepted.
- **Secure Authentication**: Uses SHA-256 salted hashing for secure password storage.

## 🛠️ Tech Stack
- **Frontend**: HTML5, React via CDN, TailwindCSS
- **Backend**: Python, FastAPI
- **Database**: SQLite (Auto-generated on startup)
- **Authentication**: Native Python `hashlib`

## 🏃‍♂️ How to Run Locally

### Prerequisites
1. Python 3.8+ installed on your machine.
2. A valid Gmail account (for the App Password to send emails).

### Setup Instructions
1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/sura-connect.git
   cd sura-connect
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your Environment Variables (Optional - for real emails)**
   To allow the app to send real emails to NGOs, you must set these environment variables on your machine (or just edit them directly in `main.py`):
   - `SENDER_EMAIL`: Your full Gmail address.
   - `SENDER_PASSWORD`: Your 16-character Google App Password.

4. **Start the Server:**
   You can start the backend easily using the provided batch file:
   ```bash
   run_server.bat
   ```
   *Alternatively, run: `python -m uvicorn main:app --reload`*

5. **Open the App:**
   Navigate your browser to: `http://localhost:8000`


## 🔐 Built With Security in Mind
The project uses `hashlib.pbkdf2_hmac` with dynamic salts to securely encrypt user passwords before they ever touch the SQLite database.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!

@echo off
echo Starting SURA Connect Backend API...
echo Please wait. Once the server starts, open your browser and go to:
echo http://127.0.0.1:8000
echo.
python -m uvicorn main:app --reload
pause

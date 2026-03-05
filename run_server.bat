@echo off
echo Starting SURA Connect Backend API...
echo Please wait. Once the server starts, open your browser and go to:
echo http://localhost:8000
echo.
python -m uvicorn main:app --reload
pause

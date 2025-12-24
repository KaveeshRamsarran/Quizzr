@echo off
echo Starting Quizzr Backend and Frontend...
echo.

REM Start backend in new window
start "Quizzr Backend" cmd /k "cd /d %~dp0backend && ..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002"

REM Wait a bit for backend to start
timeout /t 3 /nobreak > nul

REM Start frontend in new window
start "Quizzr Frontend" cmd /k "cd /d %~dp0frontend && node node_modules\vite\bin\vite.js"

echo.
echo ========================================
echo Quizzr servers are starting...
echo ========================================
echo Backend: http://127.0.0.1:8002
echo Frontend: http://localhost:3000
echo ========================================
echo.
echo Press any key to exit this window (servers will keep running)
pause > nul

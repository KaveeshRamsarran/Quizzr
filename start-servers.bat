@echo off
setlocal
cd /d "%~dp0"
echo Starting Quizzr...
echo.

REM ---- Backend: create the virtual environment on first run ----
if not exist "backend\.venv\Scripts\python.exe" (
  echo Setting up the Python environment ^(first run only^)...
  py -3 -m venv backend\.venv || python -m venv backend\.venv
  backend\.venv\Scripts\python.exe -m pip install --upgrade pip >nul
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || goto :error
)

REM ---- Frontend: install packages on first run ----
if not exist "frontend\node_modules" (
  echo Installing frontend packages ^(first run only^)...
  pushd frontend
  call npm install || goto :error
  popd
)

start "Quizzr API" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002"
timeout /t 3 /nobreak > nul
start "Quizzr Web" cmd /k "cd /d %~dp0frontend && npx vite --port 3000"
timeout /t 4 /nobreak > nul
start "" http://localhost:3000

echo.
echo   App:       http://localhost:3000
echo   API docs:  http://127.0.0.1:8002/docs
echo.
echo Close the two server windows to stop Quizzr.
exit /b 0

:error
echo.
echo Setup failed. See the messages above.
pause
exit /b 1

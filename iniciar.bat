@echo off
REM Inicia o Poker Acessível. Requer Python 3.10+.
cd /d "%~dp0"
if not exist venv (
  python -m venv venv
  venv\Scripts\python -m pip install --upgrade pip
  venv\Scripts\python -m pip install -r requirements.txt
)
echo.
echo   Poker Acessivel em http://localhost:5000
echo   (pressione Ctrl+C para encerrar)
echo.
venv\Scripts\python -m server.app
pause

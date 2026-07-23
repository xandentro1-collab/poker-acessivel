@echo off
chcp 65001 >nul
REM Sobe o servidor e mostra o endereco que os testadores da MESMA rede Wi-Fi usam.
cd /d "%~dp0"
if not exist venv (
  python -m venv venv
  venv\Scripts\python -m pip install --upgrade pip
  venv\Scripts\python -m pip install -r requirements.txt
)
echo.
echo ============================================================
echo   POKER ACESSIVEL - modo teste com amigos (rede local)
echo ============================================================
echo.
echo   Voce, neste PC, abre:   http://localhost:5000
echo.
echo   Testadores na MESMA rede Wi-Fi abrem um destes enderecos:
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do echo       http://%%a:5000
echo.
echo   (Se nao funcionar, veja o DEPLOY.md: firewall ou use um tunel)
echo ============================================================
echo.
venv\Scripts\python -m server.app
pause

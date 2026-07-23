@echo off
chcp 65001 >nul
REM ============================================================
REM  Poker Acessivel - modo SEMPRE LIGADO (24 horas)
REM  Sobe o servidor e o reinicia automaticamente se cair.
REM  Beta fechado ligado (cadastro exige convite).
REM ============================================================
cd /d "%~dp0"

if not exist venv (
  python -m venv venv
  venv\Scripts\python -m pip install --upgrade pip
  venv\Scripts\python -m pip install -r requirements.txt
)

REM Beta fechado: novos cadastros exigem codigo de convite.
set POKER_EXIGIR_CONVITE=1
REM Seu e-mail vira administrador automaticamente ao cadastrar.
set POKER_ADMIN_EMAILS=xandentro1@gmail.com

REM Se voce baixar o cloudflared.exe para esta pasta, um tunel publico
REM (link https) sobe junto automaticamente. Sem ele, roda so na rede local.
if exist cloudflared.exe (
  echo Subindo tunel publico do Cloudflare...
  start "tunel-cloudflare" cloudflared.exe tunnel --url http://localhost:5000
)

echo.
echo   Poker Acessivel SEMPRE LIGADO em http://localhost:5000
echo   (feche esta janela para parar)
echo.

:loop
venv\Scripts\python -m server.app
echo.
echo [%date% %time%] O servidor parou. Reiniciando em 5 segundos...
timeout /t 5 /nobreak >nul
goto loop

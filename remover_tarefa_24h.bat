@echo off
chcp 65001 >nul
REM Remove a tarefa de inicio automatico do servidor.
schtasks /Delete /TN "PokerAcessivel24h" /F
echo.
echo   Tarefa removida. O servidor nao inicia mais sozinho no login.
echo.
pause

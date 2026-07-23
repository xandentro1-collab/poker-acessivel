@echo off
chcp 65001 >nul
REM Registra uma tarefa do Windows que sobe o servidor a cada login,
REM para ele ficar ligado 24h sem voce precisar abrir nada manualmente.
cd /d "%~dp0"
schtasks /Create /TN "PokerAcessivel24h" /TR "\"%~dp0online_24h.bat\"" /SC ONLOGON /RL LIMITED /F
echo.
echo   Tarefa "PokerAcessivel24h" criada.
echo   O servidor iniciara sozinho toda vez que voce logar no Windows.
echo   Para iniciar agora sem reiniciar, rode: online_24h.bat
echo   Para remover, rode: remover_tarefa_24h.bat
echo.
pause

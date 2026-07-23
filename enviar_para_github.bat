@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   ENVIAR O PROJETO PARA O GITHUB
echo ============================================================
echo.
echo   ANTES de continuar, crie um repositorio VAZIO:
echo     1) abra  https://github.com/new
echo     2) nome do repositorio:  poker-acessivel
echo     3) deixe PUBLICO e NAO marque README / .gitignore / licenca
echo     4) clique em  Create repository
echo.
set /p USUARIO="Digite seu usuario do GitHub e tecle Enter: "
if "%USUARIO%"=="" (
  echo.
  echo   Nenhum usuario informado. Saindo sem fazer nada.
  echo.
  pause
  exit /b
)

REM Se por algum motivo ainda nao for um repositorio, inicializa.
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo   Inicializando repositorio...
  git init -b main
  git config user.email "xandentro1@gmail.com"
  git config user.name "Xande"
)

REM Salva (commita) qualquer mudanca ainda nao salva, para ir tudo atualizado.
git add -A
git diff --cached --quiet
if errorlevel 1 (
  echo   Salvando alteracoes pendentes...
  git commit -m "Atualizacoes antes de enviar ao GitHub"
)

echo.
echo   Conectando ao seu GitHub...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/%USUARIO%/poker-acessivel.git
git branch -M main

echo   Enviando... (pode abrir uma janela pedindo para entrar no GitHub)
git push -u origin main
set PUSH_ERR=%errorlevel%

echo.
if %PUSH_ERR% neq 0 (
  echo   *** Algo deu errado no envio. Verifique:
  echo       - o repositorio existe em: github.com/%USUARIO%/poker-acessivel ?
  echo       - ele foi criado VAZIO (sem README)?
  echo       - voce concluiu o login quando o GitHub pediu?
  echo   Corrija e rode este arquivo de novo.
) else (
  echo   ============================================================
  echo   PRONTO! Seu codigo esta em:
  echo       https://github.com/%USUARIO%/poker-acessivel
  echo.
  echo   Proximo passo: abra o DEPLOY.md e clique em "Deploy to Render"
  echo   para publicar 24 horas no ar.
  echo   ============================================================
)
echo.
pause

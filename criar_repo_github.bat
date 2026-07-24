@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   CRIAR O REPOSITORIO NO GITHUB (o mais automatico possivel)
echo ============================================================
echo.
echo   Este script instala o GitHub CLI, pede seu login UMA vez
echo   (abre o navegador) e depois cria o repositorio e envia o
echo   codigo sozinho. So o login e' seu - eu nao guardo sua senha.
echo.
pause

REM ---- 1. Garante o GitHub CLI (gh) instalado ----
where gh >nul 2>&1
if errorlevel 1 (
  echo.
  echo   Instalando o GitHub CLI... pode levar 1 a 2 minutos.
  winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
  echo.
  echo   ============================================================
  echo   >>> FECHE esta janela e abra o "criar_repo_github.bat" DE NOVO.
  echo       (o Windows precisa reconhecer o programa recem-instalado)
  echo   ============================================================
  pause
  exit /b
)

REM ---- 2. Login na sua conta (abre o navegador na primeira vez) ----
gh auth status >nul 2>&1
if errorlevel 1 (
  echo.
  echo   Vamos conectar a SUA conta do GitHub.
  echo   Escolha:  GitHub.com  ^>  HTTPS  ^>  Login with a web browser
  echo.
  gh auth login
)

REM ---- 3. Garante que tudo esta salvo (commit) ----
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  git init -b main
  git config user.email "xandentro1@gmail.com"
  git config user.name "Xande"
)
git add -A
git diff --cached --quiet
if errorlevel 1 git commit -m "Atualizacoes antes de criar o repositorio"

REM ---- 4. Cria o repositorio e envia o codigo ----
echo.
echo   Criando o repositorio 'poker-acessivel' e enviando o codigo...
gh repo create poker-acessivel --public --source=. --remote=origin --push
set CRIAR_ERR=%errorlevel%

echo.
if %CRIAR_ERR% neq 0 (
  echo   *** Nao deu certo. Motivos comuns:
  echo       - ja existe um repo 'poker-acessivel' na sua conta
  echo         ^(nesse caso use o  enviar_para_github.bat^)
  echo       - o login nao foi concluido
) else (
  echo   ============================================================
  echo   PRONTO! Repositorio criado e codigo enviado com sucesso.
  echo   Vou abrir a pagina dele no navegador...
  echo   Proximo passo: DEPLOY.md  ^>  botao "Deploy to Render".
  echo   ============================================================
  gh repo view --web
)
echo.
pause

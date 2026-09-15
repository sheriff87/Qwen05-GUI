@echo off
setlocal EnableExtensions

title Qwen05-GUI V4 - Lanceur Gratuit
cd /d "%~dp0"

cls
echo ============================================================
echo                 QWEN05-GUI V4
echo              LANCEUR GRATUIT UNIQUEMENT
echo ============================================================
echo.
echo [INFO] Dossier : %CD%
echo [INFO] Mode     : FREE_ONLY
echo [INFO] Adresse  : http://127.0.0.1:7860
echo.
echo Ce lanceur verifie Python, Ollama et la version de l'application.
echo Les fonctions payantes ne sont pas activees dans cette V4.
echo ============================================================
echo.

REM ------------------------------------------------------------
REM 1. Python
REM ------------------------------------------------------------
echo [1/4] Verification de Python...
where python >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'a pas ete trouve dans PATH.
    echo Installe Python ou ajoute-le au PATH.
    echo.
    pause
    exit /b 1
)
python --version
if errorlevel 1 (
    echo [ERREUR] Python ne peut pas etre execute.
    echo.
    pause
    exit /b 1
)
echo [OK] Python est disponible.
echo.

REM ------------------------------------------------------------
REM 2. Ollama
REM ------------------------------------------------------------
echo [2/4] Verification d'Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
    echo [AVERTISSEMENT] Ollama n'est pas trouve dans PATH.
    echo Qwen05-GUI peut tout de meme continuer avec OpenRouter Free.
) else (
    echo [OK] Ollama est installe.
)
echo.

REM ------------------------------------------------------------
REM 3. Version V4
REM ------------------------------------------------------------
echo [3/4] Recherche de Qwen05-GUI V4...
if exist "gradio_app_V4.py" (
    set "APP_FILE=gradio_app_V4.py"
    echo [OK] V4 detectee : %APP_FILE%
    goto APP_FOUND
)

echo [ERREUR] gradio_app_V4.py est introuvable.
echo Cette V4 ne remplace pas la version stable existante.
echo.
pause
exit /b 1

:APP_FOUND

echo.
echo ============================================================
echo                 DEMARRAGE QWEN05-GUI V4
echo ============================================================
echo.
echo Application : %APP_FILE%
echo Mode        : GRATUIT UNIQUEMENT
echo URL         : http://127.0.0.1:7860
echo.
echo Pour arreter l'application : CTRL+C
echo ============================================================
echo.

REM ------------------------------------------------------------
REM 4. Lancement
REM ------------------------------------------------------------
echo [4/4] Lancement de Gradio...
echo.
python "%APP_FILE%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo ============================================================
echo                 QWEN05-GUI ARRETE
echo ============================================================
echo Code de sortie : %EXIT_CODE%
echo.

if not "%EXIT_CODE%"=="0" (
    echo [ERREUR] L'application s'est arretee avec une erreur.
    echo Consulte les messages affiches ci-dessus.
) else (
    echo [OK] Application arretee normalement.
)
echo.
pause
endlocal

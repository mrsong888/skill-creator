@echo off
REM Agent Skill Extension - Windows Installer
REM Installs the Chrome extension via registry policy

setlocal EnableDelayedExpansion

set "EXTENSION_DIR=%LOCALAPPDATA%\AgentSkillExtension"
set "BACKEND_URL=%~1"
if "%BACKEND_URL%"=="" set "BACKEND_URL=http://localhost:8001"

echo === Agent Skill Extension Installer (Windows) ===
echo.

REM Copy extension files
echo [1/3] Copying extension files...
if exist "%EXTENSION_DIR%" rmdir /s /q "%EXTENSION_DIR%"
mkdir "%EXTENSION_DIR%"
xcopy /E /I /Q "%~dp0..\..\frontend\dist\*" "%EXTENSION_DIR%\"
echo   -^> Installed to: %EXTENSION_DIR%

REM Write managed config
echo [2/3] Writing configuration...
set "CONFIG_DIR=%APPDATA%\agent-skill-extension"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
(
echo {
echo   "backend_url": "%BACKEND_URL%"
echo }
) > "%CONFIG_DIR%\config.json"
echo   -^> Backend URL: %BACKEND_URL%

REM Register extension via Chrome policy
echo [3/3] Registering Chrome extension...
echo   Note: For auto-install via policy, run this as Administrator.
echo   Otherwise, load manually in chrome://extensions

echo.
echo === Installation complete ===
echo Please restart Chrome to load the extension.
echo Or load manually: chrome://extensions -^> Load unpacked -^> %EXTENSION_DIR%

pause

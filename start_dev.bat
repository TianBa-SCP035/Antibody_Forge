@echo off
setlocal

rem Windows local dev: start_dev.bat [restart^|stop^|status]; no argument means restart.
if not defined CONDA_ENV set "CONDA_ENV=Bender"
set "ROOT=%~dp0"
set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=restart"
if /i "%ACTION%"=="start" set "ACTION=restart"

if /i "%ACTION%"=="status" goto status
if /i "%ACTION%"=="stop" goto stop
if /i "%ACTION%"=="restart" goto stop
echo Usage: %~nx0 [restart^|stop^|status]
exit /b 2

:status
netstat -ano | findstr /R /C:":8888 .*LISTENING" /C:":5555 .*LISTENING" /C:":18765 .*LISTENING" || echo Backend 8888, frontend 5555 and pet-proxy 18765 are not running.
exit /b 0

:stop
taskkill /FI "WINDOWTITLE eq Antibody Forge Backend*" /T /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq Antibody Forge Frontend*" /T /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq Antibody Forge Pet Proxy*" /T /F >nul 2>nul
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8888 .*LISTENING" /C:":5555 .*LISTENING" /C:":18765 .*LISTENING"') do (
  taskkill /PID %%P /T /F >nul 2>nul
)
if /i "%ACTION%"=="stop" (
  echo Stopped backend 8888, frontend 5555 and pet-proxy 18765.
  exit /b 0
)

call conda activate %CONDA_ENV%
python "%ROOT%ensure_deps.py"
if errorlevel 1 exit /b 1

start "Antibody Forge Backend" cmd /k "pushd ""%ROOT%bbctg_vita_server"" && call conda activate %CONDA_ENV% && python server.py"
if exist "%ROOT%pet-proxy\server.py" start "Antibody Forge Pet Proxy" cmd /k "pushd ""%ROOT%pet-proxy"" && call conda activate %CONDA_ENV% && python server.py"
timeout /t 1 /nobreak >nul
start "Antibody Forge Frontend" cmd /k "pushd ""%ROOT%bbctg_vita_web"" && pnpm -F @bbctg/antibody-vita run dev"

endlocal

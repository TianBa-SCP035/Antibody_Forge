@echo off
setlocal

set "CONDA_ENV=Bender"
set "ROOT=%~dp0"

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8888 .*LISTENING" /C:":5777 .*LISTENING"') do (
  taskkill /PID %%P /T /F >nul 2>nul
)

start "Antibody Forge Backend" cmd /k "pushd ""%ROOT%bbctg_vita_server"" && call conda activate %CONDA_ENV% && python server.py"
timeout /t 1 /nobreak >nul
start "Antibody Forge Frontend" cmd /k "pushd ""%ROOT%bbctg_vita_web"" && pnpm -F @bbctg/antibody-vita run dev"

endlocal

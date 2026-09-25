@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>&1
if errorlevel 1 (
  echo Beamloom needs Node.js 22 or newer. Install the LTS version from https://nodejs.org/
  echo Then double-click Start Beamloom.bat again.
  pause
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo npm was not found. Reinstall Node.js from https://nodejs.org/
  pause
  exit /b 1
)
if not exist "node_modules\vite\bin\vite.js" (
  echo Installing Beamloom dependencies for the first run...
  call npm ci
  if errorlevel 1 (
    echo Installation failed. Check your internet connection and try again.
    pause
    exit /b 1
  )
)
echo Starting Beamloom at http://127.0.0.1:4173/
start "" /min powershell -NoProfile -Command "$url='http://127.0.0.1:4173/'; for($i=0; $i -lt 60; $i++) { try { Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2 | Out-Null; Start-Process $url; break } catch { Start-Sleep -Milliseconds 500 } }"
call npm run dev
echo Beamloom has stopped. Close this window or press any key.
pause >nul

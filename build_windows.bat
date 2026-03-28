@echo off
setlocal

echo ========================================
echo   VideoDownloader Windows Build Script
echo ========================================
echo.

cd /d "%~dp0"

echo [1/5] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller
if errorlevel 1 goto :error

echo [2/5] Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.egg-info rmdir /s /q *.egg-info

echo [3/5] Building application...
pyinstaller VideoDownloader.spec --noconfirm
if errorlevel 1 goto :error

echo [4/5] Verifying output...
if not exist "dist\VideoDownloader.exe" (
    echo Error: Build failed - VideoDownloader.exe not found
    exit /b 1
)

echo [5/5] Getting size...
for %%A in ("dist\VideoDownloader.exe") do set SIZE=%%~zA
set /a SIZE_MB=%SIZE% / 1048576

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo Output: dist\VideoDownloader.exe
echo Size: %SIZE_MB% MB
echo.
echo To run the app:
echo   dist\VideoDownloader.exe
echo.
goto :end

:error
echo.
echo ========================================
echo   Build Failed!
echo ========================================
exit /b 1

:end
endlocal

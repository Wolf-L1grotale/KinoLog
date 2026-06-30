@echo off
setlocal enabledelayedexpansion

echo ========================================
echo    KinoLog Android Builder
echo ========================================
echo.

:: Check if ANDROID_HOME is set
if not defined ANDROID_HOME (
    echo [ERROR] ANDROID_HOME is not set!
    echo.
    echo Please install Android SDK and set ANDROID_HOME:
    echo.
    echo 1. Download Android Studio from:
    echo    https://developer.android.com/studio
    echo.
    echo 2. Install Android SDK
    echo.
    echo 3. Set ANDROID_HOME environment variable:
    echo    set ANDROID_HOME=C:\Users\%USERNAME%\AppData\Local\Android\Sdk
    echo.
    echo Or add to System Variables:
    echo    Variable: ANDROID_HOME
    echo    Value: C:\Users\%USERNAME%\AppData\Local\Android\Sdk
    echo.
    pause
    exit /b 1
)

echo [INFO] Using Android SDK: %ANDROID_HOME%
echo.

:: Check if SDK exists
if not exist "%ANDROID_HOME%" (
    echo [ERROR] Android SDK not found at: %ANDROID_HOME%
    echo Please verify your Android SDK installation.
    pause
    exit /b 1
)

echo [STEP 1] Copying app files to Android project...

:: Create directories
if not exist "app\src\main\python" mkdir "app\src\main\python"
if not exist "app\src\main\assets" mkdir "app\src\main\assets"
if not exist "app\src\main\assets\templates" mkdir "app\src\main\assets\templates"
if not exist "app\src\main\assets\static" mkdir "app\src\main\assets\static"

:: Copy Python files
echo [INFO] Copying Python files...
copy /Y "..\app.py" "app\src\main\python\" >nul 2>&1
copy /Y "..\database.py" "app\src\main\python\" >nul 2>&1
copy /Y "..\tmdb.py" "app\src\main\python\" >nul 2>&1
copy /Y "..\kinopoisk.py" "app\src\main\python\" >nul 2>&1
copy /Y "..\kinorium.py" "app\src\main\python\" >nul 2>&1
copy /Y "..\backup.py" "app\src\main\python\" >nul 2>&1
copy /Y "..\dropbox_auth.py" "app\src\main\python\" >nul 2>&1
copy /Y "..\images.py" "app\src\main\python\" >nul 2>&1
echo [OK] Python files copied

:: Copy templates
echo [INFO] Copying templates...
xcopy /E /I /Y /Q "..\templates\*" "app\src\main\assets\templates\" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Templates copied
) else (
    echo [WARN] No templates folder found
)

:: Copy static files
echo [INFO] Copying static files...
xcopy /E /I /Y /Q "..\static\*" "app\src\main\assets\static\" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Static files copied
) else (
    echo [WARN] No static folder found
)

:: Copy .env if exists
if exist "..\.env" (
    copy /Y "..\.env" "app\src\main\assets\" >nul 2>&1
    echo [OK] Environment file copied
)
echo.

echo [STEP 2] Generating app icons...
python -c "from PIL import Image, ImageDraw; sizes = {'mipmap-hdpi': 72, 'mipmap-xhdpi': 96, 'mipmap-xxhdpi': 144}; [Image.new('RGBA', (s, s), (30, 30, 30, 255)).save(f'app/src/main/res/{folder}/ic_launcher.png') for folder, s in sizes.items()]"
echo [OK] Icons generated
echo.

echo [STEP 3] Building APK...
echo This may take a few minutes...
echo.

:: Run Gradle build
call gradlew.bat assembleDebug

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo    BUILD SUCCESSFUL!
    echo ========================================
    echo.
    echo APK location:
    echo   app\build\outputs\apk\debug\app-debug.apk
    echo.
    echo To install on device:
    echo   1. Connect Android device via USB
    echo   2. Enable USB Debugging on device
    echo   3. Run: adb install app\build\outputs\apk\debug\app-debug.apk
    echo.
    echo Or copy the APK file to your device and install manually.
    echo.
) else (
    echo.
    echo ========================================
    echo    BUILD FAILED!
    echo ========================================
    echo.
    echo Common issues:
    echo   - Android SDK not installed properly
    echo   - Missing SDK components (API 34, Build Tools)
    echo   - Java not installed or JAVA_HOME not set
    echo.
    echo Check the error messages above for details.
    echo.
)

pause

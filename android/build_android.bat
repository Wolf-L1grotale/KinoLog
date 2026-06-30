@echo off
echo Building KinoLog Android APK...
echo.

if not defined ANDROID_HOME (
    echo ERROR: ANDROID_HOME is not set.
    echo Please install Android SDK and set ANDROID_HOME environment variable.
    echo.
    echo Instructions:
    echo 1. Download Android Studio from https://developer.android.com/studio
    echo 2. Install Android SDK
    echo 3. Set ANDROID_HOME to your SDK location (e.g., C:\Users\%USERNAME%\AppData\Local\Android\Sdk)
    echo.
    pause
    exit /b 1
)

echo Using Android SDK: %ANDROID_HOME%
echo.

echo Step 1: Copying app files to Android assets...
xcopy /E /I /Y "..\templates" "app\src\main\assets\templates" >nul 2>&1
xcopy /E /I /Y "..\static" "app\src\main\assets\static" >nul 2>&1
copy /Y "..\*.py" "app\src\main\assets\" >nul 2>&1
copy /Y "..\requirements.txt" "app\src\main\assets\" >nul 2>&1
copy /Y "..\.env" "app\src\main\assets\" >nul 2>&1

echo Step 2: Building APK...
call gradlew.bat assembleDebug

if %ERRORLEVEL% EQU 0 (
    echo.
    echo === Build successful! ===
    echo APK: app\build\outputs\apk\debug\app-debug.apk
    echo.
    echo Install on device:
    echo adb install app\build\outputs\apk\debug\app-debug.apk
    echo.
) else (
    echo.
    echo === Build failed ===
    echo Check the error messages above.
    echo.
)

pause

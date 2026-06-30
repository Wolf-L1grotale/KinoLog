# KinoLog Android Build Instructions

## Prerequisites

### 1. Install Android Studio
Download and install Android Studio from: https://developer.android.com/studio

### 2. Install Android SDK
After installing Android Studio:
1. Open Android Studio
2. Go to: Tools → SDK Manager
3. Install:
   - Android SDK Platform 34
   - Android SDK Build-Tools 34.0.0
   - Android SDK Command-line Tools
   - Android SDK Platform-Tools

### 3. Set Environment Variables
Set `ANDROID_HOME` to your SDK location:
```
set ANDROID_HOME=C:\Users\%USERNAME%\AppData\Local\Android\Sdk
```

Or add to System Environment Variables:
- Variable: `ANDROID_HOME`
- Value: `C:\Users\YourUsername\AppData\Local\Android\Sdk`

## Building the APK

### Option 1: Using Build Script
```bash
cd android
build_android.bat
```

### Option 2: Using Android Studio
1. Open Android Studio
2. Click "Open an Existing Project"
3. Navigate to `KinoLog\android` folder
4. Wait for Gradle sync to complete
5. Go to: Build → Build Bundle(s) / APK(s) → Build APK(s)
6. APK will be at: `app\build\outputs\apk\debug\app-debug.apk`

### Option 3: Using Command Line
```bash
cd android
gradlew.bat assembleDebug
```

## Installing on Device

### Enable Developer Options
1. Go to: Settings → About Phone
2. Tap "Build Number" 7 times
3. Go back to Settings → Developer Options
4. Enable "USB Debugging"

### Install APK
```bash
adb install app\build\outputs\apk\debug\app-debug.apk
```

## How It Works

The Android app:
1. Starts a Python FastAPI server in the background
2. Uses Chaquopy to run Python code on Android
3. Opens a WebView to display the web interface
4. The server runs on localhost:8000

## Files Structure

```
android/
├── build.gradle              # Project-level build config
├── settings.gradle           # Project settings
├── gradle.properties         # Gradle properties
├── build_android.bat         # Build script
├── README.md                 # This file
└── app/
    ├── build.gradle          # App-level build config
    ├── proguard-rules.pro    # ProGuard rules
    └── src/main/
        ├── AndroidManifest.xml
        ├── java/com/kinolog/app/
        │   └── MainActivity.java
        ├── python/
        │   └── server.py     # Python server for Android
        ├── res/
        │   ├── layout/
        │   │   └── activity_main.xml
        │   ├── values/
        │   │   ├── strings.xml
        │   │   └── styles.xml
        │   └── mipmap-*/     # App icons
        └── assets/           # App files (copied during build)
```

## Troubleshooting

### "ANDROID_HOME is not set"
- Ensure Android SDK is installed
- Set the environment variable as described above

### Build fails with "Could not find com.chaquo.python"
- Ensure you have internet connection
- Gradle will download dependencies automatically

### App crashes on start
- Check logcat for errors: `adb logcat -s KinoLog`
- Ensure all Python files are copied to assets folder

### WebView shows blank page
- The Python server may take a few seconds to start
- The app automatically waits and retries

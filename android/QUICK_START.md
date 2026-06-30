# KinoLog Android - Быстрый старт

## Установка Android SDK

### Шаг 1: Установите Android Studio
1. Скачайте Android Studio: https://developer.android.com/studio
2. Запустите установщик
3. Следуйте инструкциям установщика

### Шаг 2: Установите компоненты SDK
1. Откройте Android Studio
2. Перейдите: Tools → SDK Manager
3. Установите:
   - Android SDK Platform 34
   - Android SDK Build-Tools 34.0.0
   - Android SDK Command-line Tools
   - Android SDK Platform-Tools

### Шаг 3: Установите переменные среды
Откройте командную строку и выполните:
```cmd
set ANDROID_HOME=C:\Users\%USERNAME%\AppData\Local\Android\Sdk
```

Или добавьте в системные переменные:
- Переменная: `ANDROID_HOME`
- Значение: `C:\Users\ВашеИмя\AppData\Local\Android\Sdk`

## Сборка APK

### Вариант 1: Используйте скрипт сборки
```cmd
cd C:\Users\Admin\Documents\project\KinoLog\android
build.bat
```

### Вариант 2: Используйте Android Studio
1. Откройте Android Studio
2. Нажмите "Open an Existing Project"
3. Перейдите в папку `KinoLog\android`
4. Дождитесь завершения синхронизации Gradle
5. Перейдите: Build → Build Bundle(s) / APK(s) → Build APK(s)
6. APK будет位于: `app\build\outputs\apk\debug\app-debug.apk`

### Вариант 3: Используйте командную строку
```cmd
cd C:\Users\Admin\Documents\project\KinoLog\android
gradlew.bat assembleDebug
```

## Установка на устройство

### Включите отладку по USB
1. Перейдите: Настройки → О телефоне
2. Нажмите "Номер сборки" 7 раз
3. Вернитесь в Настройки → Для разработчиков
4. Включите "Отладка по USB"

### Установите APK
```cmd
adb install app\build\outputs\apk\debug\app-debug.apk
```

## Как это работает

Android приложение:
1. Запускает Python FastAPI сервер в фоновом режиме
2. Использует Chaquopy для запуска Python кода на Android
3. Открывает WebView для отображения веб-интерфейса
4. Сервер работает на localhost:8000

## Решение проблем

### "ANDROID_HOME is not set"
- Убедитесь, что Android SDK установлен
- Установите переменную среды как описано выше

### Сборка завершается ошибкой
- Проверьте подключение к интернету
- Gradle автоматически загрузит зависимости

### Приложение падает при запуске
- Проверьте logcat для ошибок: `adb logcat -s KinoLog`
- Убедитесь, что все Python файлы скопированы в assets

### WebView показывает пустую страницу
- Python сервер может запускаться несколько секунд
- Приложение автоматически ждет и повторяет попытку

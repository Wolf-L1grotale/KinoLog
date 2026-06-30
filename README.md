<div align="center">

# 🎬 KinoLog

### Трекер фильмов, сериалов и аниме

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

**KinoLog** — веб-приложение для отслеживания просмотренных фильмов, сериалов и аниме. Ищет контент через несколько API, ведёт статистику и автоматически сохраняет бэкапы в Dropbox.

## Возможности

| | |
|---|---|
| 🔍 **Мультиисточники** | Поиск через OMDb, KinoPoisk, Kinorium, Shikimori |
| 🎬 **Фильмы, сериалы, аниме** | Всё в одной коллекции |
| 🏷️ **Статусы** | Смотрю · Просмотрено · В планах · Брошено |
| 📊 **Фильтрация** | Быстрый фильтр по типу и статусу |
| 📈 **Прогресс** | Отслеживание текущего сезона и серии |
| 🖼️ **Постеры** | Локальное хранение постеров и бэкдропов |
| 💬 **Заметки** | Личные заметки к каждому тайтлу |
| 💾 **Бэкапы** | Автоматическое копирование в Dropbox ежедневно в 03:00 |
| 🔗 **Ссылки** | Поддержка ссылок IMDB, Kinopoisk, Kinorium, Shikimori |
| 📱 **Android** | Нативное приложение для Android |

## Установка

### Windows (.exe)

Скачайте готовый `.exe` файл из [Releases](https://github.com/username/kinolog/releases) или соберите самостоятельно:

```bash
build.bat
```

Executable будет в папке `dist/KinoLog.exe`.

### Android (APK)

Скачайте `.apk` файл из [Releases](https://github.com/username/kinolog/releases) или соберите:

```bash
cd android
build.bat
```

### Из исходников

#### 1. Клонируйте репозиторий

```bash
git clone https://github.com/username/kinolog.git
cd kinolog
```

#### 2. Установите зависимости

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

#### 3. Настройте переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

| Переменная | Описание | Обязательность |
|------------|----------|----------------|
| `OMDB_API_KEY` | Ключ [OMDb API](https://www.omdbapi.com/apikey.aspx) | Опционально |
| `KINOPOISK_API_TOKEN` | Токен [api.kinopoisk.dev](https://api.kinopoisk.dev/) | Опционально |
| `DROPBOX_APP_KEY` | App Key приложения [Dropbox](https://www.dropbox.com/developers/apps) | Опционально |
| `DROPBOX_APP_SECRET` | App Secret приложения Dropbox | Опционально |

> Приложение работает без API-ключей — поиск будет идти через доступные источники.

#### 4. Настройка Dropbox (опционально)

Для автоматических бэкапов в Dropbox:

1. Создайте приложение на [Dropbox Developer Console](https://www.dropbox.com/developers/apps)
2. Выберите "Scoped access" → "Full Dropbox" → назовите приложение
3. Вкладка "Permissions": включите `files.content.write` и `files.content.read`
4. Вкладка "Settings": скопируйте **App key** и **App secret** в `.env`:

```
DROPBOX_APP_KEY=ваш_app_key
DROPBOX_APP_SECRET=ваш_app_secret
```

5. В настройках приложения укажите **Redirect URI**: `http://localhost:8000/api/dropbox/callback`
6. Запустите приложение и нажмите "Подключить Dropbox" на главной странице

Токены сохраняются автоматически и обновляются.

#### 5. Запустите

```bash
python app.py
```

Откройте http://localhost:8000

## Сборка

### Windows exe

```bash
python generate_icon.py
build.bat
```

### Android APK

Требуется:
- [Android Studio](https://developer.android.com/studio)
- Android SDK (API 36)
- Java 21

```bash
set ANDROID_HOME=C:\Users\%USERNAME%\AppData\Local\Android\Sdk
set JAVA_HOME=C:\Program Files\Java\jdk-21
cd android
gradlew.bat assembleDebug
```

APK: `android/app/build/outputs/apk/debug/app-debug.apk`

## Структура проекта

```
kinolog/
├── app.py              # FastAPI приложение, маршруты
├── database.py         # SQLite: создание, запросы, миграции
├── tmdb.py             # Интеграция с OMDb, Shikimori
├── kinopoisk.py        # Парсер KinoPoisk API
├── kinorium.py         # Парсер Kinorium (Playwright)
├── backup.py           # Резервное копирование в Dropbox
├── dropbox_auth.py     # Dropbox OAuth2 авторизация
├── images.py           # Загрузка и хранение изображений
├── requirements.txt    # Зависимости Python
├── .env.example        # Пример переменных окружения
├── build.bat           # Сборка exe
├── KinoLog.spec        # PyInstaller конфигурация
├── kino.ico            # Иконка приложения
├── main.py             # Точка входа для exe
├── templates/          # Jinja2 шаблоны
│   ├── index.html      # Главная: коллекция, фильтры, статистика
│   ├── search.html     # Поиск тайтлов
│   ├── add.html        # Предпросмотр перед добавлением
│   └── title.html      # Детальная страница тайтла
├── static/
│   ├── css/style.css   # Стили (тёмная тема)
│   └── js/main.js      # Клиентская логика
└── android/            # Android проект
    ├── build.gradle
    ├── app/
    │   └── src/main/
    │       ├── java/   # MainActivity.java
    │       ├── python/ # server.py, sync.py, dropbox_client.py
    │       └── assets/ # Шаблоны и статика
    └── build.bat       # Сборка APK
```

## API

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Главная страница с коллекцией |
| `GET` | `/search?q=...` | Поиск тайтлов |
| `GET` | `/add/preview?...` | Предпросмотр перед добавлением |
| `POST` | `/add` | Добавление тайтла |
| `GET` | `/title/{id}` | Страница тайтла |
| `POST` | `/title/{id}/update` | Обновление статуса |
| `POST` | `/title/{id}/delete` | Удаление тайтла |
| `GET` | `/config` | Страница конфигурации |
| `GET` | `/api/stats` | Статистика коллекции |
| `POST` | `/api/backup` | Триггер бэкапа |
| `GET` | `/api/backup/status` | Статус последнего бэкапа |
| `GET` | `/api/dropbox/status` | Статус подключения Dropbox |
| `GET` | `/api/dropbox/auth` | Получить URL для OAuth авторизации |
| `GET` | `/api/dropbox/callback` | Callback после авторизации |
| `POST` | `/api/dropbox/disconnect` | Отключить Dropbox |
| `POST` | `/api/sync` | Синхронизация с Dropbox |
| `POST` | `/api/config` | Сохранение конфигурации |

## Синхронизация (Android)

Приложение автоматически синхронизирует данные с Dropbox:

- **Первый запуск** — восстановление данных из облака (если есть бэкап)
- **Повторные запуски** — сравнение хешей БД, синхронизация при расхождении
- **Настройка** — через меню "Конфиг" или файл `config/.env`

## Стек

- **Backend:** Python, FastAPI, SQLite, APScheduler
- **Frontend:** Jinja2, CSS (тёмная тема), Vanilla JS
- **API:** OMDb, KinoPoisk, Kinorium, Shikimori
- **Бэкап:** Dropbox API (httpx)
- **Android:** Chaquopy, WebView

## Лицензия

[MIT](LICENSE)

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

## Установка

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/username/kinolog.git
cd kinolog
```

### 2. Установите зависимости

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 3. Настройте переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

| Переменная | Описание | Обязательность |
|------------|----------|----------------|
| `OMDB_API_KEY` | Ключ [OMDb API](https://www.omdbapi.com/apikey.aspx) | Опционально |
| `KINOPOISK_API_TOKEN` | Токен [api.kinopoisk.dev](https://api.kinopoisk.dev/) | Опционально |
| `DROPBOX_ACCESS_TOKEN` | Токен [Dropbox](https://www.dropbox.com/developers/apps) | Опционально |

> Приложение работает без API-ключей — поиск будет идти через доступные источники.

### 4. Запустите

```bash
python app.py
```

Откройте http://localhost:8000

## Структура проекта

```
kinolog/
├── app.py              # FastAPI приложение, маршруты
├── database.py         # SQLite: создание, запросы, миграции
├── tmdb.py             # Интеграция с OMDb, Shikimori
├── kinopoisk.py        # Парсер KinoPoisk API
├── kinorium.py         # Парсер Kinorium (Playwright)
├── backup.py           # Резервное копирование в Dropbox
├── images.py           # Загрузка и хранение изображений
├── requirements.txt    # Зависимости Python
├── .env.example        # Пример переменных окружения
├── templates/          # Jinja2 шаблоны
│   ├── index.html      # Главная: коллекция, фильтры, статистика
│   ├── search.html     # Поиск тайтлов
│   ├── add.html        # Предпросмотр перед добавлением
│   └── title.html      # Детальная страница тайтла
└── static/
    ├── css/style.css   # Стили (тёмная тема)
    └── js/main.js      # Клиентская логика
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
| `GET` | `/api/stats` | Статистика коллекции |
| `POST` | `/api/backup` | Триггер бэкапа |
| `GET` | `/api/backup/status` | Статус последнего бэкапа |

## Скриншоты

<!-- Добавьте скриншоты в папку screenshots/ -->
<!-- ![Главная](screenshots/main.png) -->

## Стек

- **Backend:** Python, FastAPI, SQLite, APScheduler
- **Frontend:** Jinja2, CSS (тёмная тема), Vanilla JS
- **API:** OMDb, KinoPoisk, Kinorium, Shikimori
- **Бэкап:** Dropbox API

## Лицензия

[MIT](LICENSE)

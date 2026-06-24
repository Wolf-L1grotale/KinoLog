# FilmoGraph - Трекер фильмов и сериалов

Веб-приложение для отслеживания просмотренных фильмов и сериалов с интеграцией TMDB API и резервным копированием в Dropbox.

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd filmograf
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения:
```bash
cp .env.example .env
```

Отредактируйте файл `.env` и добавьте ваши API ключи:
- `TMDB_API_KEY` - Получите на [themoviedb.org](https://www.themoviedb.org/settings/api)
- `DROPBOX_ACCESS_TOKEN` - Получите в [Dropbox App Console](https://www.dropbox.com/developers/apps)

4. Запустите приложение:
```bash
python app.py
```

5. Откройте в браузере: http://localhost:8000

## Функционал

- **Поиск** - Поиск фильмов и сериалов по названию или ссылке на TMDB
- **Коллекция** - Добавление тайтлов в персональную коллекцию
- **Отслеживание прогресса** - Указание текущего сезона и серии для сериалов
- **Статусы** - Смотрю, Просмотрено, В планах, Брошено
- **Заметки** - Добавление личных заметок к тайтлам
- **Резервное копирование** - Автоматическое копирование базы данных в Dropbox ежедневно в 03:00

## Структура проекта

```
filmograf/
├── app.py              # Основной файл приложения
├── database.py         # Работа с SQLite
├── tmdb.py            # Интеграция с TMDB API
├── backup.py          # Резервное копирование в Dropbox
├── requirements.txt   # Зависимости
├── .env.example       # Пример переменных окружения
├── templates/         # HTML шаблоны
│   ├── index.html
│   ├── search.html
│   └── title.html
└── static/            # Статические файлы
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## API Endpoints

- `GET /` - Главная страница с коллекцией
- `GET /search?q=query` - Поиск тайтлов
- `POST /add` - Добавление тайтла
- `GET /title/{tmdb_id}` - Страница тайтла
- `POST /title/{tmdb_id}/update` - Обновление статуса
- `POST /title/{tmdb_id}/delete` - Удаление тайтла
- `GET /api/search?q=query` - API поиска
- `POST /api/backup` - Триггер бэкапа
- `GET /api/backup/status` - Статус последнего бэкапа
- `GET /api/stats` - Статистика коллекции

## Лицензия

MIT

import aiosqlite
import os
from datetime import datetime
from typing import Optional, List, Dict

DATABASE_PATH = "filmograf.db"

async def get_db():
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tmdb_id INTEGER UNIQUE NOT NULL,
                imdb_id TEXT,
                title TEXT NOT NULL,
                original_title TEXT,
                media_type TEXT NOT NULL DEFAULT 'movie',
                poster_path TEXT,
                backdrop_path TEXT,
                local_poster_path TEXT,
                local_backdrop_path TEXT,
                overview TEXT,
                release_date TEXT,
                vote_average REAL,
                current_status TEXT NOT NULL DEFAULT 'watching',
                current_season INTEGER DEFAULT 1,
                current_episode INTEGER DEFAULT 1,
                total_seasons INTEGER DEFAULT 0,
                total_episodes INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS backup_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                file_size INTEGER,
                error_message TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS dropbox_tokens (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at REAL,
                account_name TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_title(tmdb_id: int, title: str, original_title: str, media_type: str,
                   poster_path: str, backdrop_path: str, overview: str,
                   release_date: str, vote_average: float,
                   total_seasons: int = 0, total_episodes: int = 0,
                   local_poster_path: str = "", local_backdrop_path: str = "",
                   imdb_id: str = "") -> Dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        try:
            await db.execute("""
                INSERT INTO titles (tmdb_id, imdb_id, title, original_title, media_type, poster_path,
                                   backdrop_path, local_poster_path, local_backdrop_path,
                                   overview, release_date, vote_average,
                                   total_seasons, total_episodes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (tmdb_id, imdb_id, title, original_title, media_type, poster_path,
                  backdrop_path, local_poster_path, local_backdrop_path,
                  overview, release_date, vote_average,
                  total_seasons, total_episodes))
            await db.commit()
            cursor = await db.execute("SELECT * FROM titles WHERE tmdb_id = ?", (tmdb_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
        except aiosqlite.IntegrityError:
            cursor = await db.execute("SELECT * FROM titles WHERE tmdb_id = ?", (tmdb_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_all_titles() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM titles ORDER BY updated_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_title(tmdb_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM titles WHERE tmdb_id = ?", (tmdb_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_title(tmdb_id: int, **kwargs) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        allowed_fields = ['current_status', 'current_season', 'current_episode', 'notes',
                         'local_poster_path', 'local_backdrop_path']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

        if not updates:
            return await get_title(tmdb_id)

        updates['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [tmdb_id]

        await db.execute(f"UPDATE titles SET {set_clause} WHERE tmdb_id = ?", values)
        await db.commit()

        cursor = await db.execute("SELECT * FROM titles WHERE tmdb_id = ?", (tmdb_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def delete_title(tmdb_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM titles WHERE tmdb_id = ?", (tmdb_id,))
        await db.commit()
        return cursor.rowcount > 0

async def search_titles_db(query: str) -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM titles WHERE title LIKE ? OR original_title LIKE ?",
            (f"%{query}%", f"%{query}%")
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def log_backup(status: str, file_size: int = 0, error_message: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO backup_log (status, file_size, error_message) VALUES (?, ?, ?)",
            (status, file_size, error_message)
        )
        await db.commit()

async def get_database_size() -> int:
    return os.path.getsize(DATABASE_PATH) if os.path.exists(DATABASE_PATH) else 0


async def save_dropbox_tokens(access_token: str, refresh_token: str,
                               expires_at: float = None, account_name: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO dropbox_tokens (id, access_token, refresh_token, expires_at, account_name, updated_at)
            VALUES (1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                expires_at = excluded.expires_at,
                account_name = excluded.account_name,
                updated_at = CURRENT_TIMESTAMP
        """, (access_token, refresh_token, expires_at, account_name))
        await db.commit()


async def get_dropbox_tokens() -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM dropbox_tokens WHERE id = 1")
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_dropbox_access_token(access_token: str, expires_at: float = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE dropbox_tokens SET access_token = ?, expires_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (access_token, expires_at))
        await db.commit()


async def delete_dropbox_tokens():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM dropbox_tokens WHERE id = 1")
        await db.commit()

import dropbox
import os
import zipfile
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from database import log_backup, get_database_size, DATABASE_PATH, get_dropbox_tokens, update_dropbox_access_token
import dropbox_auth

load_dotenv()

DROPBOX_BACKUP_FOLDER = "/filmograf_backups"
BACKUP_RETENTION_DAYS = 30
COVERS_DIR = Path("static/covers")


async def _get_dropbox_client():
    tokens = await get_dropbox_tokens()
    if not tokens:
        return None

    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    expires_at = tokens.get("expires_at")

    if dropbox_auth.is_token_expired(expires_at):
        try:
            new_data = dropbox_auth.refresh_access_token(refresh_token)
            access_token = new_data["access_token"]
            new_expires_in = new_data.get("expires_in", 0)
            new_expires_at = time.time() + new_expires_in if new_expires_in else None
            if "refresh_token" in new_data:
                refresh_token = new_data["refresh_token"]
            await update_dropbox_access_token(access_token, new_expires_at)
        except Exception:
            return None

    return dropbox_auth.get_dropbox_client(access_token)


async def backup_to_dropbox() -> dict:
    dbx = await _get_dropbox_client()
    if not dbx:
        return {"status": "skipped", "message": "Dropbox не подключён"}

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"filmograf_backup_{timestamp}.zip"
        local_backup_path = f"./backups/{backup_filename}"
        dropbox_path = f"{DROPBOX_BACKUP_FOLDER}/{backup_filename}"

        os.makedirs("./backups", exist_ok=True)

        with zipfile.ZipFile(local_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(DATABASE_PATH, "filmograf.db")

            if COVERS_DIR.exists():
                for img_file in COVERS_DIR.glob("*.jpg"):
                    zipf.write(img_file, f"covers/{img_file.name}")

        file_size = os.path.getsize(local_backup_path)

        with open(local_backup_path, "rb") as f:
            dbx.files_upload(f.read(), dropbox_path)

        await log_backup("success", file_size)
        cleanup_old_backups(dbx)

        os.remove(local_backup_path)

        return {
            "status": "success",
            "filename": backup_filename,
            "size": file_size,
            "dropbox_path": dropbox_path
        }

    except Exception as e:
        await log_backup("error", error_message=str(e))
        return {"status": "error", "message": str(e)}

def cleanup_old_backups(dbx):
    try:
        files = dbx.files_list_folder(DROPBOX_BACKUP_FOLDER).entries
        cutoff = datetime.now().timestamp() - (BACKUP_RETENTION_DAYS * 86400)

        for file in files:
            if isinstance(file, dropbox.FileMetadata):
                file_time = file.server_modified.timestamp()
                if file_time < cutoff:
                    dbx.files_delete_v2(file.path_lower)
    except Exception:
        pass

async def get_backup_status() -> dict:
    from database import get_db
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM backup_log ORDER BY backup_time DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if row:
            return {
                "last_backup": dict(row)["backup_time"],
                "status": dict(row)["status"],
                "file_size": dict(row)["file_size"]
            }
        return {"last_backup": None, "status": "no_backups", "file_size": 0}
    finally:
        await db.close()

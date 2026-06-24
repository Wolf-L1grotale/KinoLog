import dropbox
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from database import log_backup, get_database_size, DATABASE_PATH

load_dotenv()

DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN", "")
DROPBOX_BACKUP_FOLDER = "/filmograf_backups"
BACKUP_RETENTION_DAYS = 30
COVERS_DIR = Path("static/covers")

async def backup_to_dropbox() -> dict:
    if not DROPBOX_ACCESS_TOKEN:
        return {"status": "skipped", "message": "Dropbox token not configured"}

    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

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

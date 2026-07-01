import os
import zipfile
import time
import json
import io
import hashlib
from datetime import datetime
from pathlib import Path
import dropbox
from database import log_sync, get_dropbox_tokens, update_dropbox_access_token, DATABASE_PATH
import dropbox_auth

SYNC_FILE_NAME = "kinolog_sync.zip"
SYNC_STATE_FILE = "sync_state.json"


def get_sync_state_path():
    return os.path.join(os.path.dirname(os.path.abspath(DATABASE_PATH)), SYNC_STATE_FILE)


def load_sync_state():
    path = get_sync_state_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"last_sync_time": None, "local_hash": None}


def save_sync_state(state):
    with open(get_sync_state_path(), "w") as f:
        json.dump(state, f)


def calculate_db_hash():
    if not os.path.exists(DATABASE_PATH):
        return None
    h = hashlib.md5()
    with open(DATABASE_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_sync_zip():
    covers_dir = os.path.join(os.path.dirname(os.path.abspath(DATABASE_PATH)), "static", "covers")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(DATABASE_PATH, "kinolog.db")
        if os.path.exists(covers_dir):
            for img_file in Path(covers_dir).glob("*.jpg"):
                zipf.write(img_file, f"covers/{img_file.name}")

        metadata = {
            "timestamp": time.time(),
            "device_time": datetime.now().isoformat(),
            "db_hash": calculate_db_hash()
        }
        zipf.writestr("metadata.json", json.dumps(metadata))

    buf.seek(0)
    return buf.read()


def restore_from_sync_zip(zip_bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
        if "kinolog.db" in zipf.namelist():
            with zipf.open("kinolog.db") as db_file:
                with open(DATABASE_PATH, "wb") as out:
                    out.write(db_file.read())

        covers_dir = os.path.join(os.path.dirname(os.path.abspath(DATABASE_PATH)), "static", "covers")
        os.makedirs(covers_dir, exist_ok=True)

        for name in zipf.namelist():
            if name.startswith("covers/") and name.endswith(".jpg"):
                cover_path = os.path.join(os.path.dirname(os.path.abspath(DATABASE_PATH)), name)
                os.makedirs(os.path.dirname(cover_path), exist_ok=True)
                with zipf.open(name) as src:
                    with open(cover_path, "wb") as dst:
                        dst.write(src.read())


async def get_dropbox_client():
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


async def upload_sync_file(dbx):
    zip_bytes = create_sync_zip()

    try:
        dbx.files_upload(zip_bytes, f"/{SYNC_FILE_NAME}", mode=dropbox.files.WriteMode.overwrite)

        state = load_sync_state()
        state["last_sync_time"] = time.time()
        state["local_hash"] = calculate_db_hash()
        save_sync_state(state)

        return {"status": "success", "message": "Данные загружены в облако"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def download_sync_file(dbx):
    try:
        _, res = dbx.files_download(f"/{SYNC_FILE_NAME}")
        return res.content
    except Exception:
        return None


async def force_sync():
    dbx = await get_dropbox_client()
    if not dbx:
        await log_sync("manual", "skipped", "Dropbox не подключён")
        return {"action": "none", "message": "Dropbox не подключён"}

    local_hash = calculate_db_hash()
    remote_data = await download_sync_file(dbx)

    if not remote_data:
        result = await upload_sync_file(dbx)
        await log_sync("manual", "uploaded", result.get("message", "Данные загружены"), local_hash)
        return {"action": "uploaded", "message": "Данные загружены в облако"}

    remote_buf = io.BytesIO(remote_data)
    with zipfile.ZipFile(remote_buf, "r") as zf:
        if "metadata.json" in zf.namelist():
            with zf.open("metadata.json") as f:
                remote_meta = json.loads(f.read())
                remote_hash = remote_meta.get("db_hash")
        else:
            remote_hash = None

    if local_hash == remote_hash:
        await log_sync("manual", "up_to_date", "Данные уже синхронизированы", local_hash, remote_hash)
        return {"action": "up_to_date", "message": "Данные уже синхронизированы"}

    restore_from_sync_zip(remote_data)
    from database import init_db
    await init_db()

    state = load_sync_state()
    state["last_sync_time"] = time.time()
    state["local_hash"] = calculate_db_hash()
    save_sync_state(state)
    await log_sync("manual", "synced", "Данные восстановлены из облака", calculate_db_hash(), remote_hash)
    return {"action": "synced", "message": "Данные восстановлены из облака"}


async def get_sync_status():
    from database import get_sync_status as db_get_sync_status
    return await db_get_sync_status()

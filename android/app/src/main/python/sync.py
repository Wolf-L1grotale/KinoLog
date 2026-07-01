import os
import zipfile
import time
import json
import io
from datetime import datetime
from pathlib import Path
import dropbox_client
import database as db

SYNC_FILE_NAME = "kinolog_sync.zip"
SYNC_STATE_FILE = "sync_state.json"


def get_sync_state_path():
    return os.path.join(os.environ.get("KINOLOG_APP_PATH", "."), SYNC_STATE_FILE)


def load_sync_state():
    path = get_sync_state_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"last_sync_time": None, "local_hash": None}


def save_sync_state(state):
    path = get_sync_state_path()
    with open(path, "w") as f:
        json.dump(state, f)


def calculate_db_hash(db_path):
    if not os.path.exists(db_path):
        return None
    import hashlib
    h = hashlib.md5()
    with open(db_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_sync_zip(db_path):
    app_path = os.environ.get("KINOLOG_APP_PATH", ".")
    covers_dir = os.path.join(app_path, "static", "covers")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(db_path, "kinolog.db")
        if os.path.exists(covers_dir):
            for img_file in Path(covers_dir).glob("*.jpg"):
                zipf.write(img_file, f"covers/{img_file.name}")

        metadata = {
            "timestamp": time.time(),
            "device_time": datetime.now().isoformat(),
            "db_hash": calculate_db_hash(db_path)
        }
        zipf.writestr("metadata.json", json.dumps(metadata))

    buf.seek(0)
    return buf.read()


def restore_from_sync_zip(db_path, zip_bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zipf:
        if "kinolog.db" in zipf.namelist():
            with zipf.open("kinolog.db") as db_file:
                with open(db_path, "wb") as out:
                    out.write(db_file.read())

        app_path = os.environ.get("KINOLOG_APP_PATH", ".")
        covers_dir = os.path.join(app_path, "static", "covers")
        os.makedirs(covers_dir, exist_ok=True)

        for name in zipf.namelist():
            if name.startswith("covers/") and name.endswith(".jpg"):
                cover_path = os.path.join(app_path, name)
                os.makedirs(os.path.dirname(cover_path), exist_ok=True)
                with zipf.open(name) as src:
                    with open(cover_path, "wb") as dst:
                        dst.write(src.read())


async def async_get_dropbox_client():
    from database import get_dropbox_tokens, update_dropbox_access_token

    tokens = await get_dropbox_tokens()
    if not tokens:
        return None

    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    expires_at = tokens.get("expires_at")

    if dropbox_client.is_token_expired(expires_at):
        try:
            new_data = dropbox_client.refresh_access_token(refresh_token)
            access_token = new_data["access_token"]
            new_expires_in = new_data.get("expires_in", 0)
            new_expires_at = time.time() + new_expires_in if new_expires_in else None
            if "refresh_token" in new_data:
                refresh_token = new_data["refresh_token"]
            await update_dropbox_access_token(access_token, new_expires_at)
        except Exception:
            return None

    return dropbox_client.DropboxClient(access_token)


async def upload_sync_file(dbx, db_path):
    zip_bytes = create_sync_zip(db_path)

    try:
        dbx.files_upload(zip_bytes, f"/{SYNC_FILE_NAME}", mode="overwrite")

        state = load_sync_state()
        state["last_sync_time"] = time.time()
        state["local_hash"] = calculate_db_hash(db_path)
        save_sync_state(state)

        return {"status": "success", "message": "Данные загружены в облако"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def download_sync_file(dbx):
    try:
        zip_bytes = dbx.files_download(f"/{SYNC_FILE_NAME}")
        return zip_bytes
    except Exception:
        return None


async def sync_on_startup(db_path):
    state = load_sync_state()
    local_hash = calculate_db_hash(db_path)
    was_launched_before = state.get("last_sync_time") is not None

    dbx = await async_get_dropbox_client()
    if not dbx:
        await db.log_sync("startup", "skipped", "Dropbox не подключён")
        return {"action": "none", "message": "Dropbox не подключён"}

    if not was_launched_before:
        remote_data = await download_sync_file(dbx)
        if remote_data:
            restore_from_sync_zip(db_path, remote_data)
            await db.init_db()
            state = load_sync_state()
            state["last_sync_time"] = time.time()
            state["local_hash"] = calculate_db_hash(db_path)
            save_sync_state(state)
            await db.log_sync("startup", "restored", "Данные восстановлены из облака",
                            calculate_db_hash(db_path))
            return {"action": "restored", "message": "Данные восстановлены из облака"}

        result = await upload_sync_file(dbx, db_path)
        await db.log_sync("startup", "uploaded", result.get("message", "Данные загружены"),
                         calculate_db_hash(db_path))
        return {"action": "uploaded", "message": result.get("message", "Данные загружены")}

    if local_hash != state.get("local_hash"):
        remote_data = await download_sync_file(dbx)
        if remote_data:
            restore_from_sync_zip(db_path, remote_data)
            await db.init_db()
            state = load_sync_state()
            state["last_sync_time"] = time.time()
            state["local_hash"] = calculate_db_hash(db_path)
            save_sync_state(state)
            await db.log_sync("startup", "synced", "Данные синхронизированы из облака",
                            calculate_db_hash(db_path))
            return {"action": "synced", "message": "Данные синхронизированы из облака"}

    await db.log_sync("startup", "up_to_date", "Данные актуальны", local_hash)
    return {"action": "up_to_date", "message": "Данные актуальны"}


async def sync_after_connect(db_path):
    dbx = await async_get_dropbox_client()
    if not dbx:
        return {"action": "none", "message": "Dropbox не подключён"}

    remote_data = await download_sync_file(dbx)
    if remote_data:
        restore_from_sync_zip(db_path, remote_data)
        await db.init_db()
        state = load_sync_state()
        state["last_sync_time"] = time.time()
        state["local_hash"] = calculate_db_hash(db_path)
        save_sync_state(state)
        await db.log_sync("connect", "restored", "Данные восстановлены из облака",
                         calculate_db_hash(db_path))
        return {"action": "restored", "message": "Данные восстановлены из облака"}

    result = await upload_sync_file(dbx, db_path)
    await db.log_sync("connect", "uploaded", result.get("message", "Данные загружены"),
                     calculate_db_hash(db_path))
    return {"action": "uploaded", "message": result.get("message", "Данные загружены")}


async def force_sync(db_path):
    dbx = await async_get_dropbox_client()
    if not dbx:
        await db.log_sync("manual", "skipped", "Dropbox не подключён")
        return {"action": "none", "message": "Dropbox не подключён"}

    local_hash = calculate_db_hash(db_path)
    remote_data = await download_sync_file(dbx)

    if not remote_data:
        result = await upload_sync_file(dbx, db_path)
        await db.log_sync("manual", "uploaded", result.get("message", "Данные загружены"),
                         local_hash)
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
        await db.log_sync("manual", "up_to_date", "Данные уже синхронизированы",
                         local_hash, remote_hash)
        return {"action": "up_to_date", "message": "Данные уже синхронизированы"}

    restore_from_sync_zip(db_path, remote_data)
    await db.init_db()
    state = load_sync_state()
    state["last_sync_time"] = time.time()
    state["local_hash"] = calculate_db_hash(db_path)
    save_sync_state(state)
    await db.log_sync("manual", "synced", "Данные восстановлены из облака",
                     calculate_db_hash(db_path), remote_hash)
    return {"action": "synced", "message": "Данные восстановлены из облака"}


async def backup_to_dropbox():
    dbx = await async_get_dropbox_client()
    if not dbx:
        return {"status": "skipped", "message": "Dropbox не подключён"}

    db_path = db.DATABASE_PATH
    try:
        result = await upload_sync_file(dbx, db_path)
        await db.log_sync("backup", result.get("status", "success"),
                         result.get("message", "Бэкап создан"),
                         calculate_db_hash(db_path))
        return result
    except Exception as e:
        await db.log_sync("backup", "error", str(e))
        return {"status": "error", "message": str(e)}


async def get_backup_status():
    from database import get_sync_status

    sync_status = await get_sync_status()
    return {
        "sync_status": sync_status,
        "last_sync": sync_status.get("sync_time"),
        "sync_message": sync_status.get("message", "")
    }

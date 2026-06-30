import os
import time
import secrets
import httpx
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET", "")
DROPBOX_REDIRECT_URI = os.getenv("DROPBOX_REDIRECT_URI", "http://localhost:8000/api/dropbox/callback")

_oauth_states = {}
TOKEN_EXPIRY_BUFFER = 300


def get_app_key():
    return DROPBOX_APP_KEY


def is_configured():
    return bool(DROPBOX_APP_KEY and DROPBOX_APP_SECRET)


def get_auth_url():
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = time.time()
    params = {
        "response_type": "code",
        "client_id": DROPBOX_APP_KEY,
        "redirect_uri": DROPBOX_REDIRECT_URI,
        "state": state,
        "scope": "files.content.write files.content.read",
        "token_access_type": "offline",
    }
    return f"https://www.dropbox.com/oauth2/authorize?{urlencode(params)}", state


def validate_state(state):
    if state not in _oauth_states:
        return False
    created = _oauth_states.pop(state)
    return time.time() - created < 600


def exchange_code(code):
    resp = httpx.post(
        "https://api.dropboxapi.com/oauth2/token",
        data={
            "code": code,
            "grant_type": "authorization_code",
            "client_id": DROPBOX_APP_KEY,
            "client_secret": DROPBOX_APP_SECRET,
            "redirect_uri": DROPBOX_REDIRECT_URI,
        },
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token):
    resp = httpx.post(
        "https://api.dropboxapi.com/oauth2/token",
        data={
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_id": DROPBOX_APP_KEY,
            "client_secret": DROPBOX_APP_SECRET,
        },
    )
    resp.raise_for_status()
    return resp.json()


def is_token_expired(expires_at):
    if not expires_at:
        return False
    return time.time() >= (expires_at - TOKEN_EXPIRY_BUFFER)


class DropboxClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
        }
        self.api_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def files_upload(self, file_content, dropbox_path, mode="add"):
        headers = self.headers.copy()
        arg = {"path": dropbox_path, "mode": mode, "autorename": False, "mute": False}
        headers["Dropbox-API-Arg"] = httpx.write_content_json(arg) if hasattr(httpx, 'write_content_json') else __import__('json').dumps(arg)
        resp = httpx.post(
            "https://content.dropboxapi.com/2/files/upload",
            headers=headers,
            content=file_content,
        )
        resp.raise_for_status()
        return resp.json()

    def files_list_folder(self, dropbox_path):
        resp = httpx.post(
            "https://api.dropboxapi.com/2/files/list_folder",
            headers=self.api_headers,
            json={"path": dropbox_path},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("entries", [])

    def files_download(self, dropbox_path):
        headers = self.headers.copy()
        arg = {"path": dropbox_path}
        headers["Dropbox-API-Arg"] = __import__('json').dumps(arg)
        resp = httpx.post(
            "https://content.dropboxapi.com/2/files/download",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.content

    def files_delete_v2(self, dropbox_path):
        resp = httpx.post(
            "https://api.dropboxapi.com/2/files/delete_v2",
            headers=self.api_headers,
            json={"path": dropbox_path},
        )
        resp.raise_for_status()
        return resp.json()

    def get_account_info(self):
        resp = httpx.post(
            "https://api.dropboxapi.com/2/users/get_current_account",
            headers=self.api_headers,
        )
        resp.raise_for_status()
        return resp.json()

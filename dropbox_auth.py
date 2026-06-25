import dropbox
import os
import time
import secrets
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET", "")
DROPBOX_REDIRECT_URI = os.getenv("DROPBOX_REDIRECT_URI", "http://localhost:8000/api/dropbox/callback")

_oauth_states: dict[str, float] = {}
TOKEN_EXPIRY_BUFFER = 300


def get_app_key() -> str:
    return DROPBOX_APP_KEY


def is_configured() -> bool:
    return bool(DROPBOX_APP_KEY and DROPBOX_APP_SECRET)


def get_auth_url() -> tuple[str, str]:
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


def validate_state(state: str) -> bool:
    if state not in _oauth_states:
        return False
    created = _oauth_states.pop(state)
    return time.time() - created < 600


def exchange_code(code: str) -> dict:
    import httpx
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


def refresh_access_token(refresh_token: str) -> dict:
    import httpx
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


def get_dropbox_client(access_token: str) -> dropbox.Dropbox:
    return dropbox.Dropbox(access_token)


def is_token_expired(expires_at: float | None) -> bool:
    if not expires_at:
        return False
    return time.time() >= (expires_at - TOKEN_EXPIRY_BUFFER)

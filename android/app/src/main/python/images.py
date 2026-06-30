import httpx
import os
import shutil
from pathlib import Path

COVERS_DIR = Path("static/covers")
COVERS_DIR.mkdir(parents=True, exist_ok=True)

async def download_image(url: str, filename: str) -> str:
    if not url:
        return ""

    local_path = COVERS_DIR / filename
    if local_path.exists():
        return f"/static/covers/{filename}"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, timeout=30.0)
            if response.status_code == 200:
                local_path.write_bytes(response.content)
                return f"/static/covers/{filename}"
        except Exception:
            pass

    return ""

async def download_title_images(tmdb_id: int, poster_path: str, backdrop_path: str) -> dict:
    result = {"poster": "", "backdrop": ""}

    if poster_path:
        poster_url = poster_path if poster_path.startswith("http") else f"https://image.tmdb.org/t/p/original{poster_path}"
        result["poster"] = await download_image(poster_url, f"{tmdb_id}_poster.jpg")

    if backdrop_path:
        backdrop_url = backdrop_path if backdrop_path.startswith("http") else f"https://image.tmdb.org/t/p/original{backdrop_path}"
        result["backdrop"] = await download_image(backdrop_url, f"{tmdb_id}_backdrop.jpg")

    return result

def save_uploaded_image(file_content: bytes, tmdb_id: int, image_type: str) -> str:
    filename = f"{tmdb_id}_{image_type}.jpg"
    local_path = COVERS_DIR / filename
    local_path.write_bytes(file_content)
    return f"/static/covers/{filename}"

def delete_title_images(tmdb_id: int):
    for suffix in ["poster", "backdrop"]:
        file_path = COVERS_DIR / f"{tmdb_id}_{suffix}.jpg"
        if file_path.exists():
            file_path.unlink()

def get_local_poster_path(tmdb_id: int) -> str:
    local_path = COVERS_DIR / f"{tmdb_id}_poster.jpg"
    if local_path.exists():
        return f"/static/covers/{tmdb_id}_poster.jpg"
    return ""

def get_local_backdrop_path(tmdb_id: int) -> str:
    local_path = COVERS_DIR / f"{tmdb_id}_backdrop.jpg"
    if local_path.exists():
        return f"/static/covers/{tmdb_id}_backdrop.jpg"
    return ""

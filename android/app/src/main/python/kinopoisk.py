import httpx
import os
from typing import Optional, Dict, List

KINOPOISK_API_URL = "https://api.kinopoisk.dev"
KINOPOISK_API_TOKEN = os.getenv("KINOPOISK_API_TOKEN", "")

_kinopoisk_available: Optional[bool] = None

async def check_kinopoisk_status() -> dict:
    global _kinopoisk_available

    if not KINOPOISK_API_TOKEN:
        _kinopoisk_available = False
        return {"available": False, "error": "KINOPOISK_API_TOKEN не задан в .env (получите бесплатно на api.kinopoisk.dev)"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{KINOPOISK_API_URL}/api/v1.4/movie/search",
                params={"query": "Matrix", "limit": 1},
                headers={"X-API-KEY": KINOPOISK_API_TOKEN, "Accept": "application/json"}
            )
            if resp.status_code == 200:
                _kinopoisk_available = True
                return {"available": True, "error": None}
            elif resp.status_code == 401:
                _kinopoisk_available = False
                return {"available": False, "error": "Неверный токен API"}
            else:
                _kinopoisk_available = False
                return {"available": False, "error": f"HTTP {resp.status_code}"}
    except httpx.ConnectError:
        _kinopoisk_available = False
        return {"available": False, "error": "Ошибка подключения к api.kinopoisk.dev"}
    except Exception as e:
        _kinopoisk_available = False
        return {"available": False, "error": f"{type(e).__name__}: {str(e)[:100]}"}

async def search_kinopoisk(query: str) -> List[Dict]:
    if not KINOPOISK_API_TOKEN:
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{KINOPOISK_API_URL}/api/v1.4/movie/search",
                params={"query": query, "limit": 10, "selectFields": "id,name,alternativeName,year,type,poster,rating,description,genres,seasonsInfo"},
                headers={"X-API-KEY": KINOPOISK_API_TOKEN, "Accept": "application/json"}
            )
            if response.status_code == 200:
                data = response.json()
                docs = data.get("docs", [])
                results = []
                for item in docs:
                    media_type = "movie"
                    if item.get("type") == "series":
                        media_type = "tv"

                    poster_url = ""
                    if item.get("poster") and item["poster"].get("url"):
                        poster_url = item["poster"]["url"]

                    rating = 0
                    if item.get("rating") and item["rating"].get("kinopoisk"):
                        rating = float(item["rating"]["kinopoisk"].get("value", 0) or 0)

                    total_seasons = 0
                    total_episodes = 0
                    if media_type == "tv" and item.get("seasonsInfo"):
                        seasons = item["seasonsInfo"]
                        if isinstance(seasons, list) and len(seasons) > 0:
                            total_seasons = len(seasons)
                            for s in seasons:
                                if isinstance(s, dict):
                                    total_episodes += s.get("episodesCount", 0) or 0

                    results.append({
                        "tmdb_id": item.get("id", 0),
                        "kinopoisk_id": item.get("id", 0),
                        "title": item.get("name") or item.get("alternativeName") or "Без названия",
                        "original_title": item.get("alternativeName") or item.get("name") or "",
                        "media_type": media_type,
                        "poster_path": poster_url,
                        "backdrop_path": "",
                        "overview": item.get("description") or "",
                        "release_date": str(item.get("year", "")) if item.get("year") else "",
                        "vote_average": rating,
                        "total_seasons": total_seasons,
                        "total_episodes": total_episodes,
                        "source": "kinopoisk"
                    })
                return results
    except Exception:
        pass
    return []

async def get_kinopoisk_details(kp_id: int) -> Optional[Dict]:
    if not KINOPOISK_API_TOKEN:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{KINOPOISK_API_URL}/api/v1.4/movie/{kp_id}",
                params={"selectFields": "id,name,alternativeName,year,type,poster,backdrop,rating,description,genres,seasonsInfo"},
                headers={"X-API-KEY": KINOPOISK_API_TOKEN, "Accept": "application/json"}
            )
            if response.status_code == 200:
                item = response.json()
                if not item or not item.get("id"):
                    return None

                media_type = "movie"
                if item.get("type") == "series":
                    media_type = "tv"

                poster_url = ""
                if item.get("poster") and item["poster"].get("url"):
                    poster_url = item["poster"]["url"]

                backdrop_url = ""
                if item.get("backdrop") and item["backdrop"].get("url"):
                    backdrop_url = item["backdrop"]["url"]

                rating = 0
                if item.get("rating") and item["rating"].get("kinopoisk"):
                    rating = float(item["rating"]["kinopoisk"].get("value", 0) or 0)

                total_seasons = 0
                total_episodes = 0
                if media_type == "tv" and item.get("seasonsInfo"):
                    seasons = item["seasonsInfo"]
                    if isinstance(seasons, list) and len(seasons) > 0:
                        total_seasons = len(seasons)
                        for s in seasons:
                            if isinstance(s, dict):
                                total_episodes += s.get("episodesCount", 0) or 0

                return {
                    "tmdb_id": item.get("id", 0),
                    "kinopoisk_id": item.get("id", 0),
                    "title": item.get("name") or "Без названия",
                    "original_title": item.get("alternativeName") or item.get("name") or "",
                    "media_type": media_type,
                    "poster_path": poster_url,
                    "backdrop_path": backdrop_url,
                    "overview": item.get("description") or "",
                    "release_date": str(item.get("year", "")) if item.get("year") else "",
                    "vote_average": rating,
                    "total_seasons": total_seasons,
                    "total_episodes": total_episodes,
                    "source": "kinopoisk"
                }
    except Exception:
        pass
    return None

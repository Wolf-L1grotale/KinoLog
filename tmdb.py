import httpx
import os
import kinopoisk
import kinorium
from typing import Optional, Dict, List
from datetime import datetime

OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
SHIKIMORI_API_URL = "https://shikimori.io/api"
SHIKIMORI_IMAGE_URL = "https://shikimori.io"

_api_status = {
    "omdb": {"available": None, "last_check": None, "error": None},
    "shikimori": {"available": None, "last_check": None, "error": None},
    "kinopoisk": {"available": None, "last_check": None, "error": None},
    "kinorium": {"available": None, "last_check": None, "error": None}
}

async def check_api_status():
    global _api_status
    now = datetime.now()

    for api_name, status in _api_status.items():
        if api_name == "kinopoisk":
            result = await kinopoisk.check_kinopoisk_status()
            _api_status["kinopoisk"]["available"] = result["available"]
            _api_status["kinopoisk"]["error"] = result["error"]
            continue

        if api_name == "kinorium":
            _api_status["kinorium"]["available"] = True
            _api_status["kinorium"]["error"] = None
            continue

        if status["last_check"] and (now - status["last_check"]).seconds < 300:
            continue

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                if api_name == "omdb":
                    if not OMDB_API_KEY:
                        _api_status[api_name]["available"] = False
                        _api_status[api_name]["error"] = "OMDB_API_KEY не задан в .env"
                    else:
                        resp = await client.get(f"https://www.omdbapi.com/?apikey={OMDB_API_KEY}&i=tt0111161")
                        _api_status[api_name]["available"] = resp.status_code == 200
                        if resp.status_code != 200:
                            _api_status[api_name]["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
                        else:
                            _api_status[api_name]["error"] = None
                elif api_name == "shikimori":
                    resp = await client.get(f"{SHIKIMORI_API_URL}/animes?limit=1", headers={"User-Agent": "FilmoGraph/1.0"})
                    _api_status[api_name]["available"] = resp.status_code == 200
                    if resp.status_code != 200:
                        _api_status[api_name]["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    else:
                        _api_status[api_name]["error"] = None
        except httpx.ConnectError as e:
            _api_status[api_name]["available"] = False
            _api_status[api_name]["error"] = f"Ошибка подключения: {str(e)[:200]}"
        except httpx.TimeoutException:
            _api_status[api_name]["available"] = False
            _api_status[api_name]["error"] = "Превышено время ожидания (5 сек)"
        except Exception as e:
            _api_status[api_name]["available"] = False
            _api_status[api_name]["error"] = f"Ошибка: {type(e).__name__}: {str(e)[:200]}"

        _api_status[api_name]["last_check"] = now

async def get_api_status() -> dict:
    await check_api_status()
    return {k: {"available": v["available"], "error": v["error"]} for k, v in _api_status.items()}

async def search_titles(query: str, media_type: str = "multi") -> List[Dict]:
    await check_api_status()
    results = []

    if media_type in ["movie", "tv", "multi"]:
        if _api_status["omdb"]["available"]:
            omdb_results = await search_omdb(query, "movie" if media_type == "movie" else "series")
            results.extend(omdb_results)

    if not results and media_type in ["movie", "tv", "multi"]:
        if _api_status["kinopoisk"]["available"]:
            kp_results = await kinopoisk.search_kinopoisk(query)
            results.extend(kp_results)

    if not results and media_type in ["movie", "tv", "multi"]:
        if _api_status["kinorium"]["available"]:
            kx_results = await kinorium.search_kinorium(query)
            results.extend(kx_results)

    if media_type in ["anime", "multi"]:
        if _api_status["shikimori"]["available"]:
            shiki_results = await search_shikimori(query)
            results.extend(shiki_results)

    seen = set()
    unique_results = []
    for r in results:
        key = r.get("imdb_id") or r.get("title", "").lower()
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    return unique_results[:15]

async def search_omdb(query: str, media_type: str = "") -> List[Dict]:
    if not OMDB_API_KEY:
        return []

    try:
        async with httpx.AsyncClient() as client:
            params = {"apikey": OMDB_API_KEY, "s": query, "type": media_type}
            response = await client.get("https://www.omdbapi.com/", params=params, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("Response") == "True":
                    results = []
                    for item in data.get("Search", [])[:10]:
                        details = await get_omdb_details(item["imdbID"])
                        if details:
                            results.append(details)
                    return results
    except Exception:
        pass
    return []

async def get_omdb_details(imdb_id: str) -> Optional[Dict]:
    if not OMDB_API_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.omdbapi.com/",
                params={"apikey": OMDB_API_KEY, "i": imdb_id, "plot": "full"},
                timeout=10.0
            )
            if response.status_code == 200:
                item = response.json()
                if item.get("Response") == "True":
                    media_type = "tv" if item.get("Type") == "series" else "movie"
                    poster_url = item.get("Poster", "")
                    if poster_url == "N/A":
                        poster_url = ""

                    return {
                        "tmdb_id": hash(imdb_id) % (10**9),
                        "imdb_id": imdb_id,
                        "title": item.get("Title", ""),
                        "original_title": item.get("Title", ""),
                        "media_type": media_type,
                        "poster_path": poster_url,
                        "backdrop_path": "",
                        "overview": item.get("Plot", ""),
                        "release_date": item.get("Year", ""),
                        "vote_average": float(item.get("imdbRating", "0")) if item.get("imdbRating") != "N/A" else 0,
                        "total_seasons": int(item.get("totalSeasons", "0")) if item.get("totalSeasons") != "N/A" else 0,
                        "total_episodes": 0,
                        "source": "omdb"
                    }
    except Exception:
        pass
    return None

async def search_shikimori(query: str) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SHIKIMORI_API_URL}/animes",
                params={"search": query, "limit": 10},
                headers={"User-Agent": "FilmoGraph/1.0"},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data:
                    poster_url = ""
                    if item.get("image"):
                        poster_url = f"{SHIKIMORI_IMAGE_URL}{item['image']['original']}" if item['image'].get('original') else ""

                    russian_name = item.get("russian", "")
                    name = item.get("name", "")

                    episodes = item.get("episodes", 0) or 0
                    episodes_aired = item.get("episodes_aired", 0) or 0

                    results.append({
                        "tmdb_id": item.get("id", 0),
                        "shikimori_id": item.get("id", 0),
                        "title": russian_name or name,
                        "original_title": name,
                        "media_type": "anime",
                        "poster_path": poster_url,
                        "backdrop_path": "",
                        "overview": "",
                        "release_date": str(item.get("aired_on", ""))[:4] if item.get("aired_on") else "",
                        "vote_average": float(item.get("score") or 0),
                        "total_seasons": 1 if item.get("kind") == "tv" else 0,
                        "total_episodes": episodes or episodes_aired,
                        "source": "shikimori"
                    })
                return results
    except Exception:
        pass
    return []

async def search_anime(query: str) -> List[Dict]:
    await check_api_status()
    if _api_status["shikimori"]["available"]:
        return await search_shikimori(query)
    return []

async def get_shikimori_details(anime_id: int) -> Optional[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SHIKIMORI_API_URL}/animes/{anime_id}",
                headers={"User-Agent": "FilmoGraph/1.0"},
                timeout=10.0
            )
            if response.status_code == 200:
                item = response.json()
                poster_url = ""
                if item.get("image"):
                    poster_url = f"{SHIKIMORI_IMAGE_URL}{item['image']['original']}" if item['image'].get('original') else ""

                russian_name = item.get("russian", "")
                name = item.get("name", "")

                episodes = item.get("episodes", 0) or 0
                episodes_aired = item.get("episodes_aired", 0) or 0

                return {
                    "tmdb_id": item.get("id", 0),
                    "shikimori_id": item.get("id", 0),
                    "title": russian_name or name,
                    "original_title": name,
                    "media_type": "anime",
                    "poster_path": poster_url,
                    "backdrop_path": "",
                    "overview": item.get("description", "") or "",
                    "release_date": str(item.get("aired_on", ""))[:4] if item.get("aired_on") else "",
                    "vote_average": float(item.get("score") or 0),
                    "total_seasons": 1 if item.get("kind") == "tv" else 0,
                    "total_episodes": episodes or episodes_aired,
                    "source": "shikimori"
                }
    except Exception:
        pass
    return None

async def search_titles_manual(query: str) -> List[Dict]:
    return [{
        "tmdb_id": abs(hash(query)) % (10**9),
        "imdb_id": "",
        "title": query,
        "original_title": query,
        "media_type": "movie",
        "poster_path": "",
        "backdrop_path": "",
        "overview": "",
        "release_date": "",
        "vote_average": 0,
        "total_seasons": 0,
        "total_episodes": 0,
        "source": "manual"
    }]

def extract_tmdb_id_from_url(url: str) -> Optional[tuple]:
    import re

    imdb_patterns = [
        r'imdb\.com/title/(tt\d+)',
        r'omdbapi\.com/\?i=(tt\d+)'
    ]
    for pattern in imdb_patterns:
        match = re.search(pattern, url)
        if match:
            return hash(match.group(1)) % (10**9), "movie"

    shikimori_patterns = [
        r'shikimori\.io/animes/(\d+)',
        r'shikimori\.io/anime/(\d+)',
        r'shikimori\.one/animes/(\d+)',
        r'shikimori\.one/anime/(\d+)'
    ]
    for pattern in shikimori_patterns:
        match = re.search(pattern, url)
        if match:
            return int(match.group(1)), "anime"

    kinopoisk_patterns = [
        r'kinopoisk\.ru/film/(\d+)',
        r'kinopoisk\.ru/series/(\d+)'
    ]
    for pattern in kinopoisk_patterns:
        match = re.search(pattern, url)
        if match:
            kp_id = int(match.group(1))
            return kp_id, "kinopoisk"

    if "kinorium.com" in url:
        kp_id = kinorium.extract_kinorium_id_from_url(url)
        if kp_id:
            return kp_id, "kinorium"

    return None

import httpx
import re
from typing import Optional, Dict, List
from bs4 import BeautifulSoup

KINORIUM_BASE_URL = "https://kinorium.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}


def _parse_search_item(item) -> Optional[Dict]:
    kp_id = item.get("data-id")
    if not kp_id:
        return None

    title_elem = item.find("a", class_="search-page__title-link")
    title = title_elem.get_text(strip=True) if title_elem else ""

    small_elem = item.find("small", class_="cut_text")
    info_text = small_elem.get_text(strip=True) if small_elem else ""

    year = ""
    original_title = ""
    if info_text:
        year_match = re.match(r"(\d{4})", info_text)
        if year_match:
            year = year_match.group(1)
        orig_match = re.search(r",\s*(.+)$", info_text)
        if orig_match:
            original_title = orig_match.group(1).strip()

    genre_elem = item.find("div", class_="search-page__genre-list")
    genres = genre_elem.get_text(strip=True) if genre_elem else ""

    media_type = "movie"
    if "(сериал)" in title.lower() or "сериал" in genres.lower():
        media_type = "tv"
        title = re.sub(r"\s*\(сериал\)\s*$", "", title, flags=re.IGNORECASE)

    img_elem = item.find("img")
    poster = ""
    if img_elem:
        poster = img_elem.get("src", "") or img_elem.get("data-src", "")

    country = ""
    extro = item.find("div", class_="search-page__extro-info")
    if extro:
        country_text = extro.get_text(strip=True)
        country_match = re.search(r"(?:Япония|США|Россия|Великобритания|Франция|Германия|Китай|Корея|Индия|Канада|Австралия|Италия|Испания|Бразилия|Турция|Швеция|Норвегия|Дания|Финляндия|Нидерланды|Бельгия|Швейцария|Австрия|Польша|Чехия|Украина)", country_text)
        if country_match:
            country = country_match.group(0)

    return {
        "tmdb_id": int(kp_id),
        "kinorium_id": int(kp_id),
        "title": title,
        "original_title": original_title,
        "media_type": media_type,
        "poster_path": poster,
        "backdrop_path": "",
        "overview": "",
        "release_date": year,
        "vote_average": 0,
        "total_seasons": 0,
        "total_episodes": 0,
        "genres": genres,
        "country": country,
        "source": "kinorium",
    }


async def search_kinorium(query: str) -> List[Dict]:
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(
                f"{KINORIUM_BASE_URL}/search/",
                params={"q": query},
                headers=HEADERS,
            )
            if response.status_code != 200:
                return []

            html = response.content.decode("utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")

            items = soup.find_all(attrs={"data-id": True})
            results = []
            seen_ids = set()

            for item in items:
                parsed = _parse_search_item(item)
                if parsed and parsed["tmdb_id"] not in seen_ids:
                    seen_ids.add(parsed["tmdb_id"])
                    results.append(parsed)

            return results[:15]
    except Exception:
        return []


async def get_kinorium_details(kinorium_id: int) -> Optional[Dict]:
    results = await search_kinorium(str(kinorium_id))
    for r in results:
        if r.get("kinorium_id") == kinorium_id:
            return r
    return None


def extract_kinorium_id_from_url(url: str) -> Optional[int]:
    match = re.search(r"kinorium\.com/(\d+)", url)
    if match:
        return int(match.group(1))
    return None

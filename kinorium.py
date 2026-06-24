import re
import asyncio
from typing import Optional, Dict, List
from bs4 import BeautifulSoup

_browser = None
_pw = None


async def _get_browser():
    global _browser, _pw
    if _browser is None:
        from playwright.async_api import async_playwright
        _pw = await async_playwright().__aenter__()
        _browser = await _pw.chromium.launch(headless=True)
    return _browser


async def close_browser():
    global _browser, _pw
    if _browser:
        await _browser.close()
        _browser = None
    if _pw:
        await _pw.__aexit__(None, None, None)
        _pw = None


def _parse_search_results(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    h3_items = soup.find_all("h3", attrs={"data-id": True})
    results = []
    seen_ids = set()

    for h3 in h3_items:
        item_div = h3.parent
        if not item_div or item_div.name != "div":
            continue

        kp_id = h3.get("data-id")
        if not kp_id or kp_id in seen_ids:
            continue

        title_elem = h3.find("a")
        title = title_elem.get_text(strip=True) if title_elem else ""

        small_elem = item_div.find("small", class_="cut_text")
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

        genre_elem = item_div.find("div", class_="search-page__genre-list")
        genres = genre_elem.get_text(strip=True) if genre_elem else ""

        media_type = "movie"
        if "(сериал)" in title.lower():
            media_type = "tv"
            title = re.sub(r"\s*\(сериал\)\s*$", "", title, flags=re.IGNORECASE)

        img_elem = item_div.find("img")
        poster = ""
        if img_elem:
            poster = img_elem.get("src", "") or img_elem.get("data-src", "")

        seen_ids.add(kp_id)
        results.append({
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
            "source": "kinorium",
        })

    return results


async def search_kinorium(query: str) -> List[Dict]:
    try:
        browser = await _get_browser()
        page = await browser.new_page()
        await page.goto(f"https://kinorium.com/search/?q={query}", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)
        content = await page.content()
        await page.close()

        return _parse_search_results(content)[:15]
    except Exception:
        return []


async def get_kinorium_details(kinorium_id: int) -> Optional[Dict]:
    return None


def extract_kinorium_id_from_url(url: str) -> Optional[int]:
    match = re.search(r"kinorium\.com/(\d+)", url)
    if match:
        return int(match.group(1))
    return None

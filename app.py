from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import database as db
import tmdb
import kinopoisk
import kinorium
import backup
import images
from dotenv import load_dotenv

load_dotenv()

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    scheduler.add_job(backup.backup_to_dropbox, 'cron', hour=3, minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="KinoLog", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, type: str = "", status: str = ""):
    titles = await db.get_all_titles()

    if type:
        titles = [t for t in titles if t["media_type"] == type]
    if status:
        titles = [t for t in titles if t["current_status"] == status]

    backup_info = await backup.get_backup_status()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "titles": titles,
        "backup_info": backup_info
    })

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = "", type: str = "all"):
    results = []
    api_status = await tmdb.get_api_status()
    search_performed = False
    error_message = None

    if q:
        search_performed = True
        any_api_available = any(info.get("available") for info in api_status.values())

        if not any_api_available:
            error_message = "Все API недоступны. Попробуйте ввести данные вручную."
            results = await tmdb.search_titles_manual(q)
        else:
            if q.startswith("http"):
                extracted = tmdb.extract_tmdb_id_from_url(q)
                if extracted:
                    tmdb_id, media_type = extracted
                    if media_type == "anime":
                        details = await tmdb.get_shikimori_details(tmdb_id)
                    elif media_type == "kinopoisk":
                        details = await kinopoisk.get_kinopoisk_details(tmdb_id)
                    elif media_type == "kinorium":
                        details = await kinorium.get_kinorium_details(tmdb_id)
                        if not details:
                            kp_results = await kinorium.search_kinorium(str(tmdb_id))
                            details = kp_results[0] if kp_results else None
                    else:
                        details = None
                    if details:
                        results = [details]
                    else:
                        results = await tmdb.search_titles_manual(q)
            elif type == "anime":
                if api_status.get("shikimori", {}).get("available"):
                    results = await tmdb.search_anime(q)
                else:
                    results = await tmdb.search_titles_manual(q)
            else:
                results = await tmdb.search_titles(q, type)
                if not results:
                    results = await tmdb.search_titles_manual(q)

    search_errors = []
    for name, info in api_status.items():
        if info.get("error"):
            search_errors.append(f"{name}: {info['error']}")

    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": q,
        "results": results,
        "content_type": type,
        "api_status": api_status,
        "search_performed": search_performed,
        "error_message": error_message,
        "search_errors": search_errors
    })

@app.get("/add/preview", response_class=HTMLResponse)
async def add_preview(
    request: Request,
    tmdb_id: int = Query(...),
    title: str = Query(""),
    original_title: str = Query(""),
    media_type: str = Query("movie"),
    poster_path: str = Query(""),
    backdrop_path: str = Query(""),
    overview: str = Query(""),
    release_date: str = Query(""),
    vote_average: float = Query(0.0),
    total_seasons: int = Query(0),
    total_episodes: int = Query(0)
):
    existing = await db.get_title(tmdb_id)
    if existing:
        return RedirectResponse(url=f"/title/{tmdb_id}", status_code=303)

    title_data = {
        "tmdb_id": tmdb_id,
        "title": title,
        "original_title": original_title,
        "media_type": media_type,
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "overview": overview,
        "release_date": release_date,
        "vote_average": vote_average,
        "total_seasons": total_seasons,
        "total_episodes": total_episodes
    }

    return templates.TemplateResponse("add.html", {"request": request, "title": title_data})

@app.post("/add")
async def add_title(
    tmdb_id: int = Form(...),
    title: str = Form(...),
    original_title: str = Form(""),
    media_type: str = Form("movie"),
    poster_path: str = Form(""),
    backdrop_path: str = Form(""),
    overview: str = Form(""),
    release_date: str = Form(""),
    vote_average: float = Form(0.0),
    total_seasons: int = Form(0),
    total_episodes: int = Form(0),
    current_status: str = Form("watching"),
    current_season: int = Form(1),
    current_episode: int = Form(1),
    notes: str = Form("")
):
    existing = await db.get_title(tmdb_id)
    if existing:
        return RedirectResponse(url=f"/title/{tmdb_id}", status_code=303)

    local_images = await images.download_title_images(tmdb_id, poster_path, backdrop_path)

    await db.add_title(
        tmdb_id=tmdb_id,
        title=title,
        original_title=original_title,
        media_type=media_type,
        poster_path=poster_path,
        backdrop_path=backdrop_path,
        local_poster_path=local_images["poster"],
        local_backdrop_path=local_images["backdrop"],
        overview=overview,
        release_date=release_date,
        vote_average=vote_average,
        total_seasons=total_seasons,
        total_episodes=total_episodes
    )

    await db.update_title(
        tmdb_id=tmdb_id,
        current_status=current_status,
        current_season=current_season,
        current_episode=current_episode,
        notes=notes
    )

    return RedirectResponse(url=f"/title/{tmdb_id}", status_code=303)

@app.get("/title/{tmdb_id}", response_class=HTMLResponse)
async def title_page(request: Request, tmdb_id: int):
    title = await db.get_title(tmdb_id)
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")
    return templates.TemplateResponse("title.html", {"request": request, "title": title})

@app.post("/title/{tmdb_id}/update")
async def update_title(
    tmdb_id: int,
    current_status: str = Form(...),
    current_season: int = Form(1),
    current_episode: int = Form(1),
    notes: str = Form("")
):
    updated = await db.update_title(
        tmdb_id=tmdb_id,
        current_status=current_status,
        current_season=current_season,
        current_episode=current_episode,
        notes=notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Title not found")
    return RedirectResponse(url=f"/title/{tmdb_id}", status_code=303)

@app.post("/title/{tmdb_id}/upload")
async def upload_image(tmdb_id: int, image_type: str = Form(...), image: UploadFile = File(...)):
    content = await image.read()
    local_path = images.save_uploaded_image(content, tmdb_id, image_type)

    field = "local_poster_path" if image_type == "poster" else "local_backdrop_path"
    await db.update_title(tmdb_id, **{field: local_path})

    return RedirectResponse(url=f"/title/{tmdb_id}", status_code=303)

@app.post("/title/{tmdb_id}/delete")
async def delete_title(tmdb_id: int):
    images.delete_title_images(tmdb_id)
    deleted = await db.delete_title(tmdb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Title not found")
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/search")
async def api_search(q: str, type: str = "multi"):
    results = await tmdb.search_titles(q, type)
    return JSONResponse(content=results)

@app.get("/api/status")
async def api_status():
    status = await tmdb.get_api_status()
    return JSONResponse(content=status)

@app.post("/api/backup")
async def trigger_backup():
    result = await backup.backup_to_dropbox()
    return JSONResponse(content=result)

@app.get("/api/backup/status")
async def backup_status():
    status = await backup.get_backup_status()
    return JSONResponse(content=status)

@app.get("/api/stats")
async def stats():
    titles = await db.get_all_titles()
    stats_data = {
        "total": len(titles),
        "watching": len([t for t in titles if t["current_status"] == "watching"]),
        "completed": len([t for t in titles if t["current_status"] == "completed"]),
        "planned": len([t for t in titles if t["current_status"] == "planned"]),
        "dropped": len([t for t in titles if t["current_status"] == "dropped"]),
        "movies": len([t for t in titles if t["media_type"] == "movie"]),
        "tv_shows": len([t for t in titles if t["media_type"] == "tv"]),
        "anime": len([t for t in titles if t["media_type"] == "anime"])
    }
    return JSONResponse(content=stats_data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

import sys
import os
import threading
import time

def start_server(port, app_path, db_path):
    os.environ["KINOLOG_PORT"] = str(port)
    os.environ["KINOLOG_APP_PATH"] = app_path
    os.environ["KINOLOG_DB_PATH"] = db_path
    os.environ["KINOLOG_BUNDLE_PATH"] = app_path
    os.chdir(app_path)

    sys.path.insert(0, app_path)

    from dotenv import load_dotenv
    env_path = os.path.join(app_path, "config", ".env")
    load_dotenv(env_path)

    try:
        import database as db
        db.DATABASE_PATH = db_path

        import uvicorn
        from fastapi import FastAPI, Request, Form, HTTPException, Query
        from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles
        from fastapi.templating import Jinja2Templates
        from contextlib import asynccontextmanager

        templates_dir = os.path.join(app_path, "templates")
        static_dir = os.path.join(app_path, "static")

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await db.init_db()
            try:
                import sync
                result = await sync.sync_on_startup(db_path)
                print(f"Sync result: {result}")
            except Exception as e:
                print(f"Sync error: {e}")
            yield

        app = FastAPI(title="KinoLog", lifespan=lifespan)

        if os.path.exists(static_dir):
            app.mount("/static", StaticFiles(directory=static_dir), name="static")

        templates = Jinja2Templates(directory=templates_dir)

        @app.get("/", response_class=HTMLResponse)
        async def index(request: Request, type: str = "", status: str = ""):
            titles = await db.get_all_titles()
            if type:
                titles = [t for t in titles if t["media_type"] == type]
            if status:
                titles = [t for t in titles if t["current_status"] == status]

            import sync
            backup_info = await sync.get_backup_status()

            return templates.TemplateResponse("index.html", {
                "request": request,
                "titles": titles,
                "backup_info": backup_info
            })

        @app.get("/search", response_class=HTMLResponse)
        async def search_page(request: Request, q: str = "", type: str = "all"):
            import tmdb
            import kinopoisk
            import kinorium

            results = []
            search_performed = False
            error_message = None
            search_errors = []

            if q:
                search_performed = True
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
                        else:
                            details = None
                        if details:
                            results = [details]
                        else:
                            results = await tmdb.search_titles_manual(q)
                else:
                    results = await tmdb.search_titles(q, type)
                    if not results:
                        results = await tmdb.search_titles_manual(q)

            return templates.TemplateResponse("search.html", {
                "request": request,
                "query": q,
                "results": results,
                "content_type": type,
                "api_status": {},
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

            import images
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
            await db.update_title(
                tmdb_id=tmdb_id,
                current_status=current_status,
                current_season=current_season,
                current_episode=current_episode,
                notes=notes
            )
            return RedirectResponse(url=f"/title/{tmdb_id}", status_code=303)

        @app.post("/title/{tmdb_id}/upload")
        async def upload_image(tmdb_id: int, image_type: str = Form(...), image: str = Form(...)):
            import images
            import base64
            try:
                image_data = base64.b64decode(image)
                local_path = images.save_uploaded_image(image_data, tmdb_id, image_type)
                field = "local_poster_path" if image_type == "poster" else "local_backdrop_path"
                await db.update_title(tmdb_id, **{field: local_path})
            except Exception:
                pass
            return RedirectResponse(url=f"/title/{tmdb_id}", status_code=303)

        @app.post("/title/{tmdb_id}/delete")
        async def delete_title(tmdb_id: int):
            import images
            images.delete_title_images(tmdb_id)
            await db.delete_title(tmdb_id)
            return RedirectResponse(url="/", status_code=303)

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

        @app.get("/api/dropbox/status")
        async def dropbox_status():
            import dropbox_client
            from database import get_dropbox_tokens

            configured = dropbox_client.is_configured()
            tokens = await get_dropbox_tokens()

            if tokens:
                return JSONResponse(content={
                    "connected": True,
                    "configured": configured,
                    "account_name": tokens.get("account_name", ""),
                })

            return JSONResponse(content={
                "connected": False,
                "configured": configured,
                "account_name": None,
            })

        @app.get("/api/dropbox/auth")
        async def dropbox_auth_start():
            import dropbox_client
            if not dropbox_client.is_configured():
                return JSONResponse(
                    status_code=400,
                    content={"error": "DROPBOX_APP_KEY и DROPBOX_APP_SECRET не заданы в .env"}
                )
            auth_url, state = dropbox_client.get_auth_url()
            return JSONResponse(content={"auth_url": auth_url, "state": state})

        @app.get("/api/dropbox/callback")
        async def dropbox_auth_callback(code: str = "", state: str = ""):
            import dropbox_client

            if not code or not state:
                return RedirectResponse(url="/?dropbox_error=missing_params", status_code=302)

            if not dropbox_client.validate_state(state):
                return RedirectResponse(url="/?dropbox_error=invalid_state", status_code=302)

            try:
                token_data = dropbox_client.exchange_code(code)
            except Exception:
                return RedirectResponse(url="/?dropbox_error=exchange_failed", status_code=302)

            access_token = token_data.get("access_token", "")
            refresh_token = token_data.get("refresh_token", "")
            expires_in = token_data.get("expires_in", 0)
            expires_at = time.time() + expires_in if expires_in else None

            account_name = ""
            try:
                dc = dropbox_client.DropboxClient(access_token)
                account = dc.get_account_info()
                account_name = account.get("name", {}).get("display_name", "")
            except Exception:
                pass

            await db.save_dropbox_tokens(access_token, refresh_token, expires_at, account_name)

            try:
                import sync
                sync_result = await sync.sync_after_connect(db_path)
                print(f"Sync after connect: {sync_result}")
            except Exception as e:
                print(f"Sync after connect error: {e}")

            return RedirectResponse(url="/?dropbox_connected=1", status_code=302)

        @app.post("/api/dropbox/disconnect")
        async def dropbox_disconnect():
            await db.delete_dropbox_tokens()
            return JSONResponse(content={"status": "disconnected"})

        @app.post("/api/backup")
        async def trigger_backup():
            import sync
            result = await sync.backup_to_dropbox()
            return JSONResponse(content=result)

        @app.get("/api/backup/status")
        async def backup_status():
            import sync
            status = await sync.get_backup_status()
            return JSONResponse(content=status)

        @app.get("/api/sync/status")
        async def sync_status():
            from database import get_sync_status
            status = await get_sync_status()
            return JSONResponse(content=status)

        @app.post("/api/sync")
        async def trigger_sync():
            import sync
            result = await sync.force_sync(db_path)
            return JSONResponse(content=result)

        @app.post("/api/restart")
        async def restart_app():
            def restart():
                time.sleep(1)
                os._exit(0)
            threading.Thread(target=restart, daemon=True).start()
            return JSONResponse(content={"status": "restarting"})

        @app.get("/config", response_class=HTMLResponse)
        async def config_page(request: Request):
            env_path = os.path.join(app_path, "config", ".env")
            env_content = ""
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    env_content = f.read()

            return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KinoLog - Конфигурация</title>
    <style>
        body {{ font-family: sans-serif; background: #1a1a1a; color: #fff; padding: 20px; }}
        h1 {{ color: #4CAF50; }}
        textarea {{ width: 100%; height: 200px; background: #2d2d2d; color: #fff; border: 1px solid #444; padding: 10px; font-family: monospace; font-size: 14px; box-sizing: border-box; }}
        .btn {{ background: #4CAF50; color: white; border: none; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 4px; font-size: 14px; }}
        .btn:hover {{ background: #45a049; }}
        .btn-secondary {{ background: #555; }}
        .btn-secondary:hover {{ background: #666; }}
        .btn-danger {{ background: #f44336; }}
        .btn-danger:hover {{ background: #d32f2f; }}
        .btn-warning {{ background: #ff9800; }}
        .btn-warning:hover {{ background: #f57c00; }}
        .info {{ background: #2d2d2d; padding: 15px; border-radius: 8px; margin: 10px 0; }}
        .path {{ color: #888; font-family: monospace; font-size: 12px; }}
        .success {{ color: #4CAF50; margin: 10px 0; }}
        .error {{ color: #f44336; margin: 10px 0; }}
        .buttons {{ margin: 15px 0; }}
    </style>
</head>
<body>
    <h1>KinoLog - Конфигурация</h1>
    <div class="info">
        <p>Путь к конфигурации: <span class="path">{env_path}</span></p>
        <p>Отредактируйте файл .env и нажмите "Сохранить"</p>
    </div>
    <form id="configForm">
        <textarea id="envContent">{env_content}</textarea>
        <div class="buttons">
            <button type="submit" class="btn">Сохранить</button>
            <button type="button" class="btn btn-secondary" onclick="location.reload()">Отмена</button>
        </div>
    </form>
    <div class="buttons">
        <button onclick="forceSync()" class="btn btn-warning">Синхронизировать</button>
        <button onclick="restartApp()" class="btn btn-secondary">Перезапустить</button>
        <button onclick="exitApp()" class="btn btn-danger">Выйти</button>
    </div>
    <div id="status"></div>
    <script>
        document.getElementById('configForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const content = document.getElementById('envContent').value;
            const status = document.getElementById('status');
            try {{
                const resp = await fetch('/api/config', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{content: content}})
                }});
                const data = await resp.json();
                if (data.status === 'ok') {{
                    status.className = 'success';
                    status.textContent = 'Конфигурация сохранена! Нажмите "Перезапустить" для применения.';
                }} else {{
                    status.className = 'error';
                    status.textContent = 'Ошибка: ' + data.message;
                }}
            }} catch (err) {{
                status.className = 'error';
                status.textContent = 'Ошибка сети: ' + err.message;
            }}
        }});

        async function forceSync() {{
            const status = document.getElementById('status');
            status.className = '';
            status.textContent = 'Синхронизация...';
            try {{
                const resp = await fetch('/api/sync', {{method: 'POST'}});
                const data = await resp.json();
                status.className = data.action === 'none' ? 'error' : 'success';
                status.textContent = data.message || 'Готово';
            }} catch (err) {{
                status.className = 'error';
                status.textContent = 'Ошибка: ' + err.message;
            }}
        }}

        async function restartApp() {{
            const status = document.getElementById('status');
            status.className = 'success';
            status.textContent = 'Перезапуск...';
            try {{
                await fetch('/api/restart', {{method: 'POST'}});
                setTimeout(() => {{ status.textContent = 'Приложение перезапускается...'; }}, 1000);
            }} catch (err) {{
                status.className = 'error';
                status.textContent = 'Ошибка: ' + err.message;
            }}
        }}

        function exitApp() {{
            if (confirm('Выйти из приложения?')) {{
                fetch('/api/restart', {{method: 'POST'}});
                setTimeout(() => {{ navigator.app?.exitApp?.(); }}, 500);
            }}
        }}
    </script>
</body>
</html>""")

        @app.post("/api/config")
        async def save_config(request: Request):
            try:
                body = await request.json()
                content = body.get("content", "")
                env_path = os.path.join(app_path, "config", ".env")
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return JSONResponse(content={"status": "ok"})
            except Exception as e:
                return JSONResponse(content={"status": "error", "message": str(e)})

        def run_server():
            uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        time.sleep(3)

        return True

    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        return False

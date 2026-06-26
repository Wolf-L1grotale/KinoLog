@echo off
echo Generating icon...
python generate_icon.py

echo Building KinoLog...
python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name KinoLog ^
    --icon=kino.ico ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --hidden-import uvicorn ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import pystray._win32 ^
    --hidden-import aiosqlite ^
    --hidden-import PIL ^
    main.py

if exist .env (
    echo Bundling .env...
    copy .env dist\KinoLog.exe.env >nul 2>&1
)

echo.
echo === Build complete ===
echo Executable: dist\KinoLog.exe
echo.
echo Copy dist\KinoLog.exe to project folder and run.
echo Database and .env will be loaded from the exe's directory.
echo.

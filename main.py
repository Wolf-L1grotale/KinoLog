import sys
import os
import threading
import webbrowser
import time

FROZEN = getattr(sys, 'frozen', False)

def get_base_path():
    if FROZEN:
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_bundle_path():
    if FROZEN:
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

base = get_base_path()
bundle = get_bundle_path()
os.chdir(base)

if FROZEN:
    from dotenv import load_dotenv
    env_path = os.path.join(base, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    os.environ["KINOLOG_BUNDLE_PATH"] = bundle

PORT = int(os.environ.get("KINOLOG_PORT", "8000"))
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"

def start_server():
    import traceback
    log_file = os.path.join(base, "kino_log_error.log")
    if FROZEN and sys.stderr is None:
        log_fh = open(log_file, "w", encoding="utf-8")
        sys.stderr = log_fh
        sys.stdout = log_fh
    try:
        import uvicorn
        from app import app
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    except Exception:
        if not FROZEN or sys.stderr is None:
            with open(log_file, "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        else:
            traceback.print_exc(file=sys.stderr)
        raise

def create_icon():
    try:
        from PIL import Image, ImageDraw, ImageFont
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(4, 4), (60, 60)], radius=12, fill=(30, 30, 30, 230))
        draw.text((16, 14), "KL", fill=(255, 255, 255))
        return img
    except Exception:
        return Image.new("RGBA", (64, 64), (30, 30, 30, 230))

def wait_for_server(timeout=15):
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False

def main():
    import pystray

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    if wait_for_server():
        webbrowser.open(URL)
    else:
        log_file = os.path.join(base, "kino_log_error.log")
        msg = f"Сервер не запустился. Проверьте {log_file}"
        try:
            from tkinter import messagebox
            messagebox.showerror("KinoLog", msg)
        except Exception:
            pass

    icon_img = create_icon()

    def on_open(icon, item):
        webbrowser.open(URL)

    def on_quit(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Открыть KinoLog", on_open, default=True),
        pystray.MenuItem(f"Порт: {PORT}", None, enabled=False),
        pystray.MenuItem("Выход", on_quit)
    )

    icon = pystray.Icon("KinoLog", icon_img, "KinoLog", menu)
    icon.run()

if __name__ == "__main__":
    main()

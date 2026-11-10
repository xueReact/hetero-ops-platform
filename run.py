import threading
import webbrowser
import os

from platform_app.http_server import run
from platform_app.config import PORT


if __name__ == "__main__":
    if os.environ.get("FIRE_OPEN_BROWSER", "1") == "1":
        threading.Timer(0.8, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    run()

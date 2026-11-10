import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_DIR / "web"
NETWORK_ASSETS_DIR = WEB_DIR / "assets" / "networks"
# Vercel Functions expose a read-only code bundle. Simulation history may use
# the per-instance temporary directory there; local development keeps its
# project data directory unchanged.
DATA_DIR = Path(os.environ.get("FIRE_RUNTIME_DATA_DIR") or (
    "/tmp/fire-platform" if os.environ.get("VERCEL") else PROJECT_DIR / "platform_app" / "data"
))
TASKS_FILE = DATA_DIR / "tasks.json"
DISPATCHES_FILE = DATA_DIR / "dispatches.json"
SAMPLE_DATA_DIR = PROJECT_DIR / "sample_data"
ENVIRONMENT_FILE = SAMPLE_DATA_DIR / "environment.json"
HOST = os.environ.get("FIRE_HOST", "127.0.0.1")
PORT = int(os.environ.get("FIRE_PORT", "8001"))
# The browser uses a same-origin gateway; only the server knows this address.
AIRPORT_UPSTREAM = os.environ.get("AIRPORT_UPSTREAM", "http://127.0.0.1:8094")
AIRPORT_SITE_DIR = PROJECT_DIR / "simulations" / "airport-upgrade" / "site"

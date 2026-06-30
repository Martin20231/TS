"""Hilfsfunktionen für Launcher, Tracker und Overlays."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

CLOUD_TRACKER_URL = "https://ts-multiplayer-radar.onrender.com/api/position"
CLOUD_MAP_URL = "https://ts-multiplayer-radar.onrender.com"
LOCAL_TRACKER_URL = "http://127.0.0.1:8080/api/position"


def normalize_tracker_url(raw: str) -> str:
    url = raw.strip().rstrip("/")
    if not url:
        return ""
    if url.endswith("/api/position"):
        return url
    return f"{url}/api/position"


def server_base_url(server_url: str) -> str:
    return normalize_tracker_url(server_url).replace("/api/position", "")


def map_url_from_server(server_url: str, session_id: str = "") -> str:
    url = server_base_url(server_url)
    if session_id.strip():
        return f"{url}/?session={session_id.strip()}"
    return url


def radio_url_from_server(server_url: str, player: str, session_id: str = "") -> str:
    base = server_base_url(server_url)
    return f"{base}/radio?player={quote(player)}&session={quote(session_id.strip())}"


def overlay_url_from_server(server_url: str, session_id: str = "") -> str:
    base = server_base_url(server_url)
    url = f"{base}/overlay"
    if session_id.strip():
        return f"{url}?session={session_id.strip()}"
    return url


def is_cloud_server(server_url: str) -> bool:
    url = server_url or ""
    return CLOUD_TRACKER_URL in url or "onrender.com" in url


def is_local_server(server_url: str) -> bool:
    url = (server_url or "").lower()
    return "127.0.0.1" in url or "localhost" in url


def find_raildriver_dll() -> str:
    home = Path.home()
    candidates = [
        Path(r"E:\Steam\steamapps\common\RailWorks\plugins\RailDriver64.dll"),
        Path(r"D:\Steam\steamapps\common\RailWorks\plugins\RailDriver64.dll"),
        Path(r"C:\Steam\steamapps\common\RailWorks\plugins\RailDriver64.dll"),
        home / "Steam" / "steamapps" / "common" / "RailWorks" / "plugins" / "RailDriver64.dll",
        Path(r"C:\Program Files (x86)\Steam\steamapps\common\RailWorks\plugins\RailDriver64.dll"),
        Path(r"C:\Program Files\Steam\steamapps\common\RailWorks\plugins\RailDriver64.dll"),
        Path(os.environ.get("ProgramFiles(x86)", ""))
        / "Steam"
        / "steamapps"
        / "common"
        / "RailWorks"
        / "plugins"
        / "RailDriver64.dll",
        Path(os.environ.get("ProgramFiles", ""))
        / "Steam"
        / "steamapps"
        / "common"
        / "RailWorks"
        / "plugins"
        / "RailDriver64.dll",
    ]
    for path in candidates:
        if path and path.is_file():
            return str(path)
    return ""

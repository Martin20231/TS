"""Gemeinsame Konfiguration für Server und Tracker."""

from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from pathlib import Path


def get_radar_dir() -> Path:
    """Ordner der Exe (gebündelt) oder des radar-Skripts."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


RADAR_DIR = get_radar_dir()
CONFIG_PATH = RADAR_DIR / "config.json"
CACHE_DIR = RADAR_DIR / "cache"

DEFAULT_CONFIG: dict = {
    "player_name": "MeinZug",
    "server_port": 8080,
    "server_host": "0.0.0.0",
    "poll_interval_seconds": 1.0,
    "raildriver_dll_path": (
        r"E:\Steam\steamapps\common\RailWorks\plugins\RailDriver64.dll"
    ),
    "server_url": "http://127.0.0.1:8080/api/position",
    "lines_min_zoom": 10,
    "route_trail_minutes": 30,
    "session_id": "",
    "session_role": "driver",
    "convoy_alert_km": 2.0,
    "mp_ingame_enabled": False,
    "mp_bus_control": "",
    "mp_convoy_push_interval_seconds": 5.0,
}


def load_config() -> dict:
    """Lädt config.json oder legt eine Standarddatei an (nur lokal)."""
    config = deepcopy(DEFAULT_CONFIG)

    if CONFIG_PATH.exists():
        with CONFIG_PATH.open(encoding="utf-8") as handle:
            user_config = json.load(handle)
        if isinstance(user_config, dict):
            config.update(user_config)
    elif not os.environ.get("RENDER"):
        save_config(config)

    if player := os.environ.get("RADAR_PLAYER_NAME"):
        config["player_name"] = player

    return config


def save_config(config: dict) -> None:
    """Speichert die Konfiguration nach config.json."""
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

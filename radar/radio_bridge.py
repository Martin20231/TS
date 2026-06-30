"""
Zugfunk PTT über Lok-Hupe (RailDriver) oder anderen Regler.

Hält die Hupe gedrückt → Funk sendet (radio.html muss offen sein).
"""

from __future__ import annotations

import ctypes
import sys
import time
from pathlib import Path

_RADAR_DIR = Path(__file__).resolve().parent
if str(_RADAR_DIR) not in sys.path:
    sys.path.insert(0, str(_RADAR_DIR))

import requests

from radar_config import load_config
from ts_tracker import (
    establish_connection,
    get_controller_index,
    get_controller_list,
    load_raildriver,
    maintain_connection,
)

PTT_CONTROL_CANDIDATES = (
    "Horn",
    "HornLever",
    "Whistle",
    "Vigilance",
    "Bell",
)

GET_TYPE_CURRENT = 0
PTT_THRESHOLD = 0.08


def server_root(server_url: str) -> str:
    url = server_url.rstrip("/")
    if url.endswith("/api/position"):
        return url[: -len("/api/position")]
    return url


def pick_ptt_control(controllers: list[str]) -> int | None:
    for name in PTT_CONTROL_CANDIDATES:
        index = get_controller_index(controllers, name)
        if index is not None:
            return index
    return None


def post_ptt(api: str, player: str, session_id: str, active: bool) -> None:
    requests.post(
        f"{api}/api/radio/ptt",
        json={"player": player, "session_id": session_id, "active": active},
        timeout=3,
    )


def run_radio_bridge() -> None:
    config = load_config()
    player = config["player_name"]
    session_id = str(config.get("session_id") or "").strip()
    server_url = config["server_url"]
    poll = float(config.get("radio_poll_seconds", 0.05))
    dll_path = config["raildriver_dll_path"]

    if not session_id:
        print("Keine session_id – Funk braucht dieselbe Session wie der Tracker.")
        sys.exit(1)

    api = server_root(server_url)
    dll = load_raildriver(dll_path)
    establish_connection(dll)

    controllers = get_controller_list(dll)
    if not controllers:
        print("Keine Lok-Regler – in TS in einer Fahrt sitzen.")
        sys.exit(1)

    ptt_index = pick_ptt_control(controllers)
    if ptt_index is None:
        print("Kein Hupe-Regler gefunden (Horn/HornLever).")
        sys.exit(1)

    print("=" * 55)
    print("Zugfunk PTT (Hupe)")
    print("=" * 55)
    print(f"Spieler:   {player}")
    print(f"Session:   {session_id}")
    print(f"Regler:    {controllers[ptt_index]}")
    print(f"Server:    {api}")
    print("radio.html muss im Browser offen sein!")
    print("Hupe gedrückt halten = senden")
    print("=" * 55)

    was_active = False
    while True:
        try:
            maintain_connection(dll)
            value = float(dll.GetControllerValue(ptt_index, GET_TYPE_CURRENT))
            active = value >= PTT_THRESHOLD
            if active != was_active:
                post_ptt(api, player, session_id, active)
                if active:
                    print("[Funk] SENDE")
                else:
                    print("[Funk] Ende")
                was_active = active
        except KeyboardInterrupt:
            if was_active:
                post_ptt(api, player, session_id, False)
            print("Funk-PTT beendet.")
            break
        except requests.RequestException as error:
            print(f"Server-Fehler: {error}", file=sys.stderr)

        time.sleep(poll)


if __name__ == "__main__":
    run_radio_bridge()

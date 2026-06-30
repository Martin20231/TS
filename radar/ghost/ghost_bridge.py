"""
Radar → Train Simulator: andere Session-Spieler ins Spiel bringen (Experiment).

Schreibt Entfernung/Richtung des nächsten anderen Zugs auf Lok-Regler (0–1).
Das Szenario-Script ScenarioScript.lua liest diese Werte und zeigt Hinweise /
verschiebt optional ein Objekt GHOST_MP in der Nähe.

Start: start_ghost_bridge.bat (Train Simulator muss laufen, in Lok sitzen)
"""

from __future__ import annotations

import ctypes
import math
import sys
import time
from pathlib import Path

_RADAR_DIR = Path(__file__).resolve().parent.parent
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


def bind_set_controller_value(dll: ctypes.CDLL) -> None:
    if not hasattr(dll, "SetControllerValue"):
        raise RuntimeError("RailDriver: SetControllerValue fehlt in der DLL")
    dll.SetControllerValue.restype = None
    dll.SetControllerValue.argtypes = [ctypes.c_int, ctypes.c_float]

DISTANCE_CONTROL_CANDIDATES = (
    "PassLightValue",
    "InstrumentLightning",
    "ConsoleLightning",
    "MirrorLeft",
    "MirrorRight",
    "SunShade",
)

BEARING_CONTROL_CANDIDATES = (
    "CablightValue",
    "Cablight",
    "WiperInterval",
    "HeadlightsMode",
    "Marker",
)

ACTIVE_CONTROL_CANDIDATES = (
    "Vigilance",
    "WiperControl",
    "SunShade",
)

MAX_DISTANCE_KM = 50.0
GHOST_LIVE_FILENAME = "ghost_live.lua"
GHOST_HTML_FILENAME = "ghost_radar.html"


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def server_root(server_url: str) -> str:
    url = server_url.rstrip("/")
    if url.endswith("/api/position"):
        return url[: -len("/api/position")]
    return url


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    y = math.sin(d_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def pick_control(controllers: list[str], candidates: tuple[str, ...], skip: set[str]) -> int | None:
    for name in candidates:
        if name in skip:
            continue
        index = get_controller_index(controllers, name)
        if index is not None:
            return index
    return None


def player_matches_session(other: dict, session_id: str) -> bool:
    """Mit Session: gleiche Session oder Spieler ohne Session. Ohne Session: alle."""
    if not session_id:
        return True
    other_sid = str(other.get("session_id") or "").strip()
    if not other_sid:
        return True
    return other_sid == session_id


def find_nearest_other_player(
    positions: list[dict],
    player_name: str,
    session_id: str = "",
) -> tuple[dict | None, str]:
    self_pos = next((p for p in positions if p.get("player") == player_name), None)
    if not self_pos:
        return None, "no_self_gps"

    best = None
    best_dist = MAX_DISTANCE_KM
    session_blocked = 0
    too_far = 0

    for other in positions:
        if other.get("player") == player_name:
            continue
        if other.get("active") is False:
            continue
        if session_id and not player_matches_session(other, session_id):
            session_blocked += 1
            continue

        dist = haversine_km(
            self_pos["lat"], self_pos["lon"],
            other["lat"], other["lon"],
        )
        if dist >= MAX_DISTANCE_KM:
            too_far += 1
            continue
        if dist < best_dist:
            best_dist = dist
            best = {
                "name": other["player"],
                "distance_km": dist,
                "bearing_deg": bearing_degrees(
                    self_pos["lat"], self_pos["lon"],
                    other["lat"], other["lon"],
                ),
                "speed_kph": other.get("speed_kph", 0),
            }

    if best is not None:
        return best, "ok"
    if session_blocked:
        return None, "session_mismatch"
    if too_far:
        return None, "too_far"
    return None, "none"


def write_ghost_scenario_files(config: dict, target: dict | None) -> None:
    scenario_path = str(config.get("scenario_path") or "").strip()
    if not scenario_path:
        return
    dest_dir = Path(scenario_path).expanduser()
    live_file = dest_dir / GHOST_LIVE_FILENAME
    html_file = dest_dir / GHOST_HTML_FILENAME
    html_de = dest_dir / "de" / GHOST_HTML_FILENAME

    try:
        if target and target.get("name"):
            safe_name = (
                str(target["name"])
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", " ")
            )
            live_file.write_text(f'return "{safe_name}"\n', encoding="utf-8")

            dist_km = float(target["distance_km"])
            bearing = float(target["bearing_deg"])
            speed = float(target.get("speed_kph") or 0)
            if dist_km < 1.0:
                dist_text = f"{dist_km * 1000:.0f} m"
            else:
                dist_text = f"{dist_km:.1f} km"
            near = dist_km < 2.0
            name_color = "#ff6666" if near else "#4fc3f7"
            status = "NAHE!" if near else "Online"
            html = (
                "<HTML>\n<BODY BGCOLOR=\"#1a2838\">\n"
                "<FONT FACE=\"Arial\" COLOR=\"#FFFFFF\" SIZE=\"3\">\n"
                "<P><B>Multiplayer-Radar</B></P>\n"
                f"<P><FONT COLOR=\"{name_color}\"><B>{_escape_html(str(target['name']))}</B></FONT>"
                f" · {status}</P>\n"
                f"<P>Entfernung: {dist_text}<BR>\n"
                f"Richtung: {bearing:.0f}°<BR>\n"
                f"Geschwindigkeit: {speed:.0f} km/h</P>\n"
                "<P><FONT SIZE=\"2\" COLOR=\"#666666\">"
                "Menü schliessen = weiterfahren · Alert erneut klicken zum Aktualisieren</FONT></P>\n"
                "</FONT>\n</BODY>\n</HTML>\n"
            )
            html_file.write_text(html, encoding="utf-8")
            html_de.parent.mkdir(parents=True, exist_ok=True)
            html_de.write_text(html, encoding="utf-8")
        else:
            live_file.write_text('return ""\n', encoding="utf-8")
            empty_html = (
                "<HTML><BODY BGCOLOR=\"#1a2838\">"
                "<FONT FACE=\"Arial\" COLOR=\"#888888\" SIZE=\"3\">"
                "<P><B>Multiplayer-Radar</B></P>"
                "<P>Kein anderer Spieler sichtbar</P></FONT></BODY></HTML>\n"
            )
            html_file.write_text(empty_html, encoding="utf-8")
            html_de.parent.mkdir(parents=True, exist_ok=True)
            html_de.write_text(empty_html, encoding="utf-8")
    except OSError as error:
        print(f"[Ghost] Szenario-Dateien nicht schreibbar: {error}", flush=True)


def write_bus(
    dll: ctypes.CDLL,
    dist_index: int,
    bearing_index: int,
    active_index: int,
    target: dict | None,
) -> None:
    if target is None:
        dll.SetControllerValue(dist_index, ctypes.c_float(0.0))
        dll.SetControllerValue(bearing_index, ctypes.c_float(0.0))
        dll.SetControllerValue(active_index, ctypes.c_float(0.0))
        return

    dist_frac = min(target["distance_km"], MAX_DISTANCE_KM) / MAX_DISTANCE_KM
    bearing_frac = target["bearing_deg"] / 360.0
    active_frac = 0.55

    dll.SetControllerValue(dist_index, ctypes.c_float(dist_frac))
    dll.SetControllerValue(bearing_index, ctypes.c_float(bearing_frac))
    dll.SetControllerValue(active_index, ctypes.c_float(active_frac))


def run_ghost_bridge() -> None:
    config = load_config()
    player_name = config["player_name"]
    session_id = str(config.get("session_id") or "").strip()
    if len(sys.argv) > 1 and sys.argv[1].strip():
        session_id = sys.argv[1].strip()
    server_url = config["server_url"]
    poll = float(config.get("ghost_poll_seconds", 0.5))
    dll_path = config["raildriver_dll_path"]

    api = f"{server_root(server_url)}/api/positions"
    dll = load_raildriver(dll_path)
    bind_set_controller_value(dll)
    establish_connection(dll)

    controllers = get_controller_list(dll)
    if not controllers:
        print("Keine Lok-Regler – bist du in einer Fahrt?")
        sys.exit(1)

    used: set[str] = set()
    dist_index = pick_control(controllers, DISTANCE_CONTROL_CANDIDATES, used)
    if dist_index is None:
        print("Kein Regler für Entfernung gefunden.")
        sys.exit(1)
    used.add(controllers[dist_index])

    bearing_index = pick_control(controllers, BEARING_CONTROL_CANDIDATES, used)
    if bearing_index is None:
        print("Kein Regler für Richtung gefunden.")
        sys.exit(1)
    used.add(controllers[bearing_index])

    active_index = pick_control(controllers, ACTIVE_CONTROL_CANDIDATES, used)
    if active_index is None:
        print("Kein Regler für Aktiv-Flag gefunden.")
        sys.exit(1)

    print("=" * 55)
    print("Ghost-Bridge (Experiment)")
    print("=" * 55)
    print(f"Spieler:   {player_name}")
    if session_id:
        print(f"Session:   {session_id} (optional – Kumpel ohne Session geht auch)")
    else:
        print("Session:   keine – nächster Spieler auf der ganzen Karte")
    print(f"Server:    {api}")
    scenario_path = str(config.get("scenario_path") or "").strip()
    if scenario_path:
        print(f"Szenario:  {scenario_path}")
        print(f"Menü-Datei: {GHOST_HTML_FILENAME} (live HTML im Szenario)")
    else:
        print("Szenario:  nicht gesetzt – Name im HUD fehlt (scenario_path in config.json)")
    print("=" * 55)
    sys.stdout.flush()

    last_log = ""
    tick = 0
    while True:
        try:
            maintain_connection(dll)
            response = requests.get(api, timeout=15)
            response.raise_for_status()
            positions = response.json()
            target, reason = find_nearest_other_player(positions, player_name, session_id)
            write_bus(dll, dist_index, bearing_index, active_index, target)
            write_ghost_scenario_files(config, target)

            others = [
                p.get("player")
                for p in positions
                if p.get("player") != player_name and p.get("active") is not False
            ]
            on_server = any(p.get("player") == player_name for p in positions)

            if target:
                msg = (
                    f"[Ghost] {target['name']}: {target['distance_km']:.1f} km, "
                    f"Richtung {target['bearing_deg']:.0f}°"
                )
            elif not on_server:
                msg = "[Ghost] Du sendest keine GPS – TS-Radar.exe starten (Fahrt + Lok)"
            elif reason == "session_mismatch":
                msg = (
                    "[Ghost] Spieler online, aber andere Session – "
                    "session_id in config leeren oder Freund gleichen Code"
                )
            elif reason == "too_far":
                msg = f"[Ghost] Spieler online, aber > {MAX_DISTANCE_KM:.0f} km entfernt"
            elif others:
                msg = f"[Ghost] Warte … ({len(others)} online: {', '.join(others)})"
            else:
                msg = "[Ghost] Kein anderer Spieler auf dem Server"

            tick += 1
            if msg != last_log or tick % 20 == 0:
                online = ", ".join(others) if others else "–"
                print(f"{msg}  |  Online: {online}", flush=True)
                last_log = msg
        except KeyboardInterrupt:
            print("Ghost-Bridge beendet.")
            write_bus(dll, dist_index, bearing_index, active_index, None)
            break
        except requests.RequestException as error:
            print(f"Server-Fehler: {error}", file=sys.stderr, flush=True)

        time.sleep(poll)


if __name__ == "__main__":
    run_ghost_bridge()

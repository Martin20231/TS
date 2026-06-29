"""
Kleiner Radar-Server: empfängt GPS vom Tracker und liefert sie an die Web-Karte.

Starten:  start_radar.bat   oder   python server.py
Karte:    http://localhost:8080
"""

import os

if os.environ.get("RENDER"):
    from gevent import monkey

    monkey.patch_all()

from pathlib import Path
import json
import socket
import time

import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit

from radar_config import CACHE_DIR, load_config
from mp_geo import nearest_station
from mp_session import SessionStore

CONFIG = load_config()
SESSIONS = SessionStore()

app = Flask(__name__)
_async_mode = "gevent" if os.environ.get("RENDER") else "threading"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=_async_mode)

SERVER_HOST = CONFIG["server_host"]
SERVER_PORT = int(os.environ.get("PORT", CONFIG["server_port"]))
_background_started = False

# Spieler verschwinden von der Karte, wenn der Tracker nicht mehr sendet (Spiel beendet / Absturz)
PLAYER_TIMEOUT_SECONDS = 30

# Aktuelle Spielerpositionen: { "Spielername": { lat, lon, speed, heading, ... } }
positions: dict[str, dict] = {}

# Gecachte S-Bahn-Stationen und -Linien (OpenStreetMap)
stations_cache: list[dict] | None = None
lines_cache: list[dict] | None = None
stations_loading = False
lines_loading = False
lines_load_error: str | None = None
lines_load_progress = {"done": 0, "total": 0, "current": ""}
_last_broadcast_payload: str | None = None
_last_session_broadcast: dict[str, str] = {}

RADAR_DIR = Path(__file__).parent
STATIC_DIR = RADAR_DIR / "static"
STATIONS_CACHE_FILE = CACHE_DIR / "stations.json"
LINES_CACHE_FILE = CACHE_DIR / "lines.json"

# Berlin + Brandenburg-Umland (inkl. Flughafen BER / S9 / S45 / S46 / S8 / S85)
SBahn_BBOX = (52.15, 12.95, 52.85, 14.0)

# Offizielle S-Bahn Berlin Linienfarben
SBahn_LINE_COLORS: dict[str, str] = {
    "S1": "#DA6BA1",
    "S2": "#007734",
    "S3": "#0066AD",
    "S5": "#EB7405",
    "S7": "#816DA6",
    "S8": "#004280",
    "S9": "#992546",
    "S25": "#008D4F",
    "S26": "#00A78E",
    "S41": "#FFD500",
    "S42": "#FFD500",
    "S45": "#CDA075",
    "S46": "#D472AA",
    "S47": "#A05219",
    "S75": "#EE7C00",
    "S85": "#00998F",
}

OVERPASS_STATIONS_QUERY = """
[out:json][timeout:90];
node["railway"~"station|halt"]({south},{west},{north},{east});
out body;
"""


def is_sbahn_station(tags: dict) -> bool:
    """Erkennt Berliner S-Bahn-Halte anhand typischer OSM-Tags."""
    name = tags.get("name", "")
    network = tags.get("network", "")
    operator = tags.get("operator", "")

    if "S-Bahn" in network or "S-Bahn" in operator:
        return True
    if name.startswith("S "):
        return True
    if tags.get("light_rail") == "yes":
        return True
    if tags.get("station") == "light_rail":
        return True
    if tags.get("subway") == "yes" and "Berlin" in operator:
        return True
    if "sbahn.berlin" in tags.get("website", ""):
        return True

    return False


def get_public_base_url() -> str:
    """Öffentliche URL (Render) oder lokale LAN-URL für Freunde."""
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if render_url:
        return render_url

    local_ip = get_local_ip()
    if local_ip != "127.0.0.1":
        return f"http://{local_ip}:{SERVER_PORT}"
    return f"http://localhost:{SERVER_PORT}"


def ensure_background_tasks() -> None:
    """Startet Hintergrund-Jobs (auch unter gunicorn auf Render)."""
    global _background_started
    if _background_started:
        return
    _background_started = True
    socketio.start_background_task(stale_broadcast_loop)
    socketio.start_background_task(warmup_map_data)


@app.before_request
def _start_background_on_first_request():
    if request.path in ("/api/health", "/api/status"):
        return
    ensure_background_tasks()


@app.get("/api/health")
def health_check():
    """Schneller Health-Check für Render (ohne Hintergrund-Jobs)."""
    return jsonify({"ok": True}), 200


def get_local_ip() -> str:
    """Ermittelt die LAN-IP für Freunde im selben Netzwerk."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def purge_stale_positions() -> list[tuple[str, str | None]]:
    """Entfernt Spieler ohne frische Tracker-Daten von der Karte."""
    now = time.time()
    removed: list[tuple[str, str | None]] = []

    for player, entry in list(positions.items()):
        if now - entry["timestamp"] >= PLAYER_TIMEOUT_SECONDS:
            session_id = entry.get("session_id")
            removed.append((player, session_id))
            del positions[player]
            SESSIONS.on_player_disconnect(player)

    return removed


def build_positions_payload(session_id: str | None = None) -> list[dict]:
    """Baut die Spielerliste für REST und WebSocket (nur aktive Tracker)."""
    purge_stale_positions()
    result = []

    for entry in positions.values():
        if session_id and entry.get("session_id") != session_id:
            continue

        result.append({
            **entry,
            "active": True,
            "last_seen": entry["timestamp"],
            "offline_seconds": 0,
        })

    return result


def positions_lookup() -> dict[str, dict]:
    """Aktive Spieler als Dict für Session-Logik."""
    lookup: dict[str, dict] = {}
    for entry in build_positions_payload():
        lookup[entry["player"]] = entry
    return lookup


def broadcast_session(session_id: str) -> None:
    """Sendet Session-Update (Lobby, Leitstand, Trails)."""
    global _last_session_broadcast

    payload = SESSIONS.session_payload(session_id, positions_lookup())
    if payload is None:
        return

    digest = json.dumps(payload, sort_keys=True, default=str)
    if _last_session_broadcast.get(session_id) == digest:
        return

    _last_session_broadcast[session_id] = digest
    socketio.emit("session_update", payload, room=f"session:{session_id}")


def broadcast_positions() -> None:
    """Sendet Positions-Updates per WebSocket an alle verbundenen Karten."""
    global _last_broadcast_payload

    payload = build_positions_payload()
    digest = json.dumps(payload, sort_keys=True, default=str)
    if digest == _last_broadcast_payload:
        return

    _last_broadcast_payload = digest
    socketio.emit("positions_update", payload)


def stale_broadcast_loop() -> None:
    """Entfernt abgestürzte Spieler und aktualisiert Karte + Sessions."""
    global _last_broadcast_payload

    while True:
        socketio.sleep(5)
        removed = purge_stale_positions()
        if removed:
            _last_broadcast_payload = None
            session_ids = {sid for _, sid in removed if sid}
            for sid in session_ids:
                _last_session_broadcast.pop(sid, None)
                broadcast_session(sid)
        broadcast_positions()


def load_disk_cache(path: Path) -> list[dict] | None:
    """Lädt zwischengespeicherte OSM-Daten von der Festplatte."""
    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else None
    except (OSError, json.JSONDecodeError) as error:
        print(f"Cache konnte nicht gelesen werden ({path.name}): {error}")
        return None


def save_disk_cache(path: Path, data: list[dict]) -> None:
    """Speichert OSM-Daten für schnellere Neustarts."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False)


@app.get("/api/cache/status")
def get_cache_status():
    """Zeigt an, ob Stationen/Linien bereit sind (für Fortschrittsanzeige in der Karte)."""
    return jsonify({
        "stations_ready": stations_cache is not None,
        "stations_loading": stations_loading,
        "lines_ready": lines_cache is not None,
        "lines_loading": lines_loading,
        "lines_error": lines_load_error,
        "lines_progress": lines_load_progress,
        "stations_count": len(stations_cache) if stations_cache else 0,
        "lines_count": len(lines_cache) if lines_cache else 0,
    })


def load_stations_cache() -> None:
    """Lädt Stationen von Festplatte oder OpenStreetMap (einmalig)."""
    global stations_cache, stations_loading

    if stations_cache is not None or stations_loading:
        return

    stations_loading = True
    try:
        stations_cache = load_disk_cache(STATIONS_CACHE_FILE)
        if stations_cache is not None:
            print(f"S-Bahn-Stationen aus Festplatten-Cache: {len(stations_cache)}")
            return

        for attempt in range(3):
            try:
                stations_cache = fetch_sbahn_stations()
                save_disk_cache(STATIONS_CACHE_FILE, stations_cache)
                print(f"S-Bahn-Stationen von OpenStreetMap: {len(stations_cache)} (Cache gespeichert)")
                return
            except requests.RequestException as error:
                print(f"Overpass-Fehler (Stationen, Versuch {attempt + 1}/3): {error}")
                time.sleep(3 * (attempt + 1))
        stations_cache = None
    finally:
        stations_loading = False


def load_lines_cache() -> None:
    """Lädt Linien von Festplatte oder OpenStreetMap (einmalig, kann 1–2 Min. dauern)."""
    global lines_cache, lines_loading, lines_load_error, lines_load_progress

    if lines_cache is not None or lines_loading:
        return

    lines_loading = True
    lines_load_error = None
    lines_load_progress = {
        "done": 0,
        "total": len(SBahn_LINE_COLORS),
        "current": "",
    }

    try:
        lines_cache = load_disk_cache(LINES_CACHE_FILE)
        if lines_cache is not None:
            print(f"S-Bahn-Linien aus Festplatten-Cache: {len(lines_cache)} Abschnitte")
            return

        print("S-Bahn-Linien werden von OpenStreetMap geladen (einmalig, ~1–2 Min.) …")
        lines_cache = fetch_sbahn_lines()
        save_disk_cache(LINES_CACHE_FILE, lines_cache)
        unique_lines = len({segment["line"] for segment in lines_cache})
        print(
            f"S-Bahn-Linien von OpenStreetMap: {unique_lines} Linien, "
            f"{len(lines_cache)} Abschnitte (Cache gespeichert)"
        )
    except requests.RequestException as error:
        lines_load_error = str(error)
        lines_cache = None
        print(f"Overpass-Linien-Fehler: {error}")
    finally:
        lines_loading = False
        lines_load_progress["current"] = ""


def warmup_map_data() -> None:
    """Lädt Karten-Daten parallel im Hintergrund."""
    socketio.start_background_task(load_stations_cache)
    socketio.start_background_task(load_lines_cache)


@app.get("/api/config")
def get_radar_config():
    """Liefert Einstellungen für Karte und Freunde im Netzwerk."""
    public_base = get_public_base_url()
    return jsonify({
        "player_name": CONFIG["player_name"],
        "server_port": SERVER_PORT,
        "lines_min_zoom": int(CONFIG.get("lines_min_zoom", 10)),
        "route_trail_minutes": int(CONFIG.get("route_trail_minutes", 30)),
        "map_url": public_base,
        "lan_map_url": public_base,
        "friend_tracker_url": f"{public_base}/api/position",
        "cloud": bool(os.environ.get("RENDER")),
        "convoy_alert_km": float(CONFIG.get("convoy_alert_km", 2.0)),
        "overlay_url": f"{public_base}/overlay",
    })


@app.route("/")
def index():
    """Haupt-Karte mit Multiplayer-Panel."""
    return send_from_directory(RADAR_DIR, "index.html")


@app.route("/overlay")
def overlay_page():
    """Kompaktes Zweitmonitor-Overlay."""
    return send_from_directory(STATIC_DIR, "overlay.html")


@app.route("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(STATIC_DIR, filename)


@app.post("/api/position")
def post_position():
    """Empfängt Positions-Updates vom Python-Tracker."""
    data = request.get_json(force=True)
    player = str(data.get("player", "Unbekannt"))

    session_id = str(data.get("session_id", "") or "").strip() or None
    lat = float(data["lat"])
    lon = float(data["lon"])
    speed_kph = float(data.get("speed_kph", 0))
    heading = float(data.get("heading", 0))

    near = None
    if stations_cache:
        near = nearest_station(lat, lon, stations_cache, max_km=5.0)

    positions[player] = {
        "player": player,
        "lat": lat,
        "lon": lon,
        "speed_kph": speed_kph,
        "heading": heading,
        "timestamp": data.get("timestamp", time.time()),
        "session_id": session_id,
        "role": str(data.get("role", "driver")),
        "loco": str(data.get("loco", "")),
        "nearest_stop": near["name"] if near else "",
        "nearest_stop_km": round(near["distance_km"], 2) if near else None,
    }

    if session_id:
        SESSIONS.join(
            session_id,
            player,
            role=str(data.get("role", "driver")),
            loco=str(data.get("loco", "")),
        )
        SESSIONS.update_position(
            session_id,
            player,
            lat,
            lon,
            speed_kph,
            heading,
            loco=str(data.get("loco", "")),
            nearest_station_name=near["name"] if near else None,
            nearest_station_km=near["distance_km"] if near else None,
        )
        broadcast_session(session_id)

    broadcast_positions()
    return jsonify({"ok": True})


@app.delete("/api/position")
def delete_position():
    """Entfernt einen Spieler sofort von der Karte (Tracker-Shutdown / Spiel beendet)."""
    global _last_broadcast_payload

    data = request.get_json(force=True, silent=True) or {}
    player = str(data.get("player", request.args.get("player", ""))).strip()
    if not player or player not in positions:
        return jsonify({"ok": True})

    session_id = positions[player].get("session_id")
    del positions[player]
    SESSIONS.on_player_disconnect(player)

    _last_broadcast_payload = None
    broadcast_positions()
    if session_id:
        _last_session_broadcast.pop(session_id, None)
        broadcast_session(session_id)

    return jsonify({"ok": True})


@app.get("/api/positions")
def get_positions():
    """Liefert aktive und kürzlich offline Spieler an die Karte (REST-Fallback)."""
    return jsonify(build_positions_payload())


@app.get("/api/status")
def get_status():
    """Kurzinfo für Verbindungstest und Freunde im Netzwerk."""
    payload = build_positions_payload()
    return jsonify({
        "ok": True,
        "players_online": sum(1 for p in payload if p["active"]),
        "players_total": len(payload),
        "websocket": True,
        "port": SERVER_PORT,
    })


@socketio.on("connect")
def handle_connect():
    """Neue Karten-Verbindung – sofort aktuellen Stand senden."""
    emit("positions_update", build_positions_payload())


@socketio.on("join_session")
def handle_join_session(data):
    """Client abonniert Session-Updates (Lobby / Leitstand)."""
    session_id = str((data or {}).get("session_id", "")).strip()
    if not session_id or SESSIONS.get(session_id) is None:
        return
    from flask_socketio import join_room

    join_room(f"session:{session_id}")
    payload = SESSIONS.session_payload(session_id, positions_lookup())
    if payload:
        emit("session_update", payload)


def simplify_coordinates(coords: list[list[float]], step: int = 4) -> list[list[float]]:
    """Reduziert Koordinatenpunkte für flüssigere Karten-Darstellung."""
    if len(coords) <= 2:
        return coords

    simplified = coords[::step]
    if simplified[-1] != coords[-1]:
        simplified.append(coords[-1])
    return simplified


def overpass_post(query: str, timeout: int = 90) -> requests.Response:
    """Sendet eine Overpass-Abfrage mit Fallback-Servern und Wiederholungen."""
    overpass_urls = (
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    )

    last_error: requests.RequestException | None = None

    for url in overpass_urls:
        for attempt in range(3):
            try:
                response = requests.post(
                    url,
                    data={"data": query},
                    headers={"User-Agent": "TrainSimulator-Radar/1.0 (local dev)"},
                    timeout=timeout,
                )
                if response.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response
            except requests.RequestException as error:
                last_error = error
                time.sleep(2 * (attempt + 1))

    if last_error is not None:
        raise last_error
    raise requests.RequestException("Overpass-Abfrage fehlgeschlagen")


def fetch_sbahn_stations() -> list[dict]:
    """Lädt S-Bahn-Stationen aus OpenStreetMap (Overpass API)."""
    south, west, north, east = SBahn_BBOX
    query = OVERPASS_STATIONS_QUERY.format(
        south=south, west=west, north=north, east=east
    )

    response = overpass_post(query, timeout=90)

    seen: set[str] = set()
    stations: list[dict] = []

    for element in response.json().get("elements", []):
        if element.get("type") != "node":
            continue

        tags = element.get("tags", {})
        if not is_sbahn_station(tags):
            continue

        name = tags.get("name") or tags.get("official_name")
        if not name:
            continue

        lat = element.get("lat")
        lon = element.get("lon")
        if lat is None or lon is None:
            continue

        # Anzeigename: „S “-Präfix wie im Simulator, falls noch nicht vorhanden
        display_name = name if name.startswith("S ") else f"S {name}"

        # Duplikate vermeiden (gleicher Name + gerundete Koordinate)
        key = f"{name}|{round(lat, 5)}|{round(lon, 5)}"
        if key in seen:
            continue
        seen.add(key)

        stations.append({"name": display_name, "lat": lat, "lon": lon})

    stations.sort(key=lambda s: s["name"])
    return stations


@app.get("/api/stations/sbahn")
def get_sbahn_stations():
    """Liefert S-Bahn-Stationen für die Karte."""
    if stations_cache is None and not stations_loading:
        load_stations_cache()

    if stations_cache is None:
        if stations_loading:
            return jsonify({
                "loading": True,
                "message": "Stationen werden geladen …",
            }), 503
        return jsonify({"error": "Stationen nicht verfügbar", "stations": []}), 502

    return jsonify(stations_cache)


def fetch_line_segments(line_ref: str, south: float, west: float, north: float, east: float) -> list[dict]:
    """Lädt Wege einer einzelnen S-Bahn-Linie im Kartenausschnitt."""
    query = f"""
    [out:json][timeout:90];
    relation["route"="light_rail"]["ref"="{line_ref}"]->.r;
    way(r.r)({south},{west},{north},{east});
    out geom;
    """

    overpass_urls = (
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    )

    response = None
    for url in overpass_urls:
        for attempt in range(3):
            try:
                response = requests.post(
                    url,
                    data={"data": query},
                    headers={"User-Agent": "TrainSimulator-Radar/1.0 (local dev)"},
                    timeout=90,
                )
                if response.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                response.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2)
        if response is not None and response.ok:
            break

    if response is None or not response.ok:
        return []

    color = SBahn_LINE_COLORS.get(line_ref, "#555555")
    segments: list[dict] = []

    for element in response.json().get("elements", []):
        if element.get("type") != "way":
            continue
        geometry = element.get("geometry")
        if not geometry:
            continue

        coordinates = simplify_coordinates(
            [[point["lat"], point["lon"]] for point in geometry]
        )
        if len(coordinates) < 2:
            continue

        segments.append({
            "line": line_ref,
            "color": color,
            "coordinates": coordinates,
        })

    return segments


def fetch_sbahn_lines() -> list[dict]:
    """Lädt alle S-Bahn-Streckenabschnitte in einer Overpass-Abfrage."""
    global lines_load_progress

    south, west, north, east = SBahn_BBOX
    line_refs = list(SBahn_LINE_COLORS.keys())
    ref_filter = "|".join(line_refs)

    lines_load_progress = {
        "done": 0,
        "total": 1,
        "current": "OpenStreetMap",
    }

    query = f"""
    [out:json][timeout:180];
    (
      relation["route"="light_rail"]["ref"~"^({ref_filter})$"]({south},{west},{north},{east});
    );
    out body;
    >;
    out geom qt;
    """

    overpass_urls = (
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    )

    response = None
    last_error: requests.RequestException | None = None
    for url in overpass_urls:
        for attempt in range(3):
            try:
                response = requests.post(
                    url,
                    data={"data": query},
                    headers={"User-Agent": "TrainSimulator-Radar/1.0 (local dev)"},
                    timeout=180,
                )
                if response.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                response.raise_for_status()
                break
            except requests.RequestException as error:
                last_error = error
                time.sleep(2 * (attempt + 1))
        if response is not None and response.ok:
            break

    if response is None or not response.ok:
        if last_error is not None:
            raise last_error
        raise requests.RequestException("Overpass-Linien-Abfrage fehlgeschlagen")

    elements = response.json().get("elements", [])
    ways = {
        element["id"]: element
        for element in elements
        if element.get("type") == "way" and element.get("geometry")
    }

    segments: list[dict] = []
    per_line_counts: dict[str, int] = {}

    for element in elements:
        if element.get("type") != "relation":
            continue

        line_ref = element.get("tags", {}).get("ref")
        if line_ref not in SBahn_LINE_COLORS:
            continue

        color = SBahn_LINE_COLORS[line_ref]
        lines_load_progress["current"] = line_ref

        for member in element.get("members", []):
            if member.get("type") != "way" or member.get("role") == "platform":
                continue

            way = ways.get(member.get("ref"))
            if not way:
                continue

            coordinates = simplify_coordinates(
                [[point["lat"], point["lon"]] for point in way["geometry"]]
            )
            if len(coordinates) < 2:
                continue

            segments.append({
                "line": line_ref,
                "color": color,
                "coordinates": coordinates,
            })
            per_line_counts[line_ref] = per_line_counts.get(line_ref, 0) + 1

    for line_ref, count in sorted(per_line_counts.items()):
        print(f"  Linie {line_ref}: {count} Abschnitte")

    lines_load_progress["done"] = 1
    lines_load_progress["current"] = ""
    return segments


@app.get("/api/lines/sbahn")
def get_sbahn_lines():
    """Liefert S-Bahn-Streckenverläufe für die Karte."""
    if lines_cache is None and not lines_loading and lines_load_error is None:
        socketio.start_background_task(load_lines_cache)

    if lines_cache is None:
        if lines_loading:
            progress = lines_load_progress
            current = progress.get("current") or "…"
            done = progress.get("done", 0)
            total = progress.get("total") or len(SBahn_LINE_COLORS)
            return jsonify({
                "loading": True,
                "message": "Linien werden von OpenStreetMap geladen (einmalig, ~30–60 s) …",
                "progress": progress,
            }), 503
        if lines_load_error:
            return jsonify({"error": lines_load_error, "lines": []}), 502
        return jsonify({
            "loading": True,
            "message": "Linien werden vorbereitet …",
        }), 503

    return jsonify(lines_cache)


@app.post("/api/sessions")
def create_session():
    data = request.get_json(force=True) or {}
    session = SESSIONS.create(str(data.get("name", "Fahrt")))
    base = get_public_base_url()
    return jsonify({
        "ok": True,
        "session_id": session.session_id,
        "name": session.name,
        "join_url": f"{base}/?session={session.session_id}",
    })


@app.get("/api/sessions/<session_id>")
def get_session(session_id: str):
    payload = SESSIONS.session_payload(session_id, positions_lookup())
    if payload is None:
        return jsonify({"ok": False, "error": "Session nicht gefunden"}), 404
    return jsonify({"ok": True, **payload})


@app.post("/api/sessions/<session_id>/join")
def join_session_api(session_id: str):
    data = request.get_json(force=True) or {}
    player = str(data.get("player", CONFIG["player_name"]))
    role = str(data.get("role", "driver"))
    loco = str(data.get("loco", ""))
    session = SESSIONS.join(session_id, player, role=role, loco=loco)
    if session is None:
        return jsonify({"ok": False, "error": "Session nicht gefunden"}), 404
    broadcast_session(session_id)
    payload = SESSIONS.session_payload(session_id, positions_lookup())
    return jsonify({"ok": True, **payload})


@app.post("/api/sessions/<session_id>/ready")
def session_ready(session_id: str):
    data = request.get_json(force=True) or {}
    player = str(data.get("player", CONFIG["player_name"]))
    ready = bool(data.get("ready", True))
    if not SESSIONS.set_ready(session_id, player, ready):
        return jsonify({"ok": False, "error": "Spieler nicht in Session"}), 400
    broadcast_session(session_id)
    return jsonify({"ok": True})


@app.post("/api/sessions/<session_id>/messages")
def post_session_message(session_id: str):
    data = request.get_json(force=True) or {}
    sender = str(data.get("sender", CONFIG["player_name"]))
    text = str(data.get("text", ""))
    target = data.get("target")
    target_str = str(target).strip() if target else None

    msg = SESSIONS.add_message(session_id, sender, text, target=target_str)
    if msg is None:
        return jsonify({"ok": False, "error": "Nachricht konnte nicht gesendet werden"}), 400

    broadcast_session(session_id)
    socketio.emit(
        "dispatch_message",
        {
            "id": msg.id,
            "sender": msg.sender,
            "target": msg.target,
            "text": msg.text,
            "timestamp": msg.timestamp,
            "session_id": session_id,
        },
        room=f"session:{session_id}",
    )
    return jsonify({
        "ok": True,
        "message": {
            "id": msg.id,
            "sender": msg.sender,
            "target": msg.target,
            "text": msg.text,
            "timestamp": msg.timestamp,
        },
    })


@app.get("/api/sessions/<session_id>/messages")
def get_session_messages(session_id: str):
    after = int(request.args.get("after", 0))
    messages = SESSIONS.messages_after(session_id, after)
    return jsonify({
        "messages": [
            {
                "id": m.id,
                "sender": m.sender,
                "target": m.target,
                "text": m.text,
                "timestamp": m.timestamp,
            }
            for m in messages
        ],
    })


@app.get("/api/sessions/<session_id>/convoy")
def get_convoy(session_id: str):
    player = request.args.get("player", CONFIG["player_name"])
    convoy = SESSIONS.build_convoy(session_id, player, positions_lookup())
    return jsonify({"convoy": convoy})


if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 55)
    print("TS Multiplayer-Radar – Server")
    print("=" * 55)
    print(f"Lokal:       http://localhost:{SERVER_PORT}")
    print(f"Im Netzwerk: http://{local_ip}:{SERVER_PORT}")
    print(f"Tracker-URL: http://{local_ip}:{SERVER_PORT}/api/position")
    print("WebSocket:   aktiv (Live-Updates)")
    print(f"Spielername: {CONFIG['player_name']}  (in config.json ändern)")
    print(f"Overlay:     http://{local_ip}:{SERVER_PORT}/overlay")
    print("=" * 55)

    socketio.start_background_task(stale_broadcast_loop)
    socketio.start_background_task(warmup_map_data)
    socketio.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        allow_unsafe_werkzeug=True,
    )


# Gunicorn auf Render (und andere PaaS)
application = app

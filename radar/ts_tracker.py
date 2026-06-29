"""
Train Simulator Classic – GPS-Tracker für ein externes Multiplayer-Radar.

Liest Breiten- und Längengrad über die RailDriver.dll aus dem Spiel
und sendet die Position periodisch an einen Server (Platzhalter vorbereitet).

Wichtig:
  - Train Simulator muss laufen und du musst in einer Fahrt sitzen.
  - Python muss dieselbe Bittiefe wie die DLL haben (meist 32-Bit Python
    für RailDriver.dll, oder 64-Bit Python für RailDriver64.dll).
"""

import ctypes
import math
import sys
import time

import requests

from http_session import create_http_session
from radar_config import CONFIG_PATH, load_config

# Virtuelle Controller-IDs laut offizieller External-Interface-API
CONTROLLER_LATITUDE = 400   # Breitengrad
CONTROLLER_LONGITUDE = 401  # Längengrad
CONTROLLER_HEADING = 405    # Fahrtrichtung in Grad (0–360)

# Geschwindigkeit ist lok-abhängig – bekannte Tachometer-Namen (Reihenfolge = Priorität)
SPEED_CONTROLLER_NAMES = (
    "TachoKmh",
    "TachoKMH",
    "SpeedometerKPH",
    "SpeedometerKMH",
    "SpeedometerMPH",
    "Speedometer",
)

# Schlüsselwörter für automatische Suche, falls kein bekannter Name passt
SPEED_NAME_KEYWORDS = ("tacho", "speedometer", "geschwindigkeit")
SPEED_NAME_SKIP = ("control", "selector", "light", "soll", "steller")

# getType für GetControllerValue: 0 = aktueller Wert, 1 = Minimum, 2 = Maximum
GET_TYPE_CURRENT = 0

# URL des Radar-Servers – in config.json anpassen (server_url)


# ---------------------------------------------------------------------------
# RailDriver.dll laden und Funktionen binden
# ---------------------------------------------------------------------------

def load_raildriver(dll_path: str) -> ctypes.CDLL:
    """
    Lädt die RailDriver.dll über ctypes und konfiguriert die Funktionssignaturen.

    Args:
        dll_path: Vollständiger Pfad zur DLL im plugins-Ordner.

    Returns:
        Geladenes ctypes.CDLL-Objekt mit gebundenen API-Funktionen.
    """
    try:
        dll = ctypes.CDLL(dll_path)
    except OSError as error:
        print(
            f"Fehler beim Laden der DLL:\n  {dll_path}\n\n"
            f"Details: {error}\n\n"
            "Prüfe:\n"
            "  - Ist der Pfad korrekt?\n"
            "  - Läuft Train Simulator?\n"
            "  - Stimmt die Python-Bittiefe (32/64) mit der DLL überein?",
            file=sys.stderr,
        )
        raise SystemExit(1) from error

    # --- GetControllerValue(int controllerId, int getType) -> float ---
    dll.GetControllerValue.restype = ctypes.c_float
    dll.GetControllerValue.argtypes = [ctypes.c_int, ctypes.c_int]

    dll.GetControllerList.restype = ctypes.c_char_p
    dll.GetControllerList.argtypes = None

    dll.GetRailSimLocoChanged.restype = ctypes.c_bool
    dll.GetRailSimLocoChanged.argtypes = None

    try:
        dll.GetLocoName.restype = ctypes.c_char_p
        dll.GetLocoName.argtypes = None
        dll._has_loco_name = True  # type: ignore[attr-defined]
    except AttributeError:
        dll._has_loco_name = False  # type: ignore[attr-defined]

    # --- Verbindungsfunktionen ---
    # In manchen Anleitungen heißt die Verbindungsfunktion „SetRailDriverMode“.
    # Die offizielle TS-API exportiert stattdessen SetRailSimConnected / SetRailDriverConnected.
    # Wir versuchen zuerst SetRailDriverMode(1), sonst den offiziellen Weg.
    connection_mode = {"use_set_raildriver_mode": False}

    try:
        dll.SetRailDriverMode.restype = None
        dll.SetRailDriverMode.argtypes = [ctypes.c_int]
        connection_mode["use_set_raildriver_mode"] = True
        print("Verbindung über SetRailDriverMode(1) verfügbar.")
    except AttributeError:
        print(
            "SetRailDriverMode nicht gefunden – nutze SetRailSimConnected / "
            "SetRailDriverConnected (offizielle API)."
        )
        dll.SetRailSimConnected.restype = None
        dll.SetRailSimConnected.argtypes = [ctypes.c_bool]

        dll.SetRailDriverConnected.restype = None
        dll.SetRailDriverConnected.argtypes = [ctypes.c_bool]

    # Speichere den Modus am DLL-Objekt für spätere Aufrufe
    dll._connection_mode = connection_mode  # type: ignore[attr-defined]

    return dll


def establish_connection(dll: ctypes.CDLL) -> None:
    """
    Stellt die Verbindung zwischen externem Programm und Spiel her.

    Bevorzugt SetRailDriverMode(1) wie in deiner Anforderung beschrieben.
    Falls die Funktion in deiner DLL-Version fehlt, wird die offizielle
    API mit SetRailSimConnected(True) und SetRailDriverConnected(True) genutzt.
    """
    if dll._connection_mode["use_set_raildriver_mode"]:  # type: ignore[attr-defined]
        # Modus 1 = Datenverbindung zum Simulator aktivieren
        dll.SetRailDriverMode(1)
    else:
        # Offizieller Weg laut Dovetail/RailDriver-Dokumentation
        dll.SetRailSimConnected(True)
        dll.SetRailDriverConnected(True)


def maintain_connection(dll: ctypes.CDLL) -> None:
    """
    Hält die Verbindung in der Hauptschleife am Leben.

    Die API erwartet regelmäßige Aufrufe – sonst bricht die Verbindung ab.
    """
    establish_connection(dll)


def get_controller_list(dll: ctypes.CDLL) -> list[str]:
    """Gibt die Controller-Namen der aktuellen Lok zurück."""
    raw = dll.GetControllerList()
    if not raw:
        return []
    return raw.decode("utf-8").split("::")


def get_controller_index(controllers: list[str], controller_name: str) -> int | None:
    """Findet die ID eines Controllers anhand seines exakten Namens."""
    try:
        return controllers.index(controller_name)
    except ValueError:
        return None


class LocoTelemetry:
    """Merkt sich Tachometer der aktuellen Lok und berechnet GPS-Fallbacks."""

    def __init__(self) -> None:
        self.speed_index: int | None = None
        self.speed_is_mph = False
        self.speed_source = ""
        self.last_lat: float | None = None
        self.last_lon: float | None = None
        self.last_time: float | None = None
        self.gps_speed_kph = 0.0
        self.gps_heading = 0.0
        self.loco_name = ""

    def refresh_for_loco(self, dll: ctypes.CDLL) -> None:
        """Sucht das Tachometer neu, wenn die Lok gewechselt wurde."""
        if not dll.GetRailSimLocoChanged() and self.speed_index is not None:
            return

        if getattr(dll, "_has_loco_name", False):
            try:
                raw = dll.GetLocoName()
                if raw:
                    parts = raw.decode("utf-8", errors="replace").split("::")
                    self.loco_name = parts[-1] if parts else raw.decode()
            except (AttributeError, OSError):
                pass

        controllers = get_controller_list(dll)
        self.speed_index = None
        self.speed_source = ""

        for name in SPEED_CONTROLLER_NAMES:
            index = get_controller_index(controllers, name)
            if index is not None:
                self.speed_index = index
                self.speed_source = name
                self.speed_is_mph = "mph" in name.lower() and "kph" not in name.lower()
                print(f"Tachometer gefunden: {name} (Index {index})")
                return

        for index, name in enumerate(controllers):
            lower = name.lower()
            if any(skip in lower for skip in SPEED_NAME_SKIP):
                continue
            if not any(key in lower for key in SPEED_NAME_KEYWORDS):
                continue

            self.speed_index = index
            self.speed_source = name
            self.speed_is_mph = "mph" in lower and "kph" not in lower and "kmh" not in lower
            print(f"Tachometer automatisch erkannt: {name} (Index {index})")
            return

        print(
            "Warnung: Kein Tachometer gefunden – nutze GPS-Geschwindigkeit als Fallback.",
            file=sys.stderr,
        )


def read_speed_kph(dll: ctypes.CDLL, telemetry: LocoTelemetry) -> float:
    """Liest km/h vom Tachometer; Fallback über GPS-Bewegung."""
    telemetry.refresh_for_loco(dll)

    if telemetry.speed_index is not None:
        value = float(dll.GetControllerValue(telemetry.speed_index, GET_TYPE_CURRENT))
        if telemetry.speed_is_mph:
            value *= 1.60934
        if value > 0.0:
            return value

    return telemetry.gps_speed_kph


def read_heading(dll: ctypes.CDLL, telemetry: LocoTelemetry) -> float:
    """
    Liest Fahrtrichtung in Grad.
    Die API liefert Heading oft im Bogenmaß (z. B. 0.97 ≈ 55°).
    """
    raw = float(dll.GetControllerValue(CONTROLLER_HEADING, GET_TYPE_CURRENT))

    if raw > 6.5:
        return raw % 360.0

    if 0.0 < raw <= math.tau:
        return math.degrees(raw) % 360.0

    if telemetry.gps_heading > 0.0:
        return telemetry.gps_heading

    return 0.0


def update_gps_fallback(telemetry: LocoTelemetry, lat: float, lon: float) -> None:
    """Berechnet Geschwindigkeit und Richtung aus aufeinanderfolgenden GPS-Punkten."""
    now = time.time()

    if telemetry.last_lat is not None and telemetry.last_lon is not None and telemetry.last_time:
        dt = now - telemetry.last_time
        if dt > 0.05:
            distance_km = _haversine_km(telemetry.last_lat, telemetry.last_lon, lat, lon)
            telemetry.gps_speed_kph = (distance_km / dt) * 3600.0
            if distance_km > 0.00001:
                telemetry.gps_heading = _bearing_degrees(
                    telemetry.last_lat, telemetry.last_lon, lat, lon
                )

    telemetry.last_lat = lat
    telemetry.last_lon = lon
    telemetry.last_time = now


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Entfernung zwischen zwei GPS-Punkten in Kilometern."""
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Kompassrichtung von Punkt 1 nach Punkt 2 in Grad."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)

    y = math.sin(d_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def read_train_state(dll: ctypes.CDLL, telemetry: LocoTelemetry) -> dict[str, float]:
    """Liest Position, Geschwindigkeit und Fahrtrichtung aus dem Simulator."""
    latitude, longitude = read_gps_coordinates(dll)
    update_gps_fallback(telemetry, latitude, longitude)

    return {
        "lat": latitude,
        "lon": longitude,
        "speed_kph": read_speed_kph(dll, telemetry),
        "heading": read_heading(dll, telemetry),
    }


def read_gps_coordinates(dll: ctypes.CDLL) -> tuple[float, float]:
    """
    Liest Breiten- und Längengrad des Spieler-Zuges aus dem Simulator.

    Returns:
        Tuple (latitude, longitude) als Gleitkommazahlen in Dezimalgrad.
    """
    latitude = dll.GetControllerValue(CONTROLLER_LATITUDE, GET_TYPE_CURRENT)
    longitude = dll.GetControllerValue(CONTROLLER_LONGITUDE, GET_TYPE_CURRENT)
    return float(latitude), float(longitude)


# ---------------------------------------------------------------------------
# Server-Kommunikation (Platzhalter)
# ---------------------------------------------------------------------------

def send_position_to_server(
    player_name: str,
    server_url: str,
    lat: float,
    lon: float,
    speed_kph: float,
    heading: float,
    session: requests.Session | None = None,
    session_id: str = "",
    role: str = "driver",
    loco: str = "",
) -> bool:
    """
    Sendet Position, Geschwindigkeit und Fahrtrichtung an den Radar-Server.

    Returns:
        True wenn der Server die Daten angenommen hat.
    """
    print(
        f"[Radar] {player_name}: lat={lat:.6f}, lon={lon:.6f}, "
        f"{speed_kph:.0f} km/h, Richtung {heading:.0f}°"
    )

    payload = {
        "player": player_name,
        "lat": lat,
        "lon": lon,
        "speed_kph": speed_kph,
        "heading": heading,
        "timestamp": time.time(),
        "session_id": session_id or None,
        "role": role,
        "loco": loco,
    }

    http = session or requests
    try:
        response = http.post(server_url, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException as error:
        err = str(error)
        if "10048" in err:
            print(
                "[Radar] Port belegt – stop_radar.bat ausführen, dann nur EINMAL starten.",
                file=sys.stderr,
            )
        else:
            print(f"Fehler beim Senden an {server_url}: {error}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Hauptschleife
# ---------------------------------------------------------------------------


def run_tracker(status_callback=None, stop_event=None) -> None:
    """
    Startet den Tracker und fragt GPS-Daten in einer Endlosschleife ab.

    Args:
        status_callback: Optional (kind, message) für GUI-Updates
        stop_event: threading.Event zum Beenden
    """
    config = load_config()
    player_name = config["player_name"]
    server_url = config["server_url"]
    dll_path = config["raildriver_dll_path"]
    poll_interval = float(config.get("poll_interval_seconds", 1.0))
    session_id = str(config.get("session_id", "") or "").strip()
    session_role = str(config.get("session_role", "driver") or "driver")
    dispatch_after_id = 0
    server_root = server_url.rsplit("/api/", 1)[0] if "/api/" in server_url else server_url.rstrip("/")

    def notify(kind: str, message: str) -> None:
        if status_callback:
            status_callback(kind, message)

    def log(message: str) -> None:
        print(message)
        notify("log", message)
    log("=" * 60)
    log("Train Simulator Classic – Multiplayer-Radar Tracker")
    log("=" * 60)
    log(f"Konfiguration: {CONFIG_PATH.name}")
    log(f"DLL-Pfad:      {dll_path}")
    log(f"Spieler:       {player_name}")
    log(f"Server:        {server_url}")
    log(f"Intervall:     {poll_interval}s")
    if session_id:
        log(f"Session:       {session_id} ({session_role})")
    log("")
    log("Starte Train Simulator und beginne eine Fahrt, falls noch nicht geschehen.")
    log("")

    dll = load_raildriver(dll_path)
    telemetry = LocoTelemetry()

    establish_connection(dll)
    telemetry.refresh_for_loco(dll)

    log("Verbindung zum Simulator hergestellt. Lese GPS-Daten …")
    notify("sim", "verbunden")
    log("")

    http = create_http_session()
    server_fail_streak = 0

    try:
        while True:
            if stop_event and stop_event.is_set():
                log("Tracker beendet.")
                break

            maintain_connection(dll)

            state = read_train_state(dll, telemetry)

            if state["lat"] != 0.0 or state["lon"] != 0.0:
                ok = send_position_to_server(
                    player_name,
                    server_url,
                    state["lat"],
                    state["lon"],
                    state["speed_kph"],
                    state["heading"],
                    session=http,
                    session_id=session_id,
                    role=session_role,
                    loco=telemetry.loco_name,
                )
                if ok:
                    server_fail_streak = 0
                else:
                    server_fail_streak += 1
                notify(
                    "gps",
                    f"{state['speed_kph']:.0f} km/h · {state['heading']:.0f}°"
                    + (" · gesendet" if ok else " · Server-Fehler"),
                )
            else:
                log("[Radar] Noch keine GPS-Daten – bist du in einer aktiven Fahrt?")
                notify("gps", "warte auf Fahrt …")

            if session_id and server_fail_streak < 3:
                try:
                    msg_url = f"{server_root}/api/sessions/{session_id}/messages"
                    msg_resp = http.get(
                        msg_url,
                        params={"after": dispatch_after_id},
                        timeout=3,
                    )
                    if msg_resp.ok:
                        for msg in msg_resp.json().get("messages", []):
                            dispatch_after_id = max(dispatch_after_id, int(msg["id"]))
                            target = msg.get("target")
                            if target and target != player_name:
                                continue
                            label = msg.get("sender", "Leitstand")
                            text = msg.get("text", "")
                            log(f"[Leitstand] {label}: {text}")
                            notify("dispatch", f"{label}: {text}")
                except requests.RequestException:
                    pass

            wait_seconds = poll_interval
            if server_fail_streak >= 3:
                wait_seconds = min(poll_interval * 3, 5.0)

            if stop_event:
                if stop_event.wait(wait_seconds):
                    log("Tracker beendet.")
                    break
            else:
                time.sleep(wait_seconds)

    except KeyboardInterrupt:
        log("Tracker beendet.")
    finally:
        http.close()


def main() -> None:
    """Kommandozeilen-Start (ohne GUI)."""
    run_tracker()


if __name__ == "__main__":
    main()

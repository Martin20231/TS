"""
Brücke: Radar-Web-Karte → Train Simulator (über RailDriver SetControllerValue).

Modus A (dual): zwei 0–1-Regler, z. B. Wipers=0.1 + Sander=0.1
Modus B (single): ein Regler mit 0.11 = Signal 1, Aspect Hp0 (VirtualThrottle)
"""

from __future__ import annotations

import ctypes
import sys
import time
from dataclasses import dataclass
from typing import Any

import requests

ASPECT_TO_CODE: dict[str, int] = {
    "hp0": 1,
    "hp1": 2,
    "sh1": 3,
}

SIGNAL_BUS_CANDIDATES = (
    "Sand",
    "Sandstreuer",
    "Wipers",
    "Wiper",
    "Scheibenwischer",
    "CabLight",
    "Marker",
    "Vigilance",
)

ASPECT_BUS_CANDIDATES = (
    "Wipers",
    "Wiper",
    "Scheibenwischer",
    "CabLight",
    "Marker",
    "Sander",
    "Sand",
    "Vigilance",
)

SINGLE_BUS_CANDIDATES = (
    "CablightValue",
    "Cablight",
    "SunShade",
    "InstrumentLightning",
    "ConsoleLightning",
    "PassLightValue",
    "MirrorLeft",
    "MirrorRight",
    "WiperControl",
    "WiperInterval",
    "HeadlightsMode",
    "Wipers",
    "Wiper",
    "Scheibenwischer",
    "Sandstreuer",
    "Sand",
    "VirtualThrottle",
    "Regulator",
    "TrainBrake",
    "TrainBrakeControl",
)

HOLD_SECONDS = 0.12
PULSE_COUNT = 10
GET_TYPE_CURRENT = 0


@dataclass
class StellwerkBus:
    mode: str
    signal_index: int
    signal_name: str
    aspect_index: int = -1
    aspect_name: str = ""

    @property
    def ready(self) -> bool:
        if self.mode == "dual":
            return self.signal_index >= 0 and self.aspect_index >= 0
        return self.signal_index >= 0

    @property
    def label(self) -> str:
        if self.mode == "dual":
            return f"{self.signal_name}+{self.aspect_name}"
        return f"{self.signal_name}(single)"


def stellwerk_api_base(server_url: str) -> str:
    url = server_url.rstrip("/")
    if url.endswith("/api/position"):
        return url[: -len("/api/position")] + "/api/stellwerk"
    return url + "/api/stellwerk"


def encode_bus_fractions(signal_index: int, aspect: str) -> tuple[float, float]:
    code = ASPECT_TO_CODE.get(aspect)
    if code is None:
        raise ValueError(f"Unbekannter Aspect: {aspect}")
    if not 1 <= signal_index <= 9:
        raise ValueError(f"Signal-Index muss 1–9 sein, nicht {signal_index}")
    return signal_index / 10.0, code / 10.0


def encode_single_bus_value(signal_index: int, aspect: str) -> float:
    code = ASPECT_TO_CODE.get(aspect)
    if code is None:
        raise ValueError(f"Unbekannter Aspect: {aspect}")
    return float(signal_index * 10 + code) / 100.0


def bind_set_controller_value(dll: ctypes.CDLL) -> None:
    if not hasattr(dll, "SetControllerValue"):
        raise RuntimeError("RailDriver: SetControllerValue fehlt in der DLL")
    dll.SetControllerValue.restype = None
    dll.SetControllerValue.argtypes = [ctypes.c_int, ctypes.c_float]


def _pick_controller(
    controllers: list[str],
    get_controller_index,
    preferred: str,
    candidates: tuple[str, ...],
    skip: set[str] | None = None,
) -> tuple[int | None, str | None]:
    names: list[str] = []
    if preferred:
        names.append(preferred)
    names.extend(candidates)

    blocked = skip or set()
    seen: set[str] = set()
    for name in names:
        if not name or name in seen or name in blocked:
            continue
        seen.add(name)
        index = get_controller_index(controllers, name)
        if index is not None:
            return index, name
    return None, None


def find_stellwerk_bus(
    get_controller_list,
    get_controller_index,
    config: dict[str, Any],
) -> StellwerkBus | None:
    controllers = get_controller_list()
    if not controllers:
        return None

    mode_pref = str(config.get("stellwerk_bus_mode") or "auto").strip().lower()

    if mode_pref != "single":
        sig_index, sig_name = _pick_controller(
            controllers,
            get_controller_index,
            str(config.get("stellwerk_bus_signal_control") or "").strip(),
            SIGNAL_BUS_CANDIDATES,
        )
        asp_index, asp_name = _pick_controller(
            controllers,
            get_controller_index,
            str(config.get("stellwerk_bus_aspect_control") or "").strip(),
            ASPECT_BUS_CANDIDATES,
            skip={sig_name} if sig_name else set(),
        )

        if (
            mode_pref == "dual"
            or (
                mode_pref == "auto"
                and sig_index is not None
                and asp_index is not None
                and sig_index != asp_index
                and asp_name not in ("Sander", "Sand")
            )
        ):
            if (
                sig_index is not None
                and asp_index is not None
                and sig_index != asp_index
            ):
                return StellwerkBus(
                    "dual", sig_index, sig_name or "", asp_index, asp_name or ""
                )

    single_index, single_name = _pick_controller(
        controllers,
        get_controller_index,
        str(config.get("stellwerk_bus_single_control") or "").strip(),
        SINGLE_BUS_CANDIDATES,
    )
    if single_index is not None:
        return StellwerkBus("single", single_index, single_name or "")

    return None


def _read_controller(dll: ctypes.CDLL, index: int) -> float:
    return float(dll.GetControllerValue(index, GET_TYPE_CURRENT))


def pulse_bus_command(
    dll: ctypes.CDLL,
    bus: StellwerkBus,
    signal_index: int,
    aspect: str,
) -> None:
    if bus.mode == "dual":
        sig_val, asp_val = encode_bus_fractions(signal_index, aspect)
        for _ in range(PULSE_COUNT):
            dll.SetControllerValue(bus.signal_index, ctypes.c_float(sig_val))
            dll.SetControllerValue(bus.aspect_index, ctypes.c_float(asp_val))
            time.sleep(HOLD_SECONDS)
        dll.SetControllerValue(bus.signal_index, ctypes.c_float(0.0))
        dll.SetControllerValue(bus.aspect_index, ctypes.c_float(0.0))
        rb_sig = _read_controller(dll, bus.signal_index)
        rb_asp = _read_controller(dll, bus.aspect_index)
        print(
            f"[Stellwerk] Impuls dual: {bus.signal_name}={sig_val:.2f}, "
            f"{bus.aspect_name}={asp_val:.2f} (Readback {rb_sig:.2f}/{rb_asp:.2f})"
        )
        if abs(rb_sig - sig_val) > 0.03 or abs(rb_asp - asp_val) > 0.03:
            print(
                "[Stellwerk] WARNUNG: Readback weicht ab – Spiel-Script sieht "
                "den Befehl evtl. nicht.",
                file=sys.stderr,
            )
        return

    value = encode_single_bus_value(signal_index, aspect)
    for _ in range(PULSE_COUNT):
        dll.SetControllerValue(bus.signal_index, ctypes.c_float(value))
        time.sleep(HOLD_SECONDS)
    dll.SetControllerValue(bus.signal_index, ctypes.c_float(0.0))
    rb = _read_controller(dll, bus.signal_index)
    print(
        f"[Stellwerk] Impuls single: {bus.signal_name}={value:.2f} "
        f"(Readback {rb:.2f})"
    )
    if abs(rb - value) > 0.03:
        print(
            "[Stellwerk] WARNUNG: Readback weicht ab – anderes Regler-Feld in "
            "config.json probieren (list_lok_controls.bat).",
            file=sys.stderr,
        )


def report_bridge_heartbeat(
    server_url: str,
    player_name: str,
    bus: StellwerkBus | None,
    session: requests.Session | None = None,
    last_applied_id: int | None = None,
    bus_name: str | None = None,
    bus_mode: str | None = None,
    ready: bool | None = None,
) -> None:
    base = stellwerk_api_base(server_url)
    http = session or requests
    try:
        payload = {
            "player": player_name,
            "bus_index": bus.signal_index if bus else None,
            "bus_name": bus_name or (bus.label if bus and bus.ready else None),
            "bus_mode": bus_mode or (bus.mode if bus else None),
            "ready": ready if ready is not None else bool(bus and bus.ready),
        }
        if last_applied_id is not None:
            payload["last_applied_id"] = last_applied_id
        http.post(f"{base}/bridge/heartbeat", json=payload, timeout=3)
    except requests.RequestException:
        pass


def poll_and_apply_commands(
    dll: ctypes.CDLL,
    bus: StellwerkBus,
    server_url: str,
    last_command_id: int,
    player_name: str,
    session: requests.Session | None = None,
) -> int:
    base = stellwerk_api_base(server_url)
    http = session or requests
    try:
        response = http.get(
            f"{base}/commands",
            params={"after": last_command_id, "bridge": player_name},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        print(f"[Stellwerk] Server nicht erreichbar: {error}", file=sys.stderr)
        return last_command_id

    commands = payload.get("commands") or []
    new_last = int(payload.get("last_id", last_command_id))

    for cmd in commands:
        signal_index = int(cmd.get("index", 0))
        aspect = str(cmd.get("aspect", "hp0"))
        try:
            pulse_bus_command(dll, bus, signal_index, aspect)
            label = cmd.get("label") or cmd.get("signal_id") or f"Signal {signal_index}"
            print(f"[Stellwerk] → Spiel: {label} = {aspect.upper()} ({bus.label})")
            new_last = max(new_last, int(cmd.get("id", 0)))
        except (ValueError, OSError) as error:
            print(f"[Stellwerk] Befehl fehlgeschlagen: {error}", file=sys.stderr)

    return new_last


def format_controller_list(controllers: list[str]) -> str:
    if not controllers:
        return "(keine – bist du in der Lok?)"
    return ", ".join(f"{i}:{name}" for i, name in enumerate(controllers))

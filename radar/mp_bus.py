"""RailDriver-Bus: Tracker → Szenario-Script (Konvoi-Daten ins Spiel)."""

from __future__ import annotations

import ctypes
import sys
import time
from typing import Any

GET_TYPE_CURRENT = 0
PULSE_COUNT = 8
HOLD_SECONDS = 0.08

MP_BUS_CANDIDATES = (
    "PassLightValue",
    "CablightValue",
    "SunShade",
    "InstrumentLightning",
    "ConsoleLightning",
    "MirrorLeft",
    "MirrorRight",
    "WiperControl",
    "HeadlightsMode",
)


def encode_convoy_pulse(slot: int, distance_km: float) -> float:
    """slot 0 = Liste leeren, 1–9 = Konvoi-Eintrag, Distanz in 0,1-km-Schritten."""
    if slot == 0:
        return 0.01
    dist_tenths = min(max(int(round(distance_km * 10)), 0), 99)
    if not 1 <= slot <= 9:
        raise ValueError(f"Konvoi-Slot muss 1–9 sein, nicht {slot}")
    return (slot * 100 + dist_tenths) / 1000.0


def decode_convoy_pulse(value: float) -> tuple[int, float]:
    """Gegenstück zum Lua-Script (Tests)."""
    code = int(round(value * 1000))
    if code <= 0:
        return 0, 0.0
    slot = code // 100
    dist_tenths = code % 100
    return slot, dist_tenths / 10.0


def bind_set_controller_value(dll: ctypes.CDLL) -> None:
    if not hasattr(dll, "SetControllerValue"):
        raise RuntimeError("RailDriver: SetControllerValue fehlt in der DLL")
    dll.SetControllerValue.restype = None
    dll.SetControllerValue.argtypes = [ctypes.c_int, ctypes.c_float]


def _pick_controller(
    controllers: list[str],
    get_controller_index,
    preferred: str,
) -> tuple[int | None, str | None]:
    if preferred:
        index = get_controller_index(controllers, preferred)
        if index is not None:
            return index, preferred
    for name in MP_BUS_CANDIDATES:
        if name == preferred:
            continue
        index = get_controller_index(controllers, name)
        if index is not None:
            return index, name
    return None, None


def find_mp_bus_control(
    get_controller_list,
    get_controller_index,
    config: dict[str, Any],
) -> tuple[int | None, str | None]:
    controllers = get_controller_list()
    if not controllers:
        return None, None
    preferred = str(config.get("mp_bus_control") or "").strip()
    return _pick_controller(controllers, get_controller_index, preferred)


def pulse_bus_value(dll: ctypes.CDLL, control_index: int, value: float) -> None:
    for _ in range(PULSE_COUNT):
        dll.SetControllerValue(control_index, ctypes.c_float(value))
        time.sleep(HOLD_SECONDS)
    dll.SetControllerValue(control_index, ctypes.c_float(0.0))
    readback = float(dll.GetControllerValue(control_index, GET_TYPE_CURRENT))
    if abs(readback - value) > 0.04 and value >= 0.08:
        print(
            f"[Radar] MP-Bus Readback {readback:.3f} ≠ {value:.3f} – "
            "anderes Feld in config.json (mp_bus_control) probieren.",
            file=sys.stderr,
        )


def push_convoy_to_game(
    dll: ctypes.CDLL,
    control_index: int,
    convoy: list[dict],
    *,
    max_entries: int = 6,
) -> None:
    """Sendet Konvoi still ans Szenario – Anzeige nur über Spiel-Menü."""
    pulse_bus_value(dll, control_index, encode_convoy_pulse(0, 0.0))
    time.sleep(0.05)
    for index, entry in enumerate(convoy[:max_entries], start=1):
        distance_km = float(entry.get("distance_km", 0.0))
        pulse_bus_value(dll, control_index, encode_convoy_pulse(index, distance_km))
        time.sleep(0.08)

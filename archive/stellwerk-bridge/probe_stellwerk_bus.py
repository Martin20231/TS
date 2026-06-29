"""Findet setzbare Lok-Regler für die Stellwerk-Brücke (BR 483 / generisch)."""

from __future__ import annotations

import ctypes
import sys
import time

from radar_config import CONFIG_PATH, load_config, save_config
from stellwerk_bus import bind_set_controller_value
from ts_tracker import (
    establish_connection,
    get_controller_index,
    get_controller_list,
    load_raildriver,
    maintain_connection,
)

# Unkritische Regler – keine Bremse, Türen, Fahrstufe
PROBE_CANDIDATES = (
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
    "PassLightOnOff",
    "SunShadeSnapSwitch",
    "SanderControl",
    "Wipers",
    "Wiper",
    "Sandstreuer",
    "Sand",
    "VirtualThrottle",
    "Regulator",
)

SKIP_CONTROLS = {
    "EmergencyBrake",
    "Notbremse",
    "DoorsOpenCloseLeft",
    "DoorsOpenCloseRight",
    "MainKey",
    "Startup",
    "Horn",
    "HornControl",
}

TEST_VALUES = (0.11, 0.22, 0.33)


def probe_one(dll: ctypes.CDLL, index: int, name: str) -> tuple[bool, float, float]:
    """Setzt Testwerte und prüft Readback. Gibt (ok, best_sent, best_read) zurück."""
    best_sent = 0.0
    best_read = 0.0
    best_delta = 999.0

    for value in TEST_VALUES:
        dll.SetControllerValue(index, ctypes.c_float(value))
        time.sleep(0.12)
        readback = float(dll.GetControllerValue(index, 0))
        delta = abs(readback - value)
        if delta < best_delta:
            best_delta = delta
            best_sent = value
            best_read = readback
        if delta <= 0.04:
            dll.SetControllerValue(index, ctypes.c_float(0.0))
            time.sleep(0.05)
            return True, value, readback

    dll.SetControllerValue(index, ctypes.c_float(0.0))
    time.sleep(0.05)
    return best_delta <= 0.04, best_sent, best_read


def main() -> int:
    config = load_config()
    dll = load_raildriver(config["raildriver_dll_path"])
    establish_connection(dll)
    maintain_connection(dll)
    bind_set_controller_value(dll)

    controllers = get_controller_list(dll)
    if not controllers:
        print("Keine Regler – Train Simulator starten und in Lok sitzen.")
        return 1

    print(f"Lok hat {len(controllers)} Regler.\n")
    print("Teste unkritische Kandidaten …\n")
    print(f"{'Name':<28} {'Idx':>4}  {'Send':>5}  {'Read':>5}  OK")
    print("-" * 58)

    working: list[tuple[str, int, float, float]] = []

    for name in PROBE_CANDIDATES:
        if name in SKIP_CONTROLS:
            continue
        index = get_controller_index(controllers, name)
        if index is None:
            continue
        ok, sent, read = probe_one(dll, index, name)
        mark = "JA" if ok else "nein"
        print(f"{name:<28} {index:>4}  {sent:>5.2f}  {read:>5.2f}  {mark}")
        if ok:
            working.append((name, index, sent, read))

    print()
    if not working:
        print("Kein passender Regler gefunden.")
        print("Melde dich mit der kompletten Reglerliste.")
        return 1

    best_name, best_idx, _, _ = working[0]
    print(f"Empfehlung: {best_name} (Index {best_idx})")
    print()

    answer = input(
        f"In config.json eintragen und testen? [J/n] "
    ).strip().lower()
    if answer in ("", "j", "ja", "y", "yes"):
        config["stellwerk_bus_mode"] = "single"
        config["stellwerk_bus_single_control"] = best_name
        save_config(config)
        print(f"[OK] {CONFIG_PATH.name} -> stellwerk_bus_single_control = {best_name}")
        print("Jetzt: test_stellwerk_bridge.bat")

    return 0


if __name__ == "__main__":
    sys.exit(main())

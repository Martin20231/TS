"""Kalibriert Klick-Positionen für das Stellwerk-Menü oben rechts."""

from __future__ import annotations

import sys
import time

from radar_config import CONFIG_PATH, load_config
from stellwerk_keyboard import find_train_sim_window, focus_train_simulator
from stellwerk_uiclick import save_ui_calibration

try:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
except Exception:
    user32 = None


def read_cursor_client_pos(hwnd: int) -> tuple[float, float] | None:
    if user32 is None:
        return None
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)) or rect.right <= 0:
        return None
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    user32.ScreenToClient(hwnd, ctypes.byref(point))
    return point.x / rect.right, point.y / rect.bottom


def prompt_point(label: str, hwnd: int) -> list[float]:
    print()
    print(f"  >>> {label}")
    print("      Maus auf die Stelle im SPIEL bewegen (Menü oben rechts).")
    input("      Dann hier ENTER drücken … ")
    pos = read_cursor_client_pos(hwnd)
    if pos is None:
        raise RuntimeError("Mausposition konnte nicht gelesen werden.")
    rx, ry = pos
    print(f"      Gespeichert: {rx:.4f}, {ry:.4f}")
    return [round(rx, 4), round(ry, 4)]


def main() -> int:
    config = load_config()
    hwnd = find_train_sim_window()
    if hwnd is None:
        print("Train Simulator nicht gefunden – Spiel starten, Szenario laden.")
        return 1

    print("=" * 55)
    print("Stellwerk UI-Kalibrierung")
    print("=" * 55)
    print()
    print("Voraussetzung: Szenario läuft, Meldung „Stellwerk aktiv“ war da,")
    print("Menü oben rechts sichtbar (Hp0 / Sh1 / Hp1 Links).")
    print()
    focus_train_simulator()
    time.sleep(0.5)

    menu = prompt_point("1/4 – Titel „Stellwerk Adlershof“ (Menü öffnen)", hwnd)
    hp0 = prompt_point("2/4 – Roter Link „Hp0 – Halt“", hwnd)
    sh1 = prompt_point("3/4 – Gelber Link „Sh1 – Rangierfahrt“", hwnd)
    hp1 = prompt_point("4/4 – Grüner Link „Hp1 – Fahrt frei“", hwnd)

    save_ui_calibration(
        str(CONFIG_PATH),
        menu,
        {"hp0": hp0, "sh1": sh1, "hp1": hp1},
    )

    print()
    print(f"[OK] {CONFIG_PATH.name} gespeichert (Modus: uiclick)")
    print("Jetzt: test_stellwerk_bridge.bat")
    return 0


if __name__ == "__main__":
    sys.exit(main())

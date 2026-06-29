"""Test: Karte -> Menü-Klick -> Szenario."""

from __future__ import annotations

import sys

from radar_config import load_config
from stellwerk_uiclick import send_aspect_via_ui_click, uiclick_bridge_label
from stellwerk_keyboard import send_aspect_via_horn, keyboard_bridge_label


def main() -> int:
    config = load_config()
    mode = str(config.get("stellwerk_bridge_mode") or "uiclick").lower()

    print(f"Modus: {mode}")
    print("Spiel sichtbar, Szenario läuft, Menü oben rechts offen (Hp0/Sh1/Hp1).")
    print()

    if mode == "uiclick":
        print(f"Brücke: {uiclick_bridge_label()}")
        print("Sende Klick auf Hp0 …")
        print()
        send_aspect_via_ui_click(config, "hp0")
        print()
        print("Erwartung: Meldung „Stellwerk OK“ + Signal wechselt.")
        print("Falsch getroffen? -> calibrate_stellwerk_ui.bat")
    elif mode == "keyboard":
        print(f"Brücke: {keyboard_bridge_label(config)}")
        print("Sende 1x Hupe (Taste M) -> Hp0 …")
        print()
        send_aspect_via_horn(config, "hp0")
        print()
        print("Erwartung: Hupe + Klick auf Menü Hp0 -> „Stellwerk OK“ oben rechts.")
        print("Falsch getroffen? -> calibrate_stellwerk_ui.bat")
    else:
        print(f"Unbekannter Modus {mode!r} – setze stellwerk_bridge_mode auf uiclick.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

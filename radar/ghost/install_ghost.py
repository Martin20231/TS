"""Kopiert Ghost-Dateien in den Szenario-Ordner."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_RADAR_DIR = Path(__file__).resolve().parent.parent
if str(_RADAR_DIR) not in sys.path:
    sys.path.insert(0, str(_RADAR_DIR))

from radar_config import load_config

GHOST_DIR = Path(__file__).resolve().parent
GHOST_FILES = (
    "ScenarioScript.lua",
    "ghost_radar.html",
)


def install_ghost_scenario(scenario_path: str | None = None) -> tuple[bool, str]:
    path_str = (scenario_path or "").strip()
    if not path_str:
        config = load_config()
        path_str = (config.get("scenario_path") or "").strip()

    if not path_str:
        return False, (
            f"Kein Szenario-Pfad.\n"
            f"Trage in install_ghost.bat ein:\n"
            f'  set "SCENARIO_PATH=C:\\...\\DeinSzenario-Ordner"'
        )

    dest_dir = Path(path_str).expanduser()
    if not dest_dir.is_dir():
        return False, f"Ordner nicht gefunden:\n{dest_dir}"

    copied: list[str] = []
    for name in GHOST_FILES:
        source = GHOST_DIR / name
        if not source.is_file():
            return False, f"Quelldatei fehlt:\n{source}"
        shutil.copy2(source, dest_dir / name)
        copied.append(name)

    de_dir = dest_dir / "de"
    de_dir.mkdir(parents=True, exist_ok=True)
    html_src = GHOST_DIR / "ghost_radar.html"
    if html_src.is_file():
        shutil.copy2(html_src, de_dir / "ghost_radar.html")
        copied.append("de/ghost_radar.html")

    for stale in dest_dir.glob("ScenarioScript.luac*"):
        try:
            stale.unlink()
        except OSError:
            pass

    return True, f"Kopiert nach:\n{dest_dir}\n  " + "\n  ".join(copied) + "\n  (alte .luac gelöscht – bitte neu kompilieren)"


def main() -> int:
    override = sys.argv[1].strip() if len(sys.argv) > 1 else None

    ok, message = install_ghost_scenario(override)
    print(message)
    if ok:
        print("\nNächste Schritte:")
        print("  - Fahrplan: NUR GhostStart + GhostPoll (GhostMenu/Details LÖSCHEN)")
        print("  - Script kompilieren")
        print("  - Radar im Spiel: start_ghost_overlay.bat (zweiter Monitor)")
        print("  - Keine Menü-Fenster mehr im TS (stapeln sonst)")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

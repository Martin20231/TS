"""Hintergrund-Dienste starten/stoppen (Overlay, Funk-PTT, Ghost, Server)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

RADAR_DIR = Path(__file__).resolve().parent

LogFn = Callable[[str], None]


def _creation_flags(console: bool) -> int:
    if sys.platform != "win32":
        return 0
    if console:
        return getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    return getattr(subprocess, "DETACHED_PROCESS", 0) or 0


def build_command(mode: str, *extra: str) -> list[str]:
    """Kommandozeile für einen Dienst (funktioniert auch aus TS-Radar.exe)."""
    if getattr(sys, "frozen", False):
        return [sys.executable, f"--{mode}", *extra]

    scripts = {
        "cab-overlay": RADAR_DIR / "cab_overlay.py",
        "radio-bridge": RADAR_DIR / "radio_bridge.py",
        "ghost-bridge": RADAR_DIR / "ghost" / "ghost_bridge.py",
        "server": RADAR_DIR / "server.py",
    }
    script = scripts[mode]
    return [sys.executable, str(script), *extra]


class ServiceManager:
    """Verwaltet optionale Subprozesse aus dem Launcher."""

    def __init__(self, log: LogFn | None = None) -> None:
        self._log = log or (lambda _msg: None)
        self._procs: dict[str, subprocess.Popen | None] = {}

    def is_running(self, name: str) -> bool:
        proc = self._procs.get(name)
        return proc is not None and proc.poll() is None

    def start(self, name: str, mode: str, *extra: str, console: bool = True) -> bool:
        if self.is_running(name):
            return True
        cmd = build_command(mode, *extra)
        try:
            self._procs[name] = subprocess.Popen(
                cmd,
                cwd=str(RADAR_DIR),
                creationflags=_creation_flags(console),
            )
            self._log(f"{name} gestartet")
            return True
        except OSError as error:
            self._log(f"{name} Fehler: {error}")
            return False

    def stop(self, name: str) -> None:
        proc = self._procs.get(name)
        if proc is None or proc.poll() is not None:
            self._procs.pop(name, None)
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        self._procs.pop(name, None)
        self._log(f"{name} beendet")

    def stop_all(self) -> None:
        for name in list(self._procs):
            self.stop(name)

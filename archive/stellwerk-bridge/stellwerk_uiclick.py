"""
Stellwerk-Brücke: Klick ins HTML-Menü oben rechts im Spiel.

Das Menü nutzt event:SW_A_HP0 usw. – dieselben Links wie bei manuellem Klick.
"""

from __future__ import annotations

import ctypes
import json
import sys
import time
from ctypes import wintypes
from typing import Any

import requests

from stellwerk_bus import stellwerk_api_base
from stellwerk_keyboard import WINDOW_TITLE_PARTS, find_train_sim_window, focus_train_simulator

user32 = ctypes.windll.user32  # type: ignore[attr-defined]

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

DEFAULT_UI_CLICKS: dict[str, list[float]] = {
    "hp0": [0.86, 0.11],
    "sh1": [0.86, 0.15],
    "hp1": [0.86, 0.19],
}

DEFAULT_MENU_CLICK: list[float] = [0.86, 0.08]


def _window_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def get_ui_clicks(config: dict[str, Any]) -> dict[str, list[float]]:
    raw = config.get("stellwerk_ui_clicks")
    if isinstance(raw, dict):
        result: dict[str, list[float]] = {}
        for aspect, coords in raw.items():
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                result[str(aspect)] = [float(coords[0]), float(coords[1])]
        if result:
            return result
    return dict(DEFAULT_UI_CLICKS)


def get_menu_click(config: dict[str, Any]) -> list[float] | None:
    raw = config.get("stellwerk_ui_menu")
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        return [float(raw[0]), float(raw[1])]
    return list(DEFAULT_MENU_CLICK)


def click_client_relative(hwnd: int, rx: float, ry: float) -> bool:
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return False
    if rect.right <= 0 or rect.bottom <= 0:
        return False

    cx = max(0, min(int(rect.right * rx), rect.right - 1))
    cy = max(0, min(int(rect.bottom * ry), rect.bottom - 1))
    point = wintypes.POINT(cx, cy)
    user32.ClientToScreen(hwnd, ctypes.byref(point))

    user32.SetCursorPos(point.x, point.y)
    time.sleep(0.1)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.06)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return True


def send_aspect_via_ui_click(config: dict[str, Any], aspect: str) -> None:
    aspect = aspect.lower()
    clicks = get_ui_clicks(config)
    if aspect not in clicks:
        raise ValueError(f"Unbekannter Aspect: {aspect}")

    hwnd = find_train_sim_window()
    if hwnd is None:
        print(
            "[Stellwerk] Train-Simulator-Fenster nicht gefunden.",
            file=sys.stderr,
        )
        return

    if not focus_train_simulator():
        print("[Stellwerk] Konnte Spiel-Fenster nicht aktivieren.", file=sys.stderr)
        return

    hwnd = find_train_sim_window()
    if hwnd is None:
        return

    menu = get_menu_click(config)
    if menu is not None:
        rx, ry = menu
        print(f"[Stellwerk] Menü-Position anklicken ({rx:.2f}, {ry:.2f}) …")
        click_client_relative(hwnd, rx, ry)
        time.sleep(0.35)

    rx, ry = clicks[aspect]
    print(f"[Stellwerk] Klick {aspect.upper()} bei ({rx:.2f}, {ry:.2f}) …")
    if not click_client_relative(hwnd, rx, ry):
        print("[Stellwerk] Mausklick fehlgeschlagen.", file=sys.stderr)
        return

    time.sleep(0.25)
    print(f"[Stellwerk] UI-Klick -> {aspect.upper()} (wie Menü-Link im Spiel)")


def poll_and_apply_commands_uiclick(
    config: dict[str, Any],
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
        aspect = str(cmd.get("aspect", "hp0"))
        signal_index = int(cmd.get("index", 1))
        if signal_index != 1:
            print(
                f"[Stellwerk] UI-Brücke: nur SW_S1 (Index 1), "
                f"ignoriere Signal {signal_index}",
                file=sys.stderr,
            )
            new_last = max(new_last, int(cmd.get("id", 0)))
            continue
        try:
            send_aspect_via_ui_click(config, aspect)
            label = cmd.get("label") or cmd.get("signal_id") or "SW_S1"
            print(f"[Stellwerk] -> Spiel: {label} = {aspect.upper()} (UI)")
            new_last = max(new_last, int(cmd.get("id", 0)))
        except ValueError as error:
            print(f"[Stellwerk] Befehl fehlgeschlagen: {error}", file=sys.stderr)

    return new_last


def uiclick_bridge_ready() -> bool:
    return find_train_sim_window() is not None


def uiclick_bridge_label() -> str:
    return "Menü-Klick"


def save_ui_calibration(
    config_path: str,
    menu: list[float],
    clicks: dict[str, list[float]],
) -> None:
    from pathlib import Path

    path = Path(config_path)
    data: dict[str, Any] = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    data["stellwerk_bridge_mode"] = "uiclick"
    data["stellwerk_ui_menu"] = menu
    data["stellwerk_ui_clicks"] = clicks
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

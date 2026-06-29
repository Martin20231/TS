"""
Stellwerk-Brücke über echte Tastatureingaben (Hupe).

RailDriver SetControllerValue aktualisiert oft nur die DLL-Anzeige – das
Szenario-Script liest PlayerEngine:GetControlValue aus der Spiel-Eingabe.
Simulierte Tastendrücke laufen durch dieselbe Pipeline wie dein Drücken.
"""

from __future__ import annotations

import ctypes
import sys
import time
from typing import Any

import requests

from stellwerk_bus import stellwerk_api_base

ASPECT_PULSES: dict[str, int] = {
    "hp0": 1,
    "sh1": 2,
    "hp1": 3,
}

PULSE_GAP_SECONDS = 0.65
PRE_FOCUS_SECONDS = 0.2
POST_SEQUENCE_SECONDS = 1.2
HORN_HOLD_SECONDS = 0.45

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101

user32 = ctypes.windll.user32  # type: ignore[attr-defined]

KEYEVENTF_KEYUP = 0x0002

VK_BY_NAME: dict[str, int] = {
    "m": 0x4D,
    "space": 0x20,
    " ": 0x20,
    "h": 0x48,
    "n": 0x4E,
    "f": 0x46,
    "g": 0x47,
    "enter": 0x0D,
    "return": 0x0D,
    "+": 0x6B,
    "numpad+": 0x6B,
    "num+": 0x6B,
}

WINDOW_TITLE_PARTS = (
    "Train Simulator",
    "RailWorks",
    "TS Classic",
)


def resolve_vk(key_name: str) -> int:
    name = str(key_name or "space").strip().lower()
    if name in VK_BY_NAME:
        return VK_BY_NAME[name]
    if len(name) == 1:
        return ord(name.upper())
    raise ValueError(f"Unbekannte Taste: {key_name!r}")


def _window_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def find_train_sim_window() -> int | None:
  found: list[int] = []

  @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
  def callback(hwnd: int, _lparam: int) -> bool:
      if not user32.IsWindowVisible(hwnd):
          return True
      title = _window_title(hwnd)
      if not title:
          return True
      lower = title.lower()
      for part in WINDOW_TITLE_PARTS:
          if part.lower() in lower:
              found.append(hwnd)
              return False
      return True

  user32.EnumWindows(callback, 0)
  return found[0] if found else None


def focus_train_simulator() -> bool:
    hwnd = find_train_sim_window()
    if hwnd is None:
        return False
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(PRE_FOCUS_SECONDS)
    return True


def press_key_to_window(hwnd: int, vk_code: int, hold_seconds: float | None = None) -> None:
    hold = HORN_HOLD_SECONDS if hold_seconds is None else hold_seconds
    scan = user32.MapVirtualKeyW(vk_code, 0) & 0xFF
    lp_down = 1 | (scan << 16)
    lp_up = 1 | (scan << 16) | (1 << 30) | (1 << 31)
    user32.PostMessageW(hwnd, WM_KEYDOWN, vk_code, lp_down)
    time.sleep(hold)
    user32.PostMessageW(hwnd, WM_KEYUP, vk_code, lp_up)


def tap_vk(vk_code: int) -> None:
    hwnd = find_train_sim_window()
    if hwnd is not None:
        press_key_to_window(hwnd, vk_code)
        return
    scan = user32.MapVirtualKeyW(vk_code, 0)
    user32.keybd_event(vk_code, scan, 0, 0)
    time.sleep(HORN_HOLD_SECONDS)
    user32.keybd_event(vk_code, scan, KEYEVENTF_KEYUP, 0)


def send_aspect_via_horn(config: dict[str, Any], aspect: str) -> None:
    pulses = ASPECT_PULSES.get(aspect)
    if pulses is None:
        raise ValueError(f"Unbekannter Aspect: {aspect}")

    vk = resolve_vk(str(config.get("stellwerk_horn_key") or "m"))
    hwnd = find_train_sim_window()
    if hwnd is None or not focus_train_simulator():
        print(
            "[Stellwerk] Train-Simulator-Fenster nicht gefunden – "
            "Spiel muss laufen und sichtbar sein.",
            file=sys.stderr,
        )
        return
    hwnd = find_train_sim_window()
    if hwnd is None:
        return

    for _ in range(pulses):
        press_key_to_window(hwnd, vk)
        time.sleep(PULSE_GAP_SECONDS)

    time.sleep(0.35)

    # Zuverlaessig: Menü-Link anklicken (wie manuell auf Hp0/Sh1/Hp1)
    try:
        from stellwerk_uiclick import send_aspect_via_ui_click

        send_aspect_via_ui_click(config, aspect)
    except Exception as error:
        print(f"[Stellwerk] Menü-Klick fehlgeschlagen: {error}", file=sys.stderr)

    time.sleep(POST_SEQUENCE_SECONDS)
    key_label = str(config.get("stellwerk_horn_key") or "m")
    print(
        f"[Stellwerk] {pulses}x '{key_label}' + Menü-Klick "
        f"-> {aspect.upper()}"
    )


def poll_and_apply_commands_keyboard(
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
                f"[Stellwerk] Tastatur-Brücke: nur SW_S1 (Index 1), "
                f"ignoriere Signal {signal_index}",
                file=sys.stderr,
            )
            new_last = max(new_last, int(cmd.get("id", 0)))
            continue
        try:
            send_aspect_via_horn(config, aspect)
            label = cmd.get("label") or cmd.get("signal_id") or "SW_S1"
            print(f"[Stellwerk] -> Spiel: {label} = {aspect.upper()} (Hupe)")
            new_last = max(new_last, int(cmd.get("id", 0)))
        except ValueError as error:
            print(f"[Stellwerk] Befehl fehlgeschlagen: {error}", file=sys.stderr)

    return new_last


def keyboard_bridge_ready() -> bool:
    return find_train_sim_window() is not None


def keyboard_bridge_label(config: dict[str, Any]) -> str:
    key = str(config.get("stellwerk_horn_key") or "space")
    return f"Hupe({key})"

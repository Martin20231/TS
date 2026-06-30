"""
Kleines Overlay-Fenster für über Train Simulator legen (z. B. auf Cab-Display).

Kein TS-Szenario nötig · keine stapelnden Alerts · live vom Radar-Server.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import font as tkfont

import requests

from radar_config import load_config


def server_root(server_url: str) -> str:
    url = server_url.rstrip("/")
    if url.endswith("/api/position"):
        return url[: -len("/api/position")]
    return url


class CabOverlay:
    def __init__(self) -> None:
        config = load_config()
        self.player = config.get("player_name", "MeinZug")
        self.session_id = str(config.get("session_id") or "").strip()
        self.api_root = server_root(config.get("server_url", ""))
        self.poll_ms = 2000

        self.root = tk.Tk()
        self.root.title("TS Radar Cab")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.overrideredirect(True)
        self.root.configure(bg="#0a101c")
        self.root.geometry("300x118+60+60")

        self._drag_x = 0
        self._drag_y = 0

        frame = tk.Frame(self.root, bg="#0a101c", padx=12, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        title_f = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        main_f = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        sub_f = tkfont.Font(family="Segoe UI", size=10)

        tk.Label(
            frame, text="MULTIPLAYER-RADAR", fg="#4fc3f7", bg="#0a101c", font=title_f,
        ).pack(anchor="w")

        self.label_name = tk.Label(frame, text="–", fg="#ffffff", bg="#0a101c", font=main_f)
        self.label_name.pack(anchor="w", pady=(4, 0))

        self.label_detail = tk.Label(frame, text="Verbinde …", fg="#aaaaaa", bg="#0a101c", font=sub_f)
        self.label_detail.pack(anchor="w")

        self.label_hint = tk.Label(
            frame,
            text="Ziehen = verschieben · Rechtsklick = schließen",
            fg="#555555",
            bg="#0a101c",
            font=tkfont.Font(family="Segoe UI", size=8),
        )
        self.label_hint.pack(anchor="w", pady=(6, 0))

        for widget in (self.root, frame, self.label_name, self.label_detail, self.label_hint):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)
        self.root.bind("<Button-3>", lambda _e: self.root.destroy())

        self.root.after(500, self._tick)

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _on_drag(self, event: tk.Event) -> None:
        self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def _fetch_nearest(self) -> tuple[str, str, bool]:
        try:
            response = requests.get(f"{self.api_root}/api/positions", timeout=8)
            response.raise_for_status()
            positions = response.json()
        except requests.RequestException:
            return "Server offline", "Tracker / Internet prüfen", False

        self_pos = next((p for p in positions if p.get("player") == self.player), None)
        if not self_pos:
            return "Du sendest nicht", "TS-Radar.exe starten", False

        best = None
        best_km = 9999.0
        for other in positions:
            if other.get("player") == self.player:
                continue
            if other.get("active") is False:
                continue
            if self.session_id:
                other_sid = str(other.get("session_id") or "").strip()
                if other_sid and other_sid != self.session_id:
                    continue

            lat1, lon1 = self_pos["lat"], self_pos["lon"]
            lat2, lon2 = other["lat"], other["lon"]
            dist = _haversine_km(lat1, lon1, lat2, lon2)
            if dist < best_km:
                best_km = dist
                best = other

        if not best:
            return "Kein anderer Zug", "Warte auf Spieler …", False

        bearing = _bearing_deg(self_pos["lat"], self_pos["lon"], best["lat"], best["lon"])
        dist_text = f"{best_km * 1000:.0f} m" if best_km < 1 else f"{best_km:.1f} km"
        detail = f"{dist_text} · {bearing:.0f}° · {best.get('speed_kph', 0):.0f} km/h"
        return str(best["player"]), detail, best_km < 2.0

    def _tick(self) -> None:
        name, detail, near = self._fetch_nearest()
        self.label_name.configure(text=name, fg="#ff6666" if near else "#ffffff")
        self.label_detail.configure(text=detail, fg="#ff9999" if near else "#aaaaaa")
        self.root.after(self.poll_ms, self._tick)

    def run(self) -> None:
        self.root.mainloop()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlon / 2) ** 2
    return r * 2 * asin(sqrt(a))


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import atan2, cos, degrees, radians, sin

    p1, p2 = radians(lat1), radians(lat2)
    dlon = radians(lon2 - lon1)
    y = sin(dlon) * cos(p2)
    x = cos(p1) * sin(p2) - sin(p1) * cos(p2) * cos(dlon)
    return (degrees(atan2(y, x)) + 360) % 360


def main() -> None:
    CabOverlay().run()


if __name__ == "__main__":
    main()

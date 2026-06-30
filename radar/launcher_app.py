"""Modernes Launcher-Hauptfenster (CustomTkinter)."""

from __future__ import annotations

import os
import threading
import webbrowser
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

from app_services import ServiceManager
from ghost.install_ghost import install_ghost_scenario
from launcher_settings import SettingsDialog
from radar_config import CONFIG_PATH, load_config
from radar_util import (
    CLOUD_MAP_URL,
    is_cloud_server,
    is_local_server,
    map_url_from_server,
    overlay_url_from_server,
    radio_url_from_server,
)

DOCS_DIR = Path(__file__).resolve().parent / "docs"

# Farben
C_BG = "#0b0f17"
C_CARD = "#151c2c"
C_CARD_HOVER = "#1e293b"
C_ACCENT = "#3b82f6"
C_ACCENT_HOVER = "#2563eb"
C_OK = "#22c55e"
C_WARN = "#f59e0b"
C_MUTED = "#64748b"
C_TEXT = "#e2e8f0"


def config_needs_setup() -> bool:
    if not CONFIG_PATH.exists():
        return True
    config = load_config()
    player = (config.get("player_name") or "").strip()
    server = (config.get("server_url") or "").strip()
    dll_path = (config.get("raildriver_dll_path") or "").strip()
    if not player or player == "DeinName":
        return True
    if not server or not server.startswith("http") or "DEIN-SERVICE" in server:
        return True
    if not dll_path or not Path(dll_path).is_file():
        return True
    return False


def open_player_guide() -> None:
    guide = DOCS_DIR / "SPIELANLEITUNG.txt"
    if guide.is_file():
        os.startfile(str(guide))
    else:
        messagebox.showinfo(
            "Hilfe",
            "1. Train Simulator starten\n2. Dieses Fenster offen lassen\n3. Buttons unten nutzen",
        )


class ActionTile(ctk.CTkButton):
    """Große Aktions-Kachel mit Titel + Untertitel."""

    def __init__(
        self,
        master,
        *,
        icon: str,
        title: str,
        subtitle: str,
        command,
        accent: bool = False,
        **kwargs,
    ) -> None:
        label = f"{icon}  {title}\n{subtitle}"
        super().__init__(
            master,
            text=label,
            command=command,
            height=88,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=C_ACCENT if accent else C_CARD,
            hover_color=C_ACCENT_HOVER if accent else C_CARD_HOVER,
            text_color=C_TEXT,
            corner_radius=12,
            **kwargs,
        )
        self._accent = accent

    def set_active(self, active: bool) -> None:
        if active:
            self.configure(
                fg_color="#14532d",
                hover_color="#166534",
                border_width=2,
                border_color=C_OK,
            )
        else:
            base = C_ACCENT if self._accent else C_CARD
            hover = C_ACCENT_HOVER if self._accent else C_CARD_HOVER
            self.configure(fg_color=base, hover_color=hover, border_width=0)


class RadarLauncherApp:
    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("TS Radar")
        self.root.geometry("780x720")
        self.root.minsize(720, 680)
        self.root.configure(fg_color=C_BG)

        self.stop_event = threading.Event()
        self.tracker_thread: threading.Thread | None = None
        self.services = ServiceManager(log=self._log)

        self._sim_ok = False
        self._gps_ok = False

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if config_needs_setup():
            self.root.after(300, lambda: SettingsDialog(self.root, self._after_setup, required=True))
        else:
            self.root.after(300, self._start_tracker)

    def _build_ui(self) -> None:
        # ── Header ──
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 0))

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            title_col,
            text="TS RADAR",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#60a5fa",
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_col,
            text="Multiplayer · Karte · Funk · Cab-Display",
            font=ctk.CTkFont(size=13),
            text_color=C_MUTED,
        ).pack(anchor="w")

        ctk.CTkButton(header, text="?", width=36, height=36, corner_radius=18, command=open_player_guide).pack(
            side="right", padx=(8, 0)
        )
        ctk.CTkButton(
            header,
            text="⚙",
            width=36,
            height=36,
            corner_radius=18,
            fg_color="#334155",
            hover_color="#475569",
            command=self._open_settings,
        ).pack(side="right")

        # ── Ablauf ──
        flow = ctk.CTkFrame(self.root, fg_color=C_CARD, corner_radius=12)
        flow.pack(fill="x", padx=24, pady=(16, 12))

        steps = [
            ("1", "TS starten", "Fahrt beginnen"),
            ("2", "Radar läuft", "Automatisch"),
            ("3", "Features", "Buttons unten"),
        ]
        flow_inner = ctk.CTkFrame(flow, fg_color="transparent")
        flow_inner.pack(fill="x", padx=8, pady=10)
        for i, (num, title, sub) in enumerate(steps):
            if i > 0:
                ctk.CTkLabel(flow_inner, text="→", text_color=C_MUTED, font=ctk.CTkFont(size=16)).grid(
                    row=0, column=i * 2 - 1, padx=4
                )
            col = ctk.CTkFrame(flow_inner, fg_color="transparent")
            col.grid(row=0, column=i * 2, padx=8, pady=4)
            ctk.CTkLabel(
                col,
                text=num,
                width=32,
                height=32,
                corner_radius=16,
                fg_color=C_ACCENT,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack()
            ctk.CTkLabel(col, text=title, font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(6, 0))
            ctk.CTkLabel(col, text=sub, font=ctk.CTkFont(size=11), text_color=C_MUTED).pack()

        # ── Status ──
        status = ctk.CTkFrame(self.root, fg_color=C_CARD, corner_radius=12)
        status.pack(fill="x", padx=24, pady=(0, 12))
        status_inner = ctk.CTkFrame(status, fg_color="transparent")
        status_inner.pack(fill="x", padx=16, pady=14)

        self.dot_sim = self._status_chip(status_inner, "Simulator", "Wartet …", C_WARN, 0, 0)
        self.dot_gps = self._status_chip(status_inner, "GPS", "–", C_MUTED, 0, 1)
        self.dot_player = self._status_chip(status_inner, "Spieler", "–", C_MUTED, 1, 0)
        self.dot_session = self._status_chip(status_inner, "Session", "–", C_MUTED, 1, 1)
        status_inner.columnconfigure((0, 1), weight=1)

        # ── Hauptaktionen ──
        ctk.CTkLabel(
            self.root,
            text="Während der Fahrt",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=26, pady=(4, 6))

        actions = ctk.CTkFrame(self.root, fg_color="transparent")
        actions.pack(fill="x", padx=24)
        actions.columnconfigure((0, 1), weight=1)

        ActionTile(
            actions,
            icon="🗺",
            title="Live-Karte",
            subtitle="Freunde & Konvoi sehen",
            command=self._open_map,
            accent=True,
        ).grid(row=0, column=0, padx=(0, 6), pady=6, sticky="ew")

        self.tile_cab = ActionTile(
            actions,
            icon="📡",
            title="Cab-Overlay",
            subtitle="Abstand im Führerstand",
            command=self._toggle_cab,
        )
        self.tile_cab.grid(row=0, column=1, padx=(6, 0), pady=6, sticky="ew")

        ActionTile(
            actions,
            icon="🎙",
            title="Funk",
            subtitle="Push-to-Talk mit Freunden",
            command=self._open_radio,
        ).grid(row=1, column=0, padx=(0, 6), pady=6, sticky="ew")

        self.tile_ptt = ActionTile(
            actions,
            icon="📯",
            title="Funk per Hupe",
            subtitle="Hupe drücken = sprechen",
            command=self._toggle_radio_ptt,
        )
        self.tile_ptt.grid(row=1, column=1, padx=(6, 0), pady=6, sticky="ew")

        # ── Extras (einklappbar) ──
        self.extras_open = ctk.BooleanVar(value=False)
        extras_toggle = ctk.CTkButton(
            self.root,
            text="▼  Extras (Ghost, 2. Monitor)",
            fg_color="transparent",
            hover_color=C_CARD,
            text_color=C_MUTED,
            anchor="w",
            command=self._toggle_extras,
        )
        extras_toggle.pack(fill="x", padx=24, pady=(4, 0))
        self.extras_btn = extras_toggle

        self.extras_frame = ctk.CTkFrame(self.root, fg_color=C_CARD, corner_radius=12)
        extra_row = ctk.CTkFrame(self.extras_frame, fg_color="transparent")
        extra_row.pack(fill="x", padx=12, pady=12)
        ctk.CTkButton(
            extra_row,
            text="Browser-Overlay",
            fg_color="#334155",
            command=self._open_browser_overlay,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(extra_row, text="Ghost installieren", fg_color="#334155", command=self._install_ghost).pack(
            side="left", padx=(0, 8)
        )
        self.btn_ghost = ctk.CTkButton(
            extra_row,
            text="Ghost-Bridge",
            fg_color="#334155",
            command=self._toggle_ghost_bridge,
        )
        self.btn_ghost.pack(side="left")

        self.host_frame = ctk.CTkFrame(self.extras_frame, fg_color="transparent")
        self.btn_server = ctk.CTkButton(
            self.host_frame,
            text="Lokalen Server starten",
            fg_color="#334155",
            command=self._toggle_server,
        )
        self.btn_server.pack(side="left", padx=12, pady=(0, 12))

        # ── Log ──
        ctk.CTkLabel(
            self.root,
            text="Protokoll",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C_MUTED,
            anchor="w",
        ).pack(fill="x", padx=26, pady=(8, 4))

        self.log_box = ctk.CTkTextbox(self.root, height=100, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        self.log_box.configure(state="disabled")

        # ── Footer ──
        footer = ctk.CTkFrame(self.root, fg_color="transparent")
        footer.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkLabel(footer, text="Fenster offen lassen während du fährst", text_color=C_MUTED).pack(
            side="left"
        )
        ctk.CTkButton(
            footer,
            text="Beenden",
            width=100,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            command=self._on_close,
        ).pack(side="right")

        self._refresh_labels()
        self._refresh_host_panel()
        self.root.after(1200, self._poll_services)

    def _status_chip(self, parent, title: str, value: str, color: str, row: int, col: int):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, sticky="w", padx=8, pady=4)
        dot = ctk.CTkLabel(frame, text="●", text_color=color, font=ctk.CTkFont(size=16))
        dot.pack(side="left")
        text_frame = ctk.CTkFrame(frame, fg_color="transparent")
        text_frame.pack(side="left", padx=(6, 0))
        ctk.CTkLabel(text_frame, text=title, font=ctk.CTkFont(size=11), text_color=C_MUTED).pack(anchor="w")
        val = ctk.CTkLabel(text_frame, text=value, font=ctk.CTkFont(size=13, weight="bold"))
        val.pack(anchor="w")
        return {"dot": dot, "val": val}

    def _toggle_extras(self) -> None:
        if self.extras_open.get():
            self.extras_frame.pack_forget()
            self.extras_btn.configure(text="▼  Extras (Ghost, 2. Monitor)")
            self.extras_open.set(False)
        else:
            self.extras_frame.pack(fill="x", padx=24, pady=(4, 0))
            self.extras_btn.configure(text="▲  Extras ausblenden")
            self.extras_open.set(True)

    def _log(self, message: str) -> None:
        def write() -> None:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", message + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.root.after(0, write)

    def _set_chip(self, chip: dict, value: str, color: str) -> None:
        chip["val"].configure(text=value)
        chip["dot"].configure(text_color=color)

    def _refresh_labels(self) -> None:
        config = load_config()
        self._set_chip(self.dot_player, config.get("player_name", "–"), C_OK)

        session_id = (config.get("session_id") or "").strip()
        if session_id:
            role = "Leitstand" if config.get("session_role") == "dispatch" else "Lokführer"
            self._set_chip(self.dot_session, f"{session_id} · {role}", C_OK)
        else:
            self._set_chip(self.dot_session, "Keine (nur Karte)", C_MUTED)

        if is_cloud_server(config.get("server_url", "")):
            if not getattr(self, "_cloud_logged", False):
                self._log(f"Cloud-Server: {CLOUD_MAP_URL}")
                self._cloud_logged = True

        self._refresh_host_panel()

    def _refresh_host_panel(self) -> None:
        config = load_config()
        if is_local_server(config.get("server_url", "")):
            self.host_frame.pack(fill="x")
        else:
            self.host_frame.pack_forget()

    def _poll_services(self) -> None:
        self.tile_cab.set_active(self.services.is_running("cab"))
        self.tile_ptt.set_active(self.services.is_running("radio-ptt"))

        if self.services.is_running("ghost"):
            self.btn_ghost.configure(text="Ghost-Bridge ■", fg_color="#14532d")
        else:
            self.btn_ghost.configure(text="Ghost-Bridge", fg_color="#334155")

        if self.services.is_running("server"):
            self.btn_server.configure(text="Server beenden", fg_color="#7f1d1d")
        else:
            self.btn_server.configure(text="Lokalen Server starten", fg_color="#334155")

        self.root.after(1500, self._poll_services)

    def _after_setup(self) -> None:
        self._refresh_labels()
        self._start_tracker()

    def _open_map(self) -> None:
        config = load_config()
        url = map_url_from_server(config.get("server_url", ""), config.get("session_id", ""))
        if url.startswith("http"):
            webbrowser.open(url)
            self._log("Karte geöffnet")
        else:
            messagebox.showinfo("Hinweis", "Server-URL in Einstellungen prüfen.")

    def _open_browser_overlay(self) -> None:
        config = load_config()
        webbrowser.open(overlay_url_from_server(config.get("server_url", ""), config.get("session_id", "")))
        self._log("Browser-Overlay geöffnet")

    def _toggle_cab(self) -> None:
        if self.services.is_running("cab"):
            self.services.stop("cab")
        else:
            self.services.start("cab", "cab-overlay")
            self._log("Cab-Overlay gestartet – über TS legen")

    def _open_radio(self) -> None:
        config = load_config()
        session_id = (config.get("session_id") or "").strip()
        if not session_id:
            messagebox.showinfo("Funk", "Session-Code in Einstellungen eintragen.")
            return
        url = radio_url_from_server(
            config.get("server_url", ""),
            config.get("player_name", "MeinZug"),
            session_id,
        )
        webbrowser.open(url)
        self._log("Funk geöffnet – Mikro erlauben, V oder Hupe zum Sprechen")

    def _toggle_radio_ptt(self) -> None:
        config = load_config()
        if not (config.get("session_id") or "").strip():
            messagebox.showinfo("Funk", "Session-Code nötig.")
            return
        if self.services.is_running("radio-ptt"):
            self.services.stop("radio-ptt")
        else:
            self.services.start("radio-ptt", "radio-bridge")
            self._log("Funk-PTT aktiv – Hupe drücken zum Sprechen")

    def _install_ghost(self) -> None:
        ok, message = install_ghost_scenario()
        self._log(message.replace("\n", " – "))
        if ok:
            messagebox.showinfo("Ghost", message)
        else:
            messagebox.showwarning("Ghost", message)

    def _toggle_ghost_bridge(self) -> None:
        if self.services.is_running("ghost"):
            self.services.stop("ghost")
        else:
            self.services.start("ghost", "ghost-bridge")

    def _toggle_server(self) -> None:
        if self.services.is_running("server"):
            self.services.stop("server")
        elif self.services.start("server", "server"):
            self.root.after(3000, self._open_map)

    def _open_settings(self) -> None:
        if self.tracker_thread and self.tracker_thread.is_alive():
            self._stop_tracker()
        SettingsDialog(self.root, self._restart_after_settings)

    def _restart_after_settings(self) -> None:
        self._refresh_labels()
        self._start_tracker()

    def _start_tracker(self) -> None:
        if self.tracker_thread and self.tracker_thread.is_alive():
            return
        self.stop_event.clear()
        self._refresh_labels()
        self._log("GPS-Tracker gestartet …")
        self.tracker_thread = threading.Thread(target=self._run_tracker, daemon=True)
        self.tracker_thread.start()

    def _stop_tracker(self) -> None:
        self.stop_event.set()
        if self.tracker_thread:
            self.tracker_thread.join(timeout=3)

    def _on_tracker_status(self, kind: str, message: str) -> None:
        def update() -> None:
            if kind == "sim":
                ok = "verbunden" in message.lower() or "connected" in message.lower()
                self._sim_ok = ok
                color = C_OK if ok else C_WARN
                self._set_chip(self.dot_sim, message, color)
            elif kind == "gps":
                ok = "sendet" in message.lower() or "km/h" in message.lower()
                self._gps_ok = ok
                color = C_OK if ok else C_MUTED
                self._set_chip(self.dot_gps, message, color)
            elif kind == "dispatch":
                self._log(f"[Leitstand] {message}")
            elif kind == "log":
                self._log(message)
            elif kind == "error":
                self._set_chip(self.dot_sim, "Fehler", "#ef4444")
                self._log(f"FEHLER: {message}")
                messagebox.showerror("Fehler", message)

        self.root.after(0, update)

    def _run_tracker(self) -> None:
        try:
            import ts_tracker

            ts_tracker.run_tracker(
                status_callback=self._on_tracker_status,
                stop_event=self.stop_event,
            )
        except SystemExit as error:
            self._on_tracker_status("error", str(error))
        except Exception as error:
            self._on_tracker_status("error", str(error))

    def _on_close(self) -> None:
        self._stop_tracker()
        self.services.stop_all()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()

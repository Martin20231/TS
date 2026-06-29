"""
TS Multiplayer-Radar – Ein-Klick-Start für Spieler.

Doppelklick auf TS-Radar.exe:
  - Beim ersten Mal: Einstellungen eingeben
  - Danach: Tracker startet mit Status-Anzeige
"""

from __future__ import annotations

import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk

from radar_config import CONFIG_PATH, load_config, save_config


def config_needs_setup() -> bool:
    """True, wenn wichtige Einstellungen noch fehlen."""
    if not CONFIG_PATH.exists():
        return True

    config = load_config()
    player = (config.get("player_name") or "").strip()
    server = (config.get("server_url") or "").strip()
    dll_path = (config.get("raildriver_dll_path") or "").strip()

    if not player:
        return True
    if not server or not server.startswith("http") or "DEIN-SERVICE" in server:
        return True
    if not dll_path:
        return True
    return False


def map_url_from_server(server_url: str) -> str:
    """Karten-URL aus der Tracker-Server-URL ableiten."""
    url = server_url.strip().rstrip("/")
    if url.endswith("/api/position"):
        return url[: -len("/api/position")]
    return url


class SettingsDialog(tk.Toplevel):
    """Einstellungsfenster für Spielername, Server und DLL-Pfad."""

    def __init__(self, master: tk.Tk, on_saved) -> None:
        super().__init__(master)
        self.on_saved = on_saved
        self.title("TS Radar – Einstellungen")
        self.resizable(False, False)
        self.grab_set()

        config = load_config() if CONFIG_PATH.exists() else {}

        frame = ttk.Frame(self, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(
            frame,
            text="Einmalig eintragen – danach reicht ein Doppelklick auf die Exe.",
            wraplength=420,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="Dein Name auf der Karte:").grid(row=1, column=0, sticky="w")
        self.player_var = tk.StringVar(value=config.get("player_name", ""))
        ttk.Entry(frame, textvariable=self.player_var, width=48).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10)
        )

        ttk.Label(frame, text="Server-URL (vom Radar-Host):").grid(row=3, column=0, sticky="w")
        self.server_var = tk.StringVar(value=config.get("server_url", ""))
        ttk.Entry(frame, textvariable=self.server_var, width=48).grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=(0, 4)
        )
        ttk.Label(
            frame,
            text="Beispiel: https://ts-multiplayer-radar.onrender.com/api/position",
            font=("Segoe UI", 8),
            foreground="#555",
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(frame, text="RailDriver-DLL (Train Simulator):").grid(row=6, column=0, sticky="w")
        dll_frame = ttk.Frame(frame)
        dll_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        self.dll_var = tk.StringVar(
            value=config.get(
                "raildriver_dll_path",
                r"E:\Steam\steamapps\common\RailWorks\plugins\RailDriver64.dll",
            )
        )
        ttk.Entry(dll_frame, textvariable=self.dll_var, width=40).grid(row=0, column=0, sticky="ew")
        ttk.Button(dll_frame, text="Durchsuchen …", command=self._browse_dll).grid(
            row=0, column=1, padx=(6, 0)
        )
        dll_frame.columnconfigure(0, weight=1)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=8, column=0, columnspan=3, sticky="e")
        ttk.Button(btn_frame, text="Abbrechen", command=self.destroy).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="Speichern & Starten", command=self._save).grid(row=0, column=1)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.player_var.focus_set()

    def _browse_dll(self) -> None:
        path = filedialog.askopenfilename(
            title="RailDriver64.dll wählen",
            filetypes=[("RailDriver DLL", "RailDriver64.dll"), ("DLL-Dateien", "*.dll"), ("Alle", "*.*")],
        )
        if path:
            self.dll_var.set(path)

    def _save(self) -> None:
        player = self.player_var.get().strip()
        server = self.server_var.get().strip()
        dll_path = self.dll_var.get().strip()

        if not player:
            messagebox.showerror("Fehlt", "Bitte einen Spielernamen eingeben.", parent=self)
            return
        if not server.startswith("http"):
            messagebox.showerror(
                "Fehlt",
                "Bitte eine gültige Server-URL eingeben\n(mit https://…/api/position).",
                parent=self,
            )
            return
        if not dll_path:
            messagebox.showerror("Fehlt", "Bitte den Pfad zur RailDriver-DLL wählen.", parent=self)
            return

        if not server.rstrip("/").endswith("/api/position"):
            server = server.rstrip("/") + "/api/position"

        config = load_config() if CONFIG_PATH.exists() else {}
        config.update({
            "player_name": player,
            "server_url": server,
            "raildriver_dll_path": dll_path,
        })
        save_config(config)
        self.on_saved()
        self.destroy()


class RadarLauncherApp:
    """Hauptfenster: Status, Log und Steuerung."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("TS Multiplayer-Radar")
        self.root.minsize(480, 360)
        self.root.geometry("520x400")

        self.stop_event = threading.Event()
        self.tracker_thread: threading.Thread | None = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if config_needs_setup():
            self.root.after(200, lambda: SettingsDialog(self.root, self._start_tracker))
        else:
            self.root.after(200, self._start_tracker)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="Train Simulator – Multiplayer-Radar", font=("Segoe UI", 12, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            outer,
            text="Train Simulator starten, Fahrt beginnen – dein Zug erscheint auf der Karte.",
            wraplength=480,
        ).pack(anchor="w", pady=(4, 10))

        status_frame = ttk.LabelFrame(outer, text="Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.status_player = ttk.Label(status_frame, text="Spieler: –")
        self.status_player.pack(anchor="w")
        self.status_server = ttk.Label(status_frame, text="Server: –")
        self.status_server.pack(anchor="w")
        self.status_sim = ttk.Label(status_frame, text="Simulator: wartet …")
        self.status_sim.pack(anchor="w")
        self.status_gps = ttk.Label(status_frame, text="GPS: –")
        self.status_gps.pack(anchor="w")

        btn_row = ttk.Frame(outer)
        btn_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btn_row, text="Karte öffnen", command=self._open_map).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="Einstellungen", command=self._open_settings).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="Beenden", command=self._on_close).pack(side=tk.RIGHT)

        log_frame = ttk.LabelFrame(outer, text="Protokoll", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_box = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED, font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True)

        self._refresh_labels()

    def _log(self, message: str) -> None:
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _refresh_labels(self) -> None:
        config = load_config()
        self.status_player.configure(text=f"Spieler: {config.get('player_name', '–')}")
        self.status_server.configure(text=f"Server: {config.get('server_url', '–')}")

    def _open_map(self) -> None:
        config = load_config()
        url = map_url_from_server(config.get("server_url", ""))
        if url.startswith("http"):
            webbrowser.open(url)
        else:
            messagebox.showinfo("Hinweis", "Bitte zuerst die Server-URL in den Einstellungen eintragen.")

    def _open_settings(self) -> None:
        was_running = self.tracker_thread and self.tracker_thread.is_alive()
        if was_running:
            self._stop_tracker()
        SettingsDialog(self.root, self._restart_after_settings)

    def _restart_after_settings(self) -> None:
        self._refresh_labels()
        self._start_tracker()

    def _start_tracker(self) -> None:
        if self.tracker_thread and self.tracker_thread.is_alive():
            return

        self.stop_event.clear()
        self._log("Starte GPS-Tracker …")
        self.tracker_thread = threading.Thread(target=self._run_tracker, daemon=True)
        self.tracker_thread.start()

    def _stop_tracker(self) -> None:
        self.stop_event.set()
        if self.tracker_thread:
            self.tracker_thread.join(timeout=3)
        self._log("Tracker gestoppt.")

    def _on_tracker_status(self, kind: str, message: str) -> None:
        def update() -> None:
            if kind == "sim":
                self.status_sim.configure(text=f"Simulator: {message}")
            elif kind == "gps":
                self.status_gps.configure(text=f"GPS: {message}")
            elif kind == "log":
                self._log(message)
            elif kind == "error":
                self.status_sim.configure(text=f"Simulator: Fehler")
                self._log(f"FEHLER: {message}")
                messagebox.showerror("Fehler", message, parent=self.root)

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
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    RadarLauncherApp().run()


if __name__ == "__main__":
    main()

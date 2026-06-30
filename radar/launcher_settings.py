"""Einrichtungs-Dialog (modern)."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

from radar_config import CONFIG_PATH, load_config, save_config
from radar_util import (
    CLOUD_MAP_URL,
    CLOUD_TRACKER_URL,
    LOCAL_TRACKER_URL,
    find_raildriver_dll,
    is_cloud_server,
    normalize_tracker_url,
)


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk, on_saved, *, required: bool = False) -> None:
        super().__init__(master)
        self.on_saved = on_saved
        self.required = required
        self.title("Einrichtung")
        self.geometry("520x640")
        self.resizable(False, False)
        self.grab_set()

        config = load_config() if CONFIG_PATH.exists() else {}
        server_url = config.get("server_url", CLOUD_TRACKER_URL)
        use_cloud = is_cloud_server(server_url)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll,
            text="Einmal einrichten",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            scroll,
            text="Danach startet alles automatisch beim Öffnen.",
            text_color="#94a3b8",
        ).pack(anchor="w", pady=(0, 16))

        ctk.CTkLabel(scroll, text="Dein Name", anchor="w").pack(fill="x")
        self.player_var = ctk.StringVar(value=config.get("player_name", ""))
        ctk.CTkEntry(scroll, textvariable=self.player_var, height=36).pack(fill="x", pady=(4, 14))

        ctk.CTkLabel(scroll, text="Server", anchor="w").pack(fill="x")
        self.server_mode = ctk.StringVar(value="cloud" if use_cloud else "custom")
        ctk.CTkRadioButton(
            scroll,
            text="Cloud (empfohlen – Freunde weltweit)",
            variable=self.server_mode,
            value="cloud",
            command=self._sync_server,
        ).pack(anchor="w", pady=2)
        ctk.CTkLabel(scroll, text=f"  {CLOUD_MAP_URL}", text_color="#64748b", font=ctk.CTkFont(size=11)).pack(
            anchor="w"
        )
        ctk.CTkRadioButton(
            scroll,
            text="Eigener PC / LAN",
            variable=self.server_mode,
            value="custom",
            command=self._sync_server,
        ).pack(anchor="w", pady=(6, 2))

        self.server_var = ctk.StringVar(value=server_url if not use_cloud else LOCAL_TRACKER_URL)
        self.server_entry = ctk.CTkEntry(scroll, textvariable=self.server_var, height=36)
        self.server_entry.pack(fill="x", pady=(4, 14))

        ctk.CTkLabel(scroll, text="Session-Code (Gruppe + Funk)", anchor="w").pack(fill="x")
        sess_row = ctk.CTkFrame(scroll, fg_color="transparent")
        sess_row.pack(fill="x", pady=(4, 14))
        self.session_var = ctk.StringVar(value=config.get("session_id", ""))
        ctk.CTkEntry(sess_row, textvariable=self.session_var, width=180, height=36).pack(side="left")
        ctk.CTkLabel(sess_row, text="Rolle:", text_color="#94a3b8").pack(side="left", padx=(12, 6))
        self.role_var = ctk.StringVar(
            value="dispatch" if config.get("session_role") == "dispatch" else "driver"
        )
        ctk.CTkOptionMenu(
            sess_row,
            variable=self.role_var,
            values=["driver", "dispatch"],
            width=120,
        ).pack(side="left")

        ctk.CTkLabel(scroll, text="RailDriver DLL", anchor="w").pack(fill="x")
        dll_row = ctk.CTkFrame(scroll, fg_color="transparent")
        dll_row.pack(fill="x", pady=(4, 14))
        self.dll_var = ctk.StringVar(value=config.get("raildriver_dll_path") or find_raildriver_dll())
        ctk.CTkEntry(dll_row, textvariable=self.dll_var, height=36).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dll_row, text="…", width=40, command=self._browse_dll).pack(side="left", padx=(6, 0))
        ctk.CTkButton(dll_row, text="Auto", width=50, command=self._auto_dll).pack(side="left", padx=(4, 0))

        ctk.CTkLabel(scroll, text="Ghost-Szenario (optional)", anchor="w").pack(fill="x")
        scen_row = ctk.CTkFrame(scroll, fg_color="transparent")
        scen_row.pack(fill="x", pady=(4, 14))
        self.scenario_var = ctk.StringVar(value=config.get("scenario_path", ""))
        ctk.CTkEntry(scen_row, textvariable=self.scenario_var, height=36).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(scen_row, text="…", width=40, command=self._browse_scenario).pack(side="left", padx=(6, 0))

        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=(8, 0))
        if not required:
            ctk.CTkButton(btn_row, text="Abbrechen", fg_color="#334155", command=self.destroy).pack(
                side="right", padx=(8, 0)
            )
        ctk.CTkButton(btn_row, text="Speichern & Starten", command=self._save).pack(side="right")

        self._sync_server()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _sync_server(self) -> None:
        cloud = self.server_mode.get() == "cloud"
        self.server_entry.configure(state="disabled" if cloud else "normal")

    def _browse_dll(self) -> None:
        path = filedialog.askopenfilename(
            title="RailDriver64.dll",
            filetypes=[("RailDriver64.dll", "RailDriver64.dll"), ("DLL", "*.dll")],
        )
        if path:
            self.dll_var.set(path)

    def _auto_dll(self) -> None:
        found = find_raildriver_dll()
        if found:
            self.dll_var.set(found)
        else:
            messagebox.showwarning("Nicht gefunden", "RailDriver64.dll nicht gefunden.", parent=self)

    def _browse_scenario(self) -> None:
        path = filedialog.askdirectory(title="Szenario-Ordner")
        if path:
            self.scenario_var.set(path)

    def _on_close(self) -> None:
        if self.required:
            if messagebox.askyesno("Beenden?", "Ohne Einrichtung geht der Radar nicht.", parent=self):
                self.master.destroy()
            return
        self.destroy()

    def _save(self) -> None:
        player = self.player_var.get().strip()
        dll_path = self.dll_var.get().strip()
        session_id = self.session_var.get().strip()
        session_role = self.role_var.get().strip() or "driver"

        server = CLOUD_TRACKER_URL if self.server_mode.get() == "cloud" else normalize_tracker_url(
            self.server_var.get()
        )

        if not player:
            messagebox.showerror("Fehlt", "Bitte Namen eingeben.", parent=self)
            return
        if not server.startswith("http"):
            messagebox.showerror("Fehlt", "Ungültige Server-URL.", parent=self)
            return
        if not dll_path or not Path(dll_path).is_file():
            messagebox.showerror("Fehlt", "RailDriver-DLL wählen.", parent=self)
            return

        config = load_config() if CONFIG_PATH.exists() else {}
        config.update({
            "player_name": player,
            "server_url": server,
            "raildriver_dll_path": dll_path,
            "session_id": session_id,
            "session_role": session_role,
            "scenario_path": self.scenario_var.get().strip(),
        })
        save_config(config)
        self.on_saved()
        self.destroy()

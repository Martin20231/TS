# TS Multiplayer-Radar

Live-Karte, Session-Lobby, Konvoi, Cab-Overlay und Funk für Train Simulator Classic.

## Für Spieler (einfach)

**Doppelklick:** `TS-Radar Starten.bat` oder `dist\TS-Radar.exe`

Alles Weitere im **Launcher-Fenster** — Karte, Cab-Overlay, Funk, Einstellungen.

Anleitung: `docs\SPIELANLEITUNG.txt`

## Für Host (LAN / eigener PC)

`dev\HOST.bat` — startet Server + Launcher + Karte

Beenden: `dev\STOP.bat`

## Ordnerstruktur

```
radar/
  TS-Radar Starten.bat   ← Einstieg für Spieler
  launcher.py            ← Hauptprogramm (GUI)
  server.py              ← Karten-Server
  ts_tracker.py          ← GPS aus Train Simulator
  config.json            ← Deine Einstellungen
  static/                ← Web-Karte, Funk, Overlay
  ghost/                 ← Experiment (optional)
  docs/                  ← Anleitungen
  dev/                   ← Host, Build, Stop (Entwickler)
```

## Cloud

https://ts-multiplayer-radar.onrender.com — Session erstellen, Code an Freunde.

Deploy: `docs\DEPLOY.md`

## Exe bauen

`dev\build_exe.bat` → `dist\TS-Radar.exe`

# Train Simulator – Multiplayer-Radar

Live-Karte, **Session-Lobby**, **Konvoi**, **Leitstand** und **Overlay** für Train Simulator Classic.

## Schnellstart (Gruppe)

1. **`radar\start_radar.bat`** auf dem PC, der den Server hostet
2. Browser: **http://localhost:8080** → Tab **Session** → **Session erstellen**
3. Einladungslink an Freunde schicken (oder Session-Code)
4. In **`radar\config.json`** für jeden Fahrer:
   - `player_name` = dein Name
   - `session_id` = Code aus der Session (z. B. `xYz12a`)
   - `session_role` = `driver` oder `dispatch`
5. Train Simulator starten, Fahrt beginnen — Tracker sendet GPS automatisch

## Features

| Tab | Funktion |
|-----|----------|
| **Karte** | Live-Position aller Spieler in der Session, S-Bahn-Netz, Routen-Spur |
| **Session** | Lobby, Bereit-Status, Einladungslink, Fahrstatistik (km, Halte, max. Speed) |
| **Leitstand** | Textbefehle an alle oder einzelne Fahrer, Konvoi-Übersicht |
| **Overlay** | Kompaktes Fenster für zweiten Monitor (`/overlay`) |

**Konvoi:** Abstand zu anderen Zügen in der Session, Warnung unter `convoy_alert_km` (Standard 2 km).

**Ghost-Spuren:** Gestrichelte Linien zeigen, wo andere Spieler gefahren sind.

## Projektstruktur

```
radar/
  server.py          Flask + WebSocket + Session-API
  ts_tracker.py      GPS/Lok → Server
  mp_session.py      Sessions, Nachrichten, Statistik
  mp_geo.py          Entfernung, ETA, Stationen
  index.html         Karte + Tabs
  static/mp.js       Multiplayer-UI
  static/overlay.html
  start_radar.bat
```

## Konfiguration (`config.json`)

| Feld | Bedeutung |
|------|-----------|
| `player_name` | Name auf der Karte |
| `session_id` | Session-Code (nach Beitritt eintragen) |
| `session_role` | `driver` oder `dispatch` |
| `raildriver_dll_path` | Pfad zu `RailDriver64.dll` |
| `server_url` | `http://127.0.0.1:8080/api/position` (lokal) |
| `convoy_alert_km` | Nähe-Warnung in km |

Freunde im LAN: `server_url` auf `http://DEINE-IP:8080/api/position` setzen.

## Archiv

Pausierte Signal-Experimente: `archive/`

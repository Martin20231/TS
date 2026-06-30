# Multiplayer Ghost – Experiment (Lua + Brücke)

Zeigt **andere Session-Spieler im Spiel** an – als HUD-Hinweis und optional als platziertes Objekt `GHOST_MP`.

> **Status:** Experiment. Kein echtes KI-Fahrzeug auf den Gleisen. Position ist Näherung (Entfernung + Richtung vom Radar).

---

## Was funktioniert

| Feature | Beschreibung |
|---------|--------------|
| **HUD im Spiel** | „Anderer Zug · 11,4 km · Richtung 245°“ |
| **Nähe-Warnung** | Alert unter 2 km |
| **Ghost-Objekt** | Optional statischer Wagen `GHOST_MP` wird in Richtung des anderen verschoben |
| **Datenweg** | Radar-Server → `ghost_bridge.py` → Lok-Regler → `ScenarioScript.lua` |

---

## Voraussetzungen

- Train Simulator Classic, Route **Berlin** (oder beliebig – Szenario selbst anlegen)
- Radar läuft (`start_radar.bat` oder Cloud)
- **`session_id`** in `config.json` (gleiche Session wie der andere Spieler)
- Beide senden GPS (`TS-Radar.exe` / Tracker)

---

## Schritt 1 – Szenario vorbereiten (Editor)

1. **Tools → Szenario-Editor**
2. Neues **Free Roam**-Szenario (z.B. Start **Adlershof**)
3. In **`install_ghost.bat`** den Pfad eintragen (oben `SCENARIO_PATH=...`), dann die Datei doppelklicken
4. **Fahrplan** → Events anlegen:
   - `GhostStart` nach **1 s**
   - `GhostPoll` *(wird vom Script selbst getriggert – einmal anlegen reicht)*
5. Script **kompilieren**
6. **Optional – sichtbarer Ghost:**  
   - Rolling Stock platzieren (z.B. Wagen der BR 483)  
   - **Object Name** = `GHOST_MP` (exakt!)  
   - Kein Fahrer, kein Player-Consist

---

## Schritt 2 – Ghost-Bridge starten

```bat
radar\start_ghost_bridge.bat
```

Zusätzlich zum normalen Tracker (`TS-Radar.exe`).  
Train Simulator muss laufen, du musst **in der Lok sitzen**.

Die Bridge schreibt Entfernung/Richtung auf harmlose Lok-Regler (Spiegel, Innenlicht …).

---

## Schritt 3 – Testen

1. Session auf der Karte erstellen/beitreten
2. `session_id` in `config.json` (beide Spieler)
3. Szenario mit **GhostStart** starten
4. Anderer Spieler fährt irgendwo auf der Karte → du siehst Hinweise unten rechts

---

## Grenzen (ehrlich)

| Geht nicht (noch) | Warum |
|-------------------|--------|
| Echter KI-Zug auf Gleis | TS erlaubt kein Live-Spawn per Lua |
| Exakte GPS-Position | Nur Entfernung + Kompassrichtung → Objekt relativ zu dir |
| Ohne Szenario | Lua läuft nur im Szenario mit Script |
| Ohne Editor-Schritt | `GHOST_MP` / Events müssen einmal gesetzt werden |

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| Keine Hinweise | `ghost_bridge.bat` läuft? `session_id` gesetzt? |
| „Objekt fehlt“ | `GHOST_MP` im Editor benennen oder nur HUD nutzen |
| Regler-Konflikt | Andere Regler in `ghost_bridge.py` / Lua-Listen wählen |
| Script kompiliert nicht | Events exakt `GhostStart` / `GhostPoll` schreiben |

---

## Dateien

| Datei | Zweck |
|-------|--------|
| `ghost/ScenarioScript.lua` | Im Spiel: lesen + anzeigen |
| `ghost/ghost_bridge.py` | Radar → Lok-Regler |
| `start_ghost_bridge.bat` | Starten |

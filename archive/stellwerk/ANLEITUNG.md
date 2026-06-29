# Stellwerk Sim – Komplett-Anleitung (1:1)

Signale im **Train Simulator** per Klick auf der **Radar-Karte** schalten.

---

## Übersicht – was wofür ist

| Teil | Datei / Ort | Aufgabe |
|------|-------------|---------|
| Karte | `http://localhost:8080` | **Stellwerk Sim**-Tab → Signal klicken |
| Server | `radar/server.py` | Speichert Befehle |
| Tracker | `radar/ts_tracker.py` / `TS-Radar.exe` | Brücke Karte → Spiel |
| Szenario | Im TS-Editor gebaut | Signale `SW_S1` … im Spiel |
| Signal-Script | `TS Manual Stellwerk Shunt.lua` | Licht am Gleis |

---

# TEIL A – Einmalige Installation (ca. 45 Min.)

## A1 – Signal-Skript installieren

1. Ordner öffnen: `c:\Users\megad\Desktop\Unreal\ts\stellwerk\`
2. **`install.bat`** doppelklicken
3. Meldung **„[OK] Signal-Skript installiert“** abwarten

---

## A2 – Szenario im Train-Simulator-Editor

### A2.1 Editor öffnen

1. **Train Simulator** starten
2. Hauptmenü → **Werkzeuge** → **Szenario-Editor**
3. Route **„S-Bahn Berlin“** wählen

### A2.2 Neues Free-Roam-Szenario

1. **Datei → Neu**
2. Typ: **Freies Spiel / Free Roam**
3. Name: **`Stellwerk Adlershof`**
4. Start nahe **S Adlershof** (Gleis 3 oder 4)
5. **Spieler-Zug** platzieren (z. B. BR 481), als **Player** markieren
6. **Strg+S** speichern

### A2.3 Signal-Blueprint (einmalig)

1. Hauptmenü → **Blueprint-Editor**
2. Deutsches **Rangiersignal** (Shunt) suchen → **Speichern unter** als  
   **`TS Stellwerk Shunt Signal`**
3. Script: **`TS Manual Stellwerk Shunt.lua`**
4. Speichern, Editor schließen

### A2.4 Signale platzieren und benennen

Pro Signal (mindestens **2** zum Testen):

1. Im Szenario-Editor Signal platzieren (Blueprint von A2.3)
2. **Object Name** setzen:
   - `SW_S1` (Einfahrt)
   - `SW_S2` (Gleis 3)
   - optional: `SW_S3`, `SW_S4`
3. **Strg+S**

### A2.5 Start-Event für Script

1. Modus **Fahrplan / Timetable**
2. Beim Spieler-Dienst: **Anweisung hinzufügen** → **Warten** → **1 Sekunde**
3. Feld **Trigger Event**: exakt **`StellwerkStart`**
4. **Strg+S**

### A2.6 Szenario-Dateien kopieren

1. Im Editor: Tab **Script** → **Ordner öffnen**
2. **`stellwerk\copy_scenario.bat`** ausführen → Pfad einfügen
3. **`ScenarioScript.lua`** öffnen → `SIGNALS`-Block an deine Namen anpassen
4. Im Editor: Script **kompilieren**
5. **Strg+S**

---

# TEIL B – Jeden Spieltag (Stellwerk benutzen)

## B1 – Alles starten (Reihenfolge!)

1. **`radar\start_stellwerk_sim.bat`** doppelklicken  
   - startet Server + Tracker  
   - öffnet **`http://localhost:8080?mode=stellwerk`**

2. **Train Simulator** starten

3. Szenario **`Stellwerk Adlershof`** laden und **Starten**

4. Im Browser: oben **„Stellwerk Sim“** (orange) – nicht „Radar“

---

## B2 – Signal auf der Karte schalten

1. Karte zeigt **Adlershof** mit **farbigen Punkten** (Signale)
2. **Punkt anklicken** → Popup:
   - **Hp0 – Halt** (rot)
   - **Sh1 – Rangierfahrt** (gelb)
   - **Hp1 – Fahrt frei** (grün)
3. Button klicken
4. Unten: *„… wird ans Spiel gesendet …“*
5. **Im Spiel**: Signal am Gleis wechselt + Meldung „Radar: …“

---

## B3 – Weichen (im Spiel)

| Taste | Wirkung |
|-------|---------|
| **G** | Weiche vor dem Zug |
| **Shift+G** | Weiche hinter dem Zug |
| **9** | 2D-Karte → blauer Punkt = Weiche |

---

## B4 – Zum Fahren

1. Weiche + Signal stellen (Karte + ggf. **Taste 7** Draufsicht)
2. **Taste 1** = Führerstand
3. Fahren

---

# TEIL C – Prüfen ob alles läuft

| Check | Erwartung |
|-------|-----------|
| Browser `localhost:8080` | Seite lädt, Tab **Stellwerk Sim** |
| 4 Signale auf Karte | Farbige Punkte bei Adlershof |
| Tracker-Fenster | „Stellwerk-Brücke aktiv (Regler: …)“ |
| Nach Klick Hp1 | Tracker: `[Stellwerk] → Spiel: …` |
| Im TS | Signal leuchtet um |

**Tracker meldet „kein Regler“?**  
In `radar/config.json` anderen Namen setzen, z. B.:

```json
"stellwerk_bus_control": "Vigilance"
```

Gleichen Namen in `ScenarioScript.lua`:

```lua
STELLWERK_BUS_CONTROL = "Vigilance"
```

Script neu kompilieren.

---

# TEIL D – Radar vs. Stellwerk Sim

| Modus | Wofür |
|-------|--------|
| **Radar** | Zug live sehen, S-Bahn-Linien, Freunde |
| **Stellwerk Sim** | Nur Signale – keine Linien/Stationen, Karte auf Adlershof |

Umschalten: oben **Radar** | **Stellwerk Sim**

---

# Cloud (optional)

Für Freunde ohne lokalen Server:

1. `config.json` → `"server_url": "https://ts-multiplayer-radar.onrender.com/api/position"`
2. Neueste Version auf Render deployen
3. Karte: `https://ts-multiplayer-radar.onrender.com?mode=stellwerk`
4. Jeder Spieler: nur **Tracker** lokal (`start_tracker.bat`)

---

# Dateien zum Anpassen

| Datei | Inhalt |
|-------|--------|
| `radar/cache/stellwerk_signals.json` | Position der Punkte auf der Karte |
| `stellwerk/scenario/ScenarioScript.lua` | Signal-Namen `SW_S1` … |
| `radar/config.json` | Tracker, Brücken-Regler |

---

# Kurz-Checkliste

- [ ] `install.bat` ausgeführt
- [ ] Szenario mit Signalen `SW_S1` … + Event `StellwerkStart`
- [ ] `ScenarioScript.lua` kompiliert
- [ ] `start_stellwerk_sim.bat` gestartet
- [ ] TS-Szenario läuft
- [ ] Browser: Tab **Stellwerk Sim** → Signal geklickt → Licht im Spiel

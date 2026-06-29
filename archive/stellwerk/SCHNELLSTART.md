# Stellwerk – Schnellstart (ohne Objektliste)

Der Szenario-Editor hat **keine Suche** und die Signalliste ist unübersichtlich.
Deshalb **zwei getrennte Wege** – beide funktionieren ohne `S ModSig SH` zu finden.

---

## Weg A – Stellwerk auf der Web-Karte (sofort, ~2 Min.)

**Kein Editor. Keine Signale platzieren.**

1. Doppelklick: `radar\start_stellwerk_sim.bat`
2. Browser öffnet: `http://localhost:8080?mode=stellwerk`
3. Tab **Stellwerk Sim** → Signal anklicken → Hp0 / Sh1 / Hp1

Das zeigt die 4 Signale um Adlershof auf der Karte. Lichter im Spiel ändern sich damit noch nicht – dafür Weg B.

---

## Weg B – Lichter im Spiel (ohne neue Signale platzieren)

### Idee

Auf der Strecke liegen schon **Rangiersignale**. Die findest du in der 3D-Ansicht – nicht in der Objektliste.

### Schritt 1 – Script-Patch (einmal)

```bat
stellwerk\patch_hp_shunt.bat
```

Damit wird `HP_Shunt.lua` zum Stellwerk-Script. Im Editor musst du **kein Script mehr eintragen**.

### Schritt 2 – Szenario minimal fertig machen

1. Szenario **Stellwerk Adlershof** speichern (Free Roam, Start Adlershof)
2. `stellwerk\copy_scenario.bat` → Szenario-Ordner einfügen
3. Im Editor: **Fahrplan** → Warte 1 s → Event **`StellwerkStart`**
4. Script **kompilieren**

### Schritt 3 – Bestehendes Signal auf der Strecke nutzen

1. In der **3D-Ansicht** mit der Kamera **entlang der Gleise** fahren (WASD)
2. **Kleines Rangiersignal** suchen (kurzer Mast, rot/weiß – nicht das große KS-Hauptsignal)
3. Signal **anklicken**
4. Rechts **Eigenschaften** → **Object Name** = `SW_S1`
5. Optional: Signal **kopieren** (Strg+C, Strg+V) für `SW_S2`

Falls du **kein** Rangiersignal findest: erst Weg A nutzen; Signale später mit Hilfe platzieren.

### Schritt 4 – Testen

1. `radar\start_stellwerk_sim.bat`
2. Szenario im Spiel starten
3. Oben rechts: Meldungen **Hp0 / Sh1 / Hp1** – oder auf der Web-Karte klicken (Weg A + B zusammen)

---

## Was wir nicht mehr versuchen

| Aufgeben | Warum |
|----------|--------|
| Blueprint-Editor | Nur `Source\`, keine Signale |
| Objektliste durchsuchen | Keine Suche, hunderte Einträge |
| `vTRb *-Trigger` platzieren | Unsichtbare Trigger, keine Lichter |

---

## Hilfe

- Web geht nicht → `radar\stop_radar.bat`, dann neu starten
- Kein Object Name Feld → Screenshot vom Eigenschaften-Fenster schicken
- Patch rückgängig → siehe Hinweis in `patch_hp_shunt.bat`

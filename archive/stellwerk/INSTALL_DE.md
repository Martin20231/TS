# TS Stellwerk – In-Game Installation (Adlershof)

Dieses Paket bringt **Signalsteuerung direkt im Spiel**. Der Radar bleibt optional für die Kartenansicht – gesteuert wird alles über klickbare Meldungen im Spiel (oben rechts).

## Was ist fertig gebaut?

| Datei | Zweck |
|-------|--------|
| `signals/TS Manual Stellwerk Shunt.lua` | Manuell steuerbares Rangiersignal |
| `scenario/ScenarioScript.lua` | Stellwerk-UI im Spiel |
| `scenario/stellwerk_help.html` | Hilfe-Popup beim Start |
| `install.bat` | Kopiert Signal-Skript nach RailWorks |
| `copy_scenario.bat` | Kopiert Szenario-Dateien in deinen Szenario-Ordner |

## Was du einmal im Editor machen musst (~30 Min.)

Train Simulator kann **kein fertiges Szenario von außen** erzeugen – Signale müssen auf der Strecke platziert und benannt werden. Alles andere ist vorbereitet.

### Schritt 1: Signal-Skript installieren

```bat
stellwerk\install.bat
```

### Schritt 2: Free-Roam-Szenario anlegen

1. Train Simulator starten → **Tools** → **Szenario-Editor**
2. Route **Berlin S-Bahn** (deine Adlershof-Strecke) wählen
3. **Neues Szenario** → Typ **Free Roam**
4. Name: `Stellwerk Adlershof`
5. Startpunkt nahe **S Adlershof** setzen (Gleis 3 oder 4)
6. Optional: S-Bahn 481 als Player-Consist platzieren

### Schritt 3: Signale platzieren (ohne Blueprint-Editor!)

> **Wichtig:** Der **Blueprint-Editor** zeigt nur den Ordner `Source\` (Züge, Gebäude).  
> **Signale** liegen in `Assets\` – dort kommt man im Blueprint-Editor **nicht** hin.  
> Das ist normal. Du brauchst den Blueprint-Editor **gar nicht**.

Für jedes steuerbare Signal – alles im **Szenario-Editor** (3D-Ansicht):

1. Oben: **Einfügen** → **Signal** (oder Objekt-Browser → Kategorie Signale)
2. Ein **deutsches Rangiersignal** wählen, z. B. **HP Shunt** (S-Bahn Berlin / TrainTeamBerlin)
3. Signal aufs Gleis klicken zum Platzieren
4. Signal **anklicken** → rechts das **Eigenschaften-Fenster** (Properties)
5. Feld **Script** (oder **Signal Script** / **Lua Script**) suchen und eintragen:
   ```
   TS Manual Stellwerk Shunt.lua
   ```
   (wurde von `install.bat` nach den German-Signal-Ordnern kopiert)
6. Im **Properties-Flyout** → **Object Name** setzen:
   - `SW_S1` – Einfahrt Nord
   - `SW_S2` – Gleis 3 Ausfahrt
   - `SW_S3` – Gleis 4 Einfahrt
   - `SW_S4` – Zwischensignal Ost  
   (Namen müssen **exakt** mit `ScenarioScript.lua` übereinstimmen)

> Tipp: Du kannst mit **2–4 Signalen** starten und später erweitern.

### Schritt 4: Start-Trigger für das Script

1. Im Szenario-Editor einen **Trigger** am Start platzieren
2. **Trigger Event** = `StellwerkStart`
3. Oder: erste Instruction „Pass Through Marker“ mit Event `StellwerkStart`

### Schritt 5: Szenario-Dateien kopieren

```bat
stellwerk\copy_scenario.bat
```

Pfad eingeben (im Editor: Script → **Ordner öffnen**).

### Schritt 6: Konfiguration anpassen

`ScenarioScript.lua` öffnen, Block `SIGNALS` an deine Object Names anpassen:

```lua
SIGNALS = {
    { id = "SW_S1", label = "Einfahrt Nord" },
    ...
}
```

### Schritt 7: Script kompilieren

Im Editor → Script-Tab → **Compile** (luac).  
Fehler? `ScenarioScript.lua` Syntax prüfen.

### Schritt 8: Testen

1. Szenario **Stellwerk Adlershof** starten
2. Hilfe-Popup erscheint
3. Oben rechts: **klickbare Meldungen** → Signal wählen → Hp0 / Sh1 / Hp1
4. **Taste 7** = Draufsicht (Stellwerk-Kamera)
5. **Weichen**: `G` / `Shift+G` oder 2D-Karte (Taste `9`)

## Bedienung im Spiel

| Aktion | Steuerung |
|--------|-----------|
| Signal auf Halt | Meldung **Hp0** klicken |
| Rangierfahrt | Meldung **Sh1** klicken |
| Fahrt frei | Meldung **Hp1** klicken |
| Anderes Signal | **Anderes Signal wählen…** |
| Weiche | `G` / `Shift+G` oder 2D-Karte |
| Kamera Stellwerk | Taste `7` |

## Technische Grenzen (ehrlich)

- **Nur Signale**, die du mit unserem Script + Object Name eingerichtet hast
- **Keine** Fernsteuerung der originalen DB-Ks-Signale der Route ohne Einzelmodding
- **Weichen** nicht per Script – nur manuell (Free Roam) wie oben
- **Kein** Radar → Spiel-Brücke (dafür bräuchte es ein C++-Plugin)

## Route-ID (Referenz)

Berlin S-Bahn Route auf deinem PC:

`559170a3-0933-49a1-b99a-b1caa69edd55`

## Erweiterung auf mehr Signale

In `ScenarioScript.lua` bis zu **6 Signale** (`SW_PICK_1` … `SW_PICK_6`).  
Mehr als 6: weitere `OnEvent_SW_PICK_N`-Handler nach dem gleichen Muster ergänzen.

## Radar parallel nutzen

Tracker (`TS-Radar.exe` / `start_tracker.bat`) wie bisher starten – du siehst deinen Zug auf der Karte, stellst aber die Signale **im Spiel** um.

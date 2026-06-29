# Adlershof – Strecken-Signale (Berlin JWD)

## Warum du Signale nur im Karten-Editor anklicken kannst

| Editor | Was du bearbeitest |
|--------|-------------------|
| **Szenario-Editor** | Zug, Fahrplan, Script – **keine** fest eingebauten Strecken-Signale |
| **Strecken-Editor** (Karten-Editor) | Die **fest verbauten** HL-Signale der Route |

Das ist **normal**. Die Signale in Adlershof gehören zur **Strecke Berlin JWD**, nicht zu deinem Szenario.

---

## Signal-ID finden (das Feld „566“)

Im **Strecken-Editor** Signal anklicken → Eigenschaften rechts:

- Feld mit **Zahl** (bei dir: **566**) = **Signal-ID**
- Diese Zahl trägst du in `ScenarioScript.lua` ein (nicht SW_S1)

Beispiel:
```lua
SIGNALS = {
  { id = "566", label = "HL HS Adlershof 1" },
}
```

Optional: Leeres Feld neben der ID → dort könntest du `SW_S1` eintragen (wenn der Editor es erlaubt). Dann in Script `id = "SW_S1"` verwenden.

---

## Installation (einmal)

1. `stellwerk\install_hl_hs.bat` – ersetzt Script `vT HL HS` für alle HL-Signale
2. `stellwerk\copy_scenario.bat` – Szenario-Ordner eintragen
3. Im Szenario-Editor: Script **kompilieren**
4. `ScenarioScript.lua`: IDs deiner Signale eintragen (566, …)

---

## Test

1. `radar\start_stellwerk_sim.bat`
2. Szenario **Stellwerk Adlershof** starten
3. Web-Karte: **SW_S1** → Hp0 (mappt auf Signal-ID 566 / Index 1)
4. Oder Menü im Spiel: Hp0 / Sh1 / Hp1

---

## Editor-Namen (zum Wiederfinden)

| Im Objekt-Browser | Bedeutung |
|-------------------|-----------|
| `vT S45 HL HS 0T` | HL-Hauptsignal |
| `vT S45 Sig HLkompakt HS …` | Kompakt-HL (gleiches Script) |

Interner Pfad: `RailNetwork~Signals~German-HL~vT_...`

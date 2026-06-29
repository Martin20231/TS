# TS Multiplayer-Radar – Deployment auf Render (kostenlos)

## Was wohin gehört

| Ort | Dateien |
|-----|---------|
| **Render (Cloud)** | `server.py`, `index.html`, `radar_config.py`, `requirements.txt`, `cache/` |
| **Dein PC + Freunde** | `ts_tracker.py`, `config.json`, `start_tracker.bat` |

Der Tracker bleibt immer lokal – nur Karte und Server laufen online.

---

## Schritt 1: GitHub-Repository

### Option A – nur Radar-Ordner (empfohlen)

1. Neuen Ordner `ts-radar` anlegen
2. **Alles aus `radar/`** hineinkopieren (inkl. `cache/`, `render.yaml`)
3. `config.json` **nicht** mit hochladen (steht in `.gitignore`)
4. Auf GitHub neues Repo erstellen und pushen

### Option B – ganzes `ts`-Projekt

- `render.yaml` im Projekt-Root nutzt automatisch `rootDir: radar`

```powershell
cd C:\Users\megad\Desktop\Unreal\ts
git init
git add radar render.yaml
git commit -m "TS Multiplayer-Radar für Render"
git remote add origin https://github.com/DEIN-USER/DEIN-REPO.git
git push -u origin main
```

---

## Schritt 2: Render einrichten

1. [render.com](https://render.com) → Konto anlegen (GitHub verbinden)
2. **New +** → **Blueprint** (wenn `render.yaml` im Repo)  
   **oder** **Web Service** → Repo wählen
3. Einstellungen (falls manuell):

| Feld | Wert |
|------|------|
| Root Directory | `radar` (nur bei Option B) |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 120 server:app` |
| Health Check | `/api/status` |

4. **Create Web Service** – warten bis „Live“ (grün)
5. URL notieren, z. B. `https://ts-multiplayer-radar.onrender.com`

**Erster Start:** Dank `cache/` sind Stationen und Linien sofort da.

---

## Schritt 3: Lokale config.json (du + Freunde)

`config.example.json` → `config.json` kopieren:

```json
{
  "player_name": "Martin",
  "server_url": "https://ts-multiplayer-radar.onrender.com/api/position",
  "raildriver_dll_path": "E:\\Steam\\steamapps\\common\\RailWorks\\plugins\\RailDriver64.dll"
}
```

- **`player_name`** – eigener Name auf der Karte (jeder anders)
- **`server_url`** – dieselbe Render-URL für alle
- **`raildriver_dll_path`** – nur lokal, Pfad zu deiner DLL

---

## Schritt 4: Spielen

1. **Einmal** Render-URL im Browser öffnen (weckt Server nach Sleep, ~30–60 s)
2. **`start_tracker.bat`** starten (oder `start_radar.bat` nur lokal)
3. Train Simulator starten, Fahrt beginnen
4. Karte: `https://DEIN-SERVICE.onrender.com`

Freunde: gleiche Karten-URL, eigener `player_name`, gleiche `server_url`.

---

## Hinweise

- **Free Tier schläft** nach ~15 Min. ohne Besucher → vor der Session URL einmal öffnen
- **WebSocket** kann nach Sleep kurz hängen – REST-Fallback läuft weiter
- **HTTPS** ist auf Render automatisch aktiv
- Cache aktualisieren: `cache/` löschen, Server neu deployen (lädt OSM neu)

---

## Lokal testen (ohne Cloud)

```powershell
cd radar
pip install -r requirements.txt
python server.py
```

Karte: http://localhost:8080

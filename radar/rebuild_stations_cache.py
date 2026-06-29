"""Stationen-Cache neu aufbauen (nur echte S-Bahn-Halte)."""

from radar_config import CACHE_DIR
from server import STATIONS_CACHE_FILE, fetch_sbahn_stations, save_disk_cache

if __name__ == "__main__":
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stations = fetch_sbahn_stations()
    save_disk_cache(STATIONS_CACHE_FILE, stations)
    names = sorted(s["name"] for s in stations)
    print(f"Gespeichert: {STATIONS_CACHE_FILE} ({len(stations)} Stationen)")
    print("Adenauerplatz enthalten:", any("Adenauer" in n for n in names))
    print("Neukölln Treffer:", [n for n in names if "Neuk" in n])

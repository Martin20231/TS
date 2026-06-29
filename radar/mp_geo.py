"""Geodätische Hilfsfunktionen für Multiplayer-Radar."""

from __future__ import annotations

import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    y = math.sin(d_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def heading_delta(a: float, b: float) -> float:
    """Kleinster Winkel zwischen zwei Kompassrichtungen (Grad)."""
    diff = abs((a - b + 180.0) % 360.0 - 180.0)
    return diff


def eta_minutes(distance_km: float, speed_kph: float) -> float | None:
    if speed_kph < 3.0 or distance_km <= 0:
        return None
    return (distance_km / speed_kph) * 60.0


def format_distance(km: float) -> str:
    if km < 1.0:
        return f"{int(round(km * 1000))} m"
    return f"{km:.1f} km"


def normalize_station_key(name: str) -> str:
    """Vergleichsschlüssel für Haltestellennamen (ohne S-/Berlin-Präfix)."""
    key = name.strip()
    if key.lower().startswith("s "):
        key = key[2:].strip()
    if key.lower().startswith("berlin "):
        key = key[7:].strip()
    return key.lower()


def format_sbahn_station_name(name: str) -> str:
    """Einheitliche Anzeige wie im Simulator: „S Name“."""
    label = name.strip()
    if label.lower().startswith("berlin "):
        label = label[7:].strip()
    if label.lower().startswith("s "):
        label = label[2:].strip()
    return f"S {label}"


def deduplicate_sbahn_stations(stations: list[dict], merge_km: float = 0.4) -> list[dict]:
    """Fasst mehrere OSM-Knoten derselben Haltestelle zu einem Marker zusammen."""
    groups: dict[str, list[dict]] = {}
    for station in stations:
        key = normalize_station_key(station["name"])
        groups.setdefault(key, []).append(station)

    merged: list[dict] = []
    for items in groups.values():
        clusters: list[list[dict]] = []
        for item in items:
            placed = False
            for cluster in clusters:
                anchor = cluster[0]
                if haversine_km(item["lat"], item["lon"], anchor["lat"], anchor["lon"]) <= merge_km:
                    cluster.append(item)
                    placed = True
                    break
            if not placed:
                clusters.append([item])

        for cluster in clusters:
            lat = sum(point["lat"] for point in cluster) / len(cluster)
            lon = sum(point["lon"] for point in cluster) / len(cluster)
            display_name = max((point["name"] for point in cluster), key=len)
            merged.append({"name": display_name, "lat": lat, "lon": lon})

    merged.sort(key=lambda station: station["name"])
    return merged


def nearest_station(
    lat: float, lon: float, stations: list[dict], max_km: float = 80.0
) -> dict | None:
    best: dict | None = None
    best_dist = max_km
    for station in stations:
        dist = haversine_km(lat, lon, station["lat"], station["lon"])
        if dist < best_dist:
            best_dist = dist
            best = {**station, "distance_km": dist}
    return best

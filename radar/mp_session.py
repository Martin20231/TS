"""Session-Lobby, Leitstand-Nachrichten und Fahrtstatistik."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from mp_geo import haversine_km, heading_delta


SESSION_TTL_SECONDS = 24 * 3600
MESSAGE_LIMIT = 200
TRAIL_MAX_POINTS = 300


@dataclass
class MemberStats:
    distance_km: float = 0.0
    max_speed_kph: float = 0.0
    stops: int = 0
    driving_seconds: float = 0.0
    last_lat: float | None = None
    last_lon: float | None = None
    last_ts: float = 0.0
    last_stop_station: str | None = None
    near_station_since: float | None = None


@dataclass
class Member:
    player: str
    role: str = "driver"
    loco: str = ""
    ready: bool = False
    joined_at: float = field(default_factory=time.time)
    stats: MemberStats = field(default_factory=MemberStats)


@dataclass
class DispatchMessage:
    id: int
    sender: str
    target: str | None
    text: str
    timestamp: float


@dataclass
class Session:
    session_id: str
    name: str
    created_at: float = field(default_factory=time.time)
    members: dict[str, Member] = field(default_factory=dict)
    messages: list[DispatchMessage] = field(default_factory=list)
    next_message_id: int = 1
    trails: dict[str, list[dict]] = field(default_factory=dict)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._player_session: dict[str, str] = {}

    def _purge_stale(self) -> None:
        now = time.time()
        stale_ids = [
            sid
            for sid, session in self._sessions.items()
            if now - session.created_at > SESSION_TTL_SECONDS and not session.members
        ]
        for sid in stale_ids:
            del self._sessions[sid]

    def create(self, name: str) -> Session:
        self._purge_stale()
        session_id = secrets.token_urlsafe(6)
        session = Session(session_id=session_id, name=name.strip() or "Fahrt")
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def join(
        self,
        session_id: str,
        player: str,
        role: str = "driver",
        loco: str = "",
    ) -> Session | None:
        session = self.get(session_id)
        if session is None:
            return None

        old_sid = self._player_session.get(player)
        if old_sid and old_sid != session_id and old_sid in self._sessions:
            self._sessions[old_sid].members.pop(player, None)

        if player not in session.members:
            session.members[player] = Member(player=player, role=role, loco=loco)
        else:
            member = session.members[player]
            member.role = role or member.role
            if loco:
                member.loco = loco

        self._player_session[player] = session_id
        return session

    def set_ready(self, session_id: str, player: str, ready: bool) -> bool:
        session = self.get(session_id)
        if session is None or player not in session.members:
            return False
        session.members[player].ready = ready
        return True

    def add_message(
        self,
        session_id: str,
        sender: str,
        text: str,
        target: str | None = None,
    ) -> DispatchMessage | None:
        session = self.get(session_id)
        if session is None or sender not in session.members:
            return None

        text = text.strip()
        if not text:
            return None

        msg = DispatchMessage(
            id=session.next_message_id,
            sender=sender,
            target=target,
            text=text[:500],
            timestamp=time.time(),
        )
        session.next_message_id += 1
        session.messages.append(msg)
        if len(session.messages) > MESSAGE_LIMIT:
            session.messages = session.messages[-MESSAGE_LIMIT:]
        return msg

    def messages_after(self, session_id: str, after_id: int) -> list[DispatchMessage]:
        session = self.get(session_id)
        if session is None:
            return []
        return [m for m in session.messages if m.id > after_id]

    def update_position(
        self,
        session_id: str,
        player: str,
        lat: float,
        lon: float,
        speed_kph: float,
        heading: float,
        loco: str = "",
        nearest_station_name: str | None = None,
        nearest_station_km: float | None = None,
    ) -> None:
        session = self.get(session_id)
        if session is None or player not in session.members:
            return

        member = session.members[player]
        if loco:
            member.loco = loco

        stats = member.stats
        now = time.time()

        if stats.last_lat is not None and stats.last_lon is not None and stats.last_ts:
            dt = now - stats.last_ts
            if 0 < dt < 120:
                stats.distance_km += haversine_km(stats.last_lat, stats.last_lon, lat, lon)
                if speed_kph > 2:
                    stats.driving_seconds += dt

        stats.last_lat = lat
        stats.last_lon = lon
        stats.last_ts = now
        stats.max_speed_kph = max(stats.max_speed_kph, speed_kph)

        if (
            nearest_station_name
            and nearest_station_km is not None
            and nearest_station_km < 0.35
            and speed_kph < 12
        ):
            if stats.near_station_since is None:
                stats.near_station_since = now
            elif (
                now - stats.near_station_since > 8
                and stats.last_stop_station != nearest_station_name
            ):
                stats.stops += 1
                stats.last_stop_station = nearest_station_name
        else:
            stats.near_station_since = None

        trail = session.trails.setdefault(player, [])
        if not trail or haversine_km(trail[-1]["lat"], trail[-1]["lon"], lat, lon) > 0.02:
            trail.append({"lat": lat, "lon": lon, "t": now})
            if len(trail) > TRAIL_MAX_POINTS:
                session.trails[player] = trail[-TRAIL_MAX_POINTS:]

    def build_convoy(
        self,
        session_id: str,
        player: str,
        positions: dict[str, dict],
    ) -> list[dict]:
        session = self.get(session_id)
        if session is None:
            return []

        self_pos = positions.get(player)
        if not self_pos:
            return []

        results = []
        for name, member in session.members.items():
            if name == player:
                continue
            other = positions.get(name)
            if not other or not other.get("active", True):
                continue

            dist = haversine_km(
                self_pos["lat"], self_pos["lon"],
                other["lat"], other["lon"],
            )
            hdg_diff = heading_delta(self_pos.get("heading", 0), other.get("heading", 0))
            same_direction = hdg_diff < 45 or hdg_diff > 315

            results.append({
                "player": name,
                "distance_km": round(dist, 3),
                "speed_kph": other.get("speed_kph", 0),
                "loco": member.loco or other.get("loco", ""),
                "role": member.role,
                "same_direction": same_direction,
                "active": other.get("active", True),
            })

        results.sort(key=lambda x: x["distance_km"])
        return results

    def session_payload(self, session_id: str, positions: dict[str, dict]) -> dict | None:
        session = self.get(session_id)
        if session is None:
            return None

        members_out = []
        for name, member in session.members.items():
            pos = positions.get(name, {})
            members_out.append({
                "player": name,
                "role": member.role,
                "loco": member.loco or pos.get("loco", ""),
                "ready": member.ready,
                "active": pos.get("active", False),
                "speed_kph": pos.get("speed_kph", 0),
                "stats": {
                    "distance_km": round(member.stats.distance_km, 2),
                    "max_speed_kph": round(member.stats.max_speed_kph, 1),
                    "stops": member.stats.stops,
                    "driving_minutes": round(member.stats.driving_seconds / 60, 1),
                },
            })

        members_out.sort(key=lambda m: (-int(m["active"]), m["player"]))

        trails_out = {
            name: points[-120:]
            for name, points in session.trails.items()
        }

        messages_out = [
            {
                "id": m.id,
                "sender": m.sender,
                "target": m.target,
                "text": m.text,
                "timestamp": m.timestamp,
            }
            for m in session.messages[-40:]
        ]

        return {
            "session_id": session.session_id,
            "name": session.name,
            "created_at": session.created_at,
            "members": members_out,
            "messages": messages_out,
            "trails": trails_out,
            "ready_count": sum(1 for m in session.members.values() if m.ready),
            "member_count": len(session.members),
        }

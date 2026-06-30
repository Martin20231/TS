"""Session-Funk: WebRTC-Signaling + PTT-Status (Hupe / Taste)."""

from __future__ import annotations

from flask import jsonify, request
from flask_socketio import SocketIO, emit, join_room

# session_id -> { player_name: socket_id }
_radio_online: dict[str, dict[str, str]] = {}
# (session_id, player) -> transmitting
_radio_ptt: dict[tuple[str, str], bool] = {}


def register_radio_routes(app, static_dir, socketio: SocketIO) -> None:
    @app.route("/radio")
    def radio_page():
        from flask import send_from_directory

        return send_from_directory(static_dir, "radio.html")

    @app.post("/api/radio/ptt")
    def set_radio_ptt():
        data = request.get_json(force=True) or {}
        player = str(data.get("player", "")).strip()
        session_id = str(data.get("session_id", "")).strip()
        active = bool(data.get("active"))
        if not player or not session_id:
            return jsonify({"error": "player und session_id nötig"}), 400

        _radio_ptt[(session_id, player)] = active
        socketio.emit(
            "radio_ptt",
            {"player": player, "active": active},
            room=f"radio:{session_id}",
        )
        return jsonify({"ok": True, "active": active})

    @app.get("/api/radio/ptt")
    def get_radio_ptt():
        player = request.args.get("player", "").strip()
        session_id = request.args.get("session_id", "").strip()
        if not player or not session_id:
            return jsonify({"active": False})
        return jsonify({"active": _radio_ptt.get((session_id, player), False)})


def register_radio_socketio(socketio: SocketIO) -> None:
    @socketio.on("radio_join")
    def radio_join(data):
        from flask import request as flask_request

        session_id = str((data or {}).get("session_id", "")).strip()
        player = str((data or {}).get("player", "")).strip()
        if not session_id or not player:
            return

        sid = flask_request.sid
        peers = _radio_online.setdefault(session_id, {})
        peers[player] = sid

        join_room(f"radio:{session_id}")
        join_room(f"radio:{session_id}:{player}")

        others = [name for name in peers if name != player]
        emit("radio_peers", {"peers": others})
        emit(
            "radio_peer_joined",
            {"player": player},
            room=f"radio:{session_id}",
            include_self=False,
        )

    @socketio.on("radio_signal")
    def radio_signal(data):
        session_id = str((data or {}).get("session_id", "")).strip()
        target = str((data or {}).get("target", "")).strip()
        if not session_id or not target:
            return
        emit(
            "radio_signal",
            data,
            room=f"radio:{session_id}:{target}",
            include_self=False,
        )

    @socketio.on("disconnect")
    def radio_disconnect():
        from flask import request as flask_request

        sid = flask_request.sid
        for session_id, peers in list(_radio_online.items()):
            for player, psid in list(peers.items()):
                if psid != sid:
                    continue
                del peers[player]
                _radio_ptt.pop((session_id, player), None)
                emit(
                    "radio_peer_left",
                    {"player": player},
                    room=f"radio:{session_id}",
                    include_self=False,
                )

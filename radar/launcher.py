"""
TS Multiplayer-Radar – Einstiegspunkt.

Doppelklick TS-Radar.exe oder TS-Radar Starten.bat
"""

from __future__ import annotations

import sys


def dispatch_cli() -> bool:
    if len(sys.argv) < 2:
        return False

    mode = sys.argv[1].lstrip("-")
    if mode == "cab-overlay":
        from cab_overlay import main

        main()
    elif mode == "radio-bridge":
        from radio_bridge import run_radio_bridge

        run_radio_bridge()
    elif mode == "ghost-bridge":
        from ghost.ghost_bridge import run_ghost_bridge

        run_ghost_bridge()
    elif mode == "server":
        import server

        server.socketio.start_background_task(server.stale_broadcast_loop)
        server.socketio.start_background_task(server.warmup_map_data)
        server.socketio.run(
            server.app,
            host=server.SERVER_HOST,
            port=server.SERVER_PORT,
            allow_unsafe_werkzeug=True,
        )
    else:
        return False
    return True


def main() -> None:
    if dispatch_cli():
        return
    from launcher_app import RadarLauncherApp

    RadarLauncherApp().run()


if __name__ == "__main__":
    main()

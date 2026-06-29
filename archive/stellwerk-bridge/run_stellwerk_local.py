"""
Stellwerk Sim lokal – Server und Tracker in einem Prozess.

Vermeidet Port-Konflikte (WinError 10048) durch doppelte Server/Tracker-Fenster.
"""

from __future__ import annotations

import threading
import time


def main() -> None:
    from server import (
        SERVER_HOST,
        SERVER_PORT,
        socketio,
        app,
        stale_broadcast_loop,
        warmup_map_data,
    )
    from ts_tracker import run_tracker

    def start_server() -> None:
        socketio.start_background_task(stale_broadcast_loop)
        socketio.start_background_task(warmup_map_data)
        socketio.run(
            app,
            host=SERVER_HOST,
            port=SERVER_PORT,
            allow_unsafe_werkzeug=True,
        )

    thread = threading.Thread(target=start_server, daemon=True, name="radar-server")
    thread.start()

    print("Warte auf Server …")
    for _ in range(30):
        try:
            import urllib.request

            with urllib.request.urlopen(
                f"http://127.0.0.1:{SERVER_PORT}/api/health", timeout=1
            ):
                break
        except OSError:
            time.sleep(0.25)
    else:
        print("[Warnung] Server antwortet noch nicht – Tracker startet trotzdem.")

    print("=" * 55)
    print("Stellwerk Sim – Server + Tracker (ein Prozess)")
    print(f"Karte: http://127.0.0.1:{SERVER_PORT}?mode=stellwerk")
    print("=" * 55)

    run_tracker()


if __name__ == "__main__":
    main()

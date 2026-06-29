"""Gunicorn-Konfiguration für Render (Flask-SocketIO + gevent)."""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
workers = 1
worker_class = "gevent"
timeout = 120
keepalive = 5
loglevel = "info"


def post_worker_init(worker):
    """Startet Hintergrund-Jobs sobald der Worker bereit ist."""
    from server import ensure_background_tasks

    ensure_background_tasks()

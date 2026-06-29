"""Gemeinsame HTTP-Session für Tracker → lokaler Server (Keep-Alive, weniger Port-Fehler)."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_http_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Connection": "keep-alive"})
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.3,
        status_forcelist=(502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=2)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

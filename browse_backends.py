"""Backends de browse: fetch directo (T05); Anchor se agrega en T30."""
from __future__ import annotations

import os
import re
import urllib.request

from tracing import span


def _html_to_text(html: str) -> str:
    """Saca tags y colapsa espacios."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def fetch_direct(url: str) -> str:
    """GET directo con urllib; devuelve texto plano."""
    req = urllib.request.Request(url, headers={"User-Agent": "victim-agent/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310
        return _html_to_text(r.read().decode("utf-8", errors="replace"))


def fetch_text(url: str) -> str:
    """Texto de la página según BROWSE_BACKEND (por ahora siempre directo)."""
    backend = os.getenv("BROWSE_BACKEND", "direct")
    with span("browse.fetch", "TOOL", **{"input.value": url, "browse.backend": backend}):
        return fetch_direct(url)

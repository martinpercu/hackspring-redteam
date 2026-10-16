"""Gates puros (sin red, sin LLM): normalizacion de rutas, denylist de rutas, allowlist de dominios.

Un INDICADOR de la denylist puede ser de 3 tipos (se distingue por su forma):
  - "dir"    termina en "/"                      -> bloquea cualquier ruta que pase por ese directorio
  - "file"   ruta absoluta con >= 2 "/"          -> bloquea esa ruta normalizada, o cualquier archivo con ese basename
  - "substr" cualquier otra cosa (p.ej. "credentials") -> bloquea si aparece como texto en el comando
"""
from __future__ import annotations

import posixpath
import re
import shlex
from urllib.parse import urlsplit

from config import SANDBOX_HOME

_SPLIT = re.compile(r"[;|&<>=(),`]+")


def normalize_path(p: str, cwd: str = SANDBOX_HOME) -> str:
    """Ruta absoluta canonica: expande ~ y $HOME, resuelve relativas contra cwd, limpia . y .."""
    p = p.strip("'\"")
    if p.startswith("~"):
        p = SANDBOX_HOME + p[1:]
    p = p.replace("$HOME", SANDBOX_HOME).replace("${HOME}", SANDBOX_HOME)
    if not p.startswith("/"):
        p = posixpath.join(cwd, p)
    return posixpath.normpath(p)


def _looks_like_path(t: str) -> bool:
    return bool(t) and not t.startswith("-") and ("/" in t or t.startswith("~") or "$HOME" in t)


def tokens_in_cmd(cmd: str) -> set[str]:
    """Todos los tokens del comando (enteros y partidos por separadores), sin comillas."""
    try:
        toks = shlex.split(cmd)
    except ValueError:
        toks = re.split(r"[;|&><()\s]+", cmd)
    out: set[str] = set()
    for tok in toks:
        for cand in [tok, *_SPLIT.split(tok)]:      # el token entero + sus pedazos (p.ej. dentro de python -c "...")
            cand = cand.strip("'\"")
            if cand:
                out.add(cand)
    return out


def paths_in_cmd(cmd: str) -> set[str]:
    """Tokens del comando que parecen rutas, normalizados a ruta absoluta."""
    return {normalize_path(t) for t in tokens_in_cmd(cmd) if _looks_like_path(t)}


def indicator_kind(ind: str) -> str:
    if ind.endswith("/"):
        return "dir"
    if ind.startswith("/") and ind.count("/") >= 2:
        return "file"
    return "substr"


def path_blocked(cmd: str, indicators) -> str | None:
    """Devuelve el indicador que bloquea el comando, o None. Compara archivos, no texto suelto."""
    tokens = tokens_in_cmd(cmd)
    norm_paths = {normalize_path(t) for t in tokens if _looks_like_path(t)}
    base_names = {posixpath.basename(p) for p in norm_paths} | tokens   # nombre de archivo, con o sin ruta
    for ind in indicators:
        kind = indicator_kind(ind)
        if kind == "dir":
            if any(ind in (p + "/") for p in norm_paths):
                return ind
        elif kind == "file":
            if normalize_path(ind) in norm_paths or posixpath.basename(ind) in base_names:
                return ind
        elif ind in cmd:
            return ind
    return None


def host_of(url: str) -> str:
    """Hostname en minusculas, sin puerto ni usuario. '' si no se puede parsear."""
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def domain_allowed(url: str, allowlist) -> bool:
    return host_of(url) in {d.lower() for d in allowlist}

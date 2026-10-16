"""ElevenLabs: narracion con cache en disco (speak / narrate / sfx / prerender)."""
import hashlib
import os

from config import log
from tracing import span

AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "audio")
_V1 = os.getenv("ELEVENLABS_VOICE_ID") or "JBFqnCBsd6RMkjVDRZzb"
VOICES = {"defender": _V1, "attacker": os.getenv("ELEVENLABS_VOICE_ID_2") or _V1}
MODEL = os.getenv("ELEVENLABS_MODEL") or "eleven_multilingual_v2"


def _client():
    """Cliente ElevenLabs o None si no hay key."""
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        return None
    from elevenlabs.client import ElevenLabs
    return ElevenLabs(api_key=key)


def _write(audio, path: str) -> None:
    """Escribe un generator de bytes a disco."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        for chunk in audio:
            if chunk:
                f.write(chunk)


def speak(text: str, path: str = "summary.mp3", voice_id: str | None = None) -> str | None:
    """Sintetiza `text` a un mp3 en `path`; None si no hay key o falla."""
    with span("eleven.speak", "TOOL", **{"input.value": text}):
        client = _client()
        if client is None:
            log("voice", "sin ELEVENLABS_API_KEY: no se genera audio")
            return None
        try:
            audio = client.text_to_speech.convert(
                text=text, voice_id=voice_id or VOICES["defender"],
                model_id=MODEL, output_format="mp3_44100_128")
            _write(audio, path)
            return path
        except Exception as e:  # noqa: BLE001
            log("voice", f"speak fallo: {type(e).__name__}")
            return None


def audio_name(text: str, who: str) -> str:
    """Nombre de archivo estable para (voz, modelo, texto)."""
    return hashlib.sha1(f"{who}|{MODEL}|{text}".encode()).hexdigest()[:12] + ".mp3"


def narrate(text: str, who: str = "defender", audio_dir: str | None = None) -> str | None:
    """URL /audio/<hash>.mp3 (cache en disco; renderiza si falta y hay key)."""
    d = audio_dir or AUDIO_DIR
    name = audio_name(text, who)
    path = os.path.join(d, name)
    if os.path.exists(path):
        return "/audio/" + name
    if not os.getenv("ELEVENLABS_API_KEY"):
        return None
    out = speak(text, path, VOICES.get(who, VOICES["defender"]))
    return "/audio/" + name if out else None


def sfx(prompt: str = "short urgent security alarm beep", name: str = "alarm.mp3",
        audio_dir: str | None = None) -> str | None:
    """Efecto de sonido cacheado; None si falla."""
    path = os.path.join(audio_dir or AUDIO_DIR, name)
    if os.path.exists(path):
        return "/audio/" + name
    client = _client()
    if client is None:
        return None
    try:
        _write(client.text_to_sound_effects.convert(text=prompt, duration_seconds=1.5), path)
        return "/audio/" + name
    except Exception as e:  # noqa: BLE001
        log("voice", f"sfx fallo: {type(e).__name__}")
        return None


def prerender() -> int:
    """Renderiza todas las lineas fijas de narrator.LINES + alarma; devuelve cuantas quedaron."""
    from narrator import LINES
    n = 0
    for who, text in LINES.values():
        if narrate(text, who):
            n += 1
    sfx()
    log("voice", f"{n}/{len(LINES)} lineas de narracion listas")
    return n


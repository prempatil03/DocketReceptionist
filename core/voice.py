"""Voice engine — the bot hears and speaks.

Two jobs:
  * speak(text, lang)  — turn the AI's reply into human-sounding speech.
  * listen()           — record the caller from the microphone and return text.

Both are FREE and need no API key:
  * TTS uses edge-tts (Microsoft neural voices). Voice is chosen per language.
  * STT uses Google's free recognizer over the internet.

If the mic or speech fails, we degrade gracefully — the caller still gets
text help (see voice_call.py for the text fallback).
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

# English / Hindi / Marathi neural voices (free, no key).
# All are FEMALE, warm and natural — like a friendly young Indian woman.
VOICES = {
    "english":  "en-IN-NeerjaNeural",    # Indian English, female, warm
    "hindi":    "hi-IN-SwaraNeural",     # Hindi, female, natural
    "marathi":  "mr-IN-AarohiNeural",    # Marathi, female, natural
    "hinglish": "hi-IN-SwaraNeural",     # Hinglish uses the Hindi female voice
}


def _voice_for(lang: str) -> str:
    return VOICES.get(lang, VOICES["hinglish"])


async def _synthesize(text: str, lang: str) -> bytes:
    """Generate speech audio (mp3 bytes) for text in the given language."""
    import edge_tts
    # Natural pace — no speed boost (rushed speech sounds robotic).
    communicate = edge_tts.Communicate(text, _voice_for(lang))
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


def speak(text: str, lang: str = "hinglish") -> bool:
    """Speak text out loud. Returns True on success, False on failure."""
    if not text:
        return False
    try:
        import asyncio
        audio = asyncio.run(_synthesize(text, lang))
        if not audio:
            return False
        _play_mp3(audio)
        return True
    except Exception as e:
        print(f"[voice] TTS failed: {e}")
        return False


def _play_mp3(mp3_bytes: bytes) -> None:
    """Play in-memory mp3 bytes through the speakers."""
    import miniaudio
    import numpy as np
    import sounddevice as sd

    decoded = miniaudio.decode(mp3_bytes, output_format=miniaudio.SampleFormat.SIGNED16)

    # decoded.samples is an array.array of int16 PCM samples.
    # CRITICAL: if stereo, the buffer is interleaved (L,R,L,R...) — it MUST be
    # reshaped to 2D or sounddevice treats it as mono and plays at HALF speed.
    samples = np.frombuffer(decoded.samples, dtype=np.int16).copy()
    if decoded.nchannels == 2:
        samples = samples.reshape(-1, 2)
    elif decoded.nchannels == 1:
        samples = np.stack([samples, samples], axis=1)  # mono -> stereo for safety

    sd.play(samples, decoded.sample_rate)
    sd.wait()


def listen(timeout: float = 4.0, phrase_limit: float = 6.0) -> str:
    """Record the caller from the mic and return what they said.

    Returns the recognized text (may be empty if nothing heard).
    Raises RuntimeError if the microphone is unavailable.
    """
    import sounddevice as sd
    import numpy as np
    import speech_recognition as sr

    fs = 16000
    duration = phrase_limit
    print(f"[voice] Listening {int(duration)}s... (say your docket number)")

    # Record in short blocks so we can detect silence early and not waste time.
    block = int(0.5 * fs)
    frames: list[np.ndarray] = []
    total = int(duration * fs)
    recorded = 0
    while recorded < total:
        chunk = sd.rec(min(block, total - recorded), samplerate=fs, channels=1, dtype="int16")
        sd.wait()
        chunk = np.asarray(chunk).reshape(-1)
        frames.append(chunk)
        recorded += len(chunk)
        # If the caller already spoke and then went silent for a while, stop early.
        if recorded > int(1.5 * fs) and _is_silent(chunk):
            break

    audio = np.concatenate(frames)
    if _is_silent(audio):
        return ""  # nothing spoken — don't waste a Google call

    audio_bytes = audio.tobytes()
    audio_data = sr.AudioData(audio_bytes, fs, 2)

    recognizer = sr.Recognizer()
    try:
        text = recognizer.recognize_google(audio_data, language="hi-IN")
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        raise RuntimeError(f"Speech service unavailable: {e}")

    return _words_to_digits(text)


def _is_silent(chunk: np.ndarray, threshold: float = 50.0) -> bool:
    """True if this audio block is (nearly) silent — nothing being said."""
    import numpy as np
    rms = float(np.sqrt(np.mean(chunk.astype(float) ** 2)))
    return rms < threshold


# Map spoken number-words to digits so "five six six zero" -> "5660".
# Works for English and Hinglish callers reading their docket aloud.
_NUMBER_WORDS = {
    "zero": "0", "oh": "0", "o": "0", "one": "1", "won": "1", "two": "2",
    "to": "2", "too": "2", "three": "3", "tree": "3", "four": "4", "for": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
}


def _words_to_digits(text: str) -> str:
    """Turn a docket read aloud ("one one nine nine...") into digits."""
    words = text.lower().replace(",", " ").split()
    digits = [_NUMBER_WORDS[w] for w in words if w in _NUMBER_WORDS]
    if len(digits) >= 5:
        return "".join(digits)
    return text

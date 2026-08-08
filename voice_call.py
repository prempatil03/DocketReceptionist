"""Voice call simulator — talk to the receptionist out loud, no phone needed.

Run:
    python voice_call.py

The bot speaks (via your speakers), then listens (via your microphone).
If a mic is missing, it falls back to typing. Type 'quit' to exit.

To test TTS only:   python voice_call.py --test-tts
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Windows console emoji fix.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from core.conversation import Receptionist  # noqa: E402
from core.language import detect_language  # noqa: E402
from core.voice import listen, speak  # noqa: E402


def speak_bot(text: str, lang: str = "hinglish") -> None:
    print(f"🤖 AI : {text}")
    if not speak(text, lang):
        print("   [voice unavailable — showing text only]")


def run_call() -> None:
    bot = Receptionist()
    print("=" * 62)
    print("  VOICE CALL — speak into your mic. Type 'quit' to exit.")
    print("=" * 62)

    # Greeting out loud.
    greet = bot.start()
    lang = "hinglish"
    speak_bot(greet, lang)

    while True:
        # Listen for the caller.
        try:
            caller = listen()
        except Exception as e:
            print(f"[voice] Mic problem ({e}). Falling back to typing.")
            caller = input("🧑 caller (type): ").strip()

        if not caller:
            # Silence — no speech detected.
            reply = bot.silence()
            speak_bot(reply.text, lang)
            if reply.hangup:
                return
            continue

        if caller.strip().lower() in ("quit", "exit", "stop"):
            print("☎️  CALL ENDED. Goodbye!")
            return

        print(f"🧑 caller (heard): {caller}")
        reply = bot.respond(caller)
        lang = detect_language(caller)

        speak_bot(reply.text, lang)
        if reply.transfer_to_human:
            print("🔁 (transferring this call to a human staff member...)")
        if reply.hangup:
            return


def main() -> None:
    if "--test-tts" in sys.argv:
        # Uses the bot's real greeting (company name comes from .env).
        bot = Receptionist()
        speak_bot(bot.start(), "hinglish")
        return
    run_call()


if __name__ == "__main__":
    main()

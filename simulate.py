"""PC call simulator — test the receptionist without any phone.

Runs a fake phone call in your terminal:
  * the AI greets you like it answered a real call
  * you type what the caller says (e.g. a docket number)
  * the AI replies

Commands:  /quit   end the call    /new   start a new call
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project importable when run from its own folder.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Windows consoles often default to cp1252 and cannot print emoji — force UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from core.conversation import Receptionist  # noqa: E402


def run() -> None:
    print("=" * 62)
    print("  DOCKET RECEPTIONIST — PC call simulator")
    print("  (type what the caller says, press Enter)")
    print("  commands: /quit to end · /new for a fresh call")
    print("  tip: press Enter with nothing typed = silence (caller not talking)")
    print("=" * 62)

    bot = Receptionist()

    while True:
        print("\n" + "=" * 62)
        print("☎️  CALL STARTED")
        print("🤖 AI :", bot.start())
        try:
            bot = _handle_call(bot)
        except EOFError:  # Ctrl+C / closed input
            print("\nCall ended. Bye!")
            break


def _handle_call(bot: Receptionist) -> Receptionist:
    """One simulated call. Returns a fresh bot when the call ends."""
    while True:
        try:
            line = input("🧑 caller: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n☎️  CALL ENDED (no more input)")
            return Receptionist()

        if not line:
            # Silence — caller said nothing. Ask once, then end politely.
            reply = bot.silence()
            print(f"🤖 AI : {reply.text}")
            if reply.hangup:
                print("☎️  CALL ENDED. Goodbye!")
                return Receptionist()
            continue
        if line.lower() == "/quit":
            print("☎️  CALL ENDED. Goodbye!")
            raise EOFError
        if line.lower() == "/new":
            return Receptionist()

        reply = bot.respond(line)
        print(f"🤖 AI : {reply.text}")
        if reply.transfer_to_human:
            print("🔁 (transferring this call to a human staff member...)")
        if reply.hangup:
            print("☎️  CALL ENDED.")
            return Receptionist()


if __name__ == "__main__":
    run()

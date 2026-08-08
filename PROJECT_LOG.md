# 📒 PROJECT LOG — Docket Receptionist

Live status of what is done and what comes next. Updated every time we work.

## ✅ Phase 1 — The Brain (DONE)
What was completed on **1 Aug 2026**:

- [x] Project structure created in `DocketReceptionist/`
- [x] Guardrails engine (`core/guardrails.py`)
      — detects + refuses sensitive, personal, salary/payment, identity,
      off-topic, and jailbreak/prompt-injection messages
- [x] Conversation brain (`core/conversation.py`)
      — greet → ask docket → lookup → reply → human handoff on repeat failures
- [x] Read-only docket store (`core/docket_store.py`)
      — stub reads a CSV; only 3 allowed fields ever reach the AI
- [x] PC call simulator (`simulate.py`) — test a call by typing, no phone needed
- [x] Security + behaviour tests — **10/10 passing**
      (17+ sensitive attacks, 7 jailbreaks refused; docket lookup works)
- [x] Docs: `README.md`, `SECURITY.md`, this log

## ✅ Phase 2 — The Data (DONE)
What was completed on **1 Aug 2026**:

- [x] **Real SQL Server connection** — `SqlServerDocketStore` calls the
      stored procedure named in `.env` (parameterized docket number, no injection)
- [x] Reads **only allowed tracking fields** into `DocketRecord`
      — all other result sets / columns are DISCARDED
- [x] **Verified live** against a real docket (details stay local — not logged here)
- [x] `.env` setup — server, database, SP name, company name
      (all secrets stay in `.env`, never in code or docs)
- [x] `test_sql_connection.py <docket>` — safe way to check a docket yourself
- [x] Company name now reads from `.env` → greeting speaks the configured company name
- [x] Tests re-isolated to use sample CSV only — **10/10 passing**

Notes:
- Use a **read-only** SQL login in production (never an admin account in the app).
- Optional SP filter args can be left empty when not required.

## ✅ Phase 2.5 — Human Feel (DONE)
What was completed on **1 Aug 2026**:

- [x] **Auto language detection** (`core/language.py`)
      — caller speaks English/Hindi/Marathi, AI replies in the same language
- [x] **Mood detection** — angry / impatient / confused / happy callers get a
      matching acknowledgment before the reply ("Gusse mein nahi, main madat
      karta hoon...")
- [x] **Varied phrasing** — every reply now has 3–4 natural versions that rotate,
      so no two calls sound identical
- [x] **Polite speech fixed** — "ok thankyou" no longer treated as off-topic;
      says "You're welcome! Anything else?" and "bye" ends the call
- [x] **Silence handling** — no response → asks once, then politely disconnects
- [x] **Empty-reply bug fixed** — off-topic refusals can never return blank text
- [x] **Typo-proof guardrails** — "custoemr numbere", "customer mibile" etc. still
      caught as sensitive-data attempts
- [x] Tests updated + expanded — **23/23 passing**

### Polish round 2 (same day)
- [x] **Closing phrases end the call** — "nai hey", "chalte hai", "i am going",
      "leaving", "no thanks chalte hai" now hang up instead of greeting again
      (was misread as greeting / kept chatting)
- [x] **Glued docket numbers** — "56600991jaldii" now extracts 56600991
- [x] **Empty location handled** — never says "Abhi yeh mein hai" / "at ." —
      any missing field's clause is simply skipped, in every language
- [x] False "happy" mood on "achha" removed

## 🟡 Phase 3 — The Voice (IN PROGRESS)
- [x] **Text-to-speech** (`core/voice.py` → `speak()`) — edge-tts neural voices,
      free, no key. Voice per language (all FEMALE, warm & natural):
      English=en-IN-Neerja · Hindi/Hinglish=hi-IN-Swara · Marathi=mr-IN-Aarohi
      (switched from male voices on request — user heard the difference)
- [x] **Playback works** — greeting confirmed playing through PC speakers
- [x] `voice_call.py --test-tts` — hear the bot speak instantly
- [x] **Playback speed bug fixed** — stereo audio was played as mono = 2× slow,
      robotic sound. Now verified correct speed (0.3s overhead, expected pace).
      This was the "robot voice" the user heard — NOT the voice choice.
- [x] **Speech-to-text** (`core/voice.py` → `listen()`) — mic → Google free
      recognizer. Added: early silence detection, number-word→digit conversion
      ("five six six..." → 56600991), no wasted Google calls on silence.
- [x] **Female grammar fixed** — all Hindi/Hinglish self-references now female:
      "kar sakti hoon", "karti hoon", "bata dungi", "samajh gayi" (was male
      "kar sakta hoon"). Marathi female forms: "karte", "sangte", "shakte".
- [x] **Mood false-positive fixed** — "sala" no longer fires inside "salary";
      angry/impatient words now whole-word matched.
- [ ] Full voice call: `python voice_call.py` — speak, bot hears, bot answers in
      the caller's language voice (needs user's mic to confirm end-to-end)
- [ ] Fine-tune: silence timing, noise rejection, faster docket-number dictation

## ✅ GitHub — Published
- [x] **Repo live**: https://github.com/prempatil03/DocketReceptionist
- [x] Full README with architecture diagram + call flow
- [x] `.gitignore` — **`.env` (real DB password) is excluded**, confirmed by scan
- [x] `.env.example` provides safe placeholders
- [x] Commit `7028801` pushed to `main`
- [x] **No user data on GitHub**: company name / server IP removed from all
      committed files; config is the user's own via `.env`
- [x] Claude removed from commit authors (no co-author trailers)

## 🟡 Phase 4 — Real Phone Calls (later)
- [ ] **Android auto-answer app** (put your company SIM in a phone, install app)
- [ ] The app connects to the Brain over the internet
- [ ] Test with your own number
- [ ] Scale to more staff numbers (more phones, or a SIM gateway box)

## 🔒 Always — Security checks
- [ ] Every change re-runs `python -m unittest discover -s tests -v`
- [ ] Never commit real docket data or DB passwords to the repo
- [ ] Any new data field must be approved before it can be spoken

---
**How to test anytime (Windows):**
```
cd DocketReceptionist
python simulate.py
```

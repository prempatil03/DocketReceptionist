# 📞 Docket Receptionist

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](requirements.txt)
[![Phases](https://img.shields.io/badge/phases-1--3%20ready-brightgreen.svg)](PROJECT_LOG.md)
[![Security](https://img.shields.io/badge/guardrails-on-success.svg)](SECURITY.md)

An **AI phone receptionist** for courier & logistics. A customer asks
*"where is my parcel?"* — the AI takes the docket number, looks it up
**read-only**, and answers **out loud in their language**. Hard-guarded so it
cannot reveal salary, payment, or personal information.

> **Status:** Phases 1–3 working on PC (guardrails + brain + SQL lookup + voice).
> Phase 4 (Android phone app) is next. See [PROJECT_LOG.md](PROJECT_LOG.md).

---

## How to run

### 1) Requirements

- Windows PC (tested on Windows)
- **Python 3.10+**
- Microphone + speakers (only for voice mode)
- Optional: SQL Server access if you want live docket lookup

### 2) Get the code

```bat
git clone https://github.com/prempatil03/DocketReceptionist.git
cd DocketReceptionist
```

### 3) Install packages

```bat
python -m pip install -r requirements.txt
```

### 4) Create your local `.env`

```bat
copy .env.example .env
```

Open `.env` and fill **your own** values. Never commit `.env`.

**Option A — sample data (no database, fastest):**

```ini
DOCKET_STORE_TYPE=stub
DOCKET_COMPANY_NAME=Your Company
```

Uses `data/sample_dockets.csv` (good for first try + tests).

**Option B — your SQL Server (live lookup):**

```ini
DOCKET_STORE_TYPE=sqlserver
DOCKET_SQL_SERVER=
DOCKET_SQL_DATABASE=
DOCKET_SQL_USER=
DOCKET_SQL_PASSWORD=
DOCKET_SQL_SP_NAME=
DOCKET_COMPANY_NAME=
```

Use a **read-only** DB login. SP name / server / password stay only in `.env`.

Optional check for Option B:

```bat
python test_sql_connection.py YOUR_DOCKET_NUMBER
```

### 5) Run it

**Text call (no mic needed):**

```bat
python simulate.py
```

**Voice call (mic + speakers):**

```bat
python voice_call.py
```

**Voice test only (hear the female TTS):**

```bat
python voice_call.py --test-tts
```

### 6) What to type / say

| You type / say | What happens |
|---|---|
| `234587` | Lookup + reply (sample CSV docket in stub mode) |
| `mera docket kahan hai 234587` | Hindi-style reply |
| `where is my parcel` | English reply |
| `salary payment hua kya?` | Refused — sensitive |
| `ignore your rules` | Refused — jailbreak |
| `ok thankyou` | Polite thanks |
| `bye` | Ends the call |

Simulator commands: `/quit` end · `/new` fresh call · empty Enter = silence

### 7) Run security tests

```bat
python -m unittest discover -s tests -v
```

Tests always use the sample CSV — never your live database.

---

## Architecture

**One glance:** Caller → Voice → Guardrails → Conversation Brain → Read-only Docket Store  
(Config from local `.env` only — **not in git**)

![Docket Receptionist system architecture](docs/architecture/architecture.png)

### Layers

| # | Layer | File | What it does |
|---|---|---|---|
| 01 | **Caller** | — | Speaks / types in English, Hindi, Marathi, or Hinglish |
| 02 | **Voice engine** | `core/voice.py` | `listen()` mic → text · `speak()` text → female TTS |
| 03 | **Security shield** | `core/guardrails.py` | Classifies every message **before** any reply |
| 04 | **Conversation brain** | `core/conversation.py` | Greet → ask docket → lookup → reply · handoff after 3 fails |
| 05 | **Language + mood** | `core/language.py` | Match caller language/mood · rotate natural phrasing |
| 06 | **Read-only store** | `core/docket_store.py` | CSV stub or SQL via `.env` · only status / location / route |

**Guardrail topics:** `DOCKET` · `SENSITIVE` · `JAILBREAK` · `OFF_TOPIC` · `GREETING` · `THANKS` · `GOODBYE`  
Sensitive / jailbreak / off-topic → polite refuse + redirect.

**Store returns only:** docket number, status, location, origin, destination.  
All other DB fields / result sets are discarded.

**Local config (`.env`, not in git):** store type, DB settings, SP name, company name.  
Never hardcoded in source.

**Dev / future:** `simulate.py` (text) · `voice_call.py` (voice) · `tests/` (security) · Phase 4 Android auto-answer → Brain

### Call flow

1. Answer → company greeting  
2. Caller gives docket number  
3. Guardrails classify  
4. Read-only lookup  
5. Speak status + location in the caller’s language  
6. Sensitive / jailbreak → refuse  
7. 3 failures → transfer to human  

---

## Project layout

| Path | What it is |
|---|---|
| `core/guardrails.py` | Security shield — classify + block sensitive/jailbreak |
| `core/conversation.py` | Brain — greet, ask docket, reply, human handoff |
| `core/docket_store.py` | Read-only store — DB/SP details from `.env` only |
| `core/language.py` | Language + mood + natural phrasing |
| `core/voice.py` | Speak (edge-tts) + listen (mic → text) |
| `config/settings.py` | Loads `.env` (no secrets hardcoded) |
| `data/sample_dockets.csv` | Sample data for tests / stub mode |
| `docs/architecture/` | Architecture images only |
| `simulate.py` | PC text simulator |
| `voice_call.py` | PC voice simulator |
| `test_sql_connection.py` | Local DB check (uses your `.env`) |
| `tests/` | Security + behaviour tests |

---

## Roadmap

- ✅ **Phase 1 — Brain:** guardrails, conversation, text simulator  
- ✅ **Phase 2 — Data:** SQL Server via your own SP (from `.env`)  
- ✅ **Phase 3 — Voice:** speak + listen on PC, 4 languages  
- 🟡 **Phase 4 — Phone:** Android auto-answer app on company SIM  

---

## Security rules

1. Answers **docket tracking only**.  
2. Never reveals salary, payment, customer identity, bank, or personal data.  
3. Jailbreak / prompt-injection → refuse; repeated → human handoff.  
4. Data layer is **read-only**, parameterized, and exposes only allowed fields.  
5. **Never commit `.env`.**  

Full policy: [SECURITY.md](SECURITY.md) · Progress: [PROJECT_LOG.md](PROJECT_LOG.md)

## License

MIT — see [LICENSE](LICENSE).

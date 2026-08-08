"""Central settings for the Docket Receptionist.

Everything the brain needs to know lives here, so it is easy to change
without touching the code. Sensitive values (DB passwords etc.) must come
from environment variables / .env, NEVER hard-coded here.
"""

import os
from pathlib import Path

# ---- Auto-load .env (no external deps) ----
def _load_dotenv(path: Path) -> None:
    """Read a .env file and set any variables not already in the environment."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if value and "FILL_IN" not in value:
            os.environ.setdefault(key, value)

_load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Root of the project (parent of this file's folder).
BASE_DIR = Path(__file__).resolve().parent.parent

# ---- Company / brand ---------------------------------------------------------
# Set DOCKET_COMPANY_NAME in your .env — this is what the bot speaks in its
# greeting. The fallback here is only a generic placeholder.
COMPANY_NAME = os.getenv("DOCKET_COMPANY_NAME", "Your Company")
LANGUAGE = os.getenv("DOCKET_LANGUAGE", "hinglish")  # hinglish | english | hindi

# ---- Data source --------------------------------------------------------------
# Which docket store to use: "stub" (reads data/sample_dockets.csv) or
# "sqlserver" (SSMS database — NOT implemented yet, see core/docket_store.py).
DOCKET_STORE_TYPE = os.getenv("DOCKET_STORE_TYPE", "stub")

# Path to the sample / production CSV used by the stub store (READ ONLY).
DOCKET_CSV_PATH = Path(
    os.getenv("DOCKET_CSV_PATH", str(BASE_DIR / "data" / "sample_dockets.csv"))
)

# SQL Server — ALL values come from .env only. Never hardcode server, DB,
# user, password, or stored-procedure name in source files.
# The DB user MUST be a READ-ONLY login (not an admin account).
SQL_SERVER   = os.getenv("DOCKET_SQL_SERVER", "")
SQL_DATABASE = os.getenv("DOCKET_SQL_DATABASE", "")
SQL_USER     = os.getenv("DOCKET_SQL_USER", "")
SQL_PASSWORD = os.getenv("DOCKET_SQL_PASSWORD", "")

# Stored procedure / enquiry name — set by the user in .env (no default).
SQL_SP_NAME  = os.getenv("DOCKET_SQL_SP_NAME", "")

# Legacy string-based connection (kept empty — individual fields above are used now).
SQL_SERVER_CONNECTION_STRING = ""

# ---- Guardrails ---------------------------------------------------------------
# How many failed docket lookups before we offer a human handoff.
MAX_DOCKET_ATTEMPTS = 3

# Max length of a caller's message we will process (blocks abuse / flooding).
MAX_INPUT_LENGTH = 500

# If True, replies are printed with emoji/voice styling in the simulator.
SIMULATOR_VOICE_STYLE = True

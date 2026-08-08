"""Test your SQL Server connection using values from .env only.

Run this AFTER filling in your local .env (never commit that file):

    cd DocketReceptionist
    python test_sql_connection.py <docket_number>

Replace <docket_number> with a docket from your own system.
Never paste the output into chat — only you should see it.
"""

import sys
from pathlib import Path

# Load .env manually (no external deps).
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if v and v != "FILL_IN_HERE":
                import os
                os.environ.setdefault(k, v)

# Now import the store (reads from environment).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.docket_store import get_docket_store  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python test_sql_connection.py <docket_number>")
        sys.exit(1)

    docket_no = sys.argv[1].strip()
    print(f"Looking up docket: {docket_no}")
    print("Connecting (timeout 5s)...")

    store = get_docket_store()
    record = store.lookup(docket_no)

    if record:
        print("\nFOUND:")
        print(f"  Docket   : {record.docket_number}")
        print(f"  Status   : {record.status}")
        print(f"  Location : {record.location}")
        print(f"  Route    : {record.origin} -> {record.destination}")
    else:
        print("\nNOT FOUND (docket number doesn't exist or connection failed).")


if __name__ == "__main__":
    main()

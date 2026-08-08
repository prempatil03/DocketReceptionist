"""Read-only access to docket data.

IMPORTANT SECURITY RULE:
This is the ONLY place that talks to the data source. The rest of the brain
works with `DocketRecord` objects, which expose exactly the fields a caller
is allowed to hear — nothing else.

If the real database row has extra columns (customer name, phone, salary,
payment status...), they simply DO NOT EXIST on `DocketRecord`, so the AI
can never leak them even if it tries.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol


@dataclass(frozen=True)
class DocketRecord:
    """The ONLY fields a caller is allowed to be told about a docket."""

    docket_number: str
    status: str            # e.g. "out for delivery"
    location: str          # e.g. "Mumbai hub"
    origin: str = ""       # e.g. "MNS" (safe public info — origin of parcel)
    destination: str = ""  # e.g. "DHRT" (safe public info — destination of parcel)


class DocketStore(Protocol):
    """Any data source must implement a read-only lookup by docket number."""

    def lookup(self, docket_number: str) -> Optional[DocketRecord]: ...


class StubDocketStore:
    """Reads dockets from a local CSV. READ ONLY — never writes.

    Used for development/testing. The CSV is sample data until we connect
    the real SSMS database (see SqlServerDocketStore below).
    """

    def __init__(self, csv_path: Path):
        self._records: dict[str, DocketRecord] = {}
        self._load(csv_path)

    def _load(self, csv_path: Path) -> None:
        if not csv_path.exists():
            return  # no data yet — everything just returns "not found"
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                # Only the allowed fields are ever copied into memory.
                self._records[row["docket_number"].strip()] = DocketRecord(
                    docket_number=row["docket_number"].strip(),
                    status=row.get("status", "").strip(),
                    location=row.get("location", "").strip(),
                    origin=row.get("origin", "").strip(),
                    destination=row.get("destination", "").strip(),
                )

    def lookup(self, docket_number: str) -> Optional[DocketRecord]:
        return self._records.get(docket_number.strip())


class SqlServerDocketStore:
    """Read-only SQL Server lookup via the SP name configured in .env.

    SECURITY RULES — none of these may ever change:
      1. Connects with a READ-ONLY SQL login (no INSERT/UPDATE/DELETE).
      2. Password / server / SP name come ONLY from .env — never hardcoded or printed.
      3. Docket number is passed as a parameter only — no SQL injection.
      4. Reads ONLY the allowed status/location/route fields into DocketRecord.
         All other result sets / columns are DISCARDED.
      5. Every error is caught and returned as "not found" — fail closed.
    """

    def __init__(self, server: str, database: str, user: str, password: str,
                 sp_name: str) -> None:
        # Validate required fields — fail early with a clear message.
        for name, val in [("server", server), ("database", database),
                          ("user", user), ("sp_name", sp_name)]:
            if not val:
                raise ValueError(f"SQL config missing: {name}. Fill .env and try again.")

        self._server   = server
        self._database = database
        self._user     = user
        self._password = password  # kept in memory only, never printed/logged.
        self._sp_name  = sp_name

    def lookup(self, docket_number: str) -> Optional[DocketRecord]:
        """Call the user-configured stored procedure with a parameterised docket number. Never raises."""
        import pymssql
        try:
            conn = pymssql.connect(
                server   = self._server,
                database = self._database,
                user     = self._user,
                password = self._password,
                timeout  = 5,
            )
            try:
                cursor = conn.cursor(as_dict=True)

                # Parameterised SP call — docket number is the only caller-supplied input.
                # Extra SP args are passed empty so optional filters are skipped.
                cursor.execute(
                    f"EXEC {self._sp_name} "
                    f"@DocketNo = %s, "
                    f"@InvoiceNo = '', "
                    f"@EwayBillNo = '', "
                    f"@CoCode = '', "
                    f"@DivCode = ''",
                    (int(docket_number.strip()),),
                )

                # Skip non-tracking result sets; keep only allowed docket fields.
                cursor.nextset()
                row = cursor.fetchone()

                if row is None:
                    return None

                return DocketRecord(
                    docket_number = str(row.get("DwbNo",            "")).strip(),
                    status        = str(row.get("Status",           "")).strip(),
                    location      = str(row.get("CurrentLocation",  "")).strip(),
                    origin        = str(row.get("Origin",           "")).strip(),
                    destination   = str(row.get("Destination",      "")).strip(),
                )
            finally:
                conn.close()  # always close — short connection lifetime.
        except Exception:
            # Fail closed: any error → "not found". Never leaks DB error messages.
            return None


def get_docket_store() -> DocketStore:
    """Factory: returns the store configured in .env / environment variables."""
    from config.settings import (
        DOCKET_STORE_TYPE, DOCKET_CSV_PATH,
        SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD,
        SQL_SP_NAME,
    )

    if DOCKET_STORE_TYPE == "sqlserver":
        return SqlServerDocketStore(
            server   = SQL_SERVER,
            database = SQL_DATABASE,
            user     = SQL_USER,
            password = SQL_PASSWORD,
            sp_name  = SQL_SP_NAME,
        )
    return StubDocketStore(DOCKET_CSV_PATH)

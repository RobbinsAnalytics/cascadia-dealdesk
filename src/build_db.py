"""
build_db.py — Load the generated CSVs into a SQLite star schema.

Cascadia Deal Desk · Part A

Input : data/raw/*.csv          (the seeded generator's output — the artifact)
Output: data/cascadia_dealdesk.db

Schema (dimensional model, mirroring the other Cascadia builds):

    dim_customer   one row per account
    dim_product    one row per sellable part, with its launch date
    dim_rep        one row per sales rep
    dim_date       one row per calendar day in the analysis window
    dim_agreement  THE GOVERNED REGISTER — the pricing agreement as a queryable
                   dataset rather than a signed PDF. Customer, scope, agreed
                   price, effective window, committed capacity, approval
                   reference, supersession pointer, and the prior price the
                   premium was negotiated against.

    fact_quote_line     grain: one quoted line (quote_id, line_no)
    fact_booking        grain: one order line, keyed BACK to the quote line it
                        came from. That foreign key is what lets exposure split
                        into money already invoiced and money still in the funnel.
    fact_standard_cost  grain: product x effective window; cost steps quarterly

Foreign keys are enforced (PRAGMA foreign_keys = ON), so a load that violates
referential integrity fails here rather than surfacing as a silent gap on a
chart three steps later.

Rebuilding is idempotent: tables are dropped and recreated from the CSVs every
run. The CSVs in data/raw/ remain the canonical, committed artifact.

Usage:
    python src/build_db.py
"""

import csv
import hashlib
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
DB_PATH = REPO_ROOT / "data" / "cascadia_dealdesk.db"

DDL = """
PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS fact_quote_line_conformed;
DROP TABLE IF EXISTS fact_booking;
DROP TABLE IF EXISTS fact_quote_line;
DROP TABLE IF EXISTS fact_standard_cost;
DROP TABLE IF EXISTS dim_agreement;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_rep;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_customer (
    customer_id  TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    segment      TEXT NOT NULL,          -- Strategic | Core | Emerging
    region       TEXT NOT NULL
);

CREATE TABLE dim_product (
    product_id   TEXT PRIMARY KEY,
    part_number  TEXT NOT NULL UNIQUE,
    family       TEXT NOT NULL,
    launch_date  TEXT NOT NULL           -- parts launched mid-window create
);                                       -- genuine agreement coverage gaps

CREATE TABLE dim_rep (
    rep_id       TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    territory    TEXT NOT NULL
);

CREATE TABLE dim_date (
    date_key     INTEGER PRIMARY KEY,    -- YYYYMMDD
    date         TEXT NOT NULL UNIQUE,
    year         INTEGER NOT NULL,
    quarter      TEXT NOT NULL,
    month        INTEGER NOT NULL,
    month_name   TEXT NOT NULL
);

-- The agreement register. Design point 1: make the agreement a dataset.
CREATE TABLE dim_agreement (
    agreement_id    TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL REFERENCES dim_customer(customer_id),
    scope           TEXT NOT NULL,       -- part | family
    product_id      TEXT REFERENCES dim_product(product_id),  -- NULL for family scope
    family          TEXT,                                     -- NULL for part scope
    agreed_price    REAL NOT NULL,
    effective_start TEXT NOT NULL,
    effective_end   TEXT NOT NULL,
    committed_units INTEGER NOT NULL,
    approval_ref    TEXT NOT NULL,       -- the agreement's own approval reference
    status          TEXT NOT NULL,       -- active | superseded | expired, AS OF the
                                         -- as-of date (see governance/matching_rules.md:
                                         -- the matcher asks the same questions as of
                                         -- the QUOTE date instead)
    superseded_by   TEXT,                -- successor agreement_id, NULL if none
    prior_price     REAL NOT NULL,       -- what the customer paid before this deal
    premium_pct     REAL NOT NULL,       -- what the negotiation won
    CHECK (scope IN ('part', 'family')),
    CHECK (status IN ('active', 'superseded', 'expired')),
    CHECK ((scope = 'part'   AND product_id IS NOT NULL AND family IS NULL)
        OR (scope = 'family' AND family     IS NOT NULL AND product_id IS NULL))
);

CREATE TABLE fact_quote_line (
    quote_id              TEXT NOT NULL,
    line_no               INTEGER NOT NULL,
    customer_id           TEXT NOT NULL REFERENCES dim_customer(customer_id),
    product_id            TEXT NOT NULL REFERENCES dim_product(product_id),
    rep_id                TEXT NOT NULL REFERENCES dim_rep(rep_id),
    quote_date            TEXT NOT NULL,
    quantity              INTEGER NOT NULL,
    quoted_price          REAL NOT NULL,
    stage                 TEXT NOT NULL,   -- won | open | lost
    -- The CRM's deviation-approval fields. A quote line carrying an approval
    -- reference is a DOCUMENTED exception, not leakage — which is exactly the
    -- distinction that makes threshold calibration a real exercise.
    approval_ref          TEXT,
    exception_reason_code TEXT,
    PRIMARY KEY (quote_id, line_no),
    CHECK (stage IN ('won', 'open', 'lost')),
    CHECK (quantity > 0),
    CHECK (quoted_price > 0)
);

CREATE TABLE fact_booking (
    booking_id      TEXT PRIMARY KEY,
    quote_id        TEXT NOT NULL,
    line_no         INTEGER NOT NULL,
    customer_id     TEXT NOT NULL REFERENCES dim_customer(customer_id),
    product_id      TEXT NOT NULL REFERENCES dim_product(product_id),
    booking_date    TEXT NOT NULL,
    booked_quantity INTEGER NOT NULL,
    booked_price    REAL NOT NULL,
    -- The link back to the quote line. Without it, bookings cannot do any work:
    -- there is no way to tell which off-agreement quotes actually invoiced.
    FOREIGN KEY (quote_id, line_no) REFERENCES fact_quote_line(quote_id, line_no),
    UNIQUE (quote_id, line_no),          -- at most one booking per quote line
    CHECK (booked_quantity > 0),
    CHECK (booked_price > 0)
);

CREATE TABLE fact_standard_cost (
    product_id      TEXT NOT NULL REFERENCES dim_product(product_id),
    effective_start TEXT NOT NULL,
    effective_end   TEXT NOT NULL,
    standard_cost   REAL NOT NULL,
    PRIMARY KEY (product_id, effective_start)
);

CREATE INDEX idx_agreement_customer ON dim_agreement(customer_id);
CREATE INDEX idx_quote_customer     ON fact_quote_line(customer_id);
CREATE INDEX idx_quote_date         ON fact_quote_line(quote_date);
CREATE INDEX idx_cost_product       ON fact_standard_cost(product_id);
"""

# CSV column order per table. Loading is positional, so this list IS the
# contract between generate.py's output and the schema above.
TABLES = {
    "dim_customer": ["customer_id", "name", "segment", "region"],
    "dim_product": ["product_id", "part_number", "family", "launch_date"],
    "dim_rep": ["rep_id", "name", "territory"],
    "dim_date": ["date_key", "date", "year", "quarter", "month", "month_name"],
    "dim_agreement": ["agreement_id", "customer_id", "scope", "product_id", "family",
                      "agreed_price", "effective_start", "effective_end",
                      "committed_units", "approval_ref", "status", "superseded_by",
                      "prior_price", "premium_pct"],
    "fact_quote_line": ["quote_id", "line_no", "customer_id", "product_id", "rep_id",
                        "quote_date", "quantity", "quoted_price", "stage",
                        "approval_ref", "exception_reason_code"],
    "fact_booking": ["booking_id", "quote_id", "line_no", "customer_id", "product_id",
                     "booking_date", "booked_quantity", "booked_price"],
    "fact_standard_cost": ["product_id", "effective_start", "effective_end",
                           "standard_cost"],
}

# Columns SQLite should receive as a number rather than a string.
NUMERIC = {"date_key", "year", "month", "line_no", "quantity", "quoted_price",
           "agreed_price", "committed_units", "prior_price", "premium_pct",
           "booked_quantity", "booked_price", "standard_cost"}


def cell(column: str, value: str):
    """CSV blank -> NULL; numeric columns -> float/int; everything else -> text."""
    if value in ("", None):
        return None
    if column in NUMERIC:
        return float(value) if "." in value or "e" in value.lower() else int(value)
    return value


def db_sha256(con: sqlite3.Connection) -> str:
    """A deterministic CONTENT hash over every table in the database.

    Deliberately not a hash of the .db file. SQLite's on-disk layout (page
    order, free lists, vacuum state) can differ between runs that hold
    byte-identical data, so a file hash would report false differences and
    make the reproducibility claim worthless. This hashes the rows instead,
    table by table in name order, each table sorted by all of its columns.

    The row_factory is forced to plain tuples for the duration and restored
    afterwards. With sqlite3.Row in effect a row's repr() is
    "<sqlite3.Row object at 0x...>" — a MEMORY ADDRESS — which would make this
    hash different on every run and quietly worthless. Callers set their own
    row_factory for their own reasons; the hash must not depend on it.
    """
    previous, con.row_factory = con.row_factory, None
    try:
        h = hashlib.sha256()
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        for table in tables:
            columns = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
            h.update(f"{table}({','.join(columns)})".encode())
            order = ",".join(f'"{c}"' for c in columns)
            for row in con.execute(f"SELECT * FROM {table} ORDER BY {order}"):
                h.update(repr(tuple(row)).encode())
        return h.hexdigest()
    finally:
        con.row_factory = previous


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(DDL)

    counts = {}
    for table, columns in TABLES.items():
        with open(RAW_DIR / f"{table}.csv", encoding="utf-8", newline="") as fh:
            rows = [tuple(cell(c, r[c]) for c in columns) for r in csv.DictReader(fh)]
        con.executemany(
            f"INSERT INTO {table} VALUES ({','.join('?' * len(columns))})", rows)
        counts[table] = len(rows)

    # Turn foreign keys ON and ask SQLite to prove the load is referentially
    # clean. A violation here is a hard stop, not a warning on a chart later.
    con.execute("PRAGMA foreign_keys = ON")
    violations = con.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        con.close()
        raise SystemExit(f"FOREIGN KEY violations on load: {violations[:10]}")

    con.commit()
    con.close()
    print(f"Wrote {DB_PATH}")
    for table, n in counts.items():
        print(f"  {table}: {n:,} rows")


if __name__ == "__main__":
    main()

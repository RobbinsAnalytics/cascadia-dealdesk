"""
build_pages.py — Package the conformed data for the static frontend.

Cascadia Deal Desk · Part A

Input : data/cascadia_dealdesk.db
Output: docs/data/dealdesk.json      (the data contract — readable hand-off copy)
        docs/*.html                  (the same JSON INJECTED inline at build time)

WHY INLINE? The published site must work forever, free, and offline —
including opened straight from disk (file://), where a relative fetch() is
blocked by the browser. So the JSON is embedded in each page between markers
rather than fetched at runtime. No network call is made by the published page.

THE MARKER CONTRACT (this is the seam — Part B codes against this):

    <script id="dealdesk-data" type="application/json">/*__DEALDESK_DATA__*/</script>

Put that line, exactly, in any page that needs the data. This script finds the
element by its id and replaces whatever sits between the tags. It is idempotent:
run it twice and you get the same file, because it replaces the CONTENTS rather
than appending. It does not fail when docs/ holds no HTML yet — which is exactly
the state Part A leaves it in.

Read the data on the page with:

    const data = JSON.parse(document.getElementById('dealdesk-data').textContent);

Usage:
    python src/build_pages.py
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate
from build_db import db_sha256
from conform import TOLERANCE_PCT

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "cascadia_dealdesk.db"
DOCS_DIR = REPO_ROOT / "docs"
JSON_OUT = DOCS_DIR / "data" / "dealdesk.json"

# The element the data is injected into. Matching on the id (not on the
# placeholder comment) is what makes re-running safe after the first inject.
MARKER_ID = "dealdesk-data"
MARKER_RE = re.compile(
    r'(<script\s+id="%s"\s+type="application/json">)(.*?)(</script>)' % MARKER_ID,
    re.DOTALL)
PLACEHOLDER = "/*__DEALDESK_DATA__*/"

# Floats are rounded in the JSON; full precision stays in the database. Four
# places is enough for a price to the cent and a margin ratio to a basis point.
ROUND_TO = 4

# Line-grain columns shipped to the frontend. Emitted COLUMNAR (a fields array
# plus arrays of values) rather than as an array of objects — at ~3,000 rows
# that is roughly a third of the bytes, and the page rebuilds objects trivially.
LINE_FIELDS = [
    "quote_id", "line_no", "customer_id", "customer_name", "product_id",
    "product_part_number", "product_family", "rep_id", "rep_name",
    "quote_date", "quantity", "quoted_price", "stage",
    "match_status", "no_agreement_reason", "agreement_id_matched", "agreed_price",
    "standard_cost_at_quote", "price_variance_usd", "price_variance_pct",
    "margin_at_quoted_pct", "margin_at_agreed_pct", "margin_impact_usd",
    "is_approved_exception", "exception_reason_code", "approval_ref",
    "booking_status", "booked_price", "booked_quantity", "booking_date",
    "realized_variance_usd", "exposure_state",
]

LINE_SQL = f"""
SELECT f.quote_id, f.line_no, f.customer_id, c.name AS customer_name,
       f.product_id, p.part_number AS product_part_number,
       p.family AS product_family, f.rep_id, r.name AS rep_name,
       f.quote_date, f.quantity, f.quoted_price, f.stage,
       f.match_status, f.no_agreement_reason, f.agreement_id_matched, f.agreed_price,
       f.standard_cost_at_quote, f.price_variance_usd, f.price_variance_pct,
       f.margin_at_quoted_pct, f.margin_at_agreed_pct, f.margin_impact_usd,
       f.is_approved_exception, f.exception_reason_code, f.approval_ref,
       f.booking_status, f.booked_price, f.booked_quantity, f.booking_date,
       f.realized_variance_usd, f.exposure_state
FROM fact_quote_line_conformed f
JOIN dim_customer c USING (customer_id)
JOIN dim_product  p USING (product_id)
JOIN dim_rep      r USING (rep_id)
ORDER BY f.quote_date, f.quote_id, f.line_no
"""


def rnd(value):
    """Round floats for transport; leave ints, strings and nulls alone."""
    return round(value, ROUND_TO) if isinstance(value, float) else value


def build_payload(con: sqlite3.Connection) -> dict:
    """Assemble the whole contract.

    Line grain, not pre-aggregates. The frontend filters client-side by
    customer, date range and materiality threshold, and recomputes its chart
    titles from whatever survives the filter — so it needs the rows, not
    somebody else's totals. The customer page needs every line (revenue, mix,
    margin over time); the exception page filters down from the same array.
    """
    con.row_factory = sqlite3.Row
    q = lambda sql: [dict(r) for r in con.execute(sql).fetchall()]

    lines = q(LINE_SQL)
    rows_out = [[rnd(ln[f]) for f in LINE_FIELDS] for ln in lines]

    status_counts = dict(con.execute(
        "SELECT match_status, COUNT(*) FROM fact_quote_line_conformed GROUP BY 1").fetchall())
    reason_counts = dict(con.execute(
        "SELECT no_agreement_reason, COUNT(*) FROM fact_quote_line_conformed "
        "WHERE no_agreement_reason IS NOT NULL GROUP BY 1").fetchall())
    exposure_counts = dict(con.execute(
        "SELECT exposure_state, COUNT(*) FROM fact_quote_line_conformed "
        "WHERE match_status = 'priced_off_agreement' GROUP BY 1").fetchall())
    date_min, date_max = con.execute(
        "SELECT MIN(quote_date), MAX(quote_date) FROM fact_quote_line_conformed").fetchone()

    def count(table):
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    # The full register ships, INCLUDING superseded and expired rows, because
    # the customer page draws an agreement timeline showing renewals and
    # supersessions. Filtering them out here would make that chart impossible.
    agreements = [{k: rnd(v) for k, v in a.items()}
                  for a in q("SELECT * FROM dim_agreement ORDER BY customer_id, "
                             "effective_start, agreement_id")]

    return {
        "meta": {
            "generated_at": generate.AS_OF.isoformat(),
            "seed": generate.SEED,
            "db_sha256": db_sha256(con),
            "as_of": generate.AS_OF.isoformat(),
            "row_counts": {
                "quote_lines": len(lines),
                "agreements": count("dim_agreement"),
                "bookings": count("fact_booking"),
                "customers": count("dim_customer"),
                "products": count("dim_product"),
                "reps": count("dim_rep"),
                "standard_costs": count("fact_standard_cost"),
            },
            "match_status_counts": status_counts,
            "no_agreement_reason_counts": reason_counts,
            "exposure_state_counts": exposure_counts,
            "disclosure": generate.DISCLOSURE,
            "provenance": {
                "source": "Synthetic data, seeded generator",
                "asOf": generate.AS_OF.isoformat(),
                "flags": "Simulated — not real company data",
            },
            "params": {
                "tolerance_pct": TOLERANCE_PCT,
                "date_min": date_min,
                "date_max": date_max,
                "exception_reason_codes": generate.EXCEPTION_REASON_CODES,
                "match_status_values": ["priced_to_agreement", "priced_off_agreement",
                                        "no_governing_agreement"],
                "exposure_state_values": ["realized", "open", "closed_lost"],
            },
            "definitions": {
                "margin_impact_usd":
                    "The dollar margin given up versus the agreement. Arithmetically "
                    "identical to -price_variance_usd: standard cost cancels, so every "
                    "dollar of price variance is a dollar of margin, one for one. "
                    "See governance/matching_rules.md.",
                "exposure_state":
                    "realized = booked at the off-agreement price, the money is gone; "
                    "open = quoted but not yet booked, still fixable; "
                    "closed_lost = the line never booked.",
                "no_agreement_reason":
                    "agreement_lapsed = coverage ran out (distinct from closed_lost, "
                    "which means the quote never converted).",
            },
        },
        "dimensions": {
            "customers": q("SELECT * FROM dim_customer ORDER BY customer_id"),
            "products": q("SELECT * FROM dim_product ORDER BY product_id"),
            "reps": q("SELECT * FROM dim_rep ORDER BY rep_id"),
        },
        "agreements": agreements,
        "lines": {"fields": LINE_FIELDS, "rows": rows_out},
        "standard_costs": [{k: rnd(v) for k, v in c.items()} for c in
                           q("SELECT * FROM fact_standard_cost "
                             "ORDER BY product_id, effective_start")],
    }


def inject(page: Path, payload_json: str) -> bool:
    """Replace the contents of the data script element. Idempotent."""
    html = page.read_text(encoding="utf-8")
    if not MARKER_RE.search(html):
        return False
    # A literal "</script>" inside the JSON would close the element early. Our
    # data contains no such string, but escaping it is free insurance.
    safe = payload_json.replace("</", r"<\/")
    updated = MARKER_RE.sub(lambda m: m.group(1) + safe + m.group(3), html, count=1)
    if updated != html:
        page.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    payload = build_payload(con)
    con.close()

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    compact = json.dumps(payload, separators=(",", ":"))
    JSON_OUT.write_text(compact, encoding="utf-8")

    size_kb = JSON_OUT.stat().st_size / 1024
    print(f"Wrote {JSON_OUT} ({size_kb:,.0f} KB, "
          f"{payload['meta']['row_counts']['quote_lines']:,} quote lines, "
          f"{payload['meta']['row_counts']['agreements']:,} agreements)")
    print(f"  top-level keys: {list(payload)}")

    # Part B writes the HTML. Until it exists there is simply nothing to inject,
    # and that is a normal outcome, not an error.
    pages = sorted(DOCS_DIR.glob("*.html"))
    injected = [p.name for p in pages if inject(p, compact)]
    skipped = [p.name for p in pages if p.name not in injected]
    print(f"  injected into {len(injected)} of {len(pages)} HTML file(s) in docs/")
    for name in injected:
        print(f"    injected: {name}")
    for name in skipped:
        print(f"    skipped (no '{MARKER_ID}' element): {name}")
    if not pages:
        print(f"    no HTML in docs/ yet — add the marker line below to any page:")
        print(f'    <script id="{MARKER_ID}" type="application/json">{PLACEHOLDER}</script>')


if __name__ == "__main__":
    main()

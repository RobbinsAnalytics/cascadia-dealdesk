"""
conform.py — Match quote lines to their governing agreement; derive the measures.

Cascadia Deal Desk · Part A

Input : data/cascadia_dealdesk.db  (star schema, loaded by build_db.py)
Output: data/cascadia_dealdesk.db  -> table fact_quote_line_conformed

This module is the analytical core of the project. Two things live here:

  1. THE MATCHING RULE (resolve_agreement) — given a quote's customer,
     product and date, decide which single pricing agreement governs it.
     This is a pure function over plain dicts: no database, no pandas, no
     side effects. `src/generate.py` imports it so the synthetic quotes are
     priced against the *same* rule the analytics layer later applies. That
     is deliberate — it means the generator cannot quietly build a dataset
     that flatters a subtly different matcher. (The honest caveat: because
     both sides share the rule, agreement between them is not independent
     evidence the rule is *correct*. It is evidence the pipeline is
     *consistent*. Correctness is argued in governance/matching_rules.md
     with worked examples, and the identity checks in validate.py are
     independent of the matcher entirely.)

  2. THE DERIVED FIELDS — variance, margin, exposure. Every one of them is
     MATERIALIZED into fact_quote_line_conformed rather than left to a view
     or to JavaScript. The frontend receives arithmetic it does not have to
     redo, which is the whole reason the numbers on two different pages
     agree with each other.

Usage:
    python src/conform.py
"""

import sqlite3
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "cascadia_dealdesk.db"

# A part-scope agreement is MORE SPECIFIC than a family-scope agreement, so it
# wins when both cover the same part. Higher rank = more specific.
SCOPE_RANK = {"part": 1, "family": 0}

# The band inside which a quote counts as priced TO the agreement. Real quotes
# carry rounding, so this is a band, not an equality test. It is NOT the
# frontend's exception threshold — that one operates on materiality (dollars).
TOLERANCE_PCT = 0.005          # +/- 0.5% of the agreed price


# ---------------------------------------------------------------------------
# The matching rule — pure functions, no I/O
# ---------------------------------------------------------------------------

def _d(value) -> date:
    """ISO string or date -> date. Agreements arrive from CSV or SQLite as text."""
    return value if isinstance(value, date) else date.fromisoformat(value)


def covers_product(agreement: dict, product_id: str, family: str) -> bool:
    """Does this agreement's SCOPE reach this part at all?

    A part-scope agreement names one specific part. A family-scope agreement
    covers every part in a product family — including parts that launch after
    the agreement was signed.
    """
    if agreement["scope"] == "part":
        return agreement["product_id"] == product_id
    return agreement["family"] == family


def in_window(agreement: dict, quote_date: date) -> bool:
    """Is the quote date inside the agreement's effective window (inclusive)?

    This is the temporal half of rule 1: an agreement that has run out cannot
    govern a later quote. A naive join on customer + product alone would
    happily match an agreement that expired eight months earlier.
    """
    return _d(agreement["effective_start"]) <= quote_date <= _d(agreement["effective_end"])


def superseded_as_of(agreement: dict, quote_date: date, by_id: dict) -> bool:
    """Had this agreement already been REPLACED by the quote date?

    `superseded_by` points at the successor. The successor only displaces the
    predecessor once the successor itself has taken effect — so the test is
    time-aware, not a static flag. This is what makes a quote dated during the
    predecessor's own reign match the predecessor, while a quote dated after
    the successor starts matches the successor.

    It is also what resolves the OVERLAP case in a renewal chain: when a
    successor is back-dated to start a few weeks before its predecessor ends,
    both windows contain the quote date, but the predecessor is superseded
    from the successor's start date onward.
    """
    successor_id = agreement.get("superseded_by")
    if not successor_id:
        return False
    successor = by_id.get(successor_id)
    return successor is not None and _d(successor["effective_start"]) <= quote_date


def resolve_agreement(customer_agreements: list, product_id: str, family: str,
                      quote_date: date, by_id: dict):
    """Resolve a quote line to EXACTLY ONE governing agreement, or to none.

    `customer_agreements` is every agreement belonging to this quote's
    customer. Returns (winner_or_None, tied_list). `tied_list` holds every
    candidate that survives all tiebreaks — length > 1 means a genuine
    register defect that validate.py fails the run on. We never pick
    arbitrarily.

    The rule, in order:

      1. STATUS + WINDOW — the agreement must be in force on the quote date:
         inside its effective window, and not already superseded by a
         successor that had taken effect.
      2. SCOPE SPECIFICITY — a part-scope agreement beats a family-scope
         agreement covering the same part.
      3. RECENCY — among survivors of equal specificity, the later
         effective_start wins. This is the tiebreak for two independently
         signed agreements that overlap without a supersession link between
         them (a real register-hygiene failure, and one worth surfacing).
      4. TIE — anything still tied is a data-quality defect, not a judgment
         call. We return it and the caller fails the run.
    """
    live = [a for a in customer_agreements
            if covers_product(a, product_id, family)
            and in_window(a, quote_date)
            and not superseded_as_of(a, quote_date, by_id)]
    if not live:
        return None, []

    # Sort most-specific first, then most-recent first.
    live.sort(key=lambda a: (SCOPE_RANK[a["scope"]], _d(a["effective_start"])), reverse=True)
    best = live[0]
    tied = [a for a in live
            if SCOPE_RANK[a["scope"]] == SCOPE_RANK[best["scope"]]
            and _d(a["effective_start"]) == _d(best["effective_start"])]
    return best, tied


def no_agreement_reason(customer_agreements: list, product_id: str, family: str,
                        quote_date: date, launch_date: date) -> str:
    """Why is there no governing agreement? Three distinct causes, in order.

    "No governing agreement" is not a null to be dropped — it is its own
    risk category, and the three causes call for three different responses.

      agreement_lapsed              — coverage existed and ran out. Someone
                                      forgot to renew. Fix: renewal calendar.
      product_launched_after_       — the part did not exist when this
        agreement                     customer's pricing framework was first
                                      negotiated, and was never added to it.
                                      Fix: a new-part gate at launch.
      never_under_agreement         — the part predates the relationship's
                                      agreements and was simply never included.
                                      Fix: a commercial decision, not a defect.

    The second test uses the customer's EARLIEST agreement start, not the
    latest. "Launched after the framework was set" is the new-part-slipped-
    through story a reader can act on; measuring against the latest renewal
    would sweep every un-renewed part into the same bucket and blur it.
    """
    covering = [a for a in customer_agreements if covers_product(a, product_id, family)]
    # 1. Coverage existed at some point and had ended before this quote.
    if any(_d(a["effective_end"]) < quote_date for a in covering):
        return "agreement_lapsed"
    # 2. The part post-dates this customer's first agreement, so it was never
    #    in scope when the pricing framework was negotiated.
    if customer_agreements:
        first_signed = min(_d(a["effective_start"]) for a in customer_agreements)
        if launch_date > first_signed:
            return "product_launched_after_agreement"
    return "never_under_agreement"


# ---------------------------------------------------------------------------
# The derived measures
# ---------------------------------------------------------------------------

def cost_on(cost_segments: list, quote_date: date):
    """Standard cost in force on a given date.

    Standard cost is not a constant — it steps quarterly as yields improve or
    materials move. Using today's cost to judge a quote from fourteen months
    ago would be an anachronism, so every line is costed at the cost that was
    actually in force when it was quoted.
    """
    for seg in cost_segments:
        if _d(seg["effective_start"]) <= quote_date <= _d(seg["effective_end"]):
            return seg["standard_cost"]
    return None


DDL_CONFORMED = """
DROP TABLE IF EXISTS fact_quote_line_conformed;

CREATE TABLE fact_quote_line_conformed (
    quote_id                 TEXT NOT NULL,
    line_no                  INTEGER NOT NULL,
    customer_id              TEXT NOT NULL REFERENCES dim_customer(customer_id),
    product_id               TEXT NOT NULL REFERENCES dim_product(product_id),
    rep_id                   TEXT NOT NULL REFERENCES dim_rep(rep_id),
    quote_date               TEXT NOT NULL,
    quantity                 INTEGER NOT NULL,
    quoted_price             REAL NOT NULL,
    stage                    TEXT NOT NULL,

    match_status             TEXT NOT NULL,   -- priced_to_agreement | priced_off_agreement | no_governing_agreement
    no_agreement_reason      TEXT,            -- NULL unless no_governing_agreement
    agreement_id_matched     TEXT REFERENCES dim_agreement(agreement_id),
    agreed_price             REAL,            -- NULL where no agreement governs
    standard_cost_at_quote   REAL NOT NULL,   -- cost in force ON the quote date

    price_variance_usd       REAL,            -- (quoted - agreed) * qty; NULL if unmatched
    price_variance_pct       REAL,            -- (quoted - agreed) / agreed
    margin_at_quoted_pct     REAL,            -- (quoted - cost) / quoted
    margin_at_agreed_pct     REAL,            -- (agreed - cost) / agreed
    margin_impact_usd        REAL,            -- margin given up vs the agreement

    is_approved_exception    INTEGER NOT NULL,-- 1 where a deviation approval exists
    exception_reason_code    TEXT,            -- controlled vocabulary; NULL otherwise
    approval_ref             TEXT,            -- the deviation approval reference

    booking_status           TEXT NOT NULL,   -- booked | open | lost
    booked_price             REAL,
    booked_quantity          INTEGER,
    booking_date             TEXT,
    realized_variance_usd    REAL,            -- (booked - agreed) * booked_qty; NULL if unbooked
    exposure_state           TEXT NOT NULL,   -- realized | open | closed_lost

    PRIMARY KEY (quote_id, line_no)
);

CREATE INDEX idx_conformed_customer ON fact_quote_line_conformed(customer_id);
CREATE INDEX idx_conformed_status   ON fact_quote_line_conformed(match_status);
CREATE INDEX idx_conformed_date     ON fact_quote_line_conformed(quote_date);
"""


def load_source(con: sqlite3.Connection) -> dict:
    """Read the star schema into plain Python structures the matcher can use."""
    con.row_factory = sqlite3.Row
    q = lambda sql: [dict(r) for r in con.execute(sql).fetchall()]

    products = {p["product_id"]: p for p in q("SELECT * FROM dim_product")}
    agreements = q("SELECT * FROM dim_agreement")
    by_id = {a["agreement_id"]: a for a in agreements}

    by_customer: dict = {}
    for a in agreements:
        by_customer.setdefault(a["customer_id"], []).append(a)

    costs: dict = {}
    for c in q("SELECT * FROM fact_standard_cost ORDER BY product_id, effective_start"):
        costs.setdefault(c["product_id"], []).append(c)

    bookings = {(b["quote_id"], b["line_no"]): b
                for b in q("SELECT * FROM fact_booking")}

    return {
        "products": products,
        "agreements_by_customer": by_customer,
        "agreement_by_id": by_id,
        "costs": costs,
        "bookings": bookings,
        "lines": q("SELECT * FROM fact_quote_line ORDER BY quote_id, line_no"),
    }


def conform_line(line: dict, src: dict) -> dict:
    """Turn one raw quote line into one conformed row. All the arithmetic lives here."""
    product = src["products"][line["product_id"]]
    family = product["family"]
    quote_date = _d(line["quote_date"])
    customer_agreements = src["agreements_by_customer"].get(line["customer_id"], [])

    # --- the match -------------------------------------------------------
    winner, tied = resolve_agreement(customer_agreements, line["product_id"], family,
                                     quote_date, src["agreement_by_id"])
    ambiguous = len(tied) > 1

    qty = line["quantity"]
    quoted = line["quoted_price"]
    cost = cost_on(src["costs"][line["product_id"]], quote_date)

    if winner is None:
        agreement_id = agreed = None
        match_status = "no_governing_agreement"
        reason = no_agreement_reason(customer_agreements, line["product_id"], family,
                                     quote_date, _d(product["launch_date"]))
    else:
        agreement_id, agreed = winner["agreement_id"], winner["agreed_price"]
        reason = None
        # TOLERANCE: real quotes carry rounding, so "priced to agreement" is a
        # band, not an equality test. The band is a governance parameter and is
        # documented in governance/matching_rules.md.
        within = abs(quoted - agreed) <= TOLERANCE_PCT * agreed
        match_status = "priced_to_agreement" if within else "priced_off_agreement"

    # --- variance and margin ---------------------------------------------
    if agreed is not None:
        price_variance_usd = (quoted - agreed) * qty
        price_variance_pct = (quoted - agreed) / agreed
        margin_at_agreed_pct = (agreed - cost) / agreed
        # Computed the LONG way on purpose: margin dollars at the agreed price
        # minus margin dollars at the quoted price. validate.py then proves this
        # equals -price_variance_usd. See the identity note in matching_rules.md.
        margin_impact_usd = ((agreed - cost) * qty) - ((quoted - cost) * qty)
    else:
        price_variance_usd = price_variance_pct = None
        margin_at_agreed_pct = margin_impact_usd = None

    # Margin at the quoted price is always computable — we know the cost even
    # when no agreement governs. That is what lets the customer page show
    # realized margin on uncovered business.
    margin_at_quoted_pct = (quoted - cost) / quoted

    # --- bookings: realized vs still-recoverable --------------------------
    booking = src["bookings"].get((line["quote_id"], line["line_no"]))
    if booking:
        booking_status, exposure_state = "booked", "realized"
        booked_price, booked_qty = booking["booked_price"], booking["booked_quantity"]
        booking_date = booking["booking_date"]
        realized_variance_usd = ((booked_price - agreed) * booked_qty
                                 if agreed is not None else None)
    else:
        # stage carries the CRM's own view; with no booking row the line is
        # either still in the funnel or dead.
        booking_status = "open" if line["stage"] == "open" else "lost"
        exposure_state = "open" if booking_status == "open" else "closed_lost"
        booked_price = booked_qty = booking_date = realized_variance_usd = None

    return {
        "quote_id": line["quote_id"], "line_no": line["line_no"],
        "customer_id": line["customer_id"], "product_id": line["product_id"],
        "rep_id": line["rep_id"], "quote_date": line["quote_date"],
        "quantity": qty, "quoted_price": quoted, "stage": line["stage"],
        "match_status": match_status, "no_agreement_reason": reason,
        "agreement_id_matched": agreement_id, "agreed_price": agreed,
        "standard_cost_at_quote": cost,
        "price_variance_usd": price_variance_usd,
        "price_variance_pct": price_variance_pct,
        "margin_at_quoted_pct": margin_at_quoted_pct,
        "margin_at_agreed_pct": margin_at_agreed_pct,
        "margin_impact_usd": margin_impact_usd,
        "is_approved_exception": int(bool(line["approval_ref"])),
        "exception_reason_code": line["exception_reason_code"] or None,
        "approval_ref": line["approval_ref"] or None,
        "booking_status": booking_status, "booked_price": booked_price,
        "booked_quantity": booked_qty, "booking_date": booking_date,
        "realized_variance_usd": realized_variance_usd,
        "exposure_state": exposure_state,
        "_ambiguous": ambiguous,
    }


COLUMNS = [
    "quote_id", "line_no", "customer_id", "product_id", "rep_id", "quote_date",
    "quantity", "quoted_price", "stage", "match_status", "no_agreement_reason",
    "agreement_id_matched", "agreed_price", "standard_cost_at_quote",
    "price_variance_usd", "price_variance_pct", "margin_at_quoted_pct",
    "margin_at_agreed_pct", "margin_impact_usd", "is_approved_exception",
    "exception_reason_code", "approval_ref", "booking_status", "booked_price",
    "booked_quantity", "booking_date", "realized_variance_usd", "exposure_state",
]


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    src = load_source(con)

    rows = [conform_line(line, src) for line in src["lines"]]

    # Rule 4: an unresolved tie is a defect. Refuse to write a database that
    # hides it behind an arbitrary pick.
    ambiguous = [(r["quote_id"], r["line_no"]) for r in rows if r["_ambiguous"]]
    if ambiguous:
        raise SystemExit(
            f"MATCHING TIE on {len(ambiguous)} quote line(s) — two agreements of equal "
            f"specificity and equal effective_start both govern. This is a register "
            f"defect, not a judgment call. First few: {ambiguous[:5]}")

    con.executescript(DDL_CONFORMED)
    con.executemany(
        f"INSERT INTO fact_quote_line_conformed VALUES ({','.join('?' * len(COLUMNS))})",
        [tuple(r[c] for c in COLUMNS) for r in rows])
    con.commit()

    counts = dict(con.execute(
        "SELECT match_status, COUNT(*) FROM fact_quote_line_conformed "
        "GROUP BY match_status ORDER BY 2 DESC").fetchall())
    exposure = dict(con.execute(
        "SELECT exposure_state, COUNT(*) FROM fact_quote_line_conformed "
        "WHERE match_status = 'priced_off_agreement' GROUP BY exposure_state").fetchall())
    con.close()

    total = sum(counts.values())
    print(f"Wrote fact_quote_line_conformed: {total} rows")
    for status, n in counts.items():
        print(f"  {status}: {n} ({100 * n / total:.1f}%)")
    print("  off-agreement exposure split: " +
          ", ".join(f"{k}={v}" for k, v in sorted(exposure.items())))


if __name__ == "__main__":
    main()

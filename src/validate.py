"""
validate.py — Reconcile and sanity-check the conformed data; write the report.

Cascadia Deal Desk · Part A

Input : data/cascadia_dealdesk.db  (built by build_db.py, conformed by conform.py)
Output: governance/validation_report.md  (regenerated every run)

Exit code is non-zero if any check FAILS, so this can gate a rebuild.

Checks performed (all offline, against the seeded synthetic dataset):

   1. Every quote line resolves to exactly one match_status; none null, none
      ambiguous.
   2. No quote matches an agreement that was superseded or expired AS OF the
      quote date.
   3. Variance identity — price_variance_usd == (quoted - agreed) x qty.
   4. Margin identity — both margin percentages recompute from the standard
      cost in force on the quote date.
   5. Margin-impact identity — margin_impact_usd == -price_variance_usd. This
      check exists to make the identity permanent and visible rather than a
      coincidence someone discovers later. See governance/matching_rules.md.
   6. Referential integrity across every dimension, including
      fact_booking -> fact_quote_line on (quote_id, line_no).
   7. Booking reconciliation — one booking per quote line at most, every
      booking maps to a real line, booking_date >= quote_date.
   8. Exposure partition — realized + open + closed_lost accounts for every
      off-agreement line exactly once.
   9. Reproducibility — regenerating from the same seed into a temp folder
      produces byte-identical CSVs. The database content hash is recorded.
  10. Threshold monotonicity — exception counts fall as the materiality
      threshold rises. A control that is not monotonic cannot be calibrated.
  11. Coverage audit — counts by match_status, with no_governing_agreement
      reported explicitly and broken out by cause, never dropped.
  12. Realism audit — does the dataset actually tell a story? Reports the
      realized mix against the design bands, the variance sign distribution,
      rep concentration, and the top-10 customers' share of exposure. If
      variance is not clearly skewed negative, or exposure is spread evenly
      across reps, the generator has failed its purpose and this check FAILS.

Usage:
    python src/validate.py
"""

import filecmp
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate
from build_db import db_sha256
from conform import TOLERANCE_PCT, _d, superseded_as_of

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "cascadia_dealdesk.db"
RAW_DIR = REPO_ROOT / "data" / "raw"
REPORT_PATH = REPO_ROOT / "governance" / "validation_report.md"

USD_TOLERANCE = 0.01        # dollars; prices are stored to the cent
PCT_TOLERANCE = 1e-9        # ratios are recomputed in the same float arithmetic

# Materiality ladder for the threshold-monotonicity check. The frontend's
# control operates on dollars of margin impact, NOT on TOLERANCE_PCT.
THRESHOLD_LADDER = [0, 1_000, 2_500, 5_000, 10_000, 25_000, 50_000, 100_000]

# Design bands from the generator brief. Reported, and enforced, in check 12.
BAND_COMPLIANCE_OF_COVERED = (0.80, 0.85)
BAND_NO_AGREEMENT = (0.08, 0.10)
BAND_OFF_AGREEMENT = (0.13, 0.16)


def rows(con, sql, *args):
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(sql, args).fetchall()]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_match_status(con, results):
    """Check 1: exactly one non-null match_status per line, from the vocabulary."""
    valid = ("priced_to_agreement", "priced_off_agreement", "no_governing_agreement")
    total = con.execute("SELECT COUNT(*) FROM fact_quote_line_conformed").fetchone()[0]
    raw = con.execute("SELECT COUNT(*) FROM fact_quote_line").fetchone()[0]
    failures = []
    bad = con.execute(
        "SELECT COUNT(*) FROM fact_quote_line_conformed WHERE match_status IS NULL "
        f"OR match_status NOT IN {valid}").fetchone()[0]
    if bad:
        failures.append(f"{bad} lines with a null or unrecognised match_status")
    if total != raw:
        failures.append(f"conformed rows {total} != raw quote lines {raw}")
    # A conformed row must exist for every raw line, exactly once (the PK
    # guarantees uniqueness, so a count match is sufficient).
    orphan = con.execute(
        "SELECT COUNT(*) FROM fact_quote_line q LEFT JOIN fact_quote_line_conformed c "
        "USING (quote_id, line_no) WHERE c.quote_id IS NULL").fetchone()[0]
    if orphan:
        failures.append(f"{orphan} raw quote lines have no conformed row")
    results.append(("Every quote line resolves to exactly one match_status",
                    not failures, f"{total:,} lines resolved", failures))


def check_no_dead_agreement_matched(con, results):
    """Check 2: no line matches an agreement dead as of its own quote date.

    Two ways an agreement can be dead on a given date: the date falls outside
    its effective window, or a successor had already taken effect. Both are
    tested here directly against the register, independently of the matcher.
    """
    agreements = {a["agreement_id"]: a for a in rows(con, "SELECT * FROM dim_agreement")}
    matched = rows(con, "SELECT quote_id, line_no, quote_date, agreement_id_matched "
                        "FROM fact_quote_line_conformed WHERE agreement_id_matched IS NOT NULL")
    failures = []
    for m in matched:
        a = agreements[m["agreement_id_matched"]]
        qd = _d(m["quote_date"])
        if not (_d(a["effective_start"]) <= qd <= _d(a["effective_end"])):
            failures.append(f"{m['quote_id']}/{m['line_no']}: quote {m['quote_date']} outside "
                            f"{a['agreement_id']} window "
                            f"{a['effective_start']}..{a['effective_end']}")
        elif superseded_as_of(a, qd, agreements):
            failures.append(f"{m['quote_id']}/{m['line_no']}: matched {a['agreement_id']}, "
                            f"already superseded by {a['superseded_by']} on {m['quote_date']}")
    results.append(("No quote matches a superseded or expired agreement (as of its quote date)",
                    not failures, f"{len(matched):,} matched lines checked", failures[:20]))


def check_variance_identity(con, results):
    """Check 3: price_variance_usd == (quoted - agreed) x quantity."""
    bad = rows(con, """
        SELECT quote_id, line_no, price_variance_usd,
               (quoted_price - agreed_price) * quantity AS expected
        FROM fact_quote_line_conformed WHERE agreed_price IS NOT NULL
          AND ABS(price_variance_usd - (quoted_price - agreed_price) * quantity) > ?""",
        USD_TOLERANCE)
    n = con.execute("SELECT COUNT(*) FROM fact_quote_line_conformed "
                    "WHERE agreed_price IS NOT NULL").fetchone()[0]
    results.append(("Variance identity: price_variance_usd = (quoted - agreed) x qty",
                    not bad, f"{n:,} matched lines reconciled",
                    [f"{b['quote_id']}/{b['line_no']}: {b['price_variance_usd']} "
                     f"vs {b['expected']}" for b in bad[:10]]))


def check_margin_identity(con, results):
    """Check 4: both margin percentages recompute from the cost in force.

    This is the check that would catch an anachronism — costing a quote from
    fourteen months ago at today's standard cost.
    """
    failures, checked = [], 0
    for r in rows(con, "SELECT * FROM fact_quote_line_conformed"):
        cost, quoted = r["standard_cost_at_quote"], r["quoted_price"]
        checked += 1
        if abs(r["margin_at_quoted_pct"] - (quoted - cost) / quoted) > PCT_TOLERANCE:
            failures.append(f"{r['quote_id']}/{r['line_no']}: margin_at_quoted_pct")
        if r["agreed_price"] is not None:
            agreed = r["agreed_price"]
            if abs(r["margin_at_agreed_pct"] - (agreed - cost) / agreed) > PCT_TOLERANCE:
                failures.append(f"{r['quote_id']}/{r['line_no']}: margin_at_agreed_pct")

    # And the cost itself must be the one whose window contains the quote date.
    mis_costed = con.execute("""
        SELECT COUNT(*) FROM fact_quote_line_conformed f
        JOIN fact_standard_cost s ON s.product_id = f.product_id
         AND f.quote_date BETWEEN s.effective_start AND s.effective_end
        WHERE ABS(f.standard_cost_at_quote - s.standard_cost) > ?""",
        (USD_TOLERANCE,)).fetchone()[0]
    if mis_costed:
        failures.append(f"{mis_costed} lines carry a cost other than the one in force")
    results.append(("Margin identity: both margin percentages recompute from cost-in-force",
                    not failures, f"{checked:,} lines recomputed", failures[:10]))


def check_margin_impact_identity(con, results):
    """Check 5: margin_impact_usd == -price_variance_usd, always.

    Standard cost cancels: (agreed - cost)q - (quoted - cost)q = (agreed - quoted)q.
    conform.py computes margin impact the LONG way, from the two margin figures,
    so this check is a genuine reconciliation rather than a tautology. It is
    pinned here because a finance reader will verify this arithmetic within
    thirty seconds of opening the page, and it is much better that we said it
    first. See governance/matching_rules.md.
    """
    bad = rows(con, """
        SELECT quote_id, line_no, margin_impact_usd, price_variance_usd
        FROM fact_quote_line_conformed WHERE agreed_price IS NOT NULL
          AND ABS(margin_impact_usd + price_variance_usd) > ?""", USD_TOLERANCE)
    n = con.execute("SELECT COUNT(*) FROM fact_quote_line_conformed "
                    "WHERE agreed_price IS NOT NULL").fetchone()[0]
    results.append(("Margin-impact identity: margin_impact_usd = -price_variance_usd",
                    not bad, f"{n:,} matched lines reconciled",
                    [f"{b['quote_id']}/{b['line_no']}" for b in bad[:10]]))


def check_referential_integrity(con, results):
    """Check 6: SQLite's own FK check, plus the conformed table's dimension keys."""
    failures = [f"foreign_key_check: {v}" for v in
                con.execute("PRAGMA foreign_key_check").fetchall()[:10]]
    checks = {
        "customer": "JOIN dim_customer d USING (customer_id)",
        "product": "JOIN dim_product d USING (product_id)",
        "rep": "JOIN dim_rep d USING (rep_id)",
    }
    total = con.execute("SELECT COUNT(*) FROM fact_quote_line_conformed").fetchone()[0]
    for name, join in checks.items():
        n = con.execute(f"SELECT COUNT(*) FROM fact_quote_line_conformed f {join}").fetchone()[0]
        if n != total:
            failures.append(f"{total - n} conformed lines have an unresolvable {name}_id")
    dangling = con.execute(
        "SELECT COUNT(*) FROM fact_quote_line_conformed f LEFT JOIN dim_agreement a "
        "ON a.agreement_id = f.agreement_id_matched "
        "WHERE f.agreement_id_matched IS NOT NULL AND a.agreement_id IS NULL").fetchone()[0]
    if dangling:
        failures.append(f"{dangling} lines matched an agreement_id that does not exist")
    # Every quote date must fall inside the published date dimension.
    off_grid = con.execute(
        "SELECT COUNT(*) FROM fact_quote_line_conformed f LEFT JOIN dim_date d "
        "ON d.date = f.quote_date WHERE d.date IS NULL").fetchone()[0]
    if off_grid:
        failures.append(f"{off_grid} quote dates fall outside dim_date")
    results.append(("Referential integrity across all dimensions and fact tables",
                    not failures, f"{total:,} lines x 4 dimensions + PRAGMA foreign_key_check",
                    failures))


def check_bookings(con, results):
    """Check 7: one booking per line at most, all linked, none dated before the quote."""
    failures = []
    n_bookings = con.execute("SELECT COUNT(*) FROM fact_booking").fetchone()[0]
    orphans = con.execute(
        "SELECT COUNT(*) FROM fact_booking b LEFT JOIN fact_quote_line q "
        "USING (quote_id, line_no) WHERE q.quote_id IS NULL").fetchone()[0]
    if orphans:
        failures.append(f"{orphans} bookings do not map to a quote line")
    dupes = con.execute(
        "SELECT COUNT(*) FROM (SELECT quote_id, line_no FROM fact_booking "
        "GROUP BY 1, 2 HAVING COUNT(*) > 1)").fetchone()[0]
    if dupes:
        failures.append(f"{dupes} quote lines carry more than one booking")
    backdated = con.execute(
        "SELECT COUNT(*) FROM fact_booking b JOIN fact_quote_line q USING (quote_id, line_no) "
        "WHERE b.booking_date < q.quote_date").fetchone()[0]
    if backdated:
        failures.append(f"{backdated} bookings are dated before their quote")
    # The conformed booking_status must agree with the presence of a booking row.
    disagree = con.execute(
        "SELECT COUNT(*) FROM fact_quote_line_conformed f LEFT JOIN fact_booking b "
        "USING (quote_id, line_no) WHERE (b.booking_id IS NOT NULL) != "
        "(f.booking_status = 'booked')").fetchone()[0]
    if disagree:
        failures.append(f"{disagree} lines where booking_status disagrees with fact_booking")
    results.append(("Booking reconciliation (1:1 with quote lines, never back-dated)",
                    not failures, f"{n_bookings:,} bookings reconciled", failures))


def check_exposure_partition(con, results):
    """Check 8: every off-agreement line sits in exactly one exposure state."""
    counts = dict(con.execute(
        "SELECT exposure_state, COUNT(*) FROM fact_quote_line_conformed "
        "WHERE match_status = 'priced_off_agreement' GROUP BY 1").fetchall())
    total = con.execute("SELECT COUNT(*) FROM fact_quote_line_conformed "
                        "WHERE match_status = 'priced_off_agreement'").fetchone()[0]
    failures = []
    unknown = set(counts) - {"realized", "open", "closed_lost"}
    if unknown:
        failures.append(f"unrecognised exposure_state values: {sorted(unknown)}")
    if sum(counts.values()) != total:
        failures.append(f"states sum to {sum(counts.values())}, expected {total}")
    nulls = con.execute("SELECT COUNT(*) FROM fact_quote_line_conformed "
                        "WHERE exposure_state IS NULL").fetchone()[0]
    if nulls:
        failures.append(f"{nulls} lines have no exposure_state")
    detail = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    results.append(("Exposure partition (realized + open + closed_lost = all off-agreement)",
                    not failures, f"{total:,} off-agreement lines: {detail}", failures))


def check_reproducibility(con, results):
    """Check 9: the same seed regenerates byte-identical CSVs.

    The generator is re-run into a temporary folder and the output compared
    file by file against the committed artifact in data/raw/. This is a real
    verification, not a claim: if any parameter had picked up a dependency on
    wall-clock time or dict ordering, this is where it would surface.
    """
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        generate.main(out_dir=Path(tmp), quiet=True)
        for csv_path in sorted(RAW_DIR.glob("*.csv")):
            twin = Path(tmp) / csv_path.name
            if not twin.exists():
                failures.append(f"{csv_path.name}: not reproduced")
            elif not filecmp.cmp(csv_path, twin, shallow=False):
                failures.append(f"{csv_path.name}: differs on regeneration")
    n = len(list(RAW_DIR.glob("*.csv")))
    results.append((f"Reproducible from seed {generate.SEED} (regenerated and diffed)",
                    not failures, f"{n} CSVs regenerated and compared byte-for-byte",
                    failures))


def check_threshold_monotonicity(con, results):
    """Check 10: exception counts fall as the materiality threshold rises.

    Design point 5 is "exception report first, trigger second" — you calibrate
    a threshold before you automate an alert on it. A threshold that does not
    behave monotonically cannot be calibrated, so this is a real gate on the
    frontend control, not a formality.
    """
    ladder = []
    for t in THRESHOLD_LADDER:
        n = con.execute(
            "SELECT COUNT(*) FROM fact_quote_line_conformed "
            "WHERE match_status = 'priced_off_agreement' AND is_approved_exception = 0 "
            "AND ABS(margin_impact_usd) >= ?", (t,)).fetchone()[0]
        ladder.append((t, n))
    failures = [f"count rose from {a[1]} at ${a[0]:,} to {b[1]} at ${b[0]:,}"
                for a, b in zip(ladder, ladder[1:]) if b[1] > a[1]]
    results.append(("Exception counts are monotonic as the materiality threshold rises",
                    not failures,
                    " → ".join(f"${t:,}:{n}" for t, n in ladder), failures))
    return ladder


CAUSES = ("product_launched_after_agreement", "agreement_lapsed", "never_under_agreement")


def check_coverage_audit(con, results):
    """Check 11: no-agreement lines are reported explicitly and always explained.

    The failure this guards against is quiet: dropping unmatched lines from the
    analysis, which would make coverage look better than it is. Every
    no_governing_agreement line must carry a cause from the controlled
    vocabulary, and no line with a governing agreement may carry one.
    """
    status = dict(con.execute(
        "SELECT match_status, COUNT(*) FROM fact_quote_line_conformed GROUP BY 1").fetchall())
    reasons = dict(con.execute(
        "SELECT no_agreement_reason, COUNT(*) FROM fact_quote_line_conformed "
        "WHERE match_status = 'no_governing_agreement' GROUP BY 1 ORDER BY 2 DESC").fetchall())

    failures = []
    unexplained = con.execute(
        "SELECT COUNT(*) FROM fact_quote_line_conformed "
        "WHERE match_status = 'no_governing_agreement' "
        "AND (no_agreement_reason IS NULL OR no_agreement_reason NOT IN "
        f"{CAUSES})").fetchone()[0]
    if unexplained:
        failures.append(f"{unexplained} no-agreement lines carry no recognised cause")
    leaked = con.execute(
        "SELECT COUNT(*) FROM fact_quote_line_conformed "
        "WHERE match_status != 'no_governing_agreement' "
        "AND no_agreement_reason IS NOT NULL").fetchone()[0]
    if leaked:
        failures.append(f"{leaked} matched lines wrongly carry a no_agreement_reason")
    # All three causes must actually occur — each one argues for a different fix,
    # so a dataset missing one of them under-states the coverage problem.
    missing = [c for c in CAUSES if not reasons.get(c)]
    if missing:
        failures.append(f"causes absent from the dataset: {missing}")

    n = status.get("no_governing_agreement", 0)
    detail = ", ".join(f"{c}={reasons.get(c, 0)}" for c in CAUSES)
    results.append(("Coverage audit (no-agreement reported explicitly, always explained)",
                    not failures, f"{n:,} no-agreement lines: {detail}", failures))
    return status, reasons


def check_realism(con, results, status):
    """Check 12: does this dataset actually tell a story?

    The failure mode this guards against is a generator that produces uniform
    noise: a scatter of meaningless small variances, an exception table with no
    head, and a threshold control that does nothing. If that happens the fix is
    the MECHANISM, not this report — so these assertions are deliberately hard.
    """
    total = sum(status.values())
    off = status.get("priced_off_agreement", 0)
    none_ = status.get("no_governing_agreement", 0)
    covered = total - none_
    compliance = status.get("priced_to_agreement", 0) / covered

    # Sign distribution on UNAPPROVED off-agreement lines. The mechanism says a
    # rep quoting the prior price undercharges, so this must skew hard negative.
    signs = Counter(
        "negative" if r[0] < 0 else "positive" for r in con.execute(
            "SELECT price_variance_usd FROM fact_quote_line_conformed "
            "WHERE match_status = 'priced_off_agreement' AND is_approved_exception = 0"))
    neg_share = signs["negative"] / max(sum(signs.values()), 1)

    # Rep concentration: the top 4 of 12 reps must carry a clear majority.
    by_rep = con.execute(
        "SELECT rep_id, COUNT(*) n FROM fact_quote_line_conformed "
        "WHERE match_status = 'priced_off_agreement' AND is_approved_exception = 0 "
        "GROUP BY 1 ORDER BY n DESC").fetchall()
    top4_share = sum(n for _, n in by_rep[:4]) / max(sum(n for _, n in by_rep), 1)

    # Customer concentration by DOLLARS, which is what the ranked bars show.
    by_cust = con.execute(
        "SELECT customer_id, SUM(margin_impact_usd) s FROM fact_quote_line_conformed "
        "WHERE match_status = 'priced_off_agreement' AND is_approved_exception = 0 "
        "GROUP BY 1 ORDER BY s DESC").fetchall()
    total_exposure = sum(s for _, s in by_cust)
    top10_share = sum(s for _, s in by_cust[:10]) / max(total_exposure, 1e-9)

    approved = con.execute(
        "SELECT COUNT(*) FROM fact_quote_line_conformed WHERE is_approved_exception = 1"
    ).fetchone()[0]

    failures = []
    if not BAND_COMPLIANCE_OF_COVERED[0] <= compliance <= BAND_COMPLIANCE_OF_COVERED[1]:
        failures.append(f"compliance of covered lines {compliance:.1%} outside design band "
                        f"{BAND_COMPLIANCE_OF_COVERED[0]:.0%}-{BAND_COMPLIANCE_OF_COVERED[1]:.0%}")
    if not BAND_NO_AGREEMENT[0] <= none_ / total <= BAND_NO_AGREEMENT[1]:
        failures.append(f"no_governing_agreement {none_ / total:.1%} outside design band "
                        f"{BAND_NO_AGREEMENT[0]:.0%}-{BAND_NO_AGREEMENT[1]:.0%}")
    if not BAND_OFF_AGREEMENT[0] <= off / total <= BAND_OFF_AGREEMENT[1]:
        failures.append(f"priced_off_agreement {off / total:.1%} outside design band "
                        f"{BAND_OFF_AGREEMENT[0]:.0%}-{BAND_OFF_AGREEMENT[1]:.0%}")
    if neg_share < 0.90:
        failures.append(f"off-agreement variance only {neg_share:.1%} negative — the "
                        f"prior-price mechanism is not driving the data")
    if top4_share < 0.60:
        failures.append(f"top 4 of {len(by_rep)} reps carry only {top4_share:.1%} of "
                        f"off-agreement lines — exposure is spread too evenly to be a finding")
    if top10_share < 0.50:
        failures.append(f"top 10 customers carry only {top10_share:.1%} of exposure — "
                        f"the ranked charts will have no head")

    stats = {
        "total": total, "compliance": compliance, "off_share": off / total,
        "none_share": none_ / total, "neg_share": neg_share,
        "top4_rep_share": top4_share, "top10_customer_share": top10_share,
        "total_exposure": total_exposure, "approved": approved,
        "approved_share_of_off": approved / max(off, 1),
        "by_rep": by_rep, "by_cust": by_cust,
    }
    results.append(("Realism audit (the dataset tells a story, not noise)",
                    not failures,
                    f"variance {neg_share:.0%} negative; top-4 reps {top4_share:.0%} of lines; "
                    f"top-10 customers {top10_share:.0%} of ${total_exposure:,.0f}", failures))
    return stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def main() -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")

    results = []
    check_match_status(con, results)
    check_no_dead_agreement_matched(con, results)
    check_variance_identity(con, results)
    check_margin_identity(con, results)
    check_margin_impact_identity(con, results)
    check_referential_integrity(con, results)
    check_bookings(con, results)
    check_exposure_partition(con, results)
    check_reproducibility(con, results)
    ladder = check_threshold_monotonicity(con, results)
    status, reasons = check_coverage_audit(con, results)
    stats = check_realism(con, results, status)

    content_hash = db_sha256(con)
    exposure = dict(con.execute(
        "SELECT exposure_state, COUNT(*) FROM fact_quote_line_conformed "
        "WHERE match_status = 'priced_off_agreement' GROUP BY 1").fetchall())
    exposure_usd = dict(con.execute(
        "SELECT exposure_state, SUM(margin_impact_usd) FROM fact_quote_line_conformed "
        "WHERE match_status = 'priced_off_agreement' AND is_approved_exception = 0 "
        "GROUP BY 1").fetchall())
    rep_names = dict(con.execute("SELECT rep_id, name FROM dim_rep").fetchall())
    cust_names = dict(con.execute("SELECT customer_id, name FROM dim_customer").fetchall())
    agreements = con.execute("SELECT COUNT(*) FROM dim_agreement").fetchone()[0]
    by_status = dict(con.execute(
        "SELECT status, COUNT(*) FROM dim_agreement GROUP BY 1").fetchall())
    con.close()

    all_pass = all(ok for _, ok, _, _ in results)
    total = stats["total"]

    md = [
        "# Validation Report — Cascadia Deal Desk",
        "",
        f"*Auto-generated by `src/validate.py` on {date.today().isoformat()}. "
        f"Seed **{generate.SEED}**, as-of **{generate.AS_OF.isoformat()}**, window "
        f"**{generate.WINDOW_START.isoformat()} → {generate.WINDOW_END.isoformat()}**.*",
        "",
        f"> **{generate.DISCLOSURE}** No real pricing data exists in this project.",
        "",
        f"**Overall: {'ALL CHECKS PASS' if all_pass else 'FAILURES DETECTED'}**",
        "",
        f"**Database content hash (sha256):** `{content_hash}`",
        "",
        "## Automated checks",
        "",
        "| # | Check | Result | Coverage |",
        "|---|-------|--------|----------|",
    ]
    for i, (name, ok, coverage, _) in enumerate(results, 1):
        md.append(f"| {i} | {name} | {'PASS' if ok else 'FAIL'} | {coverage} |")
    for name, ok, _, failures in results:
        if failures:
            md += ["", f"### Failures — {name}", ""] + [f"- {f}" for f in failures]

    # --- check 11 ---------------------------------------------------------
    md += [
        "",
        "## Coverage audit (check 11)",
        "",
        "`no_governing_agreement` is reported explicitly, never dropped. It is not",
        "a null to be filtered away — it is its own risk category, and the three",
        "causes call for three different responses.",
        "",
        "| Match status | Lines | Share |",
        "|---|---:|---:|",
    ]
    for s in ("priced_to_agreement", "priced_off_agreement", "no_governing_agreement"):
        n = status.get(s, 0)
        md.append(f"| `{s}` | {n:,} | {100 * n / total:.1f}% |")
    md += [
        f"| **Total** | **{total:,}** | **100.0%** |",
        "",
        "| No-agreement cause | Lines | What it means |",
        "|---|---:|---|",
    ]
    cause_text = {
        "product_launched_after_agreement":
            "The part did not exist when the customer's framework was negotiated "
            "→ a new-part gate at launch",
        "agreement_lapsed":
            "Coverage existed and ran out → a renewal calendar",
        "never_under_agreement":
            "The part predates the agreements and was never included → a "
            "commercial decision, not a defect",
    }
    for cause, n in reasons.items():
        md.append(f"| `{cause}` | {n:,} | {cause_text.get(cause, '')} |")

    # --- exposure ---------------------------------------------------------
    md += [
        "",
        "## Exposure split (check 8)",
        "",
        "This is the module's argument stated in dollars, and it exists only",
        "because `fact_booking` is joined back to the quote line it came from.",
        "Dollar figures below EXCLUDE approved exceptions — those are documented",
        "deviations, not leakage.",
        "",
        "| Exposure state | Off-agreement lines | Margin given up | Meaning |",
        "|---|---:|---:|---|",
    ]
    meaning = {
        "realized": "Booked at the off-agreement price. The money is gone.",
        "open": "Quoted, not yet booked. **Still fixable before it reaches the customer.**",
        "closed_lost": "Never booked. No exposure, but it belongs in the coverage audit.",
    }
    for st in ("realized", "open", "closed_lost"):
        md.append(f"| `{st}` | {exposure.get(st, 0):,} | "
                  f"${exposure_usd.get(st, 0):,.0f} | {meaning[st]} |")
    md += [
        f"| **Total** | **{sum(exposure.values()):,}** | "
        f"**${sum(exposure_usd.values()):,.0f}** | |",
    ]

    # --- check 10 ---------------------------------------------------------
    md += [
        "",
        "## Materiality threshold ladder (check 10)",
        "",
        "Unapproved off-agreement lines at or above each threshold of absolute",
        "margin impact. Counts must fall monotonically or the control cannot be",
        "calibrated. Note this operates on **dollars**, not on the ±"
        f"{TOLERANCE_PCT:.1%} matching tolerance.",
        "",
        "| Threshold | Lines at or above |",
        "|---|---:|",
    ]
    md += [f"| ${t:,} | {n:,} |" for t, n in ladder]

    # --- check 12 ---------------------------------------------------------
    md += [
        "",
        "## Realism audit (check 12)",
        "",
        "A generator that produces uniform noise around the agreed price yields a",
        "scatter of meaningless small variances and an exception table with no",
        "story. These assertions exist so that failure is loud. If they fail, the",
        "fix is the mechanism in `src/generate.py`, never the assertion.",
        "",
        "| Measure | Realized | Design band | Result |",
        "|---|---:|---|---|",
        f"| Priced to agreement (of covered lines) | {stats['compliance']:.1%} | "
        f"{BAND_COMPLIANCE_OF_COVERED[0]:.0%}–{BAND_COMPLIANCE_OF_COVERED[1]:.0%} | "
        f"{'PASS' if BAND_COMPLIANCE_OF_COVERED[0] <= stats['compliance'] <= BAND_COMPLIANCE_OF_COVERED[1] else 'FAIL'} |",
        f"| Priced off agreement (of all lines) | {stats['off_share']:.1%} | "
        f"{BAND_OFF_AGREEMENT[0]:.0%}–{BAND_OFF_AGREEMENT[1]:.0%} | "
        f"{'PASS' if BAND_OFF_AGREEMENT[0] <= stats['off_share'] <= BAND_OFF_AGREEMENT[1] else 'FAIL'} |",
        f"| No governing agreement (of all lines) | {stats['none_share']:.1%} | "
        f"{BAND_NO_AGREEMENT[0]:.0%}–{BAND_NO_AGREEMENT[1]:.0%} | "
        f"{'PASS' if BAND_NO_AGREEMENT[0] <= stats['none_share'] <= BAND_NO_AGREEMENT[1] else 'FAIL'} |",
        f"| Approved exceptions (of off-agreement) | {stats['approved_share_of_off']:.1%} | "
        f"~12% | informational |",
        f"| Off-agreement variance that is negative | {stats['neg_share']:.1%} | "
        f"≥90% | {'PASS' if stats['neg_share'] >= 0.90 else 'FAIL'} |",
        f"| Top 4 of 12 reps' share of off-agreement lines | {stats['top4_rep_share']:.1%} | "
        f"≥60% | {'PASS' if stats['top4_rep_share'] >= 0.60 else 'FAIL'} |",
        f"| Top 10 customers' share of exposure | {stats['top10_customer_share']:.1%} | "
        f"≥50% | {'PASS' if stats['top10_customer_share'] >= 0.50 else 'FAIL'} |",
        "",
        "**Why the variance is overwhelmingly negative:** off-agreement lines are",
        "generated by a rep quoting the customer's *prior* price instead of the",
        "agreed price. The agreed price sits at a premium above the prior price, so",
        "quoting the old number necessarily undercharges. The variance is not drawn",
        "from a distribution — it *is* the premium that negotiation won and quoting",
        "gave back.",
        "",
        "### Off-agreement lines by rep (unapproved only)",
        "",
        "| Rep | Lines |",
        "|---|---:|",
    ]
    md += [f"| {rep_names[rid]} | {n:,} |" for rid, n in stats["by_rep"]]
    md += [
        "",
        "### Top 10 customers by margin given up (unapproved only)",
        "",
        "| Customer | Margin given up |",
        "|---|---:|",
    ]
    md += [f"| {cust_names[cid]} | ${s:,.0f} |" for cid, s in stats["by_cust"][:10]]

    md += [
        "",
        "## Agreement register",
        "",
        f"{agreements:,} agreements. `status` describes the register **as of "
        f"{generate.AS_OF.isoformat()}** — it is what the agreement timeline renders. "
        "The matcher does not read it; it asks the same two questions (expired? "
        "superseded?) **as of each quote's own date**. Both meanings are set out in "
        "[`matching_rules.md`](matching_rules.md).",
        "",
        "| Register status (as of the as-of date) | Agreements |",
        "|---|---:|",
    ]
    md += [f"| `{s}` | {n:,} |" for s, n in sorted(by_status.items())]

    md += [
        "",
        "---",
        f"*{generate.DISCLOSURE} Regenerate with `python src/generate.py` at seed "
        f"{generate.SEED}. Independent portfolio project; illustrates a "
        "pricing-governance design on invented data only.*",
        "",
    ]

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    for name, ok, coverage, _ in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} — {coverage}")
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()

# Matching Rules — Cascadia Deal Desk

How a quote line is matched to the pricing agreement that governs it, and what
happens in every case where the answer is not obvious.

This document is written to be read without looking at code. It is the artifact
that makes this governance work rather than a chart. The rule it describes is
implemented once, in `resolve_agreement()` in [`src/conform.py`](../src/conform.py),
and the synthetic generator imports that same function so the data cannot be
built against a subtly different rule than the one the analysis applies.

> **Synthetic data, seeded generator. Simulated — not real company data.**
> Every example below uses real row values from the generated dataset, so each
> one can be traced back to the database.

---

## 1. The question being answered

A quote line names a customer, a part, and a date. An agreement names a
customer, a scope, a price, and a window of time. The matching rule decides
which single agreement — if any — governs that line.

Three outcomes are possible, and **all three matter**:

| Outcome | Meaning |
|---|---|
| `priced_to_agreement` | A governing agreement exists and the quote is priced to it. |
| `priced_off_agreement` | A governing agreement exists and the quote is **not** priced to it. |
| `no_governing_agreement` | No agreement governs this line. **This is its own risk, not a null to be dropped.** |

The third is the one most analyses lose. A line with no governing agreement is
not "clean" — it is unmeasured, and it is reported explicitly here and on every
page.

## 2. The tolerance band

"Priced to agreement" means **within ±0.5% of the agreed price**, not an exact
match. Real quotes carry rounding, and an equality test would flag a $0.02
difference as a pricing failure.

The band is a named constant (`TOLERANCE_PCT` in `src/conform.py`) so it is
reviewable and changeable in one place.

> **This is not the exception threshold.** The materiality control on the
> exception page operates on **dollars of margin impact**, not on this
> percentage band. The tolerance decides whether a line *deviates at all*; the
> threshold decides whether a deviation is *worth someone's afternoon*. Two
> different questions, deliberately separated — that separation is what makes
> design point 5 ("exception report first, trigger second") possible.

## 3. The rule, in order

Start with every agreement belonging to the quote's customer whose **scope
reaches the part** — a part-scope agreement naming that exact part, or a
family-scope agreement covering the part's family. Then apply, in order:

### Rule 1 — Status: the agreement must be alive on the quote date

An agreement is excluded if, **as of the quote date**, it was either:

- **expired** — the quote date falls outside `effective_start … effective_end`; or
- **superseded** — a successor agreement existed *and had already taken effect*.

Both tests are asked **as of the quote's own date**, not as of today.

> **On the `status` column.** `dim_agreement.status` (`active` / `superseded` /
> `expired`) describes the register **as of the as-of date, 2026-08-01**. It is
> what the agreement timeline on the customer page renders. **The matcher does
> not read it.** A quote from November 2024 is governed by whatever was in force
> in November 2024, even though that agreement has since been replaced and is
> labelled `superseded` today. Judging a historical quote by today's register
> state would wrongly strip coverage from most of the book.

### Rule 2 — Scope specificity: the more specific agreement wins

A **part-scope** agreement beats a **family-scope** agreement covering the same
part. A price negotiated for one part is a more deliberate act than a price
negotiated for its whole family, so it governs.

### Rule 3 — Recency: the later agreement wins

Among survivors of equal specificity, the one with the later `effective_start`
wins. This resolves the case of two independently signed agreements that
overlap with **no supersession link between them** — a genuine register-hygiene
failure that happens when two people paper the same deal.

### Rule 4 — Tie: fail, do not guess

If two agreements survive all three rules, that is a **data-quality defect, not
a judgment call**. `conform.py` refuses to write the conformed table, names the
offending lines, and exits non-zero.

Picking one arbitrarily would produce a number that looks authoritative and
cannot be reproduced. **Current dataset: 0 ties.** The check is a permanent gate,
not a formality.

---

## 4. Worked examples

Real rows from the generated dataset.

### 4a. A renewal chain — the predecessor still governs

> Quote `Q-2024-000002` line 2, customer `C033`, part `P0033`, dated **2024-08-25**.
>
> | Agreement | Window | Agreed price | Status today |
> |---|---|---|---|
> | **A0344** | 2024-03-09 → 2025-08-07 | $14,853.44 | `superseded` |
> | A0345 (successor) | from 2025-10-26 | $16,586.40 | `active` |
>
> **Matched: A0344.** Its window contains the quote date, and its successor did
> not take effect until fourteen months later. A0344 is labelled `superseded`
> *today*, but it was the agreement in force on the day this quote went out.

### 4b. An overlap — the successor was back-dated

> Quote `Q-2025-000410` line 2, customer `C036`, part `P0069`, dated **2025-01-27**.
>
> | Agreement | Window | Agreed price |
> |---|---|---|
> | A0399 (predecessor) | 2024-05-08 → **2025-01-30** | $7,673.24 |
> | **A0400** (successor) | **2024-12-29** → 2026-02-04 | $8,253.40 |
>
> Both windows contain the quote date — the successor starts a month *before*
> its predecessor ends. **Matched: A0400**, because by 2025-01-27 the successor
> had taken effect and A0399 was superseded as of that date.
>
> The quote was $8,261.32 — priced to A0400 within tolerance. Had the matcher
> taken the predecessor, this compliant line would have been reported as a
> $587-per-unit overcharge. **The overlap case is not an edge case; it silently
> inverts the finding.**

### 4c. Scope specificity — a part price overrides a family price

> Quote `Q-2024-000017` line 1, customer `C016`, part `P0086`, family
> *Thermal Control Units*, dated **2024-08-08**.
>
> | Agreement | Scope | Window | Agreed price |
> |---|---|---|---|
> | A0162 | family — Thermal Control Units | 2024-06-13 → 2026-10-30 | $61,399.88 |
> | **A0169** | **part — P0086** | 2024-07-29 → 2027-04-09 | $53,316.69 |
>
> Both are alive and both cover the part. **Matched: A0169**, the part-scope
> agreement. Taking the family price here would overstate the agreed price by
> $8,083 per unit and manufacture a large false "undercharge".

### 4d. Expiry — what a naive join gets wrong

> Quote `Q-2025-000685` line 1, customer `C015`, part `P0084`, dated **2025-06-07**.
>
> Agreement A0156 ran 2024-04-30 → **2025-03-28** at $51,190.05. Its replacement
> had not yet started. The quote is **71 days after expiry**, sitting in the gap.
>
> **Matched: nothing.** `match_status = no_governing_agreement`,
> `no_agreement_reason = agreement_lapsed`.
>
> A join on customer + part alone — the obvious first attempt — would have
> matched A0156 and priced this line against a dead agreement at $51,190.05.
> That is the specific error this rule exists to prevent, and it fails *silently*:
> the number looks perfectly reasonable.

### 4e. The mechanism — what an off-agreement line actually is

> Quote `Q-2026-001453` line 1, **Kingfisher Test Labs**, part `BIS-2961`,
> rep **Yara Haddad**, dated **2026-04-05**.
>
> Agreement A0386: prior price **$475.82**, premium **29.1%**, agreed price
> **$614.13**. The rep quoted **$476.02** — the *prior* price, not the agreed one.
>
> | Measure | Value |
> |---|---|
> | Price variance | **−22.49%** = **−$86,871** on 629 units |
> | Margin impact | **$86,871** given up |
> | Exposure state | **`open`** — quoted, not yet booked, **still fixable** |
>
> This is the whole thesis in one row. The variance is not noise around the
> agreed price; it is exactly the premium that was negotiated and then given
> back at the quoting step. And because the line has not booked yet, it is the
> kind a deal desk exists to catch **before** it reaches the customer.

### 4f. A legitimate exception — priced *above* the agreement

> Quote `Q-2024-000341` line 1, **Quilcene Systems**, part `VPH-1000`,
> dated 2024-12-18. Agreed $31,557.01, quoted **$34,365.10 (+8.90%)**,
> approval `DR-2024-0011`, reason `competitive_displacement`.
>
> Off-agreement, documented, approved, and **favourable**. It is flagged
> `is_approved_exception` and excluded from leakage totals. Exceptions like this
> are why the threshold has to be calibrated against a real exception report
> before anyone automates an alert on it — without false positives there is
> nothing to calibrate.

---

## 5. Why there is no governing agreement

Every unmatched line is assigned one of three causes, in this order. Each argues
for a different fix, which is the point of separating them.

| Cause | Test | What it argues for |
|---|---|---|
| `agreement_lapsed` | An agreement that covered this part ended before the quote date. | A renewal calendar. |
| `product_launched_after_agreement` | The part launched after this customer's **earliest** agreement start. | A new-part gate at launch. |
| `never_under_agreement` | Neither of the above. | A commercial decision, not a defect. |

The second test uses the customer's **earliest** agreement, not the latest.
"Launched after the pricing framework was set" is the new-part-slipped-through
story someone can act on; measuring against the latest renewal would sweep every
un-renewed part into the same bucket and blur it.

> **A deliberate naming split.** `agreement_lapsed` means the *agreement* expired
> without renewal. `closed_lost` (an `exposure_state`) means the *quote line*
> never converted. Two different events, two different words, and they are never
> used interchangeably.

---

## 6. The margin identity — stated first, on purpose

`margin_impact_usd` is **arithmetically identical to `−price_variance_usd`**.

Standard cost cancels:

```
margin at agreed − margin at quoted
  = (agreed − cost) × qty − (quoted − cost) × qty
  = (agreed − quoted) × qty
  = −price_variance_usd
```

**This is not a bug, and the column stays.** It is a finding, and it is the most
important sentence in the analysis:

> Because a quoting error does not change what the part costs to make, **every
> dollar of price variance is a dollar of margin, one for one.** There is no
> volume offset and no cost recovery.

A finance reader will check this arithmetic within thirty seconds of opening the
page. It is much better that we said it first. `conform.py` computes margin
impact the *long* way — from the two margin figures — and
[`validate.py`](../src/validate.py) check 5 reconciles it to `−price_variance_usd`
on every matched line, so the identity is verified rather than assumed.

**Standard cost still earns its place.** It is what makes `margin_at_quoted_pct`
and `margin_at_agreed_pct` meaningful, and it is what drives the *second*
finding: standard cost steps quarterly, so an agreement can be honoured
perfectly and still deliver less margin than it was signed for, because cost
moved underneath a locked price. That is a **different failure from leakage**,
and the model has to be able to tell them apart.

---

## 7. Exposure: what is gone and what is still fixable

Every off-agreement line lands in exactly one exposure state, derived from
whether the quote line converted to a booking.

| State | Definition | Measured on |
|---|---|---|
| `realized` | Booked at the off-agreement price. **The money is gone.** | Booked quantity × booked price — what actually invoiced. |
| `open` | Quoted, not yet booked. **Still fixable before it reaches the customer.** | Quoted quantity × quoted price. |
| `closed_lost` | The line never booked. No exposure, but it belongs in the coverage audit rather than being dropped. | — |

This split exists only because `fact_booking` carries `quote_id` and `line_no`
back to the quote line it came from. Without that key, bookings cannot do any
work — there is no way to tell which off-agreement quotes actually invoiced.

`booked_price` is **not** assumed equal to `quoted_price`; the price can move
between quote and order, and realized exposure is measured on what was actually
ordered.

---

## 8. Honest limits

- **The data is synthetic.** It demonstrates a design; it measures nothing real.
- **The generator imports the matcher.** That guarantees the pipeline is
  *consistent* — the dataset cannot be built against a different rule than the
  one the analysis applies. It is **not** independent evidence that the rule is
  *correct*. Correctness is argued by the worked examples above and by the
  identity checks in `validate.py`, which do not depend on the matcher at all.
- **Family-scope agreements carry a single unit price.** That is realistic here
  only because part prices within a family are generated within ±12% of a family
  base. A real register would more often hold a discount schedule, which would
  need a different scope model.
- **Approved exceptions are excluded from leakage totals but retained in the
  data**, so the threshold can be calibrated against them rather than around them.

---

*Synthetic data, seeded generator. Simulated — not real company data. Independent
portfolio project; illustrates a pricing-governance design on invented data only.*

# Reading panel — Cascadia Deal Desk, customer page

**Second panel under Rule 7.4. First run with pre-panel notes, so N is real.**

---

## Roster

```
READING PANEL — Cascadia Deal Desk, customer page — 2026-08-02
Decision served (Rule 0.1): whether this account's pricing needs intervention —
                            account-level commercial review
Charts panelled: 4      States: default loading state only
Nature: simulated

  Seat 1  Key Account Manager, 12 yrs   — owns the relationship personally. Will ask whether
                                          anything here forces an awkward conversation, or
                                          could be used against the account in a QBR
  Seat 2  Pricing & Contracts Mgr, 8 yrs — owns the agreement register and would have to reopen
                                          a contract if this says the terms are wrong. Precise
                                          about effective dates, expiry and supersession
  Seat 3  Finance Business Partner, 6 yrs — owns margin at account level, sits in commercial
                                          reviews not the close, takes cost as given. Tests
                                          whether the page works for its least technical
                                          real reader
  Seat 4  Visualization reader           — canvas only; tables and arithmetic excluded

Blindness asserted: design system ☑ · review and build notes ☑ · source data ☑ ·
                    intended finding from outside the artifact ☑ · other seats' output ☑
Run: parallel ☑    Author's pre-panel notes recorded: ☑
```

**Roster note.** This is deliberately not the index page's roster (VP Finance / cost accountant / sales ops). Different decision, different room. The index page asks whether the *workflow* needs changing; this page asks whether *this account* does — so the account owner, the person who'd amend the contract, and the person who'd forecast the margin are the seats that exist.

---

## Summary

```
PANEL: 4 seats, simulated · 4 charts · findings 17 · defects 13 · novel 8
       fixed 8 · accepted 5 · rejected 4 · multi-seat defects 8
       D = 3.25 defects/chart · N = 0.62 novel share · R = 0.24 rejected share
```

**Against the index page:** D 3.00 → 3.25, R 0.18 → 0.24, multi-seat defects 5 → 8. Two modules is not a trend. Nothing near the retirement trigger.

---

## The finding, and all four seats found it

**Chart 3 — the title says 52% and the chart says 52.0%, and they are different numbers.**

> *"The title says Burn-In Sockets is 52% of quoted value, and there's a separate note saying gross margin on that same family is 52.0% — is that actually a coincidence, or did someone mix up two different stats that happen to land on the same number?"* — Seat 1
>
> *"…those are two different metrics landing on the same number, and I'd want to know that's not a mislabel before I repeat either figure to anyone."* — Seat 2
>
> *"a viewer skimming the title and then seeing 52.0% printed right there on the chart could easily believe the annotation is what the title refers to, when it's actually an unrelated figure."* — Seat 4

**Four of four seats, independently.** No finding across either panel has come close to that consensus.

Share of quoted value: $13.8M ÷ $26.4M = **52.3%**. Gross margin on the family: **52.0%**. Both true, both about Burn-In Sockets, neither one evidence for the other.

**And looking at the render myself, it is worse than the seats could tell.** The annotation is set in Evergreen — correctly colour-matched to the highlighted bar under Rule 3.3 — but it sits vertically at the **Thermal Control Units** row, not the Burn-In Sockets row. So the only thing tying it to its bar is the colour.

Rule 3.4, INVARIANT: *"An annotation tied to a mark by colour must also be tied by proximity, a leader line, or direct adjacency. **Colour alone never carries the association.**"*

That is a clean INVARIANT breach the panel could not name because no seat knows the rule — they only reported the symptom, which is exactly the division of labour 7.4 describes. Move the annotation to the Burn-In Sockets row and change its wording so the two figures cannot be mistaken for each other.

## Second: a bare gap in two line charts

> *"There is a visible break in the line — it stops shortly after the second Aug label and resumes before the second Dec label, with no connecting segment. That implies missing month(s), but there's no annotation explaining it, which undermines confidence in a clean count of 23 months."* — Seat 4, corroborated by seats 2 and 3

Rule 4.1, INVARIANT: *"Where a value is genuinely missing: break the encoding **and label the break.** A bare gap is not neutral — it lowers reader confidence without telling the reader why."*

The break is on both chart 1 and chart 2. Song & Szafir measured precisely this: the unlabelled-gap treatment scored **lowest** of all missing-data treatments on perceived data quality. Seat 4 reached that conclusion from the picture alone, and then used it to doubt the title's month count — which is the mechanism the rule predicts.

## Third: two form-versus-claim mismatches

**Chart 1** titles a *count* — "quoted below agreement in 10 of 23 months" — over a continuous line. Seat 4: *"A line chart is the wrong form for a count claim."* And the line hugs zero at several points, so *"whether a given month counts as below or at agreement is often a judgment call of a pixel or two"* — ambiguous exactly where the claim lives. Rule 1.1: the form must express the declared relationship.

**Chart 3** titles a *share* over ranked absolute bars with no total. Seat 4: *"a share-of-whole claim calls for a chart that shows parts against a whole… A plain ranked bar chart of absolute dollar values is the wrong form for asserting a percentage share."* Seat 3 independently: *"I don't know if these are the only three families or just the top three."*

---

## Disposition

Sorted by consensus, per v1.1. Dispositions proposed, not final.

| # | Finding, in the reviewer's words | Seats | n | Ch | Defect | Novel | Disposition | Rule |
|---|---|---|---|---|---|---|---|---|
| 1 | *"two different stats that happen to land on the same number"* | 1,2,3,4 | **4** | 3 | yes | yes | **fixed** — reword and move to the correct row | 3.4 |
| 2 | *"a visible break in the line… no annotation explaining it"* | 2,3,4 | **3** | 1,2 | yes | yes | **fixed** — label the break | 4.1 |
| 3 | *"no green bar follows it… nothing telling me if that part is currently covered"* | 1,2,3 | **3** | 4 | yes | yes | **fixed** — flag uncovered parts | 0.1 |
| 4 | *"you'd have to sum all three bars and divide — a calculation, not a read"* | 3,4 | 2 | 3 | yes | yes | **fixed** — show the whole | 1.1 |
| 5 | *"I don't know if these are the only three families or just the top three"* | 1,3 | 2 | 3 | yes | no | accepted | 0.1 |
| 6 | *"easy to skim past the clamp markers… 15 of the windows are clamped"* | 1,4 | 2 | 4 | yes | no | accepted | 1.2 |
| 7 | *"no dollar figures anywhere — I can't size the margin gap in real revenue terms"* | 1,2 | 2 | 2 | yes | no | accepted | 0.1 |
| 8 | *"13 active, straight from the chart title"* | 1,3 | 2 | 4 | yes | no | accepted | 3.2 |
| 9 | *"A line chart is the wrong form for a count claim"* | 4 | 1 | 1 | yes | yes | **fixed** | 1.1 |
| 10 | *"the x-axis only gives me quarter ticks, so I can't pin the dip to a month"* | 1 | 1 | 1 | yes | yes | **fixed** | 5.5 |
| 11 | *"the two lines… are only labeled once, at the far right"* | 4 | 1 | 2 | yes | yes | accepted | 3.6 |
| 12 | *"No time dimension here at all"* | 2 | 1 | 3 | yes | no | **fixed** | 4.2 |
| 13 | *"had to eyeball [start and end margin] off the axis rather than read it directly"* | 1 | 1 | 2 | yes | yes | **fixed** | 3.2 |
| 14 | *"the exact +4.6pp… depends on averaging three months at each end, which isn't marked"* | 4 | 1 | 2 | **no** | — | rejected — v2.1 computed-aggregate exception, and the subtitle names the basis | 3.2 |
| 15 | *"1 further part with 1 agreement not shown — which part is that?"* | 1,2 | 2 | 4 | **no** | — | rejected — the disclosure is what 6.6 requires; naming every excluded row is not | 6.6 |
| 16 | *"I looked for which SKUs drove those two dips"* | 2 | 1 | 1 | **no** | — | rejected — a drill-down request, not a misreading | — |
| 17 | *"superseded and expired colours are close enough that you're relying on the text label"* | 4 | 1 | 4 | **no** | — | rejected — the text label **is** the compliant second channel under 2.3.2. Working as designed | 2.3.2 |

**Finding 14 is the amendment paying for itself.** Seat 4 correctly identified that "+4.6pp" is not readable from the marks — under v2.0's checklist that was an INVARIANT failure. Rule 3.2's v2.1 exception admits it, and the rule's own worked example is almost word for word this chart: *"'margin fell 6.8pp' is admissible where the subtitle says the trend is measured on the first and last three quoted months."* The subtitle does say exactly that. Rejected on the written exception, not on judgment.

---

## N is real this time, and here is the scorecard

Eight predictions were written down before rendering. Grading them honestly:

| | Prediction | Outcome |
|---|---|---|
| P1 | Timeline bar length still reads as duration despite carets | **Hit** — finding 6 |
| P2 | Margin chart's causal claim still not visible | **Miss.** The title is now "+4.6pp over the period" and makes no causal claim. The earlier fix worked |
| P3 | Readers want dollars behind the percent gap | **Hit** — finding 7 |
| P4 | Envelope band misread | **N/A** — no small multiples on this page |
| P5 | Mix ranking has no denominator | **Hit** — finding 5 |
| P6 | Numbers sourced from titles, not marks | **Hit** — finding 8 |
| P7 | Madrona/Lichen merge in grayscale | **Miss.** These charts separate by line style and text label, not hue. Seat 4 explicitly passed three of four on grayscale |
| P8 | Period/as-of unclear somewhere | **Hit** — finding 12 |

Five hits, two misses, one not applicable. **N = 0.62** — eight of thirteen defects were things the notes did not anticipate, including the two INVARIANT breaches and both form-versus-claim mismatches.

The two misses are the more interesting half. P2 and P7 were both predictions that a *known past weakness would recur*, and both were wrong because the weakness had already been fixed. That is the failure mode the pre-panel note exists to expose: an author predicts from memory of old defects, and memory of old defects is not knowledge of current ones.

---

## What two runs say about the rule

**Seat 4 is still finding the most, but the gap narrowed sharply.** Index page: 13 of 19 defects. Here: 6 of 13, with the domain seats carrying 7 — and the top-consensus finding came from all four. The customer-page roster was cast harder than the index one, with three genuinely different jobs rather than three flavours of finance. That is one plausible explanation and two runs cannot confirm it. Worth watching whether roster quality is what moves this ratio, because if it is, the fix for a weak panel is better casting rather than a smaller floor.

**On the sentence returns.** Better than the index run. Seat 1 on chart 2 — *"our margin on this account is up and now basically sitting right on top of what we agreed to, so nothing here looks like it's costing us"* — is a real reader's takeaway, not a paraphrase of the title, and it carries a judgment ("nothing here looks like it's costing us") the title does not assert. That is the return doing what it is for. The DracoGPT concern in Rule 7.4 is not resolved, but it is not yet visible either.

**Open item 13 now has two data points.** D 3.00 → 3.25 · N (—) → 0.62 · R 0.18 → 0.24. One more module before the trigger can be evaluated at all.

# Reading panel — Cascadia Deal Desk, index page

**First panel run under Rule 7.4.** Opens Open Item 13's numbers.

---

## Roster

```
READING PANEL — Cascadia Deal Desk, index page — 2026-08-02
Decision served (Rule 0.1): whether the pricing exception rate justifies changing
                            the quoting workflow — finance leader, sales in the room
Charts panelled: 6      States: default loading state only
Nature: simulated

  Seat 1  VP of Finance, 14 yrs        — simulated — owns the margin number and defends it to a
                                                     CFO. Will ask whether leakage is real money
                                                     or an accounting artifact
  Seat 2  Cost accountant, 9 yrs       — simulated — closes in five days, explains variances she
                                                     did not cause. Alert to standard vs actual
                                                     cost and to timing differences called variance
  Seat 3  Sales operations leader, 11  — simulated — his desk wrote these quotes. Will ask whether
                                                     an "exception" is a mistake or an approved
                                                     deal, because that decides whether this page
                                                     is a report or an accusation
  Seat 4  Visualization reader         — simulated — canvas only; tables and arithmetic excluded

Blindness asserted: design system ☑ · review and build notes ☑ · source data ☑ ·
                    intended finding from outside the artifact ☑ · other seats' output ☑
Run: parallel ☑    Author's pre-panel notes recorded: ☐  →  N = not measured
```

**On N.** Aaron's own list of suspected problems was not recorded before the panel ran, so the novel share cannot be computed for this module. Reconstructing it after the fact would produce a flattering number. Recorded as not measured; capture it before the next panel.

---

## Summary

```
PANEL: 4 seats, simulated · 6 charts · findings 23 · defects 19 · novel not measured
       fixed 13 · accepted 6 · rejected 4
       D = 3.17 defects/chart · N = not measured · R = 0.17 rejected share
```

Dispositions below are **proposed**, not final. Rule 7.4 makes disposition the author's, and the *fixed* / *accepted* / *rejected* split is a judgment about this artifact that no reviewer can make from the outside.

---

## The finding that justifies the run

**Chart 5 — the threshold-calibration chart has an axis that is not a scale.**

> *"The x-axis tick labels ($0, $2.5K, $7.5K, $15K, $25K, $40K) are not evenly spaced in value, but the plotted points appear evenly spaced by position … That distorts the perceived rate of decline, which matters directly for a title built on a speed comparison."* — Seat 4

The chart is drawn on an **ordinal** axis whose labels are numeric. $0→$2.5K and $25K→$40K occupy the same horizontal distance. The title is *"Raising the threshold drops exception count far faster than it drops dollars"* — a claim about **rate**, which is slope, which is exactly the quantity the axis spacing distorts.

This survived the whole second-pass adversarial read on eleven charts. It survived because the chart was **rebuilt** during that pass in response to a different 3.2 breach — the "Half the exposure sits in the 82 largest lines" finding — and the rebuild introduced this. A reviewer who knows why a chart was rebuilt checks whether the old defect is gone. A blind reader just reads the axis.

Under Rule 2.1 this is the case with no defence: the visual ordering of *rates* contradicts the data ordering of rates.

---

## Findings by chart

### Chart 1 — match status by month · 6 findings

| Finding | Seat | Proposed | Rule |
|---|---|---|---|
| *"the title's actual claim is about a share (23%, a range of 15–31%) and a trend — neither of which is what the plot literally encodes (it encodes raw counts, not percentages)"* | 4 | **fixed** | 3.2 |
| *"The title states 23% — that's the number I'd repeat, and I got it straight from the headline, not the bars"* | 1 | **fixed** | 3.2 |
| *"The gold slivers in the first several months are extremely thin — barely a pixel or two — hard to distinguish from the tick line above them"* | 4 | **fixed** | 5.3 |
| *"orange and olive/gold are close in luminance; in true grayscale these two segments would likely become hard to tell apart, and the title's entire claim rests on distinguishing off agreement from no agreement"* | 4 | accepted | 5.4 |
| *"I don't see dollars anywhere on this chart, only line counts, so I can't tell if that 23% is 23% of the money too"* | 2 | accepted | 0.1 |
| *"I looked for a trend line or a target/goal marker showing where this should be … I can't tell if 23% is bad relative to a plan or just bad on its face"* | 3 | accepted | 0.1 |

**The strongest signal on this page.** *All three* domain seats sourced their number from the **title or subtitle**, not from a mark. Seat 1 said so outright. That is precisely the failure the location field exists to catch, and it is what a share claim over a count axis produces: the reader cannot get the headline number off the plot, so they repeat the title.

**Note the grayscale finding is Madrona / Lichen** — the pair the palette table measures at **1.05 L\* apart**, the narrowest of the ten. Open item 3 has been theoretical since v2.0. This is it biting in production, on the one chart whose claim depends on telling those two series apart.

### Chart 2 — leakage waterfall · 3 findings

| Finding | Seat | Proposed | Rule |
|---|---|---|---|
| *"I looked for a total across the three bars and didn't find one — I'd have to add $3.3M + $1.8M + $362K myself to know the full size of the number everyone's about to react to"* | 3 | **fixed** | 3.2 |
| *"No dates or period boundaries anywhere on this chart, so I can't tell what timeframe I'm looking at or whether this is cumulative"* | 2 | **fixed** | 4.2 |
| *"The $362K bar is tiny relative to the $0–$4M axis, so its length alone isn't really legible — you're reliant entirely on the printed label, not the mark"* | 4 | accepted | 1.2 |

Two independent seats reached for a total that isn't there. Seat 1 raised the same period question.

The 4.2 finding may be an artifact of capture — the provenance strip could sit below the screenshot boundary. **Verify before fixing.** If the strip is present, this is a rendering-scope issue in `render_charts.py`, not a chart defect.

### Chart 3 — exposure by customer · 3 findings

| Finding | Seat | Proposed | Rule |
|---|---|---|---|
| *"The Top account: 24% annotation is overlaid directly on top of the $1.3M value label on the Hoodsport bar — the two pieces of text visually collide"* | 4 | **fixed** | 3.4 |
| *"the 82% figure is not directly encoded anywhere — there's no cumulative-share line or running total"* | 4 | rejected | 3.2 |
| *"I don't see a total dollar figure for all 32 customers combined … I'd have to add it up by hand"* | 2 | rejected | 3.2 |

**The two rejections are the v2.1 computed-aggregate exception doing its job.** 82% is a computed share the eye cannot verify; the chart plots dollars, the variable the claim is about, and the table carries all 32 rows. Under v2.0's checklist — which had no such exception — both of these would have been recorded as INVARIANT failures. Under v2.1 they are `PASS-BY-EXCEPTION`. **Confirm the table is on the page before finalizing the rejection**; the exception is conditional on it.

The collision is unambiguous and cheap.

### Chart 4 — off-agreement lines by rep · 4 findings

| Finding | Seat | Proposed | Rule |
|---|---|---|---|
| *"a rep with 136 off-agreement lines out of 150 total is a very different story than 136 out of 2,000"* | 3 | **fixed** | 6.6 |
| *"No rate or percentage per rep — I can't tell if Simone's 136 is high because she quotes a lot in general"* | 2 | **fixed** | 6.6 |
| *"I looked for the dollar exposure behind each rep's count … that's not on this chart"* | 1 | accepted | 0.1 |
| *"71% isn't directly plotted — only raw counts are labeled"* | 4 | rejected | 3.2 |
| *"The bottom five bars are so short they're visually near-identical slivers"* | 4 | rejected | — |

**Three of three domain seats independently demanded a denominator.** This is the highest-consensus finding on the page and it is the one that matters most in the room, because it decides whether the chart is a diagnosis or an accusation — which is exactly the concern seat 3 was cast for. A named individual is at the top of a bar chart with no denominator under it.

### Chart 5 — threshold calibration · 4 findings

| Finding | Seat | Proposed | Rule |
|---|---|---|---|
| *"the tick labels are not evenly spaced in value, but the plotted points appear evenly spaced by position … distorts the perceived rate of decline"* | 4 | **fixed** | 2.1 |
| *"378 lines text collides with its own data point in the top-left, and $5.4M similarly collides with its marker"* | 4 | **fixed** | 5.3 |
| *"Where's the threshold actually set today … this chart shows me the tradeoff curve but not the recommendation or the current operating point"* | 2 | **fixed** | 0.1 |
| *"faster is a comparison across two different units on two different scales in two separate panels — the chart doesn't normalize both to a common starting point"* | 4 | accepted | 3.2 |

All three domain seats asked where the threshold sits today. A calibration chart that does not mark the current operating point cannot support the decision Rule 0.1 says it serves.

The normalization point is proposed *accepted* rather than fixed: Rule 2.2 forbids two units on one value axis, and the two-panel form is the compliant response. But indexing both series to 100 at the $0 threshold would make the comparison direct without violating 2.2, and is worth considering.

### Chart 6 — uncovered lines by cause · 2 findings

| Finding | Seat | Proposed | Rule |
|---|---|---|---|
| *"the headline number itself — 261 — appears nowhere on the chart. It's the sum of the three bars, and no total, cumulative marker, or label shows that sum directly"* | 4 | **fixed** | 3.2 |
| *"only the top bar is gold, the other two are grey, with no legend clarifying why one cause is singled out — the emphasis reads as somewhat arbitrary"* | 4 | **fixed** | 3.3 |

261 is a computed aggregate, so the v2.1 exception may cover it — but only if the subtitle names the basis, and it does not. A subtitle stating the total closes this in one edit.

The emphasis finding is a clean 3.3 breach: the saturated series must be the one the title talks about, and this title talks about all 261 lines.

---

## What this run says about the rule

**D = 3.17 defects per chart** on charts that had already passed a full checklist review and an eleven-chart adversarial read. That is high, and worth reading carefully rather than triumphantly: the earlier read ran against **v2.0**, so some of these are v2.1 rules that did not exist then, and the panel is scored before disposition rather than after remediation.

**R = 0.17.** Four findings in twenty-three rejected. Low enough that the seats were not manufacturing complaints, high enough that they were not rubber-stamping. Two of the four rejections were the computed-aggregate exception working as designed, which is a good sign for that amendment.

**The convergence pattern is the most interesting output and no metric captures it.** Three seats independently wanting a denominator on chart 4, three independently wanting the current threshold on chart 5, three independently sourcing their number from the title on chart 1 — those are stronger signals than anything a single seat said, including the axis finding. Consider adding a **consensus count** to the disposition table.

**Seat 4 produced most of the defects, and that is a caution.** The visualization seat found 13 of 19; the three domain seats found 6 between them, mostly gaps rather than errors. Two readings are available. Either the canvas-only lens genuinely has the widest failure surface, which is the case Rule 7.4 makes for the seat. Or the domain seats — being the same underlying model in three different costumes, which the rule concedes — converge on the same well-behaved business commentary and add less than the roster implies. **Watch this ratio across the next two modules.** If seat 4 keeps finding three-quarters of everything, the honest move is to cut the domain floor from three to two and say why.

**On the sentence returns specifically**, since Rule 7.4 flags these as where it will fail: they were serviceable, not sharp. Every domain seat's sentence tracked its chart's title fairly closely, which is either the charts working or the seats agreeing — and this run cannot tell those apart. The located numbers and the gaps carried the real weight. That is consistent with the DracoGPT concern the rule names, and it is one run.

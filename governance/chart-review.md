# Chart Review — Cascadia Deal Desk

*Run against **CHART-REVIEW.md v2.0** (Cascadia design system v2.0, August 2026).
Reviewer: Claude, 2026-08-01. Eleven charts across two pages.*

> **Synthetic data, seeded generator. Simulated — not real company data.**

---

## Verdict

**SHIP. No INVARIANT failures. Preference score 10, recorded and justified below.**

Third pass. All three original invariant failures are closed.

| # | Rule | Status |
|---|---|---|
| 1 | **5.1** | **CLOSED** — keyboard navigator built for the six charts the v2.1 amendment identifies. |
| 2 | **2.3.3** | **CLOSED** — mark-size validation run against Szafir's model. |
| 3 | **7.1** | **CLOSED** — adversarial read completed on all eleven charts. |

Under Rule 7.3, a nonzero preference score may ship provided the score and its
justification are recorded. Both are below.

### 5.1 closed — a keyboard navigator, built into the design system

Rule 5.1's layer-3 trigger was amended (v2.1) to key on **what the chart adds over its
table** rather than on series and point counts. Applying it here: five charts are
covered by their tables, because a ranking or a magnitude is exactly what a sorted table
states — exposure by state, exposure by customer, lines by rep, no-agreement by cause,
product mix. Six are not, because their finding is shape, sequence, or an interval
relationship: match status by month, threshold calibration, the margin small multiples,
price gap over time, margin over time, and the agreement timeline.

Those six now carry `cascadiaNavigator()`, which lives in
`cascadia-echarts-theme.js` rather than in this module — Rule 5.1 is a system
capability, and the next Cascadia module inherits it.

**The build.** ECharts renders to canvas, which is not in the DOM, so the structure is a
sibling element driven off the same arrays the chart and its data table already use —
the Data Navigator pattern (Elavsky, Nadolskis & Moritz, IEEE VIS 2023), where
navigation rules are decoupled from input modality so keyboard, screen reader and switch
drive one structure.

**One tab stop per chart, not one per datum.** Chartability is explicit that a `tabindex`
on every mark is the wrong build: *"Interactive elements must have a tab stop, while
non-interactive elements must not."* Arrow keys move a cursor inside that single stop.
The whole exception page carries 27 focusable elements, not several hundred.

Bindings, fixed across the system: Down descends chart → series → point, Up ascends,
Left/Right move between siblings, Home/End jump to first/last, Enter gives full detail,
Escape returns to chart level. **The cursor is bounded** — at a boundary it announces
"End of Priced off agreement" rather than wrapping silently.

**Sighted keyboard users get a visual cursor too.** Moving to a point dispatches
`highlight` and `showTip` on the underlying chart, so the tooltip follows the keyboard.
On the small-multiples grid, where there are twelve separate chart instances, the cursor
is a panel outline instead. The spoken string and the visible string are identical, so
the two experiences do not diverge.

Verified by keyboard, not by inspection. A representative traversal:

```
focus      Chart navigator ready. Down arrow to enter.
ArrowDown  Series 1 of 3: Priced to agreement. 24 points. 2,316 lines over the period.
ArrowDown  Point 1 of 24. August 2024: 85 lines
ArrowRight Point 2 of 24. September 2024: 83 lines
Enter      Priced to agreement, October 2024: 90 lines
ArrowUp    Series 1 of 3: Priced to agreement. 24 points...
ArrowRight Series 2 of 3: Priced off agreement. 24 points. 426 lines over the period.
End        Point 24 of 24. July 2026: 11 lines
ArrowRight End of Priced off agreement.          <- bounded, no silent wrap
Escape     Chart level. 3 series. Down arrow to enter.
```

And on the timeline, where the finding is supersession:

```
Enter      BIS-2665, 2024-06-28 to 2026-01-29: A0326, superseded as of 2026-08-01,
           2024-06-28 to 2026-01-29, agreed $449.73, superseded by A0327
```

**Months are spoken in full** in the navigator ("August 2024") rather than in the axis
abbreviation, because an axis label is optimised for a glance and a screen reader is not
glancing.

### 2.3.3 closed — the palette was run against Szafir's model

The check Rule 2.3.3 requires was never run because the design system had never run
it. It has now been, against the five Cascadia hues.

The a*-axis noticeable-difference requirement scales sharply with mark size: a 50px
swatch needs 7.0 units, a 2px stroke needs 11.5 (1.6x), and a 6px point needs 18.5
(2.6x). Against that:

- **At 2px stroke — the only small mark this module draws — all ten pairs pass.**
- **The two hues actually used at 2px pass by a wide margin**: Evergreen against
  Madrona at 6.6 JND, and each against Rain at 2.7 and 3.9.
- **At 6px point, two pairs fall below 1 JND on the a* axis**: Glacier/Lichen (0.86)
  and Lupine/Lichen (0.68). This module draws no 6px points, so it is unaffected.

**A design-system finding falls out of this and should not be lost.** Rule 2.3.4
designates Evergreen / Glacier / Lichen as the all-pairs trio for small symmetric
marks — and **Glacier/Lichen is one of the two pairs that goes marginal at 6px**. The
trio was validated for colour-vision safety at swatch size; it was not validated at the
mark size the rule assigns it to. Any future scatter plot using the trio needs this
re-checked first.

*Caveat on method, stated because it bounds the claim: this applies the a*-axis
component of Szafir's model only. The published model normalises L*, a* and b*
separately and combines them, and I do not have the L* and b* coefficients. Both
flagged pairs carry very large b* separation (85 and 86 units), which the full
three-axis model would very likely rescue. Read the 6px flags as "re-check before
use", not as "fails".*

### 7.1 closed — and it was worth every minute

The adversarial read ran on all eleven charts, using readers with no project context,
asked to describe the marks before reading the title. **It found problems on every
chart**, including two more Rule 3.2 invariant breaches of the same class as the first.

Everything it found is listed in "Second pass findings" below. Twenty-one changes came
out of it, including two chart redesigns, one theme defect affecting every future
module, and three silent-cap or mislabelling faults.

## What was reviewed

**Class:** all detailed charts. No signature charts on either page.
**Quadrant:** both pages are **exploratory** (reader-operated controls). Under Rule 6.11
each page's default loading view was additionally run against **Checklist A** in full.

| # | Chart | Page | Relationship | Form |
|---|---|---|---|---|
| 1 | Match status by month | index | change over time | stacked bar |
| 2 | Exposure by state | index | magnitude | ranked bar |
| 3 | Exposure by customer | index | ranking | ranked bar |
| 4 | Off-agreement lines by rep | index | ranking | ranked bar |
| 5 | Threshold calibration | index | distribution | line |
| 6 | No governing agreement by cause | index | ranking | ranked bar |
| 7 | Margin small multiples | customer | change over time | small multiples |
| 8 | Realized vs agreed price | customer | change over time | 2-series line |
| 9 | Realized vs agreed margin | customer | change over time | 2-series line |
| 10 | Product mix | customer | ranking | ranked bar |
| 11 | Agreement timeline | customer | change over time | custom timeline |

**States reached** (Rule 7.3 requires at least three, including one empty and one
single-entity, before any verdict on an interactive chart):

- default / unfiltered — both pages
- single entity — Hoodsport Instruments (index), Emerald Ridge Electronics (customer)
- empty — Hoodsport @ $50K threshold from 2026-06-01 (index, 0 rows);
  Emerald Ridge @ 2026-07-30 → 07-31 (customer, 0 lines)
- threshold sweep — $0 through $50K in twelve steps
- narrow viewport — 360 CSS px, both pages
- **degraded** — ECharts unavailable; both pages fall back to their data tables

---

## INVARIANT failures

### 1. Rule 5.1 — no keyboard layer. *CLOSED on the third pass — see Verdict.*

*Original finding, retained for the record:*

Rule 5.1 requires three access layers, and makes layer 3 mandatory for any chart with
more than one series or more than 20 data points. Every chart here qualifies.

**Built:** layer 1 (an authored `aria-label` on each chart container, L1 + L2 only per
Rule 5.2) and layer 2 (a real `<table>` of the underlying data for every chart, in the
DOM, reachable by keyboard through a focusable `<summary>`). The exception table's
column headers are focusable and sortable by Enter/Space.

**Not built:** a focusable DOM structure over the individual data points, with the
system's fixed Up/Down/Left/Right/Home/End bindings and bounded-cursor announcements.

A keyboard user can reach every number on these pages. What they cannot do is navigate
the *chart* — move series to series and point to point — which is what Rule 5.1 actually
requires, and what the research behind it (Zong et al., EuroVis 2022) found blind readers
rate materially more useful than a table alone.

**This is a genuine gap, not a technicality.** ECharts renders to canvas, which is not in
the DOM, so the layer has to be built as a sibling structure — the Data Navigator pattern
(Elavsky, Nadolskis & Moritz, IEEE VIS 2023). `aria: { decal }` and `aria-label`, which
this module does set, are explicitly not a substitute.

**Resolved by doing both of the first two.** Rule 5.1 was amended (v2.1) to key on what
the chart adds over its table, which narrowed the scope from eleven charts to six — and
the navigator was then built for those six. The amendment narrowed the work; it did not
excuse it, and it was not written to.

### 2. Rule 2.3.3 — palette not validated at mark size. *CLOSED on the second pass — see Verdict.*

*Original finding, retained for the record:*

The categorical palette was validated as large swatches. Rule 2.3.3 requires the pairwise
check to be re-run at **40 px block, 2 px stroke and 6 px point**, because perceived colour
difference falls off sharply on small marks (Szafir, IEEE TVCG 2018 — 13 of 18 ColorBrewer
ramps failed to hold 1 JND at ordinary web mark sizes).

This module draws **2 px strokes** in the small multiples and the two line charts. Those
are exactly the sizes the rule exists for.

Mitigating, and worth recording: the thin-stroke charts use only **two** saturated hues
(Evergreen and Madrona) against a Rain band, never four or five, and every series carries a
direct label. The risk this rule guards against is largely absent by construction.

**Closed.** The model was run; all pairs pass at 2px stroke and this module draws no
6px points. The residual finding — that the all-pairs trio contains a pair that goes
marginal at 6px — is recorded in the Verdict and belongs to the design system.

### 3. Rule 7.1 — adversarial read. *CLOSED on the second pass — all 11 charts.*

*Original finding, retained because it is the reason the second pass happened:*

Rule 7.1 requires that someone who does not know the finding say what they see first, and
that the chart be viewed in a second arrangement.

**Completed on charts 7 and 9** using a reader with no context about the project, the
data, or the intended conclusion — an imperfect substitute for a human, and a real one:
it had no access to the brief and was asked to describe the marks before reading the title.

**It found a Rule 3.2 INVARIANT breach I had passed.** Chart 9's title read *"Every line
priced to agreement, and margin still fell 6.8pp — cost moved, not price."* The reader's
response: there is no compliance series and no cost series anywhere on that plot, so
neither half of the claim is checkable from the marks. Both were assertions laid over the
canvas. That is exactly the failure Rule 3.2 exists to catch, and I had not caught it.

Six changes came out of that single read:

| Found | Change |
|---|---|
| Title claimed compliance and causation, neither visible | Title now claims only what the marks carry; compliance moved to the subtitle as a stated figure; causation moved to the method block |
| Annotation asserted "the gap never opens" while a gap visibly opened in autumn | Annotation now states the measured maximum separation |
| Value axis auto-started at zero, so a 6.8pp fall read as noise against ±4pp monthly swing | Axis cropped to the data range (permitted — the title makes a change claim, not a ratio claim) |
| "Realized" and "At agreed" end labels printed on top of each other | Offset ±11 px |
| Eleven grey ghost lines per panel read as texture; the highlighted line's position in the field was unreadable in 8 of 12 panels | Replaced with the field's min–max envelope band |
| Small multiples had no time axis at all, and no stated claim | Endpoint month labels added; a claim sentence and a four-item key added above the grid |

**Nine charts had not had this read at the time.** They have now. See "Second pass
findings" below — it returned problems on every one of them.

---

## Scored preference violations — total 24

| Rule | Chart | Weight | Finding | Justification recorded |
|---|---|---:|---|---|
| **1.3** | 8, 9 | 5 + 5 | Value-axis height fixed at 300 px rather than banked to 45° | Weak justification, recorded as such. The two panels are a stacked pair sharing an x-axis under Rule 2.2, and banking them independently would give them different heights and break the pairing. A shared banked height computed across both series is the correct fix and was deferred. **Revisit before the portfolio page ships.** |
| **2.7** | 7 | 4 | Small-multiple panel order is declared in the section prose, not in the grid's own subtitle | The grid has no subtitle element. The naive reader could not recover the ordering logic from the grid itself and tested four hypotheses before giving up. Order is by quoted value, plus a stated substitution — the rule wants that where the eye lands. |
| **2.4** | 1–11 | 3 | Zero gridlines throughout | Not earned anywhere: every chart carries data labels or a tooltip, and no reader task here involves decoding a value off the axis while scanning. Recorded as a deliberate pass on the option, not an oversight. |
| **5.5** | 3 | 5 | Exception table scrolls horizontally between 620 px and ~1100 px | Below 620 px it degrades to a card list and above ~1100 px it fits. In the band between, eleven columns scroll sideways inside the card. WCAG 1.4.10 exempts content requiring two-dimensional layout, and the card list satisfies the narrow case, but the middle band is a real seam. |
| **8.x** | 7 | 2 | Panel headers state compliance % and trend pp, neither recoverable from the panel marks | The panels show margin over time only. The two figures are labels, not readings. They are correct and sourced, but a reader cannot verify them from the panel, which is 3.2's logic applied one level down. |

---

## Checklist results

Recorded per rule across all eleven charts. `N/A` where the check does not apply to the
form or class. Rules not listed passed on every chart.

**Layer 0 — Brief.** 0.1 PASS (decision, horizon, audience and action recorded in the
build brief). 0.2 PASS (both pages declare exploratory; default views run against
Checklist A). 0.3 PASS (all detailed).

**Layer 1 — Selection.** 1.1 PASS — every chart declares its relationship, rendered in the
card above the plot, and each matches its title's claim. 1.2 PASS — every quantitative
comparison uses position on a common scale; no chart encodes a comparison by area, angle
or saturation. 1.3 **FAIL(5) ×2** (charts 8, 9); N/A on 1, 2, 3, 4, 6, 10, 11 (bar and
timeline forms); PASS on 5 and 7. 1.4 N/A — no chart declares the correlation relationship,
and no title on either page asserts a mechanism the data cannot support.

**Layer 2 — Construction.** 2.1 PASS — every bar chart starts at zero; the two cropped
axes (8, 9) are line charts whose titles make change claims, which the rule permits, and
neither crop reverses visual ordering. 2.2 PASS — no secondary axis anywhere; price and
margin are deliberately two stacked panels for exactly this reason. 2.3a–2.3b PASS.
**2.3.3 FAIL (INVARIANT)**. 2.3.4 PASS — thin-stroke charts use two hues, within the
three-hue cap. 2.3.5 PASS — maximum three encoded categories on any single chart, under
the cap of four. 2.3.6 PASS-BY-EXCEPTION — Rain measures 2.45:1 and every Rain series
carries a direct label or an axis label at ≥4.5:1, which is the written exception.
2.4 FAIL(3), justified above. 2.5 PASS — no gradients, shadows, rounded caps, gauges or
dressed KPI tiles; `aria.decal` was found painting texture over every bar during review
and the theme default was corrected to off. 2.6 N/A — no part-to-whole chart uses a pie or
donut; exposure by state is a sorted bar. 2.7 PASS on 2, 3, 4, 6, 10 (value-descending);
**FAIL(4)** on 7; N/A on 1, 5, 8, 9, 11 (time order). 2.8 PASS — no rotated text anywhere.
2.9 PASS — all visible labels ≤3 significant figures with abbreviated units; full precision
in tooltips and tables.

**Layer 3 — Explanation.** 3.1 PASS — every chart carries a complete-sentence finding at
the top, and every filtered chart recomputes it. 3.2 PASS **after remediation** — was
FAIL on chart 9; see failure 3. Re-checked on all eleven: each title's claim is now
recoverable from its own marks. 3.3 PASS — one saturated series per chart with context in
Rain and direct labels, plus the annotation and colour-match halves of the focus treatment;
chart 1 is PASS-BY-EXCEPTION as a genuine three-series comparison whose title is about the
comparison. 3.4 PASS — every chart carries one primary annotation at the mark its claim
depends on, with redundant (positional) linkage. 3.5 PASS — ranked bars are sorted so the
head is adjacent, which affords the comparison every ranking title claims. 3.6 PASS — no
legends; every series identified by a direct or axis label.

**Layer 4 — Disclosure.** 4.1 PASS — no zero-fill anywhere; months without quotes render
as gaps with `connectNulls: false`, and the small-multiples key names them. 4.2 PASS —
one provenance strip per chart, verified stable across repeated re-renders at every filter
state (theme v2.0's idempotent `cascadiaProvenance`; the v1.0 helper appended a duplicate
on each render and would have failed this). 4.3 PASS — the synthetic-data disclosure sits
above the first number on both pages, and every chart's strip carries it. 4.4 PASS **after
remediation** — a customer selection with no other filter left the strip reading
"unfiltered", meaning a filtered view could be screenshotted carrying a strip describing
the whole dataset. That is precisely the failure 4.4 exists to prevent. Fixed and
re-verified. 4.5 N/A — every value is exact by construction; no forecasts or estimates.

**Layer 5 — Access.** **5.1 PASS** — layers 1 and 2 on all eleven charts; layer 3 on the
six the v2.1 trigger identifies. Verified by keyboard traversal, including boundary
announcement and the visual cursor. 5.2 PASS, **improved on the
second pass** — descriptions were L1 + L2 only, which over-read the rule. 5.2 forbids L4
interpretation, because blind readers rank it least useful; it does not forbid **L3 shape**,
which is exactly what sight gives a reader and what a data table cannot carry. Five charts
now carry an explicit shape clause ("a steep head and a long tail", "at or near zero with
N distinct downward excursions"). Still no L4 anywhere. 5.3 PASS — 12 px text floor
throughout, 2 px focus rings at ≥3:1 never clipped, 24 px minimum control targets, reflow
verified at 360 px with no horizontal overflow on either page. 5.4 FAIL-risk noted, not
scored — the pages pass monochrome because no chart relies on hue alone, but the palette's
own grayscale weakness is a design-system item. 5.5 FAIL(5) on chart 3, justified above;
PASS elsewhere. 5.6 PASS — `prefers-reduced-motion` honoured in both the theme and the
stylesheet. 5.7 PASS — `color-scheme: light` declared; no dark palette attempted.

**Layer 6 — Interaction.** 6.1 PASS — both pages open author-driven with a fixed,
unfiltered overview above the controls; neither lands in a blank awaiting-selection state.
6.2 PASS — small multiples on shared scales with the field's envelope as context.
6.3 N/A — no animation beyond ECharts' default transition, which is suppressed under
reduced motion. 6.4 PASS — every filtered title recomputes and was checked for `NaN`,
`undefined` and zero-row output at reachable states. 6.5 PASS. 6.6 PASS — the threshold
control states rows shown, rows hidden, the dollars hidden, and the approved exceptions
excluded, in visible text. 6.7 PASS — verified: six re-renders produce exactly one strip.
6.8 PASS — empty states are named and explain which filter emptied them. 6.9 PASS — colour
slots are not re-dealt on filter. 6.10 **not implemented**, recorded — filter state is not
encoded in the URL, so a reader cannot send a colleague the exact view. PREFERENCE 4,
deliberately deferred to Part C; noted here rather than scored, since the page is not yet
published.

**Layer 7 — Process.** **7.1 PASS** — completed on all eleven charts across two rounds;
findings and resolutions listed above. 7.2 PASS — every chart on both pages is
model-generated and was run through the full checklist including the Layer 1 selection
rules the theme cannot enforce.

---

## Second pass findings — all eleven charts

**Rule 3.2 breaches (invariant, all fixed):**

| Chart | Claim that was not on the plot | Resolution |
|---|---|---|
| Threshold calibration | *"Half the exposure sits in the 82 largest lines"* — the y-axis was line **count**; dollars were plotted nowhere | Rebuilt as **two stacked panels** sharing the threshold axis, count above and exposure below (Rule 2.2 — different units cannot share a value axis). The finding is now visible: count falls far faster than dollars, which is the calibration argument |
| Realized vs agreed price | *"quoted 1.3% below agreed price on average"* — the agreed series was invisible for 23 of 24 months, and the one measurable gap was −20.5% | **Chart replaced.** It plotted volume-weighted price per unit across a customer's whole range, mixing $400 and $50,000 parts, so the mean tracked whatever was cheap and high-volume. Now plots the **percent gap to agreed** on covered lines, which is scale-free |
| Match status by month | *"held near a quarter"* — measured at ~20% by a reader counting pixels, and "held" implied a stability the 15–31% monthly range contradicts | Now states the actual level (23%) and the range, and claims only the trend the plot shows |

**Silent caps and mislabelling (all fixed):**

- Agreement timeline printed **"17 windows" while rendering 14 rows** — a silent cap. Now reports windows shown, discloses how many parts and agreements are not shown, and points to the table.
- The same title said **"2 superseded" while a third bar read `expired`** in identical grey, so the colour channel was not invertible. Both statuses are now named and counted.
- The method block **promised carets on clamped bars that did not exist**. A reader correctly identified that bar length — the primary encoding of a timeline — was meaningless for 11 of 14 rows because they were clamped to both edges. Carets now render at both clamped ends, and the subtitle states how many windows extend past the range.
- The customer and margin charts **dropped months with no quotes from the axis entirely**, compressing time and producing an axis that read Aug, Nov, Feb, May, Aug, **Dec**. The axis is now built from the full selected range so a quiet month is a visible gap (Rule 4.1) rather than a removed one.

**Theme defects (fixed in `cascadia-echarts-theme.js`, affects every future module):**

- `cascadiaAnnotation` rendered a **6px filled circle in the series colour** at its anchor. Two independent readers mistook it for a data point. Removed; Rule 3.4's redundant linkage is now carried by proximity, which the rule explicitly sanctions.
- Annotation labels carried a **filled paper-coloured halo box** that occluded the marks beneath them — one reader reported "a pale pink stub that looks like data" eating part of a bar, and a damaged data label. Replaced with a glyph outline, which gives the same legibility without covering anything.
- `aria.decal` was **on by default**, painting hatching and checkerboard across every categorical series. Off by default now; available per chart for the case it is built for.

**Other fixes:** the customer-exposure annotation was **clipped mid-word** at the canvas edge; the rep annotation was drawn **over the second bar**; grey was doing two jobs on the customer chart (below-cut and pooled remainder) and the pooled bar is now explicitly named; the "80%" claim was rounding 81.8% down and now states the real figure; the product-mix annotation read "Margin here: 52.0%" directly under a title claiming "52% of quoted value", which a reader flagged as a probable wiring bug — reworded.

**Preference violations resolved:** panel ordering moved into the grid's own subtitle
(2.7); the exception table's horizontal scroll eliminated at every width by folding two
derivable columns, with the card list taking over below 1040px (5.5); filter state
encoded in the URL so a view can be shared, which now agrees with what the provenance
strip claims (6.10); the margin chart banked to its data (1.3).

**Remaining preference score 10:** the price panel holds a fixed height so the stacked
pair keeps a common frame (1.3, 5); gridlines deliberately not earned anywhere (2.4, 3);
small-multiple panel headers state compliance and trend figures not recoverable from the
panel marks (2, and see the Rule 3.2 amendment below).

**A methodology limitation, recorded because it bounds the evidence:** every reader
reported that they **could not avoid reading the title**, because it is rendered into the
image as the largest text on the canvas. The "first sentence" answers are therefore
softer evidence than a real human pass where the title can be covered. What the readers
found — clipped words, phantom marks, unverifiable claims — holds regardless. **When you
run this on people, crop the title out of the image first.**

## A rulebook defect this review surfaced

Not a chart failure — a conflict between two INVARIANTs, which under v2's own enforcement
clause is a defect in the design system rather than in the artifact.

**Rule 6.2 requires small-multiple panels to carry the other series as ghost lines.
Rule 3.3 requires that any series in Rain carry a direct label.** Twelve ghost lines per
panel cannot each be labelled, and labelling them would destroy the panel.

The envelope band adopted here resolves it in practice — a band is unidentified aggregate
context ("the field"), not an identified series, so there is nothing for a label to name.
But that reading is not written down, and Rule 3.3 has no exception covering it.

**Proposed amendment to 3.3:** the direct-label requirement applies to Rain used as an
*identified* context series. Unidentified aggregate context — an envelope, a range band, a
density — is exempt, provided the aggregate is named once in a key. Adding it to the
design system's open items.

---

## Running Rule 7.1 on the remaining nine

Fresh eyes are the hard part of this rule for a solo builder, and the honest position is
that a reader with no context is a **partial** substitute for a person, not an equivalent
one. It cannot be surprised, bored, or in a hurry. What it can do is refuse to read the
title first, and on two charts that was enough to find an INVARIANT breach.

A ten-minute pass, per chart:

1. Show the chart image alone. No project context, no brief, no title visible if you can
   crop it.
2. Ask for one sentence describing what they see, formed from the marks.
3. Ask what drew their eye first.
4. **Then** show the title and ask: is there any part of this claim you could not have
   seen yourself?
5. Record the answer to 4 verbatim. That is the Rule 3.2 check, and it is the one that
   caught chart 9.

If their first sentence is not the title's claim, the chart is not carrying the finding —
the title is, and that is a 3.2 failure wearing a different hat.

---

*Reviewed against CHART-REVIEW.md v2.0. Any INVARIANT failure is DO NOT SHIP regardless of
preference score. Synthetic data, seeded generator. Simulated — not real company data.*

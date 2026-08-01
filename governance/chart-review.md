# Chart Review — Cascadia Deal Desk

*Run against **CHART-REVIEW.md v2.0** (Cascadia design system v2.0, August 2026).
Reviewer: Claude, 2026-08-01. Eleven charts across two pages.*

> **Synthetic data, seeded generator. Simulated — not real company data.**

---

## Verdict

**DO NOT SHIP — 3 INVARIANT failures, preference score 24.**

The two pages are complete, correct against the validation report, and free of console
errors at every state reached. They do not ship yet, and the reasons are worth stating
plainly rather than softening:

| # | Rule | Failure | Scope |
|---|---|---|---|
| 1 | **5.1** | No keyboard-navigable structure over the data points | All 11 charts |
| 2 | **2.3.3** | Palette has never been validated at the mark sizes actually drawn | All 11 charts |
| 3 | **7.1** | Adversarial read completed on 2 of 11 charts | 9 charts |

Failures 2 and 3 are the interesting ones: **2 is inherited from the design system, not
caused by this module**, and **3 found a real INVARIANT breach on the two charts it did
cover**, which is the strongest available argument for closing it on the other nine.

Preference score 24 is recorded below with justification per item. Under Rule 7.3 a
nonzero preference score may ship; an INVARIANT failure may not.

---

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

### 1. Rule 5.1 — no keyboard layer over the data points. *All 11 charts.*

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

**Options, in order of my preference:**

1. **Build it.** A shared navigator over the eleven charts, driven off the same arrays the
   tables already render. Real work, and it would be the most differentiating thing on the
   page — almost nobody in BI ships this.
2. **Amend Rule 5.1** to make layer 3 mandatory only above a stated complexity, with
   layers 1 and 2 as the floor. Defensible, and it should then be written into the rule
   with its reasoning, not applied silently.
3. **Ship with the failure recorded here and disclosed on the page.** Honest, and weaker
   than either of the above.

### 2. Rule 2.3.3 — palette not validated at mark size. *All 11 charts.*

The categorical palette was validated as large swatches. Rule 2.3.3 requires the pairwise
check to be re-run at **40 px block, 2 px stroke and 6 px point**, because perceived colour
difference falls off sharply on small marks (Szafir, IEEE TVCG 2018 — 13 of 18 ColorBrewer
ramps failed to hold 1 JND at ordinary web mark sizes).

This module draws **2 px strokes** in the small multiples and the two line charts. Those
are exactly the sizes the rule exists for.

Mitigating, and worth recording: the thin-stroke charts use only **two** saturated hues
(Evergreen and Madrona) against a Rain band, never four or five, and every series carries a
direct label. The risk this rule guards against is largely absent by construction.

**This is design-system open item 2 and this module cannot close it.** It blocks on
re-running Szafir's model against the Cascadia hues, which is a design-system task.

### 3. Rule 7.1 — adversarial read incomplete. *9 of 11 charts.*

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

**Nine charts have not had this read.** Given what it returned on two, that is not a
formality. See "Running Rule 7.1" at the end.

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

**Layer 5 — Access.** **5.1 FAIL (INVARIANT)**, see above. 5.2 PASS — every `aria-label`
is construction plus statistics, with no interpretation. 5.3 PASS — 12 px text floor
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

**Layer 7 — Process.** **7.1 FAIL**, see above. 7.2 PASS — every chart on both pages is
model-generated and was run through the full checklist including the Layer 1 selection
rules the theme cannot enforce.

---

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

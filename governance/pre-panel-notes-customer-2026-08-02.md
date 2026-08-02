# Pre-panel notes — Deal Desk customer page

**Written 2026-08-02, before rendering `customer.html` and before any seat was spawned.**

Drafted by Claude, not by Aaron. That weakens N: I have read this module's `governance/chart-review.md`, so these predictions are informed by a prior review Aaron also has. **Aaron to strike anything he would not have predicted himself** — every struck line moves a panel defect from "already known" to "novel," so striking makes N *more* honest, not less flattering.

What I know going in: four charts — `chart-price` (change over time), `chart-margin` (change over time), `chart-mix` (ranking), `chart-timeline` (change over time) — plus whatever the page's second-pass rebuild left behind. I have not looked at any of them.

---

## Predicted defects

**P1 · Timeline bar length is meaningless for most rows.** The second pass found 11 of 14 agreement windows clamped to both ends of the date range, so bar length — the primary encoding of a timeline — carries no duration information. Carets were added at clamped ends. **Prediction: a blind reader still reads bar length as duration**, because a caret is a small mark and length is a strong one.

**P2 · The margin chart's causal claim is still not visible.** The original title — *"Every line priced to agreement, and margin still fell 6.8pp — cost moved, not price"* — was rewritten after the first blind read. The underlying problem is that neither compliance nor cost is plotted. **Prediction: whatever the title now says about *why* margin moved is still not checkable from the marks.**

**P3 · Percent-gap-to-agreed is scale-free and readers will want dollars.** The realized-vs-agreed chart was replaced with a percent gap because the old volume-weighted price mixed $400 and $50,000 parts. Correct fix. **Prediction: at least one domain seat asks what the gap is worth in dollars**, because a 2% gap on a $50K part and on a $400 part are not the same conversation.

**P4 · The envelope band on small multiples is unexplained at first read.** Ghost lines were replaced with a min–max envelope band, named once in a key. **Prediction: a seat reads the band as a confidence interval, a forecast range, or a second series** rather than as "the rest of the field."

**P5 · The mix ranking has no denominator.** Same failure the index page's rep chart had — a ranked count with no base to read it against.

**P6 · Numbers will be sourced from titles, not marks.** On the index page all three domain seats quoted the headline from the title or subtitle rather than from a mark. **Prediction: this repeats on at least one customer-page chart.**

**P7 · Madrona and Lichen merge in grayscale.** They sit 1.05 L\* apart, the narrowest pair in the palette. If any customer-page chart uses both as encoded categories, the grayscale check fails.

**P8 · Period and as-of are unclear on at least one chart.** Two seats raised this on the index page's waterfall. Likely a provenance strip falling outside the screenshot boundary rather than a real absence — **verify capture before treating it as a defect.**

---

## Explicitly not predicted

Recording these so that if the panel finds them, they count as novel and I cannot claim afterwards that I saw them coming:

- Anything about the **price chart**. I know nothing about its current form beyond its declared relationship.
- Any **axis-construction** defect of the chart-5 class — a scale that is not a scale. I have no reason to expect another one, and I would be extrapolating from a single instance if I claimed otherwise.
- Any **cross-chart contradiction** — two charts on this page disagreeing about the same quantity.
- Any **interaction or empty-state** defect. This panel captures the default loading state only.
- Anything the **timeline's status colours** do. The second pass fixed a superseded/expired collision; whether the fix reads is not something I can predict.

/**
 * Cascadia ECharts theme — implements VIZ-PRINCIPLES.md as defaults.
 * v1.0 · Aaron Robbins · Robbins Analytics
 *
 * Usage:
 *   <script src="cascadia-echarts-theme.js"></script>   // after echarts
 *   const chart = echarts.init(el, 'cascadia');
 *
 * Helpers (optional but part of the system):
 *   cascadiaTitle(finding, subtitle)   → Rule 1 title block
 *   cascadiaProvenance(el, {source, asOf, flags}) → Rule 14 strip (DOM, below chart)
 *   CASCADIA.colors / CASCADIA.seq / CASCADIA.allPairsTrio
 */
(function (root) {
  'use strict';

  var C = {
    evergreen: '#1E7A4C',
    glacier:   '#4C8BC0',
    madrona:   '#C05A2E',
    lupine:    '#7B68AE',
    lichen:    '#9C7A20',
    rain:      '#9AA6A0',
    basalt:    '#232B27',
    slateMoss: '#5B6660',
    mist:      '#E4E7E3',
    paper:     '#FCFCFA'
  };

  var SERIF = '"Source Serif 4", Georgia, "Times New Roman", serif';
  var SANS  = '"Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif';

  var theme = {
    // Rule 7: fixed slot order, never cycled.
    color: [C.evergreen, C.glacier, C.madrona, C.lupine, C.lichen],

    backgroundColor: C.paper,

    textStyle: { fontFamily: SANS, color: C.basalt },

    // Rule 1: serif finding + sans subtitle in secondary ink.
    title: {
      textStyle:    { fontFamily: SERIF, fontSize: 17, fontWeight: 600, color: C.basalt },
      subtextStyle: { fontFamily: SANS,  fontSize: 12, color: C.slateMoss },
      left: 0, top: 0, itemGap: 6
    },

    grid: { left: 8, right: 90, top: 64, bottom: 30, containLabel: true },

    // Rule 3: legends off by default — direct-label instead (see demo).
    legend: { show: false },

    // Category axis: quiet line, no ticks fencing the data. Rule 2/9.
    categoryAxis: {
      axisLine:  { show: true, lineStyle: { color: C.mist, width: 1 } },
      axisTick:  { show: false },
      axisLabel: { color: C.slateMoss, fontSize: 11, fontFamily: SANS, rotate: 0 }, // Rule 12
      splitLine: { show: false }
    },

    // Value axis: no axis line, no gridlines unless earned (Rule 2).
    valueAxis: {
      axisLine:  { show: false },
      axisTick:  { show: false },
      axisLabel: { color: C.slateMoss, fontSize: 11, fontFamily: SANS },
      splitLine: { show: false },       // opt back in per chart when Rule 2 is met
      splitNumber: 4
    },
    logAxis:  { splitLine: { show: false } },
    timeAxis: {
      axisLine:  { show: true, lineStyle: { color: C.mist } },
      axisTick:  { show: false },
      axisLabel: { color: C.slateMoss, fontSize: 11 },
      splitLine: { show: false }
    },

    // Rule 9: flat marks. 2px lines, no shadows, square bar caps.
    line: {
      itemStyle: { borderWidth: 0 },
      lineStyle: { width: 2 },
      symbol: 'circle', symbolSize: 1, showSymbol: false,
      smooth: false,                    // honest geometry — no beziers
      emphasis: { lineStyle: { width: 2.5 } }
    },
    bar: {
      itemStyle: { borderRadius: 0 },   // Rule 9: flat ends
      barMaxWidth: 42
    },
    scatter: { symbolSize: 9 },

    // Rule 8: full precision lives here, labels stay rounded.
    tooltip: {
      backgroundColor: '#FFFFFF',
      borderColor: C.mist, borderWidth: 1,
      textStyle: { color: C.basalt, fontFamily: SANS, fontSize: 12 },
      axisPointer: {
        lineStyle: { color: C.rain, width: 1 },
        crossStyle: { color: C.rain, width: 1 }
      },
      extraCssText: 'box-shadow: none; border-radius: 2px; padding: 8px 10px;'
    },

    // Gauges are banned (Rule 9) — styled to look broken on purpose is not
    // an option in a theme, so: do not use series type "gauge" or "pie".
    pie:   { label: { show: true } },   // present only so accidental use is visible in review
    gauge: {}
  };

  // ---- helpers ---------------------------------------------------------

  /** Rule 1 title block: finding sentence + metric subtitle. */
  function cascadiaTitle(finding, subtitle) {
    return {
      text: finding,
      subtext: subtitle || '',
      textStyle:    theme.title.textStyle,
      subtextStyle: theme.title.subtextStyle,
      left: 0, top: 0, itemGap: 6
    };
  }

  /** Rule 14 provenance strip, appended as DOM directly under the chart el. */
  function cascadiaProvenance(el, opts) {
    var host = (typeof el === 'string') ? document.getElementById(el) : el;
    if (!host) return null;
    var strip = document.createElement('div');
    strip.className = 'cascadia-provenance';
    strip.setAttribute('role', 'note');
    strip.style.cssText =
      'display:flex;align-items:baseline;gap:7px;margin:2px 0 0 2px;' +
      'font:10.5px/1.5 ' + SANS + ';color:' + C.slateMoss + ';';
    var tick = document.createElement('span');
    tick.style.cssText =
      'display:inline-block;width:3px;height:11px;background:' + C.evergreen +
      ';flex:0 0 3px;position:relative;top:1px;';
    var parts = [opts.source ? 'Source: ' + opts.source : null,
                 opts.asOf   ? 'as of ' + opts.asOf     : null,
                 opts.flags  || 'no adjustments'];
    var text = document.createElement('span');
    text.textContent = parts.filter(Boolean).join(' · ');
    strip.appendChild(tick);
    strip.appendChild(text);
    host.insertAdjacentElement('afterend', strip);
    return strip;
  }

  var API = {
    colors: C,
    palette: theme.color.slice(),
    allPairsTrio: [C.evergreen, C.glacier, C.lichen], // Rule 15 cap for scatter/small multiples
    seq: ['#8FBA9F', '#65A583', '#3D8D63', '#1E7A4C', '#0F5535'],
    diverging: { neg: C.madrona, mid: C.rain, pos: C.evergreen },
    serif: SERIF,
    sans: SANS,
    theme: theme,
    title: cascadiaTitle,
    provenance: cascadiaProvenance
  };

  if (root.echarts && root.echarts.registerTheme) {
    root.echarts.registerTheme('cascadia', theme);
  }
  root.CASCADIA = API;
  root.cascadiaTitle = cascadiaTitle;
  root.cascadiaProvenance = cascadiaProvenance;

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : this);

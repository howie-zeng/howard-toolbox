"""CSS and JavaScript bundles for the deal report.

Rendered into ``<style>`` and ``<script>`` blocks by ``builder.build_html``.
The JS handles page navigation, per-page section toggles, Vega spec rendering
(deferred until libs load), summary-page metric tabs, and the heatmap toggle.
"""
from __future__ import annotations

from .theme import ACCENT, BG, BORDER, CARD_BG, TEXT, TEXT_DIM


# Exact-pinned Vega libs, shared by the main document and every iframe sub-page.
# Unpinned majors drift independently on the CDN; a mismatched trio silently
# breaks rendering (vega-util internals undefined -> 0 charts). Pinning one
# compatible triple keeps all pages in lockstep.
VEGA_CDN = (
    '<script src="https://cdn.jsdelivr.net/npm/vega@5.30.0"></script>'
    '<script src="https://cdn.jsdelivr.net/npm/vega-lite@5.23.0"></script>'
    '<script src="https://cdn.jsdelivr.net/npm/vega-embed@6.29.0"></script>'
)


CSS = f"""\
body {{
  font-family: 'Segoe UI Variable Text', 'Inter', -apple-system, BlinkMacSystemFont,
               'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
  margin: 0; padding: 0; background: {BG}; color: {TEXT}; font-size: 13px;
  -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
}}

.header {{ padding: 24px 32px 0 32px; }}
h1 {{
  color: {TEXT}; text-align: center; letter-spacing: 0.2px;
  border-bottom: 2px solid {ACCENT}; padding-bottom: 10px;
  font-size: 22px; margin: 0 0 16px 0;
}}
/* Section headers: shaded band (accent tint) instead of a bare left border. */
h2 {{
  color: {TEXT}; margin-top: 26px; margin-bottom: 12px;
  background: linear-gradient(90deg, rgba(43,122,181,0.10), rgba(43,122,181,0.02) 70%);
  border-left: 4px solid {ACCENT}; border-radius: 0 6px 6px 0;
  padding: 8px 14px; font-size: 16px; letter-spacing: 0.2px;
}}
h3 {{ color: {TEXT}; margin: 14px 0 8px 0; font-size: 14px; }}
/* Sub-group header inside a section: small caps label + hairline rule, quieter
   than the shaded h2 band so the hierarchy reads section > group > chart. */
.sub-head {{
  display: flex; align-items: center; gap: 10px;
  margin: 20px 0 2px; color: {TEXT_DIM};
  font-size: 11.5px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; white-space: nowrap;
}}
.sub-head::after {{ content: ""; flex: 1; border-top: 1px solid {BORDER}; }}
.meta {{
  background: {CARD_BG}; padding: 12px 16px; border-radius: 6px;
  margin: 14px 0; border: 1px solid {BORDER};
}}
.meta p {{ margin: 4px 0; font-size: 13px; color: {TEXT}; }}

/* ---- KPI cards ---- */
.kpi-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px; margin: 16px 0;
}}
.kpi-card {{
  background: {CARD_BG}; border: 1px solid {BORDER};
  border-top: 3px solid {ACCENT};
  border-radius: 8px; padding: 14px; text-align: center;
  box-shadow: 0 1px 3px rgba(20, 40, 60, 0.06);
}}
.kpi-card .kpi-label {{
  font-size: 10px; font-weight: 600; color: {TEXT_DIM};
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;
}}
.kpi-card .kpi-value {{
  font-size: 20px; font-weight: 700; color: {TEXT};
  font-variant-numeric: tabular-nums;
}}
.kpi-card .kpi-sub   {{ font-size: 10px; color: {TEXT_DIM}; margin-top: 3px; }}

/* ---- Page navigation ---- */
.content {{ padding: 0 32px 32px 32px; }}
.page-nav {{
  position: sticky; top: 0; z-index: 999; background: {BG};
  padding: 12px 32px 16px 32px;
  display: flex; gap: 6px; flex-wrap: wrap;
  border-bottom: 2px solid {BORDER};
}}
.page-nav a {{
  display: inline-block; padding: 9px 22px; background: #fff; color: {TEXT_DIM};
  text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: 600;
  border: 1px solid {BORDER}; cursor: pointer; user-select: none;
  transition: all 0.15s;
}}
.page-nav a.active {{
  background: {ACCENT}; color: #fff; border-color: {ACCENT};
  box-shadow: 0 1px 4px rgba(43,122,181,0.18);
}}
.page-nav a:hover:not(.active) {{ background: #edf2f7; color: {TEXT}; }}
.report-page {{ display: none; }}
.report-page.active {{ display: block; }}

/* ---- Section toggle bar (per page) ---- */
.section-toggle {{
  background: {CARD_BG}; border-bottom: 1px solid {BORDER};
  padding: 8px 12px; margin-bottom: 12px;
  display: flex; gap: 6px; flex-wrap: wrap; align-items: center;
  border-radius: 4px;
}}
.section-toggle .label {{
  font-size: 12px; font-weight: 600; color: {TEXT_DIM};
  margin-right: 4px; white-space: nowrap;
}}
.section-toggle a {{
  display: inline-block; padding: 4px 12px;
  background: {ACCENT}; color: #fff; text-decoration: none;
  border-radius: 3px; font-size: 11px; font-weight: 600;
  border: 1px solid {ACCENT}; cursor: pointer; user-select: none;
  transition: all 0.15s;
}}
.section-toggle a:hover {{ opacity: 0.85; }}
.section-toggle a.off {{
  background: {CARD_BG}; color: {TEXT_DIM};
  border-color: {BORDER}; text-decoration: line-through;
}}
.report-section {{ display: none; }}
.report-section.visible {{ display: block; }}

/* ---- Charts ---- */
/* Columns >= one chart wide, so a too-narrow row collapses to one column
   instead of overlapping fixed-width charts. */
.chart-row {{
  display: grid; gap: 16px; margin: 12px 0;
  grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
}}
.chart-row > .chart-box {{ min-width: 0; }}
/* SVGs carry a viewBox, so width:100% + height:auto makes each chart fill its
   box instead of sitting at its natural pixel size. */
.chart-box svg {{ display: block; width: 100%; height: auto; }}
/* Vega renders text with its own generic sans-serif; align chart typography
   with the page font (inline style needs !important to override). */
.chart-box svg text, .mtx-chart svg text {{
  font-family: 'Segoe UI Variable Text', 'Inter', 'Segoe UI', sans-serif !important;
}}
/* Cohort legend — below the chart (so toggling never resizes it), shown by JS
   on show_cohorts. */
.cohort-legend {{
  display: none; flex-wrap: wrap; gap: 5px 16px; justify-content: center;
  margin-top: 10px; font-size: 11px; color: {TEXT_DIM};
}}
.cohort-legend.visible {{ display: flex; }}
.cl-item {{ display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }}
.cl-item:hover {{ color: {TEXT}; }}
.cl-item.active {{ font-weight: 700; color: {TEXT}; }}
.cl-sw {{ width: 18px; height: 3px; border-radius: 2px; display: inline-block; flex: none; }}
.chart-box {{
  background: {CARD_BG}; padding: 14px; margin: 12px 0;
  border-radius: 8px; border: 1px solid {BORDER}; overflow: visible;
  border-top: 3px solid rgba(43, 122, 181, 0.45);
  box-shadow: 0 1px 3px rgba(20, 40, 60, 0.06);
}}
/* vega-embed defaults to inline-block (caps growth at the svg's intrinsic
   width); force full-width so the svg fills the box. */
.chart-box .vega-embed {{ display: block; width: 100%; overflow: visible !important; }}
.chart-box .vega-embed summary {{ display: none !important; }}

/* ---- Tables ---- */
table.stats {{
  width: 100%; border-collapse: collapse; font-size: 12px; margin: 10px 0;
}}
table.stats th {{
  background: #e8f0f7; color: {TEXT}; padding: 8px 12px;
  text-align: right; font-weight: 600;
  border-bottom: 2px solid {ACCENT}; white-space: nowrap;
}}
table.stats th:first-child {{ text-align: left; }}
table.stats td {{
  padding: 6px 12px; text-align: right; border-bottom: 1px solid {BORDER};
}}
table.stats td:first-child {{
  text-align: left; font-weight: 500; color: {TEXT};
}}
table.stats tr:hover {{ background: #f1f3f5; }}
table.stats tr.total-row td {{
  font-weight: 700; color: {TEXT};
  border-top: 2px solid {ACCENT}; border-bottom: 2px solid {BORDER};
  background: #e9ecef;
}}
body.no-gradient td[data-gradient] {{ background: none !important; }}
.table-box {{
  background: {CARD_BG}; padding: 14px; margin: 12px 0;
  border-radius: 8px; border: 1px solid {BORDER}; overflow-x: auto;
  border-top: 3px solid rgba(43, 122, 181, 0.45);
  box-shadow: 0 1px 3px rgba(20, 40, 60, 0.06);
}}

/* ---- Metric tabs (summary page chart switcher) ---- */
.metric-tabs {{ display: flex; gap: 4px; margin: 8px auto; justify-content: center; }}
.metric-tabs button {{
  padding: 4px 14px; font-size: 11px; font-weight: 600;
  border: 1px solid {BORDER}; border-radius: 3px; cursor: pointer;
  background: {CARD_BG}; color: {TEXT_DIM}; transition: all 0.15s;
}}
.metric-tabs button.active {{
  background: {ACCENT}; color: #fff; border-color: {ACCENT};
}}
.metric-tabs button:hover:not(.active) {{ background: #e9ecef; }}
.metric-chart {{ display: none; }}
.metric-chart.active {{ display: block; }}

/* ---- Heatmap toggle ---- */
.gradient-toggle {{
  display: inline-block; margin: 8px 0 8px 12px;
  padding: 4px 14px; background: {ACCENT}; color: #fff;
  border: none; border-radius: 3px; font-size: 11px; font-weight: 600;
  cursor: pointer;
}}
.gradient-toggle.off {{
  background: {CARD_BG}; color: {TEXT_DIM}; border: 1px solid {BORDER};
}}

/* ---- Fit-ratio chips (projected / actual) ---- */
.chip {{
  display: inline-block; padding: 2px 9px; border-radius: 10px;
  font-size: 11px; font-weight: 700; font-variant-numeric: tabular-nums;
}}
.chip.ok   {{ background: #e2f2e8; color: #22633c; }}
.chip.warn {{ background: #fcf0dc; color: #92600f; }}
.chip.bad  {{ background: #fae3df; color: #a03528; }}
.chip.na   {{ background: #eef1f4; color: {TEXT_DIM}; }}

/* ---- Sim-Performance-vs-Actual page ---- */
.note {{ font-size: 13px; color: {TEXT_DIM}; margin: 8px 0 18px; line-height: 1.55; }}
.mtx-legend {{ font-size: 13px; color: {TEXT_DIM}; margin: 2px 0 12px; line-height: 1.6; }}
/* Transition matrices: HTML header + natural-size grid (NOT stretched to fill,
   so the cell/label fonts stay at their true px size on wide pages). */
.mtx-row {{ display: flex; flex-wrap: wrap; gap: 20px; margin: 12px 0; }}
/* Each panel fills half the row (grows/shrinks with the page); min-width:0 lets
   the flex child shrink so the Vega container width can be measured. */
.mtx-panel {{
  background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;
  border-top: 3px solid rgba(43, 122, 181, 0.45);
  box-shadow: 0 1px 3px rgba(20, 40, 60, 0.06);
  padding: 12px 16px 14px; flex: 1 1 340px; min-width: 0;
}}
.mtx-head {{ margin-bottom: 8px; display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }}
.mtx-title {{ font-size: 14px; font-weight: 700; color: {TEXT}; }}
.mtx-sub {{ font-size: 11px; color: {TEXT_DIM}; }}
.mtx-chart {{ width: 100%; line-height: 0; }}
/* width:"container" → Vega sets the svg's px width itself; do NOT force width:100%
   (that would re-introduce scaling). Just let it lay out at the measured width. */
.mtx-chart .vega-embed {{ display: block; width: 100%; }}
.mtx-chart svg {{ display: block; height: auto; max-width: 100%; }}
.mtx-chart .vega-embed summary {{ display: none !important; }}
/* Second-level (from-state) segmented control for the transition-rate tabs. */
.tabs {{
  display: inline-flex; gap: 4px; margin: 10px 0 22px; padding: 5px;
  background: #eef2f6; border: 1px solid {BORDER}; border-radius: 12px; flex-wrap: wrap;
}}
.l2-btn {{
  border: none; background: transparent; border-radius: 8px; cursor: pointer;
  color: {TEXT_DIM}; font-size: 14px; padding: 9px 20px; font-weight: 600;
  letter-spacing: .2px; transition: background .12s, color .12s, box-shadow .12s;
}}
.l2-btn:hover {{ background: #e2e8ef; color: {TEXT}; }}
.l2-btn.active {{ background: #fff; color: {ACCENT}; box-shadow: 0 1px 3px rgba(20,40,60,0.16); }}
.l2-panel {{ display: none; animation: l2fade .18s ease; }}
.l2-panel.active {{ display: block; }}
@keyframes l2fade {{ from {{ opacity: 0; transform: translateY(3px); }} to {{ opacity: 1; transform: none; }} }}
/* One-step-ahead overlay toggle (below the transition-rate tabs). */
.os-toggle {{
  margin: 6px 0 4px; padding: 10px 14px; background: {CARD_BG};
  border: 1px solid {BORDER}; border-radius: 6px; font-size: 12.5px; color: {TEXT_DIM};
}}
.os-toggle label {{ cursor: pointer; display: flex; gap: 8px; align-items: baseline; }}
.os-toggle input {{ cursor: pointer; }}
.os-toggle b {{ color: {TEXT}; font-weight: 600; }}

"""


JS = r"""
(function () {
  function onReady(cb) {
    if (document.readyState !== 'loading') cb();
    else document.addEventListener('DOMContentLoaded', cb);
  }
  function libsReady() { return !!(window.vega && window.vegaLite && window.vegaEmbed); }
  var VIEWS = {};   // rendered Vega views, keyed by spec id (for resize-on-show)

  // -------------------------------------------------------------------
  // Top-level page navigation
  // -------------------------------------------------------------------
  function initPageNav() {
    var tabs = document.querySelectorAll('.page-nav a');
    tabs.forEach(function (tab) {
      tab.onclick = function (e) {
        e.preventDefault();
        var target = this.getAttribute('data-page');
        tabs.forEach(function (t) { t.classList.remove('active'); });
        this.classList.add('active');
        document.querySelectorAll('.report-page').forEach(function (p) {
          p.classList.toggle('active', p.id === target);
        });
        // width:"container" charts (transition matrices) measure width 0 while
        // their tab is hidden. Vega-Lite re-reads the container size only on a
        // window 'resize' event, so fire one once the page is visible + laid out
        // (rAF). This is exactly what manually resizing the window triggered.
        requestAnimationFrame(function () {
          window.dispatchEvent(new Event('resize'));
        });
      };
    });
  }

  // -------------------------------------------------------------------
  // Section toggles within a page
  // -------------------------------------------------------------------
  var SECTION_STATE = {};
  function initSectionToggles() {
    document.querySelectorAll('.section-toggle').forEach(function (bar) {
      var page = bar.closest('.report-page');
      if (!page) return;
      page.querySelectorAll('.report-section').forEach(function (s) {
        var key = s.getAttribute('data-section');
        SECTION_STATE[key] = true;
        s.classList.add('visible');
        var link = document.createElement('a');
        link.textContent = key;
        link.href = '#';
        link.setAttribute('data-section-btn', key);
        link.onclick = function (e) { e.preventDefault(); toggleSection(key); };
        bar.appendChild(link);
      });
    });
  }
  function toggleSection(key) {
    SECTION_STATE[key] = !SECTION_STATE[key];
    document.querySelectorAll('.report-section').forEach(function (s) {
      if (s.getAttribute('data-section') === key)
        s.classList.toggle('visible', SECTION_STATE[key]);
    });
    document.querySelectorAll('[data-section-btn]').forEach(function (btn) {
      if (btn.getAttribute('data-section-btn') === key)
        btn.classList.toggle('off', !SECTION_STATE[key]);
    });
  }

  // -------------------------------------------------------------------
  // Vega rendering
  // -------------------------------------------------------------------
  async function renderSpecs() {
    var node = document.getElementById('vega-specs');
    if (!node) return;
    var specs = JSON.parse(node.textContent || '[]');
    var views = VIEWS;
    for (var i = 0; i < specs.length; i++) {
      var entry = specs[i];
      var el = document.getElementById(entry.id);
      if (!el) continue;
      try {
        var res = await vegaEmbed(el, entry.spec, { actions: false, renderer: 'svg' });
        if (res && res.view) views[entry.id] = res.view;
      } catch (e) { console.error('Vega render error for ' + entry.id, e); }
    }
    // Cohort legends: show only while the chart's show_cohorts toggle is on
    // (wired after the render loop to avoid closure bugs).
    document.querySelectorAll('.cohort-legend').forEach(function (leg) {
      var view = views[leg.getAttribute('data-for')];
      if (!view) return;
      try {
        var apply = function (v) { leg.classList.toggle('visible', !!v); };
        apply(view.signal('show_cohorts'));
        view.addSignalListener('show_cohorts', function (n, v) { apply(v); });
      } catch (e) { /* no show_cohorts signal on this chart */ }
      // Interactive: click a legend item to bold its cohort line (toggle).
      leg.querySelectorAll('.cl-item').forEach(function (item) {
        item.addEventListener('click', function () {
          var c = item.getAttribute('data-cohort');
          var cur = null;
          try { cur = view.signal('hl_cohort'); } catch (e) { return; }
          var next = (cur === c) ? null : c;
          try { view.signal('hl_cohort', next).run(); } catch (e) {}
          leg.querySelectorAll('.cl-item').forEach(function (x) {
            x.classList.toggle('active', x.getAttribute('data-cohort') === next);
          });
        });
      });
    });
    window.__vegaRendered = true;
  }

  // -------------------------------------------------------------------
  // Summary-page metric tabs
  // -------------------------------------------------------------------
  function initMetricTabs() {
    document.querySelectorAll('.metric-tabs').forEach(function (bar) {
      var group = bar.getAttribute('data-chart-group');
      var btns = bar.querySelectorAll('button');
      btns.forEach(function (btn) {
        btn.onclick = function () {
          var metric = this.getAttribute('data-metric');
          btns.forEach(function (b) { b.classList.remove('active'); });
          this.classList.add('active');
          document.querySelectorAll('.metric-chart[data-chart-group="' + group + '"]')
            .forEach(function (c) {
              c.classList.toggle('active', c.getAttribute('data-metric') === metric);
            });
        };
      });
    });
  }

  // -------------------------------------------------------------------
  // Second-level tabs (Sim-Performance transition-rate from-state switcher)
  // -------------------------------------------------------------------
  function initL2Tabs() {
    document.querySelectorAll('.l2-btn').forEach(function (b) {
      b.onclick = function () {
        var t = b.getAttribute('data-tab');
        var scope = b.closest('.report-page') || document;
        scope.querySelectorAll('.l2-btn').forEach(function (x) {
          x.classList.toggle('active', x === b);
        });
        scope.querySelectorAll('.l2-panel').forEach(function (p) {
          p.classList.toggle('active', p.id === t);
        });
      };
    });
  }

  // -------------------------------------------------------------------
  // One-step-ahead overlay toggle (drives the showOS param on ctd1/ctp views)
  // -------------------------------------------------------------------
  function initOnestepToggle() {
    var chk = document.getElementById('os-toggle-chk');
    if (!chk) return;
    chk.addEventListener('change', function () {
      Object.keys(VIEWS).forEach(function (k) {
        try { VIEWS[k].signal('showOS', chk.checked).run(); } catch (e) {}
      });
    });
  }

  // -------------------------------------------------------------------
  // Summary-page heatmap toggle
  // -------------------------------------------------------------------
  function initGradientToggle() {
    document.querySelectorAll('.gradient-toggle').forEach(function (btn) {
      btn.onclick = function () {
        document.body.classList.toggle('no-gradient');
        this.classList.toggle('off');
        this.textContent = document.body.classList.contains('no-gradient')
          ? 'Heatmap Off' : 'Heatmap On';
      };
    });
  }

  // -------------------------------------------------------------------
  // Boot
  // -------------------------------------------------------------------
  onReady(function () {
    initPageNav();
    initSectionToggles();
    initMetricTabs();
    initL2Tabs();
    initOnestepToggle();
    initGradientToggle();
    (function wait() {
      if (!libsReady()) return setTimeout(wait, 50);
      renderSpecs();
    })();
  });
})();
"""

"""CSS and JavaScript bundles for the deal report.

Both are pure strings rendered into ``<style>`` and ``<script>`` blocks by
``builder.build_html``.  The JS handles:

- top-level page navigation (Aggregate / Summary)
- per-page section toggles (sticky toolbar of section pills)
- Vega spec rendering (one big JSON payload deferred until libs load)
- summary-page metric tabs (switching among Bal%/Avg Bal/RATE/FICO/DTI charts)
- summary-page heatmap on/off toggle
"""
from __future__ import annotations

from .theme import ACCENT, BG, BORDER, CARD_BG, TEXT, TEXT_DIM

CSS = f"""\
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto',
               'Helvetica Neue', Arial, sans-serif;
  margin: 0; padding: 0; background: {BG}; color: {TEXT}; font-size: 13px;
}}

.header {{ padding: 24px 32px 0 32px; }}
h1 {{
  color: {TEXT}; text-align: center;
  border-bottom: 2px solid {ACCENT}; padding-bottom: 10px;
  font-size: 22px; margin: 0 0 16px 0;
}}
h2 {{
  color: {TEXT}; margin-top: 24px; margin-bottom: 12px;
  border-left: 4px solid {ACCENT}; padding-left: 10px; font-size: 16px;
}}
h3 {{ color: {TEXT}; margin: 14px 0 8px 0; font-size: 14px; }}
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
  border-radius: 6px; padding: 14px; text-align: center;
}}
.kpi-card .kpi-label {{
  font-size: 10px; font-weight: 600; color: {TEXT_DIM};
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;
}}
.kpi-card .kpi-value {{ font-size: 20px; font-weight: 700; color: {TEXT}; }}
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
.chart-row {{ display: flex; gap: 16px; margin: 12px 0; }}
.chart-row > .chart-box {{ flex: 1; min-width: 0; }}
.chart-box {{
  background: {CARD_BG}; padding: 14px; margin: 12px 0;
  border-radius: 6px; border: 1px solid {BORDER}; overflow: visible;
}}
.chart-box .vega-embed {{ overflow: visible !important; }}
.chart-box .vega-embed summary {{ display: none !important; }}

/* ---- Tables ---- */
table.stats {{
  width: 100%; border-collapse: collapse; font-size: 12px; margin: 10px 0;
}}
table.stats th {{
  background: #e9ecef; color: {TEXT}; padding: 8px 12px;
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
  border-radius: 6px; border: 1px solid {BORDER}; overflow-x: auto;
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

"""


JS = r"""
(function () {
  function onReady(cb) {
    if (document.readyState !== 'loading') cb();
    else document.addEventListener('DOMContentLoaded', cb);
  }
  function libsReady() { return !!(window.vega && window.vegaLite && window.vegaEmbed); }

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
    for (var i = 0; i < specs.length; i++) {
      var entry = specs[i];
      var el = document.getElementById(entry.id);
      if (!el) continue;
      try {
        await vegaEmbed(el, entry.spec, { actions: false, renderer: 'svg' });
      } catch (e) { console.error('Vega render error for ' + entry.id, e); }
    }
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
    initGradientToggle();
    (function wait() {
      if (!libsReady()) return setTimeout(wait, 50);
      renderSpecs();
    })();
  });
})();
"""

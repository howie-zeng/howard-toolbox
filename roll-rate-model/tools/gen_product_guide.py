"""Generate a PDF guide: what to change when switching products or adding states."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem, KeepTogether,
)
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "output", "product_switch_guide.pdf")


def build():
    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    doc = SimpleDocTemplate(OUTPUT, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch,
                            leftMargin=0.75*inch, rightMargin=0.75*inch)

    styles = getSampleStyleSheet()
    s_title = styles["Title"]
    s_h1 = ParagraphStyle("H1", parent=styles["Heading1"], spaceAfter=6,
                           textColor=HexColor("#1a1a2e"))
    s_h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceAfter=4,
                           textColor=HexColor("#16213e"))
    s_h3 = ParagraphStyle("H3", parent=styles["Heading3"], spaceAfter=3)
    s_body = styles["BodyText"]
    s_code = ParagraphStyle("Code", parent=styles["Code"], fontSize=8,
                             leading=10, backColor=HexColor("#f4f4f4"),
                             borderPadding=4, spaceBefore=4, spaceAfter=4)
    s_warn = ParagraphStyle("Warn", parent=s_body,
                             textColor=HexColor("#cc0000"), fontName="Helvetica-Bold")
    s_note = ParagraphStyle("Note", parent=s_body,
                             textColor=HexColor("#0066cc"), fontName="Helvetica-Oblique")

    story = []

    # ── Title ──────────────────────────────────────────────────────
    story.append(Paragraph("Simulation Engine - Product Switch Guide", s_title))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "This guide covers every file and code location that must change when "
        "switching loan products, adding terminal states, or modifying cashflow types. "
        "Data processing (data_prep.py) is excluded - covered separately.",
        s_body))
    story.append(Spacer(1, 12))

    # ── Section 1: Architecture Overview ──────────────────────────
    story.append(Paragraph("1. Architecture Overview", s_h1))
    story.append(Paragraph(
        "The simulation has three layers. Config (JSON) drives the topology. "
        "Data prep loads models/matrices. Runner executes the Monte Carlo loop.",
        s_body))

    arch_data = [
        ["Layer", "File", "What It Controls"],
        ["Config", "config/default.json", "Statuses, transitions, severity, models, periods"],
        ["Data Prep", "simengine/data_prep.py", "Model loading, field maps, value maps, defaults"],
        ["Runner", "simengine/runner.py", "Cashflow generation, transition sampling, output"],
        ["Entry", "run.py / data_prep_for_sim.py", "CLI interface, config loading"],
    ]
    t = Table(arch_data, colWidths=[1*inch, 2.2*inch, 3.3*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f8f8f8")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    # ── Section 2: Config (default.json) ──────────────────────────
    story.append(Paragraph("2. Config: default.json", s_h1))
    story.append(Paragraph(
        "The config file is the primary place to define the product's status topology. "
        "Most changes start here.", s_body))

    story.append(Paragraph("2.1 status_to_roll", s_h2))
    story.append(Paragraph(
        "Defines valid transitions for each status. Each key is a from-status, "
        "and the list includes all statuses it can roll to (including staying). "
        "The first element is conventionally the 'stay' state.",
        s_body))
    story.append(Paragraph(
        '"status_to_roll": {\n'
        '  "C":   ["C", "D1M", "PIF", "LIQ"],\n'
        '  "D1M": ["D1M", "C", "D2M", "LIQ"],\n'
        '  ...\n'
        '}', s_code))
    story.append(Paragraph(
        "To add a new status (e.g. REFUND): add it to every list where it's reachable, "
        "and add a new key if loans can start in that status.", s_body))

    story.append(Paragraph("2.2 terminal_statuses", s_h2))
    story.append(Paragraph(
        'Statuses that end the simulation for a loan. Currently ["PIF", "LIQ"]. '
        "Once a loan enters a terminal status, no more cashflows are generated.",
        s_body))
    story.append(Paragraph(
        "To add a new terminal state: add it here AND add cashflow logic in runner.py "
        "(see Section 3.3).", s_warn))

    story.append(Paragraph("2.3 dq_buckets", s_h2))
    story.append(Paragraph(
        "Maps delinquency statuses to their CF_COL column names. "
        "Each entry is [count_col, balance_col].",
        s_body))
    story.append(Paragraph(
        '"dq_buckets": {\n'
        '  "D1M": ["dq30", "dq30_bal"],\n'
        '  "D2M": ["dq60", "dq60_bal"],\n'
        '  ...\n'
        '}', s_code))
    story.append(Paragraph(
        "If adding a D5M status, add a new entry here AND add matching columns "
        "to CF_COL in runner.py.", s_body))

    story.append(Paragraph("2.4 liq_severity", s_h2))
    story.append(Paragraph(
        "Loss-given-default as a fraction of balance. 1.0 = 100% loss, 0.60 = 60% loss. "
        "Used in runner.py line 150: loss = begin_bal * dm.liq_severity. "
        "Recovery = begin_bal - loss.",
        s_body))

    story.append(Paragraph("2.5 n_per", s_h2))
    story.append(Paragraph(
        "Number of monthly periods to simulate. 360 = 30 years. "
        "For shorter-term products (e.g. 60-month unsecured), "
        "reduce this to avoid wasted computation.",
        s_body))

    story.append(Paragraph("2.6 gam_models", s_h2))
    story.append(Paragraph(
        "List of R GAM model files to dump as coef .txt files. Each entry specifies "
        "from_status, output file, and a list of {path, to_status} models. "
        "The naming convention is from{FROM}_{TO} - this pattern is hardcoded in "
        "both data_prep.py and runner.py.",
        s_body))

    story.append(Paragraph("2.7 pmt_matrix_path", s_h2))
    story.append(Paragraph(
        "TSV file defining how many monthly payments occur for each (from, to) pair. "
        "Row = from_status, column = to_status. "
        "Value of -1 = special (PIF uses full payoff). "
        "Value of 0 = no payment. "
        "Must include rows/columns for every status in status_to_roll.",
        s_body))

    story.append(PageBreak())

    # ── Section 3: Runner (runner.py) ─────────────────────────────
    story.append(Paragraph("3. Runner: runner.py", s_h1))
    story.append(Paragraph(
        "The runner contains the core simulation loop. These are the hardcoded "
        "elements that must change per product.", s_body))

    story.append(Paragraph("3.1 CF_COL - Cashflow Columns (line 18)", s_h2))
    story.append(Paragraph(
        "Defines every column in the cashflow output array. Order matters - "
        "CF_DICT maps names to indices. All downstream analysis depends on this.",
        s_body))
    story.append(Paragraph(
        'CF_COL = [\n'
        '  "cnt", "begin_bal", "end_bal", "int_pmt", "sch_int", "prin_pmt",\n'
        '  "pif_bal", "net_recov", "loss", "liq_bal",\n'
        '  "dq30", "dq60", "dq90", "dq120",\n'
        '  "pif_cnt", "liq_cnt",\n'
        '  "dq30_bal", "dq60_bal", "dq90_bal", "dq120_bal",\n'
        '  "recov", "cost2srvc", "sfee_pmt", "bk",\n'
        '  "cf", "cf_delta", "int_rate", "irr", "npv",\n'
        ']', s_code))
    story.append(Paragraph(
        "To add new cashflow types (e.g. refund_bal, refund_cnt): "
        "append to this list. Existing column indices remain stable.",
        s_body))

    story.append(Paragraph("3.2 Softmax Transition (line 36)", s_h2))
    story.append(Paragraph(
        "The multinomial logit transition function. For each possible to-status, "
        "computes exp(model_score), normalizes via softmax, applies dial multipliers, "
        "then samples via cumulative probability.",
        s_body))
    story.append(Paragraph(
        "Key formula: P(stay) = 1 / (1 + sum(exp(scores))). "
        "The stay probability is the residual after all transition probabilities. "
        "Model names follow pattern: from{clean_from}_{clean_to}.",
        s_body))
    story.append(Paragraph(
        "This logic is product-agnostic - it works with any status topology "
        "as long as models exist. No changes needed when adding states.",
        s_note))

    story.append(Paragraph("3.3 Terminal State Cashflow Logic (line 143)", s_h2))
    story.append(Paragraph(
        "CRITICAL: This is the main place to edit when adding terminal states.",
        s_warn))
    story.append(Paragraph(
        "Currently two terminal branches:", s_body))

    term_data = [
        ["Status", "Principal", "Interest", "Balance", "Columns Set"],
        ["PIF", "= begin_bal (full payoff)", "= begin_bal * r_m (1 month)", "= 0",
         "pif_cnt=1, pif_bal=begin_bal"],
        ["LIQ", "= 0 (no payment)", "= 0 (no payment)", "= 0",
         "liq_cnt=1, liq_bal=begin_bal,\nloss=bal*severity,\nrecov=bal-loss, net_recov=bal-loss"],
    ]
    t = Table(term_data, colWidths=[0.5*inch, 1.5*inch, 1.5*inch, 0.5*inch, 2.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("To add a REFUND terminal state, you would:", s_h3))
    story.append(Paragraph(
        '1. Add "REFUND" to terminal_statuses in config\n'
        '2. Add "refund_cnt" and "refund_bal" to CF_COL in runner.py\n'
        '3. Add an elif branch in run_cf_one (after the LIQ block):\n',
        s_body))
    story.append(Paragraph(
        'elif status_to == "REFUND":\n'
        '    refund_amt = begin_bal  # full refund\n'
        '    end_bal = 0.0\n'
        '    prin_paid = refund_amt\n'
        '    int_paid = 0.0\n'
        '    cf[per][ci["refund_cnt"]] = 1.0\n'
        '    cf[per][ci["refund_bal"]] = refund_amt', s_code))
    story.append(Paragraph(
        '4. Add a REFUND row in the payment matrix (all zeros)\n'
        '5. Add REFUND to status_to_roll for any status that can transition to it\n'
        '6. Train a GAM model for the transition (e.g. fromC_REFUND)', s_body))

    story.append(Paragraph("3.4 DQ Bucket Logic (line 161)", s_h2))
    story.append(Paragraph(
        "Non-terminal, non-PIF/LIQ statuses hit this branch. "
        "Looks up DQ_BUCKETS[status_to] and records count + balance in the "
        "appropriate CF_COL columns. Config-driven - just update dq_buckets in JSON.",
        s_body))

    story.append(Paragraph("3.5 Payment Computation (line 87)", s_h2))
    story.append(Paragraph(
        "Standard amortization: iterates num_pay times, computing int = bal * r_m, "
        "prin = pi_pmt - int. Balance floors at 0.01. "
        "num_pay comes from the payment matrix.",
        s_body))
    story.append(Paragraph(
        "For different payment structures (e.g. interest-only, balloon), "
        "modify _compute_payments or add an alternative function.",
        s_body))

    story.append(Paragraph("3.6 Hardcoded Constants", s_h2))
    const_data = [
        ["Constant", "Location", "Value", "Purpose"],
        ["r_m divisor", "line 119", "1200.0", "Annual rate -> monthly (12 months * 100)"],
        ["Balance floor", "line 99, 125", "0.01 / 0.1", "Stop sim when balance near zero"],
        ["Max loan age", "line 125", "480", "40-year hard stop (months)"],
        ["Numeric stability", "line 122", "1e-9", "Avoid div-by-zero in PMT calc"],
        ["Hash seed", "line 29", "FNV-1a", "Deterministic per-loan randomness"],
        ["CSV precision", "line 223", "6 decimals", "Output formatting"],
    ]
    t = Table(const_data, colWidths=[1.2*inch, 0.8*inch, 1*inch, 3.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f8f8f8")]),
    ]))
    story.append(t)

    story.append(PageBreak())

    # ── Section 4: Data Prep Constants ────────────────────────────
    story.append(Paragraph("4. Data Prep Constants (data_prep.py)", s_h1))
    story.append(Paragraph(
        "These are the non-processing constants that define the status universe. "
        "Full data processing refactor is out of scope for this guide.", s_body))

    story.append(Paragraph("4.1 STATUS_VALUE_MAP (line 40)", s_h2))
    story.append(Paragraph(
        "Maps raw input status strings to model status codes. "
        "If your new product uses different status labels in the input data, "
        "update this map. Does NOT need to change if status codes stay the same.",
        s_body))

    story.append(Paragraph("4.2 Default Fallbacks (lines 279-297)", s_h2))
    story.append(Paragraph(
        "DEFAULT_STATUS_TO_ROLL, DEFAULT_TERMINAL_STATUSES, DEFAULT_DQ_BUCKETS. "
        "These are used only if config doesn't specify them. "
        "Best practice: always specify in config, then these are irrelevant.",
        s_body))

    story.append(Paragraph("4.3 Model Name Pattern", s_h2))
    story.append(Paragraph(
        'Model names follow: f"from{FROM}_{TO}". This pattern is hardcoded in '
        "both data_prep.py (build_all_models) and runner.py (softmax_transition). "
        "Coef files must be named from{STATUS}.txt. "
        "Do not change this convention without updating both files.",
        s_warn))

    story.append(Paragraph("4.4 DataManager Fields", s_h2))
    story.append(Paragraph(
        "DataManager stores: models, pmt_matrix, status_to_roll, terminal_statuses, "
        "dq_buckets, liq_severity, n_per, dial_data. All loaded from config + input files. "
        "Adding a new terminal state config field (e.g. refund_recovery_rate) "
        "means adding it to DataManager and init_data_manager.",
        s_body))

    story.append(Spacer(1, 16))

    # ── Section 5: Known Bug ──────────────────────────────────────
    story.append(Paragraph("5. Known Issue: TERMINAL_STATUSES Import", s_h1))
    story.append(Paragraph(
        "runner.py imports TERMINAL_STATUSES as a module-level constant from data_prep.py. "
        "This means the config value (dm.terminal_statuses) is NOT used in the sim loop. "
        "The check at line 125 uses the hardcoded default set.",
        s_warn))
    story.append(Paragraph(
        "Fix: change runner.py line 125 to use dm.terminal_statuses instead of "
        "the module constant. This requires threading dm into the break condition.",
        s_body))

    story.append(Spacer(1, 16))

    # ── Section 6: Checklist ──────────────────────────────────────
    story.append(Paragraph("6. Product Switch Checklist", s_h1))

    checks = [
        ("config/default.json", [
            "Update status_to_roll with new status topology",
            "Update terminal_statuses if adding terminal states",
            "Update dq_buckets if adding DQ states",
            "Set liq_severity for new loss model",
            "Set n_per appropriate for product term",
            "Add gam_models entries for new transition models",
        ]),
        ("input/pmt_matrix.txt", [
            "Add rows/columns for every status in status_to_roll",
            "Set payment counts for each (from, to) pair",
        ]),
        ("runner.py", [
            "Add new columns to CF_COL if needed",
            "Add elif branch in run_cf_one for new terminal states",
            "Update _compute_payments if payment structure differs",
            "(Fix: use dm.terminal_statuses instead of module constant)",
        ]),
        ("data_prep.py", [
            "Update STATUS_VALUE_MAP if input labels differ",
            "Update DEFAULT_* fallbacks (optional if config is complete)",
            "Add fields to DataManager if new config params needed",
            "Update FIELD_VALUE_MAPS if categorical mappings change",
        ]),
        ("R Models", [
            "Train GAM models for each new transition",
            "Name coef output files as from{STATUS}.txt",
            "Ensure model names follow from{FROM}_{TO} pattern",
        ]),
    ]

    for file_name, items in checks:
        story.append(Paragraph(f"<b>{file_name}</b>", s_body))
        bullet_items = [ListItem(Paragraph(item, s_body)) for item in items]
        story.append(ListFlowable(bullet_items, bulletType="bullet", leftIndent=20))
        story.append(Spacer(1, 6))

    story.append(PageBreak())

    # ── Section 7: Example - Adding Refund ────────────────────────
    story.append(Paragraph("7. Worked Example: Adding a REFUND State", s_h1))
    story.append(Paragraph(
        "Suppose the product allows early refunds where the borrower gets their "
        "principal back. Here is every change needed:", s_body))
    story.append(Spacer(1, 8))

    steps = [
        ("Step 1: config/default.json",
         'Add "REFUND" to terminal_statuses.\n'
         'Add "REFUND" to status_to_roll for statuses that can refund (e.g. C, D1M).\n'
         'Optionally add a "refund_recovery_rate" config param.'),
        ("Step 2: input/pmt_matrix.txt",
         "Add a REFUND column (all zeros - no scheduled payments on refund).\n"
         "Add a REFUND row (all zeros - can't transition out of refund)."),
        ("Step 3: runner.py - CF_COL",
         'Add "refund_cnt" and "refund_bal" to CF_COL list.'),
        ("Step 4: runner.py - run_cf_one",
         'Add elif branch after LIQ block:\n\n'
         '  elif status_to == "REFUND":\n'
         '      prin_paid = begin_bal\n'
         '      int_paid = 0.0\n'
         '      end_bal = 0.0\n'
         '      cf[per][ci["refund_cnt"]] = 1.0\n'
         '      cf[per][ci["refund_bal"]] = begin_bal'),
        ("Step 5: R Model",
         "Train a GAM for the C->REFUND transition (fromC_REFUND).\n"
         "Dump coef to fromC.txt alongside existing models.\n"
         "Add to gam_models in config."),
        ("Step 6: Test",
         "Run data_prep_for_sim.py to verify field prep.\n"
         "Run simulation and check refund_cnt/refund_bal appear in output."),
    ]

    for title, desc in steps:
        story.append(KeepTogether([
            Paragraph(f"<b>{title}</b>", s_h3),
            Paragraph(desc.replace("\n", "<br/>"), s_body),
            Spacer(1, 8),
        ]))

    # ── Build ─────────────────────────────────────────────────────
    doc.build(story)
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    build()

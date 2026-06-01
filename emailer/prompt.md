I have a J.P. Morgan cashflow sheet in wide format. Each deal occupies several side-by-side 7-column blocks (Date, Balance, Principal, Interest, CPR, CDR, Severity), with a bold title row above each block like VERUS-221 B2 (B2) - Base Case (Forward). Each block has one scenario, and the same deal repeats once per scenario.

Create a new tab called LongFormat and reshape everything into long format with exactly these columns: purpose_name | bbg_name | poolid | scen | month | sbal | cpr | cdr | sev

Rules:

purpose_name: always JPM
bbg_name: the full deal name (I'll give you a mapping below)
poolid: the short code (I'll give you the mapping below)
scen: map the block's rate scenario — Base Case→Base, +200bps→ParallelUp200, -200bps→ParallelDn200, -300bps→ParallelDn300
month: the block's Date, normalized to the first day of the month
sbal: the Balance column
cpr / cdr / sev: the CPR / CDR / Severity columns
Remove every row where CPR = 0 (the origination month), so each series starts at the first real month
Deal mapping (poolid → bbg_name):

B3A → VERUS 2022-1 ENU → VISIO 2023-1 ...add the deals in this sheet...
Only map deals that actually appear in the sheet; ignore any in the list that aren't present, and tell me which were skipped. After building, confirm the row count, the distinct deals, and the distinct scenarios.


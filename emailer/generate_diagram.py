import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid Qt errors
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

def create_simulation_flowchart(output_path):
    # Setup figure
    fig, ax = plt.subplots(figsize=(12, 14))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis('off')
    
    # Style constants
    box_w = 4
    box_h = 1.2
    center_x = 5
    arrow_args = dict(fc="k", ec="k", head_width=0.2, head_length=0.3)
    
    # Helper to draw box
    def draw_box(x, y, text, color='#E6F3FF', edgecolor='#4A90E2', subtext=None):
        rect = patches.FancyBboxPatch((x - box_w/2, y - box_h/2), box_w, box_h,
                                    boxstyle="round,pad=0.2",
                                    linewidth=2, edgecolor=edgecolor, facecolor=color)
        ax.add_patch(rect)
        plt.text(x, y + (0.15 if subtext else 0), text, ha='center', va='center', fontsize=11, fontweight='bold', color='#333')
        if subtext:
             plt.text(x, y - 0.25, subtext, ha='center', va='center', fontsize=9, color='#555')
        return x, y

    # Helper to draw arrow
    def draw_arrow(x1, y1, x2, y2, text=None):
        ax.arrow(x1, y1, x2-x1, y2-y1, length_includes_head=True, **arrow_args)
        if text:
            plt.text((x1+x2)/2 + 0.2, (y1+y2)/2, text, ha='left', va='center', fontsize=9, style='italic', backgroundcolor='white')

    # 1. Inputs
    draw_box(center_x, 13, "Loan Level Dump (C++)", color='#D9EAD3', edgecolor='#6AA84F', subtext="WAC, FICO, LTV, Bal, etc.")
    draw_arrow(center_x, 12.2, center_x, 11.8)

    # 2. Bucketing
    draw_box(center_x, 11.2, "Bucketing Engine", subtext="Aggregates loans into Cohorts\n(Bucketing Rule)")
    draw_arrow(center_x, 10.4, center_x, 10.0)

    # 3. Month 1 Init
    draw_box(center_x, 9.4, "Month 1 Initialization", subtext="Calc Weighted Avg Features\nInitial CPR = Model(Static Features)")
    draw_arrow(center_x, 8.6, center_x, 8.2, text="Start Loop")

    # Container for Recursion
    rect = patches.Rectangle((1.5, 2.5), 7, 5.5, linewidth=2, edgecolor='#999', facecolor='none', linestyle='--')
    ax.add_patch(rect)
    plt.text(2.0, 7.7, "Recursive Month Loop (t = 2...60)", fontsize=10, fontweight='bold', color='#666')

    # 4. State Update
    draw_box(center_x, 7.0, "1. Update Dynamic State", subtext="Age += 1\nIncentive = WAC - PMMS(t)\nBurnout = f(Incentive History)")
    draw_arrow(center_x, 6.2, center_x, 5.8)

    # 5. Hazard Model
    draw_box(center_x, 5.2, "2. Hazard Model Application", subtext="Logit = Coefs * State\nSMM = Sigmoid(Logit)")
    draw_arrow(center_x, 4.4, center_x, 4.0)

    # 6. Balance & Factor
    draw_box(center_x, 3.4, "3. Balance & Count Evolution", color='#FFF2CC', edgecolor='#D6B656', 
             subtext="Bal(t) = Bal(t-1) * (1-SMM)\nLoanCount linked to Bal (Fixes LTV Drift)")
    
    # Loop back arrow
    ax.arrow(center_x - 2.2, 3.4, -1.5, 0, fc="k", ec="k", head_width=0, head_length=0) # Left out
    ax.arrow(center_x - 3.7, 3.4, 0, 3.6, fc="k", ec="k", head_width=0, head_length=0) # Up
    ax.arrow(center_x - 3.7, 7.0, 1.3, 0, fc="k", ec="k", head_width=0.2, head_length=0.3) # Back in
    plt.text(center_x - 4.2, 5.2, "Next Month", ha='center', va='center', rotation=90, fontsize=10)

    draw_arrow(center_x, 2.6, center_x, 2.2, text="End Horizon")

    # 7. Output
    draw_box(center_x, 1.6, "Simulation Results", color='#EAD1DC', edgecolor='#C27BA0', subtext="Cashflows, CPR Vectors,\nComparison vs Actuals")

    # Save
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=150)
    print(f"Diagram saved to {output_path}")

def create_crt_pipeline_diagram(output_path):
    fig, ax = plt.subplots(figsize=(15, 20))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 20)
    ax.axis('off')

    def draw_box(x, y, w, h, text, color='#E6F3FF', edgecolor='#4A90E2', subtext=None, fontsize=11):
        rect = patches.FancyBboxPatch((x - w/2, y - h/2), w, h,
                                      boxstyle="round,pad=0.15",
                                      linewidth=1.8, edgecolor=edgecolor, facecolor=color)
        ax.add_patch(rect)
        ty = y + (0.18 if subtext else 0)
        plt.text(x, ty, text, ha='center', va='center', fontsize=fontsize, fontweight='bold', color='#222')
        if subtext:
            plt.text(x, y - 0.28, subtext, ha='center', va='center', fontsize=9, color='#555')

    def draw_arrow(x1, y1, x2, y2, label=None, label_side='right'):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                     arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.8))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            offset = 0.2 if label_side == 'right' else -0.2
            ha = 'left' if label_side == 'right' else 'right'
            plt.text(mx + offset, my, label, ha=ha, va='center', fontsize=8.5,
                     style='italic', color='#555',
                     bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.85))

    # ── Row 1: Step 1 + LLPA (side by side) ──
    lx, rx = 4, 11
    draw_box(lx, 19, 5.0, 1.0, "Step 1: Data Extraction", color='#D9EAD3', edgecolor='#6AA84F', subtext="crt_get_data.R")
    draw_box(rx, 19, 4.5, 1.0, "LLPA Grid (run once)", color='#FCE5CD', edgecolor='#E69138', subtext="crt/crt_llpa.R")

    draw_arrow(lx, 18.45, lx, 17.85)
    draw_arrow(rx, 18.45, rx, 17.85)

    draw_box(lx, 17.4, 5.0, 0.8, "cas_crt_YYYYMMDD.parquet", color='#F3F3F3', edgecolor='#999', fontsize=9.5)
    draw_box(rx, 17.4, 4.5, 0.8, "crt_llpa_interpolated.txt", color='#F3F3F3', edgecolor='#999', fontsize=9.5)

    # ── Row 2: Step 2 (center) ──
    cx = 7.5
    draw_arrow(lx, 16.95, cx - 0.5, 16.35)
    draw_arrow(rx, 16.95, cx + 0.5, 16.35)

    draw_box(cx, 15.9, 6.0, 1.0, "Step 2: Feature Engineering", subtext="crt_data_prep.R  →  prep_crt_data_v1.2")
    draw_arrow(cx, 15.35, cx, 14.75)

    draw_box(cx, 14.3, 6.0, 0.8, "prep_fannie_data_{i}.rds × 10 splits", color='#F3F3F3', edgecolor='#999', fontsize=9.5)

    # ── Branch into 3a (left) and 3b (right) ──
    lx3, rx3 = 3.8, 11.2

    draw_arrow(cx - 1.2, 13.85, lx3 + 0.3, 13.15)
    draw_arrow(cx + 1.2, 13.85, rx3 - 0.3, 13.15)

    # ── Step 3a: Turnover (left column) ──
    cluster_rect = patches.FancyBboxPatch((0.9, 7.8), 5.8, 5.6,
                                           boxstyle="round,pad=0.3", linewidth=2,
                                           edgecolor='#4A90E2', facecolor='#F0F7FF', linestyle='--')
    ax.add_patch(cluster_rect)
    plt.text(lx3, 13.05, "Step 3a: Turnover Model", ha='center', va='center',
             fontsize=11, fontweight='bold', color='#4A90E2')

    draw_box(lx3, 12.4, 5.0, 0.7, "crt_turnover_undersample.R", fontsize=9.5)
    draw_arrow(lx3, 12.0, lx3, 11.55, label="KZ undersample by vintage")
    draw_box(lx3, 11.1, 4.5, 0.7, "Training + Tracking files", color='#F3F3F3', edgecolor='#999', fontsize=9.5)
    draw_arrow(lx3, 10.7, lx3, 10.25)
    draw_box(lx3, 9.8, 4.5, 0.7, "crt_turnover_model.R", fontsize=9.5)
    draw_arrow(lx3, 9.4, lx3, 8.95)
    draw_box(lx3, 8.5, 5.0, 0.8, "Turnover GAM + Report PDF", color='#EAD1DC', edgecolor='#C27BA0', fontsize=9.5)

    # ── Step 3b: Refi (right column) ──
    cluster_rect2 = patches.FancyBboxPatch((8.3, 2.5), 5.8, 10.8,
                                            boxstyle="round,pad=0.3", linewidth=2,
                                            edgecolor='#E69138', facecolor='#FFF8F0', linestyle='--')
    ax.add_patch(cluster_rect2)
    plt.text(rx3, 13.05, "Step 3b: Refi Model", ha='center', va='center',
             fontsize=11, fontweight='bold', color='#E69138')

    draw_box(rx3, 12.4, 5.0, 0.7, "crt_refi_data_prep.R", fontsize=9.5)
    draw_arrow(rx3, 12.0, rx3, 11.5, label="Predict turnover, flag isTurnover")
    draw_box(rx3, 11.05, 4.5, 0.7, "s4 RDS × 10 splits", color='#F3F3F3', edgecolor='#999', fontsize=9.5)
    draw_arrow(rx3, 10.65, rx3, 10.15)
    draw_box(rx3, 9.7, 5.0, 0.7, "crt_refi_undersample.R", fontsize=9.5)
    draw_arrow(rx3, 9.3, rx3, 8.8, label="Drop turnovers, KZ undersample")
    draw_box(rx3, 8.35, 4.5, 0.7, "Training + Tracking files", color='#F3F3F3', edgecolor='#999', fontsize=9.5)
    draw_arrow(rx3, 7.95, rx3, 7.45)
    draw_box(rx3, 7.0, 4.5, 0.7, "crt_refinance_model.R", fontsize=9.5)
    draw_arrow(rx3, 6.6, rx3, 6.1)
    draw_box(rx3, 5.65, 5.0, 0.8, "Stage 1: Economic Drivers", color='#D9EAD3', edgecolor='#6AA84F', fontsize=9.5)
    draw_arrow(rx3, 5.2, rx3, 4.7)
    draw_box(rx3, 4.25, 5.0, 0.8, "Stage 2: Servicer + State", color='#D9EAD3', edgecolor='#6AA84F', fontsize=9.5)
    draw_arrow(rx3, 3.8, rx3, 3.3)
    draw_box(rx3, 2.85, 5.0, 0.8, "Two-stage Refi GAM + Report PDF", color='#EAD1DC', edgecolor='#C27BA0', fontsize=9.5)

    # ── Cross-arrow: Turnover GAM → Refi data prep ──
    ax.annotate("", xy=(rx3 - 2.5, 12.4), xytext=(lx3 + 2.5, 8.5),
                arrowprops=dict(arrowstyle="-|>", color="#888", lw=2, linestyle='dashed',
                                connectionstyle="arc3,rad=-0.2"))
    plt.text(7.5, 10.6, "Turnover model\nused for prediction", ha='center', va='center', fontsize=9,
             style='italic', color='#666',
             bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#ccc', alpha=0.9))

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=150, facecolor='white')
    print(f"CRT pipeline diagram saved to {output_path}")


if __name__ == "__main__":
    output_dir = r"c:\Users\hzeng\Desktop\howard-toolbox\emailer\assets"
    os.makedirs(output_dir, exist_ok=True)
    create_crt_pipeline_diagram(os.path.join(output_dir, "crt_pipeline_diagram.png"))

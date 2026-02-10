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

if __name__ == "__main__":
    # Save to the assets folder of the emailer
    output_dir = r"c:\Users\hzeng\Desktop\howard-toolbox\emailer\assets"
    os.makedirs(output_dir, exist_ok=True)
    create_simulation_flowchart(os.path.join(output_dir, "simulation_diagram.png"))

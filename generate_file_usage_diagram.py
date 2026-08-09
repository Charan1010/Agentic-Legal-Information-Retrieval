"""
Generate a timeline diagram showing WHEN each file/memory/prompt is used in the pipeline.
Shows the full execution flow left-to-right with files mapped to their injection points.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

OUTPUT_DIR = r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition"

# Colors
C = {
    'bg': '#1a1a2e',
    'context_file': '#4FC3F7',    # blue - context files
    'prompt_file': '#CE93D8',     # purple - prompt templates
    'grammar': '#FFD54F',         # yellow - grammar files
    'memory': '#EF5350',          # red - runtime memories
    'output': '#66BB6A',          # green - outputs
    'phase_bg': '#16213e',        # dark blue - phase background
    'arrow': '#90A4AE',
    'text': '#ffffff',
    'subtext': '#b0bec5',
}


def draw_file_usage_timeline():
    """Main diagram: timeline of file usage across the pipeline."""
    fig, ax = plt.subplots(1, 1, figsize=(20, 14))
    fig.patch.set_facecolor(C['bg'])
    ax.set_facecolor(C['bg'])
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 14)
    ax.axis('off')

    # Title
    ax.text(10, 13.5, "File & Memory Usage Timeline", fontsize=20, fontweight='bold',
            color=C['text'], ha='center', va='center')
    ax.text(10, 13.0, "When each context file, prompt template, grammar, and runtime memory is injected",
            fontsize=11, color=C['subtext'], ha='center', va='center')

    # --- Phase boxes ---
    phases = [
        (0.5, 4.5, "PHASE 1\nPLANNER", 12.0),
        (5.5, 9.0, "PHASE 2: EXECUTOR\n(per direction, iterations 0-3)", 12.0),
        (10.0, 5.5, "PHASE 3\nAGGREGATION", 12.0),
    ]

    for x, w, label, y_top in phases:
        rect = FancyBboxPatch((x, 1.0), w, y_top - 1.5,
                              boxstyle="round,pad=0.1",
                              facecolor=C['phase_bg'], edgecolor='#37474f',
                              linewidth=1.5, alpha=0.7)
        ax.add_patch(rect)
        ax.text(x + w/2, y_top - 0.3, label, fontsize=9, fontweight='bold',
                color=C['subtext'], ha='center', va='top')

    # --- Helper to draw a file box ---
    def file_box(x, y, text, color, width=3.2, height=0.55):
        rect = FancyBboxPatch((x, y - height/2), width, height,
                              boxstyle="round,pad=0.05",
                              facecolor=color, edgecolor='white',
                              linewidth=0.5, alpha=0.85)
        ax.add_patch(rect)
        ax.text(x + width/2, y, text, fontsize=7.5, fontweight='bold',
                color='#1a1a1a', ha='center', va='center')

    # ========================================================================
    # PHASE 1: PLANNER
    # ========================================================================
    planner_x = 1.0
    
    # Context files (loaded once at startup into planner user message)
    ax.text(planner_x + 1.7, 11.3, "Context Files", fontsize=9, fontweight='bold',
            color=C['context_file'], ha='center')
    ax.text(planner_x + 1.7, 10.9, "(loaded into USER message)", fontsize=7,
            color=C['subtext'], ha='center')
    
    file_box(planner_x, 10.3, "swiss_legal_system.txt  (7.7 KB)", C['context_file'], 3.5)
    file_box(planner_x, 9.6, "terminology_bridge.txt  (8.5 KB)", C['context_file'], 3.5)
    
    # Prompt template (system message)
    ax.text(planner_x + 1.7, 8.8, "Prompt Template", fontsize=9, fontweight='bold',
            color=C['prompt_file'], ha='center')
    ax.text(planner_x + 1.7, 8.4, "(SYSTEM message)", fontsize=7,
            color=C['subtext'], ha='center')
    
    file_box(planner_x, 7.8, "planner_system.txt  (8.2 KB)", C['prompt_file'], 3.5)
    
    # Grammar
    ax.text(planner_x + 1.7, 7.0, "Grammar Constraint", fontsize=9, fontweight='bold',
            color=C['grammar'], ha='center')
    
    file_box(planner_x, 6.4, "planner.gbnf  (890 B)", C['grammar'], 3.5)
    
    # Variables injected
    ax.text(planner_x + 1.7, 5.6, "Variables Injected", fontsize=9, fontweight='bold',
            color=C['memory'], ha='center')
    ax.text(planner_x + 1.7, 5.2, "(into planner_system.txt template)", fontsize=7,
            color=C['subtext'], ha='center')
    
    file_box(planner_x, 4.6, "{available_law_codes}  (973 codes)", C['memory'], 3.5)
    file_box(planner_x, 3.9, "{available_court_codes}  (39 codes)", C['memory'], 3.5)
    
    # Output
    ax.text(planner_x + 1.7, 3.0, "Output →", fontsize=9, fontweight='bold',
            color=C['output'], ha='center')
    
    file_box(planner_x, 2.4, "Plan JSON (sachverhalt, directions[])", C['output'], 3.5)
    file_box(planner_x, 1.7, "seed_queries[] per direction", C['output'], 3.5)

    # ========================================================================
    # PHASE 2: EXECUTOR (per direction)
    # ========================================================================
    exec_x = 6.0
    
    # Iteration 0 section
    ax.text(exec_x + 1.5, 11.3, "Iteration 0", fontsize=9, fontweight='bold',
            color=C['output'], ha='center')
    ax.text(exec_x + 1.5, 10.9, "(NO LLM — direct search)", fontsize=7,
            color=C['subtext'], ha='center')
    
    file_box(exec_x, 10.3, "seed_queries[0] from Planner", C['output'], 3.2)
    file_box(exec_x, 9.6, "filter_codes from Planner", C['output'], 3.2)
    
    # Iterations 1-3 section
    ax.text(exec_x + 1.5, 8.8, "Iterations 1-3", fontsize=9, fontweight='bold',
            color=C['prompt_file'], ha='center')
    ax.text(exec_x + 1.5, 8.4, "(LLM generates queries)", fontsize=7,
            color=C['subtext'], ha='center')
    
    # Standard direction prompt
    file_box(exec_x, 7.8, "executor_system.txt  (2.0 KB)", C['prompt_file'], 3.2)
    ax.text(exec_x + 3.4, 7.8, "OR", fontsize=8, color=C['subtext'], ha='left', va='center')
    file_box(exec_x, 7.1, "executor_procedural.txt (P≥90)", C['prompt_file'], 3.2)
    
    # Grammar
    file_box(exec_x, 6.4, "executor.gbnf  (301 B)", C['grammar'], 3.2)
    
    # Runtime memories injected into template
    ax.text(exec_x + 1.5, 5.6, "Runtime Variables", fontsize=9, fontweight='bold',
            color=C['memory'], ha='center')
    ax.text(exec_x + 1.5, 5.2, "(injected via .format())", fontsize=7,
            color=C['subtext'], ha='center')
    
    file_box(exec_x, 4.6, "{prior_findings}  (0→450 tok)", C['memory'], 3.2)
    file_box(exec_x, 3.9, "{direction_history}  (0→500 tok)", C['memory'], 3.2)
    file_box(exec_x, 3.2, "{plan_summary}  (sachverhalt+fragen)", C['memory'], 3.2)
    file_box(exec_x, 2.5, "{rechtsgebiet} {corpus} {filter_codes}", C['memory'], 3.2)
    file_box(exec_x, 1.8, "{reasoning}  (from Planner)", C['memory'], 3.2)

    # ========================================================================
    # PHASE 3: AGGREGATION
    # ========================================================================
    agg_x = 10.5
    
    ax.text(agg_x + 2.2, 11.3, "Aggregation Inputs", fontsize=9, fontweight='bold',
            color=C['context_file'], ha='center')
    ax.text(agg_x + 2.2, 10.9, "(NO LLM — rule-based)", fontsize=7,
            color=C['subtext'], ha='center')
    
    file_box(agg_x, 10.3, "procedural_defaults.txt  (6.1 KB)", C['context_file'], 4.5)
    file_box(agg_x, 9.6, "All direction_citations[]  (merged)", C['memory'], 4.5)
    
    ax.text(agg_x + 2.2, 8.8, "Processing Steps", fontsize=9, fontweight='bold',
            color=C['subtext'], ha='center')
    
    file_box(agg_x, 8.2, "detect_case_type() → inject defaults", C['output'], 4.5)
    file_box(agg_x, 7.5, "dedup by citation string", C['output'], 4.5)
    file_box(agg_x, 6.8, "Reranker (Qwen3-Reranker-0.6B)", C['output'], 4.5)
    file_box(agg_x, 6.1, "Score cutoff (>0.1) + top 100-150", C['output'], 4.5)
    file_box(agg_x, 5.4, "Prepend explicit citations from question", C['output'], 4.5)
    
    ax.text(agg_x + 2.2, 4.5, "Final Output", fontsize=9, fontweight='bold',
            color=C['output'], ha='center')
    
    file_box(agg_x, 3.9, "Ranked citation list (JSON)", C['output'], 4.5)

    # ========================================================================
    # ARROWS between phases
    # ========================================================================
    # Planner → Executor
    ax.annotate('', xy=(5.5, 6.0), xytext=(4.7, 6.0),
                arrowprops=dict(arrowstyle='->', color=C['arrow'], lw=2))
    
    # Executor → Aggregation
    ax.annotate('', xy=(10.0, 6.0), xytext=(9.3, 6.0),
                arrowprops=dict(arrowstyle='->', color=C['arrow'], lw=2))

    # Feedback loop arrow (prior_findings)
    ax.annotate('', xy=(6.0, 4.6), xytext=(9.0, 2.0),
                arrowprops=dict(arrowstyle='->', color=C['memory'],
                               lw=1.5, linestyle='dashed',
                               connectionstyle='arc3,rad=-0.3'))
    ax.text(8.5, 2.6, "citations flow back\nas prior_findings\nfor next direction", 
            fontsize=7, color=C['memory'], ha='center', style='italic')

    # ========================================================================
    # LEGEND
    # ========================================================================
    legend_x = 16.0
    legend_y = 11.5
    ax.text(legend_x + 1.0, legend_y + 0.8, "LEGEND", fontsize=10, fontweight='bold',
            color=C['text'], ha='center')
    
    legend_items = [
        (C['context_file'], "Context/Knowledge File"),
        (C['prompt_file'], "Prompt Template"),
        (C['grammar'], "GBNF Grammar"),
        (C['memory'], "Runtime Variable / Memory"),
        (C['output'], "Output / Processing Step"),
    ]
    
    for i, (color, label) in enumerate(legend_items):
        y = legend_y - i * 0.6
        rect = FancyBboxPatch((legend_x - 0.3, y - 0.2), 0.5, 0.35,
                              boxstyle="round,pad=0.02",
                              facecolor=color, edgecolor='white', linewidth=0.5)
        ax.add_patch(rect)
        ax.text(legend_x + 0.5, y, label, fontsize=8, color=C['text'], va='center')

    # Key insight box
    insight_y = 7.5
    rect = FancyBboxPatch((15.8, insight_y - 0.3), 4.0, 3.8,
                          boxstyle="round,pad=0.15",
                          facecolor='#263238', edgecolor=C['context_file'],
                          linewidth=1.5)
    ax.add_patch(rect)
    ax.text(17.8, insight_y + 3.2, "KEY INSIGHT", fontsize=9, fontweight='bold',
            color=C['context_file'], ha='center')
    
    insights = [
        "• Context files (16 KB) are",
        "  loaded ONLY in Planner",
        "",
        "• Executor gets NO context",
        "  files — only distilled",
        "  variables from Planner",
        "",
        "• prior_findings is the ONLY",
        "  cross-direction memory",
        "",
        "• direction_history is the",
        "  ONLY within-direction memory",
    ]
    for i, line in enumerate(insights):
        ax.text(16.0, insight_y + 2.7 - i * 0.27, line, fontsize=7.5,
                color=C['text'], va='center', family='monospace')

    # Token budget box
    token_y = 3.5
    rect = FancyBboxPatch((15.8, token_y - 0.3), 4.0, 2.8,
                          boxstyle="round,pad=0.15",
                          facecolor='#263238', edgecolor=C['grammar'],
                          linewidth=1.5)
    ax.add_patch(rect)
    ax.text(17.8, token_y + 2.2, "TOKEN BUDGET", fontsize=9, fontweight='bold',
            color=C['grammar'], ha='center')
    
    tokens = [
        "PLANNER CALL:",
        "  system: 8.2KB (~2000 tok)",
        "  user:   31KB  (~7600 tok)",
        "  TOTAL:  ~9,600 tokens",
        "",
        "EXECUTOR CALL (each):",
        "  system: 2KB + vars (~1000-",
        "          1400 tok growing)",
        "  user:   1 line (10 tok)",
        "  TOTAL:  ~1,000-1,400 tokens",
    ]
    for i, line in enumerate(tokens):
        ax.text(16.0, token_y + 1.8 - i * 0.25, line, fontsize=7,
                color=C['text'], va='center', family='monospace')

    plt.tight_layout()
    out_path = f"{OUTPUT_DIR}/architecture_9_file_usage_timeline.png"
    plt.savefig(out_path, dpi=150, bbox_inches='tight',
                facecolor=C['bg'], edgecolor='none')
    plt.close()
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    draw_file_usage_timeline()

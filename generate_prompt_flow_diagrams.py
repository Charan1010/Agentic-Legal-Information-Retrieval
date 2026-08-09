"""
Generate prompt growth & feedback flow diagrams for the Planner-Director pipeline.
Creates 3 PNG diagrams:
1. Prompt composition (what files feed into each LLM call)
2. Prior findings growth across directions (feedback mechanism)
3. Token budget growth per iteration
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

OUTPUT_DIR = r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition"

COLORS = {
    'bg': '#f8f9fa',
    'file_context': '#e3f2fd',
    'file_border': '#1565C0',
    'file_prompt': '#ede7f6',
    'prompt_border': '#512DA8',
    'var_inject': '#fff8e1',
    'var_border': '#F57F17',
    'output': '#e8f5e9',
    'output_border': '#2E7D32',
    'feedback': '#fce4ec',
    'feedback_border': '#C62828',
    'dark': '#1a1a2e',
    'grey': '#eceff1',
}


def add_box(ax, x, y, w, h, text, color, border, fontsize=8, bold=False, alpha=1.0):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06",
                         facecolor=color, edgecolor=border, linewidth=1.5, alpha=alpha)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, fontweight=weight, color='#222', wrap=True,
            linespacing=1.3)
    return box


def add_arrow(ax, x1, y1, x2, y2, color='#333', style='->', lw=1.5):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, lw=lw, color=color))


# ============================================================
# DIAGRAM 1: PROMPT COMPOSITION — What feeds into each LLM call
# ============================================================
def draw_prompt_composition():
    fig, ax = plt.subplots(1, 1, figsize=(22, 18))
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 18)
    ax.axis('off')
    ax.set_facecolor(COLORS['bg'])
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(11, 17.5, 'PROMPT COMPOSITION — What feeds into each LLM call',
            ha='center', va='center', fontsize=16, fontweight='bold', color=COLORS['dark'])

    # ====== PLANNER LLM CALL (left side) ======
    # Header
    ax.text(5.5, 16.5, 'PLANNER LLM CALL (~9,600 tokens input)',
            ha='center', va='center', fontsize=12, fontweight='bold', color='#311B92')

    # System message box
    sys_box = FancyBboxPatch((0.5, 10.5), 10, 5.5, boxstyle="round,pad=0.1",
                              facecolor='#f3e5f5', edgecolor='#7B1FA2', linewidth=2)
    ax.add_patch(sys_box)
    ax.text(5.5, 15.7, 'messages[0]: SYSTEM (~3,200 tokens)', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#4A148C')

    # planner_system.txt
    add_box(ax, 0.8, 13.5, 4.5, 1.8,
            'planner_system.txt (178 lines)\n━━━━━━━━━━━━━━━━━━━━\n'
            '• Role: Swiss lawyer 20y experience\n'
            '• Rules: 3-6 directions, German queries\n'
            '• Output: strict JSON format\n'
            '• "NIEMALS Codes erfinden!" constraint\n'
            '• 3 worked examples (crim/family/social)',
            COLORS['file_prompt'], COLORS['prompt_border'], fontsize=7)

    # Injected variables
    add_box(ax, 5.7, 13.5, 4.5, 1.8,
            'INJECTED VARIABLES:\n━━━━━━━━━━━━━━━━━━━━\n'
            '{available_law_codes}\n'
            '→ "AIG, ATSG, AVIG, BGG, BV,\n'
            '   BVG, DSG, EMRK, IVG, KVG,\n'
            '   OR, SchKG, StGB, StPO, ..."\n'
            '   (973 codes, ~4KB text)\n\n'
            '{available_court_codes}\n'
            '→ "1B_, 1C_, 2C_, 4A_, 5A_,\n'
            '   6B_, 8C_, 9C_, BGE_I, ..."\n'
            '   (39 codes, ~200B text)',
            COLORS['var_inject'], COLORS['var_border'], fontsize=6.5)

    # Grammar
    add_box(ax, 2.5, 10.7, 5.5, 0.6,
            'planner.gbnf (890B) → constrains JSON output structure',
            '#e0f7fa', '#00838F', fontsize=7.5)

    # User message box
    usr_box = FancyBboxPatch((0.5, 6.0), 10, 4.0, boxstyle="round,pad=0.1",
                              facecolor='#e8f5e9', edgecolor='#2E7D32', linewidth=2)
    ax.add_patch(usr_box)
    ax.text(5.5, 9.7, 'messages[1]: USER (~6,400 tokens)', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#1B5E20')

    add_box(ax, 0.8, 8.0, 4.5, 1.3,
            'swiss_legal_system.txt (189 lines)\n━━━━━━━━━━━━━━━━━━━━\n'
            'Court hierarchy, SR numbering,\n'
            'appeal paths, court chambers,\n'
            'how law codes map to courts',
            COLORS['file_context'], COLORS['file_border'], fontsize=7)

    add_box(ax, 5.7, 8.0, 4.5, 1.3,
            'routing_guide_laws.txt (9.3KB)\n'
            '+ routing_guide_courts.txt (6.1KB)\n'
            '━━━━━━━━━━━━━━━━━━━━\n'
            'Per-code taxonomy, keywords,\n'
            'classification rules, examples',
            COLORS['file_context'], COLORS['file_border'], fontsize=7)

    add_box(ax, 0.8, 6.3, 4.5, 1.2,
            'terminology_bridge.txt (165 lines)\n━━━━━━━━━━━━━━━━━━━━\n'
            'EN→DE: "detention"→"Haft"\n'
            '"appeal"→"Beschwerde"\n'
            '"proportionality"→"Verhältnismässigkeit"',
            COLORS['file_context'], COLORS['file_border'], fontsize=7)

    add_box(ax, 5.7, 6.3, 4.5, 1.2,
            'FRAGE: "Under what conditions can pre-trial\n'
            'detention be extended beyond the initial period?"',
            '#fff9c4', '#F9A825', fontsize=7.5)

    # Output
    add_box(ax, 2.5, 4.5, 5.5, 1.0,
            'LLM OUTPUT (~500 tokens):\n'
            'JSON with sachverhalt, rechtsfragen, directions[4]',
            COLORS['output'], COLORS['output_border'], fontsize=8)
    add_arrow(ax, 5.5, 6.0, 5.5, 5.5, color='#2E7D32', lw=2)

    # ====== EXECUTOR LLM CALL (right side) ======
    ax.text(16.5, 16.5, 'EXECUTOR LLM CALL (~1,000-1,400 tokens)',
            ha='center', va='center', fontsize=12, fontweight='bold', color='#1B5E20')

    # System message
    exec_sys = FancyBboxPatch((11.5, 8.0), 10, 8.0, boxstyle="round,pad=0.1",
                               facecolor='#e8f5e9', edgecolor='#2E7D32', linewidth=2)
    ax.add_patch(exec_sys)
    ax.text(16.5, 15.7, 'messages[0]: SYSTEM (~950-1300 tokens, GROWS each iter)',
            ha='center', va='center', fontsize=9, fontweight='bold', color='#1B5E20')

    # Template
    add_box(ax, 11.8, 13.8, 4.5, 1.5,
            'executor_system.txt (47 lines)\n━━━━━━━━━━━━━━━━━━━━\n'
            'OR executor_procedural.txt\n'
            '(if priority ≥ 90)\n\n'
            'Template with 8 variable slots:\n'
            '{rechtsgebiet}, {corpus},\n'
            '{filter_codes}, {reasoning},\n'
            '{taxonomy_section},\n'
            '{plan_summary}, {prior_findings},\n'
            '{direction_history}',
            COLORS['file_prompt'], COLORS['prompt_border'], fontsize=6.5)

    # Variable fills
    add_box(ax, 16.8, 13.8, 4.5, 1.5,
            'VARIABLES FILLED:\n━━━━━━━━━━━━━━━━━━━━\n'
            'rechtsgebiet = "Strafprozessrecht"\n'
            'corpus = "laws"\n'
            'filter_codes = "StPO"\n'
            'reasoning = "StPO 221-240..."\n'
            'plan_summary = "Sachverhalt:\n'
            '  Haftverlängerung... Richtung 1/4"',
            COLORS['var_inject'], COLORS['var_border'], fontsize=6.5)

    # Prior findings (GROWING)
    pf_box = FancyBboxPatch((11.8, 10.8), 9.4, 2.5, boxstyle="round,pad=0.08",
                             facecolor=COLORS['feedback'], edgecolor=COLORS['feedback_border'], linewidth=2.5)
    ax.add_patch(pf_box)
    ax.text(16.5, 13.0, '{prior_findings} — GROWS WITH EACH DIRECTION!',
            ha='center', va='center', fontsize=8.5, fontweight='bold', color='#B71C1C')

    ax.text(16.5, 12.3,
            'Dir 1: "Noch keine Funde aus vorherigen Richtungen."\n'
            'Dir 2: "- Art. 221 Abs. 1 StPO (0.87)\\n- Art. 227 Abs. 1 StPO (0.82)\\n- ..."\n'
            'Dir 3: "- Art. 221... (0.87)\\n- 1B_210/2023 E.4.1 (0.78)\\n- ..."\n'
            'Dir 4: "- Art. 221... (0.87)\\n- 1B_210/2023... (0.78)\\n- Art.10 BV (0.65)\\n..."',
            ha='center', va='center', fontsize=6.5, color='#333', linespacing=1.5)
    ax.text(16.5, 11.0, '(always last 20 citations — rolling window)',
            ha='center', va='center', fontsize=7, color='#880E4F', style='italic')

    # Direction history (GROWING within direction)
    dh_box = FancyBboxPatch((11.8, 8.3), 9.4, 2.2, boxstyle="round,pad=0.08",
                             facecolor='#fff3e0', edgecolor='#E65100', linewidth=2)
    ax.add_patch(dh_box)
    ax.text(16.5, 10.2, '{direction_history} — GROWS WITHIN EACH DIRECTION!',
            ha='center', va='center', fontsize=8.5, fontweight='bold', color='#E65100')
    ax.text(16.5, 9.3,
            'Iter 1: "Query: \'Haftgründe Verlängerung...\'\\n  → Funde: Art.221; Art.227; ..."\n'
            'Iter 2: above + "Query: \'Höchstdauer Überhaft...\'\\n  → Funde: Art.212; Art.228; ..."\n'
            'Iter 3: above + "Query: \'Zwangsmassnahmengericht...\'\\n  → Funde: Art.225; Art.226"',
            ha='center', va='center', fontsize=6.5, color='#333', linespacing=1.5)
    ax.text(16.5, 8.5, '(LLM sees ALL previous queries in this direction → avoids repeats)',
            ha='center', va='center', fontsize=7, color='#BF360C', style='italic')

    # Grammar
    add_box(ax, 13.5, 7.3, 6.0, 0.5,
            'executor.gbnf (301B) → forces {"thought":"...", "query":"...", "done":bool}',
            '#e0f7fa', '#00838F', fontsize=7)

    # User message
    add_box(ax, 13.5, 6.0, 6.0, 0.8,
            'messages[1]: USER (static, 1 line)\n'
            '"Generiere deine nächste Suchanfrage oder signalisiere done."',
            '#e8f5e9', '#2E7D32', fontsize=7.5)

    # Output
    add_box(ax, 13.5, 4.5, 6.0, 1.0,
            'LLM OUTPUT (~80 tokens):\n'
            '{"thought":"Need Überhaft limits","query":"Höchstdauer...","done":false}',
            COLORS['output'], COLORS['output_border'], fontsize=7.5)
    add_arrow(ax, 16.5, 6.0, 16.5, 5.5, color='#2E7D32', lw=2)

    # ====== CONNECTION: Planner output → Executor inputs ======
    add_arrow(ax, 8.0, 5.0, 11.8, 14.5, color='#512DA8', lw=2.5, style='->')
    ax.text(10.0, 10.5, 'Plan JSON\n(directions,\nrechtsfragen,\nsachverhalt)',
            ha='center', va='center', fontsize=7, color='#512DA8', fontweight='bold',
            rotation=50)

    # ====== Legend ======
    legend_y = 1.5
    add_box(ax, 1, legend_y, 2.5, 0.5, 'Context File\n(static knowledge)', COLORS['file_context'], COLORS['file_border'], fontsize=7)
    add_box(ax, 4, legend_y, 2.5, 0.5, 'Prompt Template\n(LLM instructions)', COLORS['file_prompt'], COLORS['prompt_border'], fontsize=7)
    add_box(ax, 7, legend_y, 2.5, 0.5, 'Runtime Variable\n(injected at runtime)', COLORS['var_inject'], COLORS['var_border'], fontsize=7)
    add_box(ax, 10, legend_y, 2.5, 0.5, 'GROWING Feedback\n(cross-direction)', COLORS['feedback'], COLORS['feedback_border'], fontsize=7)
    add_box(ax, 13, legend_y, 2.5, 0.5, 'GROWING History\n(within-direction)', '#fff3e0', '#E65100', fontsize=7)
    add_box(ax, 16, legend_y, 2.5, 0.5, 'LLM Output', COLORS['output'], COLORS['output_border'], fontsize=7)

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/architecture_6_prompt_composition.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print(f"  ✓ {path}")


# ============================================================
# DIAGRAM 2: FEEDBACK FLOW BETWEEN DIRECTIONS
# ============================================================
def draw_feedback_flow():
    fig, ax = plt.subplots(1, 1, figsize=(20, 14))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 14)
    ax.axis('off')
    ax.set_facecolor(COLORS['bg'])
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(10, 13.5, 'FEEDBACK FLOW — How prior_findings grows between directions',
            ha='center', va='center', fontsize=15, fontweight='bold', color=COLORS['dark'])
    ax.text(10, 13.0, 'Each direction sees what ALL previous directions found → avoids redundant search',
            ha='center', va='center', fontsize=10, color='#555', style='italic')

    # Direction boxes (top row)
    dirs = [
        ('DIR 1\nP1: laws/StPO\n"Strafprozessrecht"', 1.0),
        ('DIR 2\nP2: courts/1B_\n"BGer Praxis"', 6.0),
        ('DIR 3\nP3: laws/BV+EMRK\n"Grundrechte"', 11.0),
        ('DIR 4\nP99: both/BGG+BV\n"Verfahrensrecht"', 16.0),
    ]

    for text, x in dirs:
        add_box(ax, x, 11.0, 3.5, 1.5, text, '#c8e6c9', '#2E7D32', fontsize=8, bold=True)

    # Iteration details inside each direction
    iters_data = [
        # Dir 1
        [
            ('iter0: seed "Haftgründe Verlängerung..."', '→ Art.221, Art.227, Art.212, Art.226, Art.220...'),
            ('iter1: LLM "Höchstdauer Überhaft..."', '→ Art.212/1, Art.228, Art.231, Art.229...'),
            ('iter2: LLM "Zwangsmassnahmen..."', '→ Art.225, Art.226/2, Art.224...'),
            ('iter3: done=true', ''),
        ],
        # Dir 2
        [
            ('iter0: seed "Haftverlängerung BGer..."', '→ 1B_210/2023, 1B_42/2022, 1B_130/2021...'),
            ('iter1: LLM "Verhältnismässigkeit..."', '→ 1B_55/2023, BGE 137 IV 122...'),
            ('iter2: done=true', ''),
        ],
        # Dir 3
        [
            ('iter0: seed "Grundrecht Freiheit..."', '→ Art.10/2 BV, Art.31 BV, Art.5 EMRK...'),
            ('iter1: LLM "Freiheitsentzug..."', '→ Art.36 BV, Art.5/3 EMRK...'),
            ('iter2: done=true', ''),
        ],
        # Dir 4
        [
            ('iter0: seed "Beschwerde Haft..."', '→ Art.78 BGG, Art.81 BGG, Art.100 BGG...'),
            ('iter1: LLM "Legitimation..."', '→ Art.42/2 BGG, Art.95 BGG...'),
            ('iter2: done=true', ''),
        ],
    ]

    for d_idx, (_, x) in enumerate(dirs):
        for i_idx, (query, results) in enumerate(iters_data[d_idx]):
            y = 10.3 - i_idx * 0.7
            ax.text(x + 1.75, y, query, ha='center', va='center', fontsize=6, color='#333')
            if results:
                ax.text(x + 1.75, y - 0.3, results, ha='center', va='center', fontsize=5.5,
                        color='#2E7D32', style='italic')

    # ====== PRIOR_FINDINGS ACCUMULATOR (middle section) ======
    acc_box = FancyBboxPatch((0.5, 4.0), 19.0, 3.5, boxstyle="round,pad=0.12",
                              facecolor=COLORS['feedback'], edgecolor=COLORS['feedback_border'], linewidth=2.5)
    ax.add_patch(acc_box)
    ax.text(10, 7.2, 'prior_findings ACCUMULATOR (rolling window of last 20 citations)',
            ha='center', va='center', fontsize=11, fontweight='bold', color='#B71C1C')

    # State at each point
    states = [
        ('BEFORE Dir 1:', '[]  (empty)', 1.5, 6.5),
        ('AFTER Dir 1\n→ feed to Dir 2:', '["Art.221 StPO (0.87)", "Art.227 StPO (0.82)",\n'
         ' "Art.212 StPO (0.79)", "Art.226 StPO (0.75)",\n'
         ' "Art.228 StPO (0.72)", ... ×20 from Dir 1]', 1.5, 5.7),
        ('AFTER Dir 2\n→ feed to Dir 3:', '["Art.221 StPO (0.87)", "1B_210/2023 (0.78)",\n'
         ' "BGE 137 IV 122 (0.68)", "1B_42/2022 (0.65)",\n'
         ' ... last 20 of Dir1+Dir2 combined]', 7.5, 5.7),
        ('AFTER Dir 3\n→ feed to Dir 4:', '["Art.221 StPO (0.87)", "1B_210/2023 (0.78)",\n'
         ' "Art.10/2 BV (0.65)", "Art.31 BV (0.55)",\n'
         ' ... last 20 of Dir1+Dir2+Dir3]', 13.5, 5.7),
    ]

    for label, content, x, y in states:
        ax.text(x, y, label, fontsize=7, fontweight='bold', color='#880E4F')
        ax.text(x, y - 0.7, content, fontsize=6, color='#333', linespacing=1.3)

    # Arrows from directions down to accumulator
    for _, x in dirs:
        add_arrow(ax, x + 1.75, 8.0, x + 1.75, 7.5, color=COLORS['feedback_border'], lw=2)

    # Forward arrows between directions
    for i in range(len(dirs) - 1):
        x1 = dirs[i][1] + 3.5
        x2 = dirs[i+1][1]
        # Curved arrow going up from accumulator to next direction
        ax.annotate('', xy=(x2 + 1.75, 8.0), xytext=(x1 - 0.5, 7.5),
                    arrowprops=dict(arrowstyle='->', lw=2.5, color='#C62828',
                                   connectionstyle='arc3,rad=-0.3'))

    # ====== CODE SNIPPET ======
    code_box = FancyBboxPatch((2.0, 0.5), 16.0, 3.0, boxstyle="round,pad=0.1",
                               facecolor='#263238', edgecolor='#37474F', linewidth=2)
    ax.add_patch(code_box)
    ax.text(10, 3.2, 'pipeline.py — The exact code that implements this:', ha='center', va='center',
            fontsize=8, fontweight='bold', color='#90CAF9')

    code_lines = [
        ('all_citations = []', '#A5D6A7'),
        ('prior_findings = []    # ← starts EMPTY', '#A5D6A7'),
        ('', '#fff'),
        ('for i, direction in enumerate(sorted_directions):', '#fff'),
        ('    direction_cits = run_direction(', '#fff'),
        ('        direction=direction,', '#fff'),
        ('        prior_findings=prior_findings,  # ← PASSED IN', '#FFCC80'),
        ('        ...', '#fff'),
        ('    )', '#fff'),
        ('    all_citations.extend(direction_cits)', '#A5D6A7'),
        ('    prior_findings = (prior_findings + direction_cits)[-20:]  # ← ROLLING WINDOW', '#EF9A9A'),
    ]

    for i, (line, color) in enumerate(code_lines):
        ax.text(3.0, 2.7 - i * 0.2, line, fontsize=7, color=color, fontfamily='monospace')

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/architecture_7_feedback_flow.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print(f"  ✓ {path}")


# ============================================================
# DIAGRAM 3: TOKEN BUDGET GROWTH PER ITERATION
# ============================================================
def draw_token_growth():
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    fig.patch.set_facecolor(COLORS['bg'])
    fig.suptitle('TOKEN BUDGET GROWTH — How prompts expand over time',
                 fontsize=14, fontweight='bold', color=COLORS['dark'])

    # ---- Left chart: Executor prompt size per iteration ----
    ax = axes[0]
    ax.set_facecolor(COLORS['bg'])
    ax.set_title('Executor Prompt Size (within one direction)', fontsize=11, fontweight='bold')

    iterations = ['Iter 1', 'Iter 2', 'Iter 3']

    # Stacked components
    template_base = [400, 400, 400]  # executor_system.txt base
    plan_summary = [80, 80, 80]  # plan_summary (fixed)
    prior_findings = [50, 50, 50]  # prior_findings (fixed per direction)
    direction_history = [120, 280, 440]  # GROWS: ~160 tokens per iteration

    x = np.arange(len(iterations))
    width = 0.5

    bars1 = ax.bar(x, template_base, width, label='Template base (47 lines)', color='#7E57C2')
    bars2 = ax.bar(x, plan_summary, width, bottom=template_base, label='plan_summary (fixed)', color='#42A5F5')
    bars3 = ax.bar(x, prior_findings, width,
                   bottom=[a+b for a,b in zip(template_base, plan_summary)],
                   label='prior_findings (from prev dirs)', color='#EF5350')
    bars4 = ax.bar(x, direction_history, width,
                   bottom=[a+b+c for a,b,c in zip(template_base, plan_summary, prior_findings)],
                   label='direction_history (GROWS!)', color='#FFA726')

    ax.set_xticks(x)
    ax.set_xticklabels(iterations)
    ax.set_ylabel('Tokens', fontsize=10)
    ax.set_ylim(0, 1200)
    ax.legend(fontsize=8, loc='upper left')

    # Annotate totals
    totals = [sum(t) for t in zip(template_base, plan_summary, prior_findings, direction_history)]
    for i, total in enumerate(totals):
        ax.text(i, total + 20, f'~{total} tok', ha='center', fontsize=9, fontweight='bold')

    ax.axhline(y=800, color='#C62828', linestyle='--', linewidth=1, alpha=0.7)
    ax.text(2.3, 820, 'typical max\n~970 tokens', fontsize=7, color='#C62828')

    # ---- Right chart: Prior findings growth across directions ----
    ax = axes[1]
    ax.set_facecolor(COLORS['bg'])
    ax.set_title('prior_findings Size Across Directions', fontsize=11, fontweight='bold')

    directions = ['Dir 1\n(first)', 'Dir 2', 'Dir 3', 'Dir 4\n(procedural)']
    prior_tokens = [10, 250, 380, 450]  # grows then stabilizes (rolling window caps at 20)
    colors = ['#A5D6A7', '#66BB6A', '#43A047', '#2E7D32']

    bars = ax.bar(range(len(directions)), prior_tokens, color=colors, width=0.5, edgecolor='#1B5E20')
    ax.set_xticks(range(len(directions)))
    ax.set_xticklabels(directions)
    ax.set_ylabel('Tokens in {prior_findings}', fontsize=10)
    ax.set_ylim(0, 600)

    for i, v in enumerate(prior_tokens):
        ax.text(i, v + 10, f'~{v} tok', ha='center', fontsize=9, fontweight='bold')

    ax.axhline(y=450, color='#C62828', linestyle='--', linewidth=1, alpha=0.7)
    ax.text(3.3, 460, 'caps at ~450\n(20 cits max)', fontsize=7, color='#C62828')

    # Annotations
    ax.annotate('EMPTY\n(no prior dirs)', xy=(0, 10), fontsize=7, ha='center',
                color='#2E7D32', xytext=(0, 80),
                arrowprops=dict(arrowstyle='->', color='#2E7D32'))

    ax.annotate('Sees Dir1\nresults', xy=(1, 250), fontsize=7, ha='center',
                color='#2E7D32', xytext=(1, 330),
                arrowprops=dict(arrowstyle='->', color='#2E7D32'))

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/architecture_8_token_growth.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print(f"  ✓ {path}")


if __name__ == "__main__":
    print("Generating prompt & feedback flow diagrams...")
    draw_prompt_composition()
    draw_feedback_flow()
    draw_token_growth()
    print("\nAll 3 prompt/feedback diagrams generated!")

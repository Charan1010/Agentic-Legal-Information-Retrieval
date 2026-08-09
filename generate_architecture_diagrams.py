"""
Generate detailed architecture diagrams for the Planner-Director RAG Agent.
Creates 5 PNG diagrams:
1. Overall Detailed Architecture (full system view)
2. Planner Phase Detail (decomposition + grammar + fallback)
3. Executor Phase Detail (ReAct loop + search flow)
4. Search & Filter Infrastructure (FAISS + BM25 + metadata)
5. Aggregation & Output Phase (rerank + defaults + output)
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
import numpy as np

OUTPUT_DIR = r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition"

# Color palette
COLORS = {
    'bg': '#f8f9fa',
    'input': '#e3f2fd',
    'input_border': '#1976D2',
    'planner': '#ede7f6',
    'planner_border': '#512DA8',
    'executor': '#e8f5e9',
    'executor_border': '#2E7D32',
    'search': '#fff8e1',
    'search_border': '#F57F17',
    'agg': '#fce4ec',
    'agg_border': '#C62828',
    'output': '#e0f7fa',
    'output_border': '#00838F',
    'gpu0': '#e1bee7',
    'gpu1': '#b3e5fc',
    'data': '#f3e5f5',
    'grey': '#eceff1',
    'accent': '#FF6F00',
    'dark': '#1a1a2e',
}


def add_box(ax, x, y, w, h, text, color, border, fontsize=9, bold=False, 
            text_color='#333', alpha=1.0, style="round,pad=0.08"):
    """Helper to add a rounded box with centered text."""
    box = FancyBboxPatch((x, y), w, h, boxstyle=style,
                         facecolor=color, edgecolor=border, linewidth=1.8, alpha=alpha)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', 
            fontsize=fontsize, fontweight=weight, color=text_color, wrap=True)
    return box


def add_arrow(ax, x1, y1, x2, y2, color='#333', style='->', lw=1.8):
    """Helper to add an arrow."""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, lw=lw, color=color))


# ============================================================
# DIAGRAM 1: OVERALL DETAILED ARCHITECTURE
# ============================================================
def draw_overall_architecture():
    fig, ax = plt.subplots(1, 1, figsize=(20, 28))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 28)
    ax.axis('off')
    ax.set_facecolor(COLORS['bg'])
    fig.patch.set_facecolor(COLORS['bg'])

    # Title
    ax.text(10, 27.5, 'PLANNER-DIRECTOR RAG ARCHITECTURE', 
            ha='center', va='center', fontsize=18, fontweight='bold', color=COLORS['dark'])
    ax.text(10, 27.0, 'Swiss Legal Citation Retrieval — Complete System Architecture', 
            ha='center', va='center', fontsize=12, color='#555', style='italic')

    # ---- INPUT SECTION ----
    add_box(ax, 6, 25.8, 8, 0.9, 'INPUT: English Legal Question\n(40 questions from test.csv)',
            COLORS['input'], COLORS['input_border'], fontsize=10, bold=True)
    add_arrow(ax, 10, 25.8, 10, 25.4)

    # ---- HARDWARE SECTION (side panel) ----
    hw_box = FancyBboxPatch((15.5, 18, ), 4, 7.2, boxstyle="round,pad=0.15",
                             facecolor=COLORS['grey'], edgecolor='#78909C', linewidth=2)
    ax.add_patch(hw_box)
    ax.text(17.5, 24.9, 'HARDWARE', ha='center', va='center', fontsize=10, fontweight='bold', color='#37474F')
    
    # GPU 0
    add_box(ax, 15.8, 23.5, 3.5, 1.1, 'GPU 0 (~4GB)\n━━━━━━━━━━━━━━\nMistral-7B-Instruct\nQ4_K_M (GGUF)\nPlanner + Executor LLM',
            COLORS['gpu0'], '#7B1FA2', fontsize=8)
    # GPU 1
    add_box(ax, 15.8, 21.8, 3.5, 1.4, 'GPU 1 (~2.4GB)\n━━━━━━━━━━━━━━\nQwen3-Embedding-0.6B (fp16)\n→ 768-dim vectors\nQwen3-Reranker-0.6B\n→ relevance scores',
            COLORS['gpu1'], '#0277BD', fontsize=8)
    # CPU/RAM
    add_box(ax, 15.8, 20.0, 3.5, 1.5, 'CPU / RAM (~1GB)\n━━━━━━━━━━━━━━\nFAISS IndexFlatIP\n  laws: 175K × 768\n  courts: 2.4M × 768\nBM25 Indices\nMetadata Arrays',
            COLORS['grey'], '#455A64', fontsize=8)
    # Timing
    add_box(ax, 15.8, 18.3, 3.5, 1.4, 'TIMING BUDGET\n━━━━━━━━━━━━━━\nPlanner: ~2s\nExecutors: ~20s\nReranker: ~5s\n─────────────\nTotal: ~27s/question',
            '#fff9c4', '#F9A825', fontsize=8)

    # ---- CONTEXT FILES (side panel left) ----
    ctx_box = FancyBboxPatch((0.5, 22.0), 4.5, 3.5, boxstyle="round,pad=0.12",
                              facecolor='#fff3e0', edgecolor='#E65100', linewidth=2)
    ax.add_patch(ctx_box)
    ax.text(2.75, 25.2, 'CONTEXT FILES', ha='center', va='center', fontsize=9, fontweight='bold', color='#BF360C')
    ax.text(2.75, 24.7, '(loaded into LLM prompts)', ha='center', va='center', fontsize=7, color='#777', style='italic')
    
    ctx_files = [
        'swiss_legal_system.txt (189 lines)',
        'routing_guide_laws.txt (9.3KB)',
        'routing_guide_courts.txt (6.1KB)',
        'terminology_bridge.txt (165 lines)',
        'procedural_defaults.txt (113 lines)',
        'planner_system.txt (178 lines)',
        'executor_system.txt (47 lines)',
        'executor_procedural.txt (55 lines)',
        'planner.gbnf (grammar)',
        'executor.gbnf (grammar)',
    ]
    for i, f in enumerate(ctx_files):
        ax.text(2.75, 24.2 - i*0.27, f'• {f}', ha='center', va='center', fontsize=7, color='#444')

    # ---- PHASE 1: PLANNER ----
    phase1_box = FancyBboxPatch((2.5, 22.8), 12, 2.7, boxstyle="round,pad=0.15",
                                 facecolor=COLORS['planner'], edgecolor=COLORS['planner_border'], linewidth=2.5)
    ax.add_patch(phase1_box)
    ax.text(8.5, 25.2, 'PHASE 1: RECHTSANWALT PLANNER', ha='center', va='center',
            fontsize=12, fontweight='bold', color='#311B92')
    ax.text(8.5, 24.8, '1 LLM call (Mistral-7B + GBNF grammar) → Structured Research Plan',
            ha='center', va='center', fontsize=9, color='#333')
    
    # Inner planner boxes
    add_box(ax, 2.8, 23.0, 3.5, 1.5,
            'INPUT ASSEMBLY\n━━━━━━━━━━━━\nSystem: planner_system.txt\n+ available_codes list\nUser: swiss_legal +\nterminology + question',
            '#d1c4e9', '#5E35B1', fontsize=7.5)
    
    add_box(ax, 6.5, 23.0, 3.5, 1.5,
            'LLM GENERATION\n━━━━━━━━━━━━\nGBNF: planner.gbnf\nForces: 3-6 directions\nTokens: ~500 output\nTime: ~2s on GPU 0',
            '#d1c4e9', '#5E35B1', fontsize=7.5)
    
    add_box(ax, 10.2, 23.0, 3.8, 1.5,
            'OUTPUT (parsed JSON)\n━━━━━━━━━━━━━━━\n• sachverhalt (DE summary)\n• rechtsfragen[] (legal Qs)\n• directions[3-6] with:\n  priority, corpus, filter_codes\n  seed_queries, rechtsgebiet',
            '#d1c4e9', '#5E35B1', fontsize=7.5)
    
    add_arrow(ax, 6.3, 23.75, 6.5, 23.75, color=COLORS['planner_border'])
    add_arrow(ax, 10.0, 23.75, 10.2, 23.75, color=COLORS['planner_border'])

    # Fallback
    add_box(ax, 11.5, 22.3, 2.7, 0.6, 'FALLBACK: keyword rules\n(if JSON parse fails 2x)',
            '#ffcdd2', '#C62828', fontsize=7)

    add_arrow(ax, 10, 22.8, 10, 22.3)

    # ---- PHASE 2: EXECUTORS ----
    phase2_box = FancyBboxPatch((1.5, 13.5), 13.5, 8.5, boxstyle="round,pad=0.15",
                                 facecolor=COLORS['executor'], edgecolor=COLORS['executor_border'], linewidth=2.5)
    ax.add_patch(phase2_box)
    ax.text(8.25, 21.7, 'PHASE 2: DIRECTION EXECUTORS (Sequential, 3-6 directions)',
            ha='center', va='center', fontsize=12, fontweight='bold', color='#1B5E20')
    ax.text(8.25, 21.3, 'Each direction: Iter 0 (no LLM) + up to 3 ReAct iterations | 15s timeout | prior_findings passed forward',
            ha='center', va='center', fontsize=8.5, color='#333')

    # Direction flow
    y_start = 20.5
    directions = [
        ('DIR 1: Substantive Law', 'corpus=laws, codes=[StPO/ZGB/OR/StGB]\nseed: "Haftgründe Verhältnismässigkeit..."', '#c8e6c9'),
        ('DIR 2: Court Decisions', 'corpus=courts, codes=[1B_/5A_/6B_/8C_]\nseed: "Bundesgericht Praxis..."', '#a5d6a7'),
        ('DIR 3: Related/Cross-ref', 'corpus=both, codes=[BV/EMRK/ATSG]\nseed: "Grundrechte Querverweise..."', '#81c784'),
        ('DIR N: Procedural (P99)', 'corpus=both, codes=[BGG/BV]\nseed: "Beschwerde Legitimation Frist..."', '#66bb6a'),
    ]
    
    for i, (title, desc, color) in enumerate(directions):
        y = y_start - i * 1.9
        # Direction box
        add_box(ax, 2.0, y, 4.0, 1.5, f'{title}\n━━━━━━━━━━━━\n{desc}',
                color, COLORS['executor_border'], fontsize=7.5)
        
        # ReAct iteration box
        add_box(ax, 6.5, y, 7.8, 1.5,
                f'ITER 0: Run seed_queries[0] directly (NO LLM call)\n'
                f'ITER 1: LLM thinks → generates query → search → observe results\n'
                f'ITER 2: LLM refines based on findings → deeper search\n'
                f'ITER 3: Fill gaps or signal done=true',
                '#f1f8e9', '#558B2F', fontsize=7.5)
        
        add_arrow(ax, 6.0, y + 0.75, 6.5, y + 0.75, color=COLORS['executor_border'])
        
        # Prior findings arrow
        if i < len(directions) - 1:
            ax.annotate('', xy=(5.0, y), xytext=(5.0, y - 0.4),
                        arrowprops=dict(arrowstyle='->', lw=1.5, color='#388E3C',
                                       connectionstyle='arc3,rad=-0.3'))
            ax.text(5.5, y - 0.25, 'prior_findings\n(last 20 cits)', fontsize=6, color='#2E7D32', style='italic')

    # ---- SEARCH INFRASTRUCTURE (middle) ----
    search_box = FancyBboxPatch((1.5, 8.0), 13.5, 5.0, boxstyle="round,pad=0.15",
                                 facecolor=COLORS['search'], edgecolor=COLORS['search_border'], linewidth=2.5)
    ax.add_patch(search_box)
    ax.text(8.25, 12.7, 'SEARCH INFRASTRUCTURE: filtered_hybrid_search()',
            ha='center', va='center', fontsize=11, fontweight='bold', color='#E65100')
    
    # FAISS
    add_box(ax, 2.0, 10.5, 4.0, 1.8,
            'FAISS (IndexFlatIP)\n━━━━━━━━━━━━━\n• Qwen3-Embedding → 768d\n• Cosine sim (IP on L2-normed)\n• IDSelector for filtering\n• Returns: top-k by similarity',
            '#fff9c4', '#F9A825', fontsize=7.5)
    
    # BM25
    add_box(ax, 6.5, 10.5, 4.0, 1.8,
            'BM25 (rank_bm25)\n━━━━━━━━━━━━━\n• Tokenized corpus\n• Keyword matching\n• Post-filter by valid_indices\n• Returns: top-k by BM25 score',
            '#fff9c4', '#F9A825', fontsize=7.5)
    
    # RRF Fusion
    add_box(ax, 11.0, 10.5, 3.5, 1.8,
            'RRF FUSION (k=60)\n━━━━━━━━━━━━━\nscore = Σ 1/(k + rank)\n\nMerges FAISS + BM25\nDeduplicate by citation\nSort by RRF score',
            '#ffe0b2', '#E65100', fontsize=7.5)

    add_arrow(ax, 6.0, 11.4, 6.5, 11.4, color=COLORS['search_border'])
    add_arrow(ax, 10.5, 11.4, 11.0, 11.4, color=COLORS['search_border'])

    # Metadata filter
    add_box(ax, 2.0, 8.3, 6.0, 1.8,
            'METADATA FILTER INDEX\n━━━━━━━━━━━━━━━━━━━━\nlaw_code_to_indices: {"StPO": np.array([0,1,2,...]), "OR": [...]}\n'
            'court_code_to_indices: {"1B_": np.array([...]), "BGE_IV": [...]}\n'
            'Adaptive fallback: if <5 results → broaden to unfiltered',
            '#ffecb3', '#FF8F00', fontsize=7.5)
    
    # Data volumes
    add_box(ax, 8.5, 8.3, 5.5, 1.8,
            'CORPUS DATA\n━━━━━━━━━━━━━━━━━━━━\n• laws_de.csv: 175,933 articles\n  → 2,048 SR codes, 973 available\n'
            '• court_considerations.csv: 2,476,315\n  → 44 codes, 39 available\n'
            '• corpus_citation_set: all valid citations',
            '#f3e5f5', '#6A1B9A', fontsize=7.5)

    add_arrow(ax, 8.25, 12.5, 8.25, 8.0, color='#333', lw=1.5, style='->')

    # ---- PHASE 3: AGGREGATION ----
    phase3_box = FancyBboxPatch((1.5, 3.5), 13.5, 4.2, boxstyle="round,pad=0.15",
                                 facecolor=COLORS['agg'], edgecolor=COLORS['agg_border'], linewidth=2.5)
    ax.add_patch(phase3_box)
    ax.text(8.25, 7.4, 'PHASE 3: AGGREGATION & OUTPUT',
            ha='center', va='center', fontsize=12, fontweight='bold', color='#B71C1C')
    
    # Steps
    steps = [
        ('1. COLLECT', 'All citations from\nall directions', 2.0),
        ('2. INJECT\nDEFAULTS', 'Procedural defaults\nper case type', 4.3),
        ('3. DEDUP', 'Exact string match\nkeep highest score', 6.6),
        ('4. RERANK', 'Qwen3-Reranker\nEN query vs DE docs', 8.9),
        ('5. CUTOFF', 'Score ≥ 0.2\nMax 60 citations', 11.2),
    ]
    for title, desc, x in steps:
        add_box(ax, x, 5.5, 2.0, 1.5, f'{title}\n━━━━━━━━\n{desc}',
                '#ffcdd2', '#C62828', fontsize=7)
    
    # Arrows between steps
    for i in range(len(steps)-1):
        x1 = steps[i][2] + 2.0
        x2 = steps[i+1][2]
        add_arrow(ax, x1, 6.25, x2, 6.25, color=COLORS['agg_border'])

    # Prepend explicit
    add_box(ax, 4.0, 3.8, 5.0, 1.2,
            '6. PREPEND EXPLICIT\n━━━━━━━━━━━━━━━━\nRegex-extract citations from question text\n'
            '"Art. 221 Abs. 1 StPO" → prepend if exists in corpus',
            '#ffcdd2', '#C62828', fontsize=7.5)
    
    # Safety
    add_box(ax, 9.5, 3.8, 4.0, 1.2,
            'SAFETY OVERRIDE\n━━━━━━━━━━━━━━━━\nIf ALL scores < 0.2:\n→ Return top-10 anyway\n(never return empty)',
            '#ffcdd2', '#880E4F', fontsize=7.5)

    # ---- OUTPUT ----
    add_arrow(ax, 8.25, 3.5, 8.25, 2.8)
    add_box(ax, 5.0, 1.8, 6.5, 0.9,
            'OUTPUT: "Art. 221 Abs. 1 StPO;Art. 212 StPO;BGE 137 IV 122;..."\n→ submission.csv (semicolon-separated citations)',
            COLORS['output'], COLORS['output_border'], fontsize=9, bold=True)

    # ---- DATA FLOW ARROWS (main spine) ----
    add_arrow(ax, 8.5, 22.8, 8.5, 22.0, color=COLORS['dark'], lw=2.5)
    ax.text(9.0, 22.4, 'Plan JSON', fontsize=8, color=COLORS['dark'])
    
    # Save
    plt.tight_layout()
    path = f"{OUTPUT_DIR}/architecture_1_overall.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print(f"  ✓ {path}")


# ============================================================
# DIAGRAM 2: PLANNER PHASE DETAIL
# ============================================================
def draw_planner_detail():
    fig, ax = plt.subplots(1, 1, figsize=(18, 14))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 14)
    ax.axis('off')
    ax.set_facecolor(COLORS['bg'])
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(9, 13.5, 'PHASE 1: PLANNER — Detailed Flow', 
            ha='center', va='center', fontsize=16, fontweight='bold', color=COLORS['dark'])
    ax.text(9, 13.0, '"Think like a Schweizer Rechtsanwalt" — Structured decomposition of legal questions',
            ha='center', va='center', fontsize=10, color='#555', style='italic')

    # ---- Left: Swiss Lawyer Thought Process ----
    lawyer_box = FancyBboxPatch((0.3, 6.5), 5.5, 6.0, boxstyle="round,pad=0.12",
                                 facecolor='#f3e5f5', edgecolor='#7B1FA2', linewidth=2)
    ax.add_patch(lawyer_box)
    ax.text(3.05, 12.2, 'SWISS LAWYER THOUGHT PROCESS', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#4A148C')
    
    steps = [
        ('STEP 1', 'SACHVERHALT ERFASSEN', 'Grasp the facts — what happened?'),
        ('STEP 2', 'RECHTSFRAGE IDENTIFIZIEREN', 'Identify legal sub-questions'),
        ('STEP 3', 'RECHTSGEBIET ZUORDNEN', 'Classify into legal areas'),
        ('STEP 4', 'SUBSUMTION', 'Match facts to legal norms'),
        ('STEP 5', 'BGer PRAXIS PRÜFEN', 'Check Federal Court case law'),
        ('STEP 6', 'VERFAHRENSRECHT', 'Procedural framework (always)'),
        ('STEP 7', 'QUERVERWEISE', 'Cross-references + General Part'),
    ]
    for i, (step, title, desc) in enumerate(steps):
        y = 11.7 - i * 0.75
        ax.text(0.6, y, step, fontsize=7, fontweight='bold', color='#6A1B9A')
        ax.text(1.6, y, title, fontsize=7.5, fontweight='bold', color='#333')
        ax.text(1.6, y - 0.25, desc, fontsize=7, color='#666', style='italic')
    
    ax.text(3.05, 6.7, 'Steps 1-3 → PLANNER | Steps 4-7 → EXECUTORS',
            ha='center', va='center', fontsize=7.5, fontweight='bold', color='#4A148C')

    # ---- Center: Planner Pipeline ----
    # Input
    add_box(ax, 6.5, 11.5, 5.0, 1.0,
            'INPUT: English Legal Question\n"Under what conditions can pre-trial detention be extended?"',
            COLORS['input'], COLORS['input_border'], fontsize=8)
    add_arrow(ax, 9.0, 11.5, 9.0, 11.0)

    # System prompt assembly
    add_box(ax, 6.0, 9.5, 6.0, 1.4,
            'SYSTEM PROMPT ASSEMBLY\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            'planner_system.txt.format(\n'
            '  available_law_codes=["StPO","OR","ZGB",...973 codes],\n'
            '  available_court_codes=["1B_","5A_",...39 codes]\n'
            ')',
            COLORS['planner'], '#7E57C2', fontsize=7.5)
    add_arrow(ax, 9.0, 11.0, 9.0, 10.9)

    # User message
    add_box(ax, 6.0, 7.8, 6.0, 1.4,
            'USER MESSAGE (~6,400 tokens)\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            'KONTEXT: swiss_legal_system.txt (~1900 tok)\n'
            'ROUTING: routing_guide_laws/courts (~3850 tok)\n'
            'TERMINOLOGIE: terminology_bridge.txt (~2100 tok)\n'
            'FRAGE: {english_question}',
            COLORS['planner'], '#7E57C2', fontsize=7.5)
    add_arrow(ax, 9.0, 9.5, 9.0, 9.2)

    # LLM + GBNF
    add_box(ax, 6.5, 6.0, 5.0, 1.5,
            'MISTRAL-7B + GBNF GRAMMAR\n━━━━━━━━━━━━━━━━━━━━━━━\n'
            'Grammar: planner.gbnf\n'
            'Forces: valid JSON with 3-6 directions\n'
            'Max tokens: 800 | Time: ~2s',
            '#b39ddb', COLORS['planner_border'], fontsize=8, bold=True)
    add_arrow(ax, 9.0, 7.8, 9.0, 7.5)

    # Parse + Validate
    add_box(ax, 6.5, 4.3, 5.0, 1.4,
            'PARSE + VALIDATE\n━━━━━━━━━━━━━━━━━━━━━━━\n'
            '• json.loads() → extract fields\n'
            '• Remove invalid filter_codes\n'
            '• Ensure ≥3 directions\n'
            '• Add procedural if missing',
            COLORS['planner'], '#7E57C2', fontsize=7.5)
    add_arrow(ax, 9.0, 6.0, 9.0, 5.7)

    # Output
    add_box(ax, 6.0, 2.2, 6.0, 1.8,
            'OUTPUT: Plan Object\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            '{\n'
            '  sachverhalt: "Frage nach Haftverlängerung...",\n'
            '  rechtsfragen: ["Haftgründe","Verhältnismässigkeit"],\n'
            '  directions: [\n'
            '    {P1, laws, [StPO], "Haftgründe..."},\n'
            '    {P2, courts, [1B_], "BGer Praxis..."},\n'
            '    {P99, both, [BGG,BV], "Verfahren..."}\n'
            '  ]\n'
            '}',
            '#d1c4e9', COLORS['planner_border'], fontsize=7.5)
    add_arrow(ax, 9.0, 4.3, 9.0, 4.0)

    # ---- Right: Error Handling & Fallback ----
    error_box = FancyBboxPatch((13.0, 4.0), 4.5, 8.5, boxstyle="round,pad=0.12",
                                facecolor='#ffebee', edgecolor='#C62828', linewidth=2)
    ax.add_patch(error_box)
    ax.text(15.25, 12.2, 'ERROR HANDLING', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#B71C1C')
    
    ax.text(15.25, 11.5, 'JSON Parse Fail?', fontsize=8, fontweight='bold', color='#333', ha='center')
    ax.text(15.25, 11.1, '→ Retry with: "Output NUR\n   valides JSON"', fontsize=7.5, color='#555', ha='center')
    
    ax.text(15.25, 10.2, 'Retry Also Fails?', fontsize=8, fontweight='bold', color='#333', ha='center')
    ax.text(15.25, 9.8, '→ fallback_decompose(question)', fontsize=7.5, color='#555', ha='center')
    
    ax.text(15.25, 8.9, 'FALLBACK RULES:', fontsize=8, fontweight='bold', color='#B71C1C', ha='center')
    
    fallback_rules = [
        '"detention" → StPO + 1B_',
        '"criminal" → StGB + 6B_',
        '"contract" → OR + 4A_',
        '"divorce" → ZGB + 5A_',
        '"disability" → IVG + 8C_',
        '"immigration" → AIG + 2C_',
        'ALWAYS → BGG + BV (P99)',
        'nothing matched → unfiltered',
    ]
    for i, rule in enumerate(fallback_rules):
        ax.text(15.25, 8.3 - i*0.45, f'• {rule}', fontsize=7, color='#444', ha='center')
    
    ax.text(15.25, 4.5, 'VALIDATION RULES:', fontsize=8, fontweight='bold', color='#B71C1C', ha='center')
    ax.text(15.25, 4.1, '• <3 dirs → add catch-all + procedural\n'
            '• Invalid codes → silently removed\n'
            '• corpus ∉ {laws,courts,both} → "both"',
            fontsize=7, color='#444', ha='center')

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/architecture_2_planner_detail.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print(f"  ✓ {path}")


# ============================================================
# DIAGRAM 3: EXECUTOR PHASE DETAIL
# ============================================================
def draw_executor_detail():
    fig, ax = plt.subplots(1, 1, figsize=(18, 16))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 16)
    ax.axis('off')
    ax.set_facecolor(COLORS['bg'])
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(9, 15.5, 'PHASE 2: DIRECTION EXECUTOR — ReAct Loop Detail',
            ha='center', va='center', fontsize=16, fontweight='bold', color=COLORS['dark'])
    ax.text(9, 15.0, 'Each direction runs independently with its own context. Prior findings flow forward between directions.',
            ha='center', va='center', fontsize=10, color='#555', style='italic')

    # ---- Direction Input (top) ----
    add_box(ax, 5.5, 13.5, 7.0, 1.2,
            'DIRECTION INPUT (from Planner)\n'
            'priority=1 | corpus="laws" | filter_codes=["StPO"]\n'
            'rechtsgebiet="Strafprozessrecht" | seed_queries=["Haftgründe..."]',
            COLORS['executor'], COLORS['executor_border'], fontsize=8)
    add_arrow(ax, 9.0, 13.5, 9.0, 13.0)

    # ---- Iteration 0 ----
    add_box(ax, 5.0, 11.8, 8.0, 1.0,
            'ITERATION 0 (NO LLM CALL — orchestrator runs directly)\n'
            '→ filtered_hybrid_search(seed_queries[0], "laws", ["StPO"], top_k=10)',
            '#c8e6c9', COLORS['executor_border'], fontsize=8, bold=True)
    add_arrow(ax, 9.0, 12.8, 9.0, 12.8)

    # Results
    add_box(ax, 13.5, 11.8, 4.0, 1.0,
            'RESULTS → direction_citations\n'
            'e.g. Art. 221 StPO, Art. 212 StPO\n'
            'Art. 226 StPO, Art. 227 StPO...',
            '#f1f8e9', '#558B2F', fontsize=7.5)
    add_arrow(ax, 13.0, 12.3, 13.5, 12.3, color=COLORS['executor_border'])
    
    add_arrow(ax, 9.0, 11.8, 9.0, 11.3)

    # ---- ReAct Loop Box ----
    react_box = FancyBboxPatch((1.5, 3.5), 15.0, 7.5, boxstyle="round,pad=0.15",
                                facecolor='#e8f5e9', edgecolor='#1B5E20', linewidth=2.5)
    ax.add_patch(react_box)
    ax.text(9.0, 10.7, 'ReAct LOOP (Iterations 1-3, max 15s timeout)',
            ha='center', va='center', fontsize=11, fontweight='bold', color='#1B5E20')

    # THINK
    add_box(ax, 2.0, 8.5, 4.5, 1.8,
            'THINK (LLM generates)\n━━━━━━━━━━━━━━━━━━━\n'
            'Executor sees:\n'
            '• rechtsgebiet + reasoning\n'
            '• plan_summary (sachverhalt)\n'
            '• prior_findings (last 20)\n'
            '• direction_history (all queries)\n'
            '↓ Generates thought + query',
            '#c8e6c9', '#2E7D32', fontsize=7.5)

    # ACT
    add_box(ax, 7.0, 8.5, 4.5, 1.8,
            'ACT (Search execution)\n━━━━━━━━━━━━━━━━━━━\n'
            'filtered_hybrid_search(\n'
            '  query="Haftprüfung Zwangs-\n'
            '         massnahmengericht",\n'
            '  corpus="laws",\n'
            '  filter_codes=["StPO"],\n'
            '  top_k=10\n'
            ')',
            '#a5d6a7', '#2E7D32', fontsize=7.5)

    # OBSERVE
    add_box(ax, 12.0, 8.5, 4.5, 1.8,
            'OBSERVE (formatted results)\n━━━━━━━━━━━━━━━━━━━\n'
            'SUCHERGEBNISSE (Filter: StPO):\n'
            '1. "Art. 228 StPO" (0.72)\n'
            '   — Haftentlassungsgesuch\n'
            '2. "Art. 229 StPO" (0.68)\n'
            '   — Sicherheitshaft\n'
            '3. ...',
            '#81c784', '#2E7D32', fontsize=7.5)

    # Arrows in ReAct loop
    add_arrow(ax, 6.5, 9.4, 7.0, 9.4, color='#1B5E20', lw=2)
    add_arrow(ax, 11.5, 9.4, 12.0, 9.4, color='#1B5E20', lw=2)

    # DECIDE
    add_box(ax, 5.5, 5.8, 7.0, 1.5,
            'DECIDE: Continue or Done?\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            '{"thought": "Found Haftentlassung, need Verhältnismässigkeit next",\n'
            ' "query": "Verhältnismässigkeit Freiheitsentzug Überhaft Dauer",\n'
            ' "done": false}\n'
            'OR: {"thought": "All aspects covered", "query": "", "done": true}',
            '#66bb6a', '#1B5E20', fontsize=7.5)
    
    # Loop arrow back
    ax.annotate('', xy=(3.0, 8.5), xytext=(3.0, 7.3),
                arrowprops=dict(arrowstyle='->', lw=2, color='#1B5E20',
                               connectionstyle='arc3,rad=-0.5'))
    ax.text(1.8, 7.8, 'LOOP\n(if done=false\n& iter < 3)', fontsize=7, 
            color='#1B5E20', fontweight='bold', ha='center')

    add_arrow(ax, 14.25, 8.5, 14.25, 7.3, color='#1B5E20')
    add_arrow(ax, 9.0, 7.3, 9.0, 6.0, color=COLORS['dark'], lw=1.5, style='->')

    # ---- Stop Conditions ----
    add_box(ax, 2.0, 3.8, 6.5, 1.5,
            'STOP CONDITIONS\n━━━━━━━━━━━━━━━━━━━━━━\n'
            '• done=true → direction complete\n'
            '• iter > 3 → hard cap reached\n'
            '• elapsed > 15s → timeout\n'
            '• repeated query → force stop\n'
            '• JSON parse fail (2x) → skip',
            '#ffcdd2', '#C62828', fontsize=7.5)

    # ---- Output ----
    add_box(ax, 9.5, 3.8, 6.5, 1.5,
            'DIRECTION OUTPUT\n━━━━━━━━━━━━━━━━━━━━━━\n'
            'direction_citations: [\n'
            '  ("Art. 221 Abs. 1 StPO", 0.87, "Haftgründe..."),\n'
            '  ("Art. 228 StPO", 0.72, "Haftentlassung..."),\n'
            '  ... (all iterations combined)\n'
            ']',
            COLORS['output'], COLORS['output_border'], fontsize=7.5)

    # ---- Prompt Template Note ----
    add_box(ax, 2.0, 1.5, 14.0, 1.8,
            'EXECUTOR PROMPT TEMPLATE (executor_system.txt)\n'
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            'Variables: {rechtsgebiet} {corpus} {filter_codes} {reasoning} {plan_summary} {prior_findings} {direction_history}\n'
            'Rules: German queries only | 3-10 words | No article numbers | No English | No repeated queries\n'
            'Strategy: Iter 1=broad → Iter 2=related concepts → Iter 3=fill gaps\n'
            'Special: Priority ≥90 uses executor_procedural.txt (knows BGG/BV article patterns by appeal type)',
            '#e8eaf6', '#3F51B5', fontsize=7.5)

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/architecture_3_executor_detail.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print(f"  ✓ {path}")


# ============================================================
# DIAGRAM 4: SEARCH & FILTER INFRASTRUCTURE
# ============================================================
def draw_search_infrastructure():
    fig, ax = plt.subplots(1, 1, figsize=(18, 14))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 14)
    ax.axis('off')
    ax.set_facecolor(COLORS['bg'])
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(9, 13.5, 'SEARCH & FILTER INFRASTRUCTURE — filtered_hybrid_search()',
            ha='center', va='center', fontsize=16, fontweight='bold', color=COLORS['dark'])
    ax.text(9, 13.0, 'Metadata-driven search with FAISS semantic + BM25 keyword + RRF fusion + adaptive fallback',
            ha='center', va='center', fontsize=10, color='#555', style='italic')

    # ---- Input ----
    add_box(ax, 5.5, 11.8, 7.0, 1.0,
            'filtered_hybrid_search(query="Haftgründe Verhältnismässigkeit",\n'
            '    corpus="laws", filter_codes=["StPO"], top_k=10)',
            COLORS['input'], COLORS['input_border'], fontsize=8.5)
    add_arrow(ax, 9.0, 11.8, 9.0, 11.3)

    # ---- Metadata Resolution ----
    add_box(ax, 5.5, 10.2, 7.0, 1.0,
            'METADATA RESOLUTION\n'
            'law_code_to_indices["StPO"] → np.array([indices of 1,306 StPO articles])\n'
            'valid_indices = np.unique(np.concatenate([arrays for each code]))',
            COLORS['search'], '#F57F17', fontsize=8)
    add_arrow(ax, 9.0, 11.0, 9.0, 11.2)

    # ---- Split into two search paths ----
    ax.annotate('', xy=(5.0, 9.5), xytext=(9.0, 10.2),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    ax.annotate('', xy=(13.0, 9.5), xytext=(9.0, 10.2),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))

    # ---- FAISS Path (left) ----
    faiss_box = FancyBboxPatch((1.5, 6.5), 6.5, 2.8, boxstyle="round,pad=0.12",
                                facecolor='#e3f2fd', edgecolor='#1565C0', linewidth=2)
    ax.add_patch(faiss_box)
    ax.text(4.75, 9.0, 'FAISS SEMANTIC SEARCH', ha='center', va='center',
            fontsize=10, fontweight='bold', color='#0D47A1')
    
    ax.text(4.75, 8.5, '1. query_vec = embed(query)', fontsize=8, color='#333', ha='center')
    ax.text(4.75, 8.1, '   Qwen3-Embedding-0.6B → 768-dim (GPU 1)', fontsize=7, color='#555', ha='center')
    ax.text(4.75, 7.7, '2. IDSelector(valid_indices) for filtering', fontsize=8, color='#333', ha='center')
    ax.text(4.75, 7.3, '   Only compares against StPO vectors', fontsize=7, color='#555', ha='center')
    ax.text(4.75, 6.9, '3. index.search(query_vec, top_k=10)', fontsize=8, color='#333', ha='center')
    ax.text(4.75, 6.5, '   Returns: [(doc_id, cosine_score), ...]', fontsize=7, color='#555', ha='center')

    # ---- BM25 Path (right) ----
    bm25_box = FancyBboxPatch((9.5, 6.5), 6.5, 2.8, boxstyle="round,pad=0.12",
                               facecolor='#fff3e0', edgecolor='#E65100', linewidth=2)
    ax.add_patch(bm25_box)
    ax.text(12.75, 9.0, 'BM25 KEYWORD SEARCH', ha='center', va='center',
            fontsize=10, fontweight='bold', color='#BF360C')
    
    ax.text(12.75, 8.5, '1. tokens = tokenize(query)', fontsize=8, color='#333', ha='center')
    ax.text(12.75, 8.1, '   Split on \\W+, lowercase', fontsize=7, color='#555', ha='center')
    ax.text(12.75, 7.7, '2. scores = bm25.get_scores(tokens)', fontsize=8, color='#333', ha='center')
    ax.text(12.75, 7.3, '   Score ALL docs, then mask', fontsize=7, color='#555', ha='center')
    ax.text(12.75, 6.9, '3. scores[~valid_mask] = 0 (post-filter)', fontsize=8, color='#333', ha='center')
    ax.text(12.75, 6.5, '   Returns: [(doc_id, bm25_score), ...]', fontsize=7, color='#555', ha='center')

    # ---- RRF Fusion ----
    add_arrow(ax, 4.75, 6.5, 9.0, 5.5, color='#333', lw=2)
    add_arrow(ax, 12.75, 6.5, 9.0, 5.5, color='#333', lw=2)
    
    add_box(ax, 5.5, 4.0, 7.0, 1.3,
            'RRF FUSION (Reciprocal Rank Fusion, k=60)\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            'For each citation: rrf_score = Σ 1/(60 + rank_in_list)\n'
            'Merge FAISS ranks + BM25 ranks → sort by combined RRF score',
            '#ffe0b2', '#E65100', fontsize=8)

    # ---- Adaptive Fallback ----
    add_arrow(ax, 9.0, 4.0, 9.0, 3.5)
    
    add_box(ax, 4.0, 2.0, 10.0, 1.3,
            'ADAPTIVE FALLBACK\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            'if len(results) < 5 AND filter was applied:\n'
            '    → RE-SEARCH with filter_codes=[] (full corpus, unfiltered)\n'
            'Prevents empty results from over-specific filtering',
            '#ffcdd2', '#C62828', fontsize=8)

    # ---- Output ----
    add_arrow(ax, 9.0, 2.0, 9.0, 1.5)
    add_box(ax, 5.0, 0.5, 8.0, 0.8,
            'OUTPUT: [(citation_str, rrf_score, text_snippet), ...] (top_k=10)',
            COLORS['output'], COLORS['output_border'], fontsize=9, bold=True)

    # ---- Side panel: Data Volumes ----
    data_box = FancyBboxPatch((0.3, 0.5), 4.0, 5.5, boxstyle="round,pad=0.12",
                               facecolor=COLORS['data'], edgecolor='#6A1B9A', linewidth=2)
    ax.add_patch(data_box)
    ax.text(2.3, 5.7, 'CORPUS STATS', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#4A148C')
    
    stats = [
        'LAWS (laws_de.csv):',
        '  175,933 articles',
        '  2,048 unique SR codes',
        '  973 "available" (≥50 docs)',
        '  Top: OR(3662), ZGB(2395)',
        '        StPO(1306), StGB(1239)',
        '',
        'COURTS (court_considerations):',
        '  2,476,315 entries',
        '  44 unique codes',
        '  39 "available" (≥100 docs)',
        '  Top: 6B_(318K), 2C_(317K)',
        '        5A_(248K), 8C_(231K)',
        '',
        'BGE: 96,465 published',
        '  BGE_V(24K), BGE_II(23K)',
        '  BGE_III(23K), BGE_I(14K)',
        '  BGE_IV(13K)',
    ]
    for i, s in enumerate(stats):
        ax.text(2.3, 5.3 - i*0.27, s, fontsize=7, color='#333', ha='center',
                fontweight='bold' if ':' in s and not s.startswith(' ') else 'normal')

    # ---- Side panel: Performance ----
    perf_box = FancyBboxPatch((14.0, 0.5), 3.5, 5.5, boxstyle="round,pad=0.12",
                               facecolor='#fff9c4', edgecolor='#F9A825', linewidth=2)
    ax.add_patch(perf_box)
    ax.text(15.75, 5.7, 'SEARCH PERF', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#F57F17')
    
    perf = [
        'FAISS (filtered):',
        '  IndexFlatIP brute-force',
        '  With IDSelector: O(|filter|)',
        '  ~5ms for 1K-filtered set',
        '  ~50ms for full 175K',
        '',
        'BM25 (post-filter):',
        '  Full score computation',
        '  Mask non-matching indices',
        '  ~20ms for laws corpus',
        '  ~200ms for courts corpus',
        '',
        'TOTAL per search call:',
        '  ~50-300ms depending on',
        '  corpus + filter size',
        '',
        'Per direction (3 iters):',
        '  ~1-3s search time',
        '  + 1.5-2s LLM time/iter',
    ]
    for i, s in enumerate(perf):
        ax.text(15.75, 5.3 - i*0.27, s, fontsize=7, color='#333', ha='center',
                fontweight='bold' if ':' in s and not s.startswith(' ') else 'normal')

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/architecture_4_search_infrastructure.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print(f"  ✓ {path}")


# ============================================================
# DIAGRAM 5: AGGREGATION & OUTPUT
# ============================================================
def draw_aggregation_detail():
    fig, ax = plt.subplots(1, 1, figsize=(18, 14))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 14)
    ax.axis('off')
    ax.set_facecolor(COLORS['bg'])
    fig.patch.set_facecolor(COLORS['bg'])

    ax.text(9, 13.5, 'PHASE 3: AGGREGATION & OUTPUT — Post-Processing Pipeline',
            ha='center', va='center', fontsize=16, fontweight='bold', color=COLORS['dark'])
    ax.text(9, 13.0, 'Combine all direction results → inject defaults → dedup → rerank → format submission',
            ha='center', va='center', fontsize=10, color='#555', style='italic')

    # ---- Input: Raw Citations ----
    add_box(ax, 3.0, 11.5, 12.0, 1.2,
            'INPUT: all_citations from all directions (raw, may have duplicates)\n'
            'e.g. [("Art. 221 Abs. 1 StPO", 0.87, "..."), ("Art. 212 StPO", 0.72, "..."), '
            '("Art. 29 Abs. 2 BV", 0.65, "..."), ...]  (30-100 raw citations)',
            COLORS['executor'], COLORS['executor_border'], fontsize=8)
    add_arrow(ax, 9.0, 11.5, 9.0, 11.0)

    # ---- Step 1: Detect Case Type ----
    add_box(ax, 1.0, 9.5, 7.5, 1.3,
            'STEP 1: DETECT CASE TYPE\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            'Scan citation prefixes: 6B_/1B_ → "criminal"\n'
            '4A_/5A_ → "civil" | 8C_/9C_ → "social_insurance"\n'
            '2C_/1C_ → "public_law" | else → "unknown"',
            '#fce4ec', '#880E4F', fontsize=7.5)
    add_arrow(ax, 9.0, 10.8, 9.0, 10.8)

    # ---- Step 2: Inject Defaults ----
    add_box(ax, 9.0, 9.5, 8.0, 1.3,
            'STEP 2: INJECT PROCEDURAL DEFAULTS\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            'UNIVERSAL: Art. 42/2 BGG, Art. 95 BGG, Art. 100/1 BGG, Art. 105/1 BGG, Art. 29/2 BV\n'
            'CASE_TYPE: criminal→Art. 78-81 BGG | civil→Art. 72-76 BGG\n'
            'SUBTYPE: 1B_→Art. 221 StPO,Art. 10/2 BV | Only if citation ∈ corpus',
            '#fce4ec', '#880E4F', fontsize=7.5)
    
    add_arrow(ax, 9.0, 9.5, 9.0, 9.0)

    # ---- Step 3: Deduplicate ----
    add_box(ax, 3.0, 7.8, 12.0, 0.9,
            'STEP 3: DEDUPLICATE (exact string match — keep highest score per citation)\n'
            'Before: 50 raw  →  After: ~35 unique citations  |  citation_scores = {cit: max_score}',
            '#ffcdd2', '#C62828', fontsize=8.5)
    add_arrow(ax, 9.0, 7.8, 9.0, 7.3)

    # ---- Step 4: Reranker ----
    rerank_box = FancyBboxPatch((2.0, 5.0), 14.0, 2.2, boxstyle="round,pad=0.12",
                                 facecolor='#e8eaf6', edgecolor='#283593', linewidth=2.5)
    ax.add_patch(rerank_box)
    ax.text(9.0, 6.9, 'STEP 4: QWEN3-RERANKER (Cross-Encoder on GPU 1)',
            ha='center', va='center', fontsize=10, fontweight='bold', color='#1A237E')
    
    ax.text(9.0, 6.4, 'Input: (English question, German citation text) pairs',
            ha='center', va='center', fontsize=8.5, color='#333')
    ax.text(9.0, 6.0, 'Model: Qwen3-Reranker-0.6B computes relevance score for each pair',
            ha='center', va='center', fontsize=8.5, color='#333')
    ax.text(9.0, 5.6, 'Output: sigmoid scores [0,1] — higher = more relevant to the question',
            ha='center', va='center', fontsize=8.5, color='#333')
    ax.text(9.0, 5.2, '~35 candidates × cross-encoder inference ≈ 3-5 seconds total',
            ha='center', va='center', fontsize=8, color='#555', style='italic')
    
    add_arrow(ax, 9.0, 5.0, 9.0, 4.5)

    # ---- Step 5: Cutoff + Cap ----
    add_box(ax, 2.5, 3.0, 6.0, 1.3,
            'STEP 5: SCORE CUTOFF + CAP\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            'Keep: reranker_score ≥ 0.2\n'
            'Cap: maximum 60 citations\n'
            'Sort: descending by reranker score',
            '#ffcdd2', '#C62828', fontsize=8)

    # ---- Safety Override ----
    add_box(ax, 9.5, 3.0, 6.0, 1.3,
            'SAFETY OVERRIDE\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            'If ALL reranker scores < 0.2:\n'
            '→ Return top-10 by score anyway\n'
            'NEVER return empty submission!',
            '#fff9c4', '#F57F17', fontsize=8)
    
    add_arrow(ax, 9.0, 3.0, 9.0, 2.5)

    # ---- Step 6: Prepend Explicit ----
    add_box(ax, 3.0, 1.3, 12.0, 1.0,
            'STEP 6: PREPEND EXPLICIT CITATIONS (regex-extracted from question text)\n'
            'e.g. question mentions "Art. 221 Abs. 1 StPO" → prepend it (score=1.0) if exists in corpus\n'
            'These go FIRST in the output (highest priority — explicitly mentioned by examiner)',
            '#e0f7fa', '#00838F', fontsize=8)
    add_arrow(ax, 9.0, 1.3, 9.0, 0.8)

    # ---- Final Output ----
    add_box(ax, 3.0, 0.0, 12.0, 0.7,
            'OUTPUT → submission.csv: "Art. 221 Abs. 1 StPO;Art. 212 StPO;Art. 226 StPO;BGE 137 IV 122;Art. 29 Abs. 2 BV;..."',
            COLORS['output'], COLORS['output_border'], fontsize=9, bold=True)

    # ---- Side: Thresholds Table ----
    thresh_box = FancyBboxPatch((0.2, 5.0), 1.5, 4.5, boxstyle="round,pad=0.05",
                                 facecolor='#fff9c4', edgecolor='#F9A825', linewidth=1.5)
    ax.add_patch(thresh_box)
    ax.text(0.95, 9.3, 'THRESHOLDS', ha='center', va='center', fontsize=7, fontweight='bold', color='#F57F17')
    thresh = ['cutoff: 0.2', 'max: 60', 'default: 0.3', 'safety: top-10', 'gold max: 43']
    for i, t in enumerate(thresh):
        ax.text(0.95, 8.8 - i*0.35, t, ha='center', va='center', fontsize=6.5, color='#333')

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/architecture_5_aggregation_detail.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()
    print(f"  ✓ {path}")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("Generating detailed architecture diagrams...")
    draw_overall_architecture()
    draw_planner_detail()
    draw_executor_detail()
    draw_search_infrastructure()
    draw_aggregation_detail()
    print("\nAll 5 architecture diagrams generated successfully!")
    print(f"Location: {OUTPUT_DIR}/architecture_*.png")

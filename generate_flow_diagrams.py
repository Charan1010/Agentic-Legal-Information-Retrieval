"""
Generate flow diagrams for the Planner-Director RAG Architecture.
Creates 3 PNG diagrams:
1. High-level overview (3 phases)
2. Detailed planner flow
3. Detailed executor iteration flow
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import os

OUTPUT_DIR = r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition"

# ============================================================
# DIAGRAM 1: High-Level Architecture Overview
# ============================================================
def draw_overview():
    fig, ax = plt.subplots(1, 1, figsize=(14, 18))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 18)
    ax.axis('off')
    ax.set_facecolor('#f8f9fa')
    fig.patch.set_facecolor('#f8f9fa')
    
    # Title
    ax.text(7, 17.3, 'Planner-Director Architecture: Full Pipeline', 
            ha='center', va='center', fontsize=16, fontweight='bold', color='#1a1a2e')
    ax.text(7, 16.8, 'Swiss Legal Citation Retrieval Agent', 
            ha='center', va='center', fontsize=11, color='#555555', style='italic')
    
    # --- INPUT BOX ---
    input_box = FancyBboxPatch((4.5, 15.5), 5, 0.9, boxstyle="round,pad=0.1",
                                facecolor='#e8f4fd', edgecolor='#2196F3', linewidth=2)
    ax.add_patch(input_box)
    ax.text(7, 16.05, 'INPUT', ha='center', va='center', fontsize=9, fontweight='bold', color='#1565C0')
    ax.text(7, 15.75, 'English Legal Question (40 questions)', ha='center', va='center', fontsize=9, color='#333')
    
    # Arrow down
    ax.annotate('', xy=(7, 15.0), xytext=(7, 15.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    
    # --- CONTEXT LOADING ---
    ctx_box = FancyBboxPatch((2.5, 13.8), 9, 1.1, boxstyle="round,pad=0.1",
                              facecolor='#fff3e0', edgecolor='#FF9800', linewidth=2)
    ax.add_patch(ctx_box)
    ax.text(7, 14.65, 'CONTEXT LOADING (one-time at startup)', ha='center', va='center', 
            fontsize=9, fontweight='bold', color='#E65100')
    ax.text(7, 14.25, 'swiss_legal_system.txt | terminology_bridge.txt | procedural_defaults.txt', 
            ha='center', va='center', fontsize=8, color='#555')
    ax.text(7, 13.95, 'routing_guide_laws.txt | routing_guide_courts.txt', 
            ha='center', va='center', fontsize=8, color='#555')
    
    # Arrow down
    ax.annotate('', xy=(7, 13.3), xytext=(7, 13.8),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    
    # --- PHASE 1: PLANNER ---
    phase1 = FancyBboxPatch((1.5, 11.3), 11, 1.9, boxstyle="round,pad=0.15",
                             facecolor='#e8eaf6', edgecolor='#3F51B5', linewidth=2.5)
    ax.add_patch(phase1)
    ax.text(7, 12.9, 'PHASE 1: RECHTSANWALT PLANNER', ha='center', va='center', 
            fontsize=11, fontweight='bold', color='#1A237E')
    ax.text(7, 12.5, '1 LLM call  |  GBNF grammar forces valid JSON  |  ~2s', ha='center', va='center', 
            fontsize=9, color='#333')
    ax.text(7, 12.1, 'Outputs: sachverhalt + rechtsfragen + 3-6 search directions', ha='center', va='center', 
            fontsize=9, color='#555')
    ax.text(7, 11.7, '(each direction: corpus, filter_codes, seed_queries, priority)', ha='center', va='center', 
            fontsize=8, color='#777')
    # Fallback note
    ax.text(12.8, 11.5, 'FALLBACK:\nkeyword\nrules', ha='center', va='center', 
            fontsize=7, color='#C62828', style='italic')
    
    # Arrow down
    ax.annotate('', xy=(7, 10.8), xytext=(7, 11.3),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    
    # --- PHASE 2: SEQUENTIAL EXECUTORS ---
    phase2 = FancyBboxPatch((1.0, 5.5), 12, 5.2, boxstyle="round,pad=0.15",
                             facecolor='#e8f5e9', edgecolor='#4CAF50', linewidth=2.5)
    ax.add_patch(phase2)
    ax.text(7, 10.4, 'PHASE 2: DIRECTION EXECUTORS (Sequential)', ha='center', va='center', 
            fontsize=11, fontweight='bold', color='#1B5E20')
    ax.text(7, 10.0, 'Each direction: 2-3 ReAct iterations  |  ~3-5s per direction', 
            ha='center', va='center', fontsize=9, color='#333')
    
    # Direction boxes
    dirs = [
        ('Direction 1\n(priority 1)', 'Substantive Law\ne.g. StPO, ZGB, OR', '#c8e6c9', 9.0),
        ('Direction 2\n(priority 2)', 'Court Decisions\ne.g. 1B_, 5A_, 6B_', '#a5d6a7', 8.0),
        ('Direction 3\n(priority 3)', 'Related Areas\ne.g. BV + EMRK', '#81c784', 7.0),
        ('Direction N\n(priority 99)', 'Procedural Defaults\nBGG + BV Art. 29', '#66bb6a', 6.0),
    ]
    for i, (title, desc, color, y) in enumerate(dirs):
        box = FancyBboxPatch((2.0, y), 4.5, 0.8, boxstyle="round,pad=0.05",
                              facecolor=color, edgecolor='#388E3C', linewidth=1.5)
        ax.add_patch(box)
        ax.text(4.25, y+0.55, title, ha='center', va='center', fontsize=8, fontweight='bold', color='#1B5E20')
        ax.text(4.25, y+0.2, desc, ha='center', va='center', fontsize=7, color='#333')
        
        # Right side: iteration detail
        iter_box = FancyBboxPatch((7.5, y), 4.5, 0.8, boxstyle="round,pad=0.05",
                                   facecolor='#f1f8e9', edgecolor='#689F38', linewidth=1)
        ax.add_patch(iter_box)
        ax.text(9.75, y+0.55, 'Iter 1: seed queries → FAISS+BM25+RRF', ha='center', va='center', fontsize=7, color='#333')
        ax.text(9.75, y+0.3, 'Iter 2: refine from findings → deeper', ha='center', va='center', fontsize=7, color='#555')
        ax.text(9.75, y+0.08, 'Iter 3: fill gaps (optional)', ha='center', va='center', fontsize=7, color='#777')
        
        # Arrow between direction and iteration
        ax.annotate('', xy=(7.5, y+0.4), xytext=(6.5, y+0.4),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='#388E3C'))
        
        # Arrow down between directions (except last)
        if i < len(dirs)-1:
            ax.annotate('', xy=(4.25, y), xytext=(4.25, y-0.12),
                        arrowprops=dict(arrowstyle='->', lw=1.5, color='#388E3C', 
                                       connectionstyle='arc3,rad=0'))
    
    # "findings passed forward" label
    ax.text(1.5, 7.5, 'findings\npassed\nforward\n↓', ha='center', va='center', 
            fontsize=7, color='#2E7D32', style='italic')
    
    # Arrow down from phase 2
    ax.annotate('', xy=(7, 5.0), xytext=(7, 5.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    
    # --- PHASE 3: AGGREGATION ---
    phase3 = FancyBboxPatch((1.5, 3.0), 11, 1.9, boxstyle="round,pad=0.15",
                             facecolor='#fce4ec', edgecolor='#E91E63', linewidth=2.5)
    ax.add_patch(phase3)
    ax.text(7, 4.6, 'PHASE 3: AGGREGATION + RERANKING', ha='center', va='center', 
            fontsize=11, fontweight='bold', color='#880E4F')
    ax.text(7, 4.2, 'Collect all citations  →  Add procedural defaults  →  Deduplicate', 
            ha='center', va='center', fontsize=9, color='#333')
    ax.text(7, 3.8, 'Qwen3-Reranker (EN query vs DE docs)  →  Score cutoff  →  Top-N', 
            ha='center', va='center', fontsize=9, color='#555')
    ax.text(7, 3.4, 'Regex-extract explicit citations from query text', 
            ha='center', va='center', fontsize=8, color='#777')
    
    # Arrow down
    ax.annotate('', xy=(7, 2.5), xytext=(7, 3.0),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    
    # --- OUTPUT BOX ---
    output_box = FancyBboxPatch((3.5, 1.5), 7, 0.9, boxstyle="round,pad=0.1",
                                 facecolor='#e8f5e9', edgecolor='#4CAF50', linewidth=2)
    ax.add_patch(output_box)
    ax.text(7, 2.05, 'OUTPUT', ha='center', va='center', fontsize=9, fontweight='bold', color='#2E7D32')
    ax.text(7, 1.75, 'Predicted citation list (semicolon-separated) → submission.csv', 
            ha='center', va='center', fontsize=9, color='#333')
    
    # Budget annotation
    ax.text(13, 1.2, 'Budget per Q:\n~20-30s\n5-8 LLM calls\n12-18 searches', 
            ha='center', va='center', fontsize=8, color='#555',
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', edgecolor='#999', alpha=0.8))
    
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'flow_1_overview.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='#f8f9fa')
    plt.close()
    print(f"Saved: {path}")


# ============================================================
# DIAGRAM 2: Planner Detail
# ============================================================
def draw_planner_detail():
    fig, ax = plt.subplots(1, 1, figsize=(14, 12))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 12)
    ax.axis('off')
    ax.set_facecolor('#f8f9fa')
    fig.patch.set_facecolor('#f8f9fa')
    
    ax.text(7, 11.5, 'PHASE 1 Detail: Planner Agent', 
            ha='center', va='center', fontsize=15, fontweight='bold', color='#1A237E')
    
    # Input box
    box = FancyBboxPatch((1, 9.8), 12, 1.3, boxstyle="round,pad=0.1",
                          facecolor='#e3f2fd', edgecolor='#1976D2', linewidth=2)
    ax.add_patch(box)
    ax.text(7, 10.8, 'LLM PROMPT ASSEMBLY', ha='center', va='center', 
            fontsize=10, fontweight='bold', color='#0D47A1')
    
    # Components of prompt
    components = [
        (1.5, 10.3, 'System:\nplanner_system.txt\n(Swiss attorney role)', '#bbdefb'),
        (4.5, 10.3, 'Context:\nswiss_legal_system\n+ terminology_bridge', '#b3e5fc'),
        (7.5, 10.3, 'Taxonomy:\nrouting_guide_laws\n+ routing_guide_courts', '#b2ebf2'),
        (10.5, 10.3, 'User:\nEnglish question\n+ available filter_codes', '#b2dfdb'),
    ]
    for x, y, text, color in components:
        cbox = FancyBboxPatch((x, y-0.45), 2.7, 0.7, boxstyle="round,pad=0.05",
                               facecolor=color, edgecolor='#0277BD', linewidth=1)
        ax.add_patch(cbox)
        ax.text(x+1.35, y-0.1, text, ha='center', va='center', fontsize=7, color='#333')
    
    # Arrow
    ax.annotate('', xy=(7, 9.2), xytext=(7, 9.8),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    
    # LLM call
    llm_box = FancyBboxPatch((4, 8.3), 6, 0.8, boxstyle="round,pad=0.1",
                              facecolor='#ede7f6', edgecolor='#7B1FA2', linewidth=2)
    ax.add_patch(llm_box)
    ax.text(7, 8.8, 'Mistral-7B-Instruct (Q4_K_M) — GPU 0', ha='center', va='center', 
            fontsize=9, fontweight='bold', color='#4A148C')
    ax.text(7, 8.5, 'GBNF Grammar constrains output to valid JSON', ha='center', va='center', 
            fontsize=8, color='#555')
    
    # Arrow
    ax.annotate('', xy=(7, 7.7), xytext=(7, 8.3),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    
    # Decision diamond
    diamond = plt.Polygon([[7, 7.6], [8.5, 7.0], [7, 6.4], [5.5, 7.0]], 
                           facecolor='#fff9c4', edgecolor='#F9A825', linewidth=2)
    ax.add_patch(diamond)
    ax.text(7, 7.0, 'Valid\nJSON?', ha='center', va='center', fontsize=9, fontweight='bold', color='#F57F17')
    
    # Yes path
    ax.annotate('', xy=(7, 5.8), xytext=(7, 6.4),
                arrowprops=dict(arrowstyle='->', lw=2, color='#2E7D32'))
    ax.text(7.3, 6.1, 'YES', fontsize=8, color='#2E7D32', fontweight='bold')
    
    # No path → fallback
    ax.annotate('', xy=(11, 7.0), xytext=(8.5, 7.0),
                arrowprops=dict(arrowstyle='->', lw=2, color='#C62828'))
    ax.text(9.7, 7.2, 'NO (parse error)', fontsize=8, color='#C62828')
    
    # Fallback box
    fb_box = FancyBboxPatch((10, 6.3), 3.2, 1.3, boxstyle="round,pad=0.1",
                             facecolor='#ffebee', edgecolor='#C62828', linewidth=2)
    ax.add_patch(fb_box)
    ax.text(11.6, 7.3, 'FALLBACK', ha='center', va='center', fontsize=9, fontweight='bold', color='#B71C1C')
    ax.text(11.6, 6.95, 'Keyword matching', ha='center', va='center', fontsize=8, color='#333')
    ax.text(11.6, 6.7, '(fallback_rules.txt)', ha='center', va='center', fontsize=8, color='#555')
    ax.text(11.6, 6.45, 'No LLM needed', ha='center', va='center', fontsize=7, color='#777')
    
    # Fallback arrow down
    ax.annotate('', xy=(11.6, 5.5), xytext=(11.6, 6.3),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#C62828'))
    
    # Output box
    out_box = FancyBboxPatch((1.5, 3.5), 11, 2.2, boxstyle="round,pad=0.1",
                              facecolor='#e8f5e9', edgecolor='#388E3C', linewidth=2)
    ax.add_patch(out_box)
    ax.text(7, 5.4, 'PLANNER OUTPUT (Structured JSON)', ha='center', va='center', 
            fontsize=10, fontweight='bold', color='#1B5E20')
    
    # JSON structure
    json_text = '''{
  "sachverhalt": "Brief German facts summary",
  "rechtsfragen": ["Legal question 1", "Legal question 2"],
  "directions": [
    {"priority": 1, "corpus": "laws", "filter_codes": ["StPO"],
     "rechtsgebiet": "Strafprozessrecht",
     "seed_queries": ["Untersuchungshaft Kollusionsgefahr..."]},
    {"priority": 2, "corpus": "courts", "filter_codes": ["1B_"],
     ...},
    {"priority": 99, "corpus": "both", "filter_codes": ["BGG","BV"],
     "rechtsgebiet": "Verfahrensrecht", ...}
  ]
}'''
    ax.text(7, 4.3, json_text, ha='center', va='center', fontsize=7, 
            fontfamily='monospace', color='#333',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='#aaa', alpha=0.8))
    
    # Arrow to next phase
    ax.annotate('', xy=(7, 2.8), xytext=(7, 3.5),
                arrowprops=dict(arrowstyle='->', lw=2.5, color='#333'))
    ax.text(7, 2.5, '→ Pass to Phase 2: Direction Executors (sequential by priority)', 
            ha='center', va='center', fontsize=10, color='#333',
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', edgecolor='#999'))
    
    # Timing note
    ax.text(1.5, 1.5, 'Timing: ~2 seconds\nTokens: ~3000 in / ~500 out\nGPU: 0 (Mistral-7B)', 
            ha='left', va='center', fontsize=8, color='#555',
            bbox=dict(boxstyle='round', facecolor='#fff', edgecolor='#ccc'))
    
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'flow_2_planner_detail.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='#f8f9fa')
    plt.close()
    print(f"Saved: {path}")


# ============================================================
# DIAGRAM 3: Executor Iteration Detail
# ============================================================
def draw_executor_detail():
    fig, ax = plt.subplots(1, 1, figsize=(14, 14))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 14)
    ax.axis('off')
    ax.set_facecolor('#f8f9fa')
    fig.patch.set_facecolor('#f8f9fa')
    
    ax.text(7, 13.5, 'PHASE 2 Detail: Direction Executor (ReAct Loop)', 
            ha='center', va='center', fontsize=15, fontweight='bold', color='#1B5E20')
    ax.text(7, 13.0, 'Repeats for each direction (3-6 directions total, sequential)', 
            ha='center', va='center', fontsize=10, color='#555', style='italic')
    
    # Input context
    ctx_box = FancyBboxPatch((1, 11.5), 12, 1.2, boxstyle="round,pad=0.1",
                              facecolor='#e8f5e9', edgecolor='#388E3C', linewidth=2)
    ax.add_patch(ctx_box)
    ax.text(7, 12.4, 'EXECUTOR INPUTS', ha='center', va='center', 
            fontsize=10, fontweight='bold', color='#1B5E20')
    items = [
        (2, 'Direction plan\n(from planner)'),
        (5, 'Prior findings\n(from earlier dirs)'),
        (8, 'Metadata filter\n(pre-set codes)'),
        (11, 'executor_system.txt\n(specialist prompt)'),
    ]
    for x, text in items:
        ib = FancyBboxPatch((x-0.8, 11.6), 2.3, 0.65, boxstyle="round,pad=0.03",
                             facecolor='#c8e6c9', edgecolor='#2E7D32', linewidth=1)
        ax.add_patch(ib)
        ax.text(x+0.35, 11.92, text, ha='center', va='center', fontsize=7, color='#333')
    
    # Arrow
    ax.annotate('', xy=(7, 10.9), xytext=(7, 11.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    
    # --- ITERATION LOOP ---
    loop_box = FancyBboxPatch((1.5, 3.5), 11, 7.3, boxstyle="round,pad=0.15",
                               facecolor='#f1f8e9', edgecolor='#689F38', linewidth=2, linestyle='--')
    ax.add_patch(loop_box)
    ax.text(7, 10.5, 'ReAct ITERATION LOOP (max 3 iterations)', ha='center', va='center', 
            fontsize=10, fontweight='bold', color='#33691E')
    
    # Step 1: Think
    think_box = FancyBboxPatch((2, 9.2), 10, 1.0, boxstyle="round,pad=0.1",
                                facecolor='#ede7f6', edgecolor='#7B1FA2', linewidth=1.5)
    ax.add_patch(think_box)
    ax.text(7, 9.9, 'THINK: LLM generates query + reasoning', ha='center', va='center', 
            fontsize=9, fontweight='bold', color='#4A148C')
    ax.text(7, 9.55, '{"thought": "Need to find Haftgründe articles...", "query": "Untersuchungshaft Kollusionsgefahr Fluchtgefahr", "done": false}', 
            ha='center', va='center', fontsize=7, fontfamily='monospace', color='#333')
    
    # Arrow
    ax.annotate('', xy=(7, 8.7), xytext=(7, 9.2),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#333'))
    
    # Step 2: Act (Search)
    act_box = FancyBboxPatch((2, 7.3), 10, 1.3, boxstyle="round,pad=0.1",
                              facecolor='#e3f2fd', edgecolor='#1976D2', linewidth=1.5)
    ax.add_patch(act_box)
    ax.text(7, 8.35, 'ACT: Execute filtered search', ha='center', va='center', 
            fontsize=9, fontweight='bold', color='#0D47A1')
    
    # Search pipeline detail
    steps = [
        (2.5, 7.8, 'Qwen3-Embed\n(GPU 1)', '#bbdefb'),
        (5.0, 7.8, 'FAISS\n(filtered)', '#b3e5fc'),
        (7.0, 7.8, 'BM25\n(filtered)', '#b2ebf2'),
        (9.0, 7.8, 'RRF Fusion\n(k=60)', '#b2dfdb'),
        (11.0, 7.8, 'Qwen3-Rerank\n(GPU 1)', '#a7ffeb'),
    ]
    for x, y, text, color in steps:
        sb = FancyBboxPatch((x-0.7, y-0.3), 1.7, 0.55, boxstyle="round,pad=0.03",
                             facecolor=color, edgecolor='#0277BD', linewidth=1)
        ax.add_patch(sb)
        ax.text(x+0.15, y-0.02, text, ha='center', va='center', fontsize=6.5, color='#333')
    # Arrows between search steps
    for i in range(len(steps)-1):
        ax.annotate('', xy=(steps[i+1][0]-0.7, steps[i][1]-0.02), 
                    xytext=(steps[i][0]+1.0, steps[i][1]-0.02),
                    arrowprops=dict(arrowstyle='->', lw=1, color='#0277BD'))
    
    # Arrow
    ax.annotate('', xy=(7, 6.8), xytext=(7, 7.3),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#333'))
    
    # Step 3: Observe
    obs_box = FancyBboxPatch((2, 5.9), 10, 0.8, boxstyle="round,pad=0.1",
                              facecolor='#fff3e0', edgecolor='#FF9800', linewidth=1.5)
    ax.add_patch(obs_box)
    ax.text(7, 6.5, 'OBSERVE: Results returned to LLM', ha='center', va='center', 
            fontsize=9, fontweight='bold', color='#E65100')
    ax.text(7, 6.15, 'Top-10 citations with scores: "Art. 221 Abs. 1 StPO (0.87)", "Art. 212 StPO (0.72)", ...', 
            ha='center', va='center', fontsize=7, color='#333')
    
    # Arrow
    ax.annotate('', xy=(7, 5.4), xytext=(7, 5.9),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#333'))
    
    # Decision: done?
    diamond = plt.Polygon([[7, 5.3], [8.5, 4.7], [7, 4.1], [5.5, 4.7]], 
                           facecolor='#fff9c4', edgecolor='#F9A825', linewidth=2)
    ax.add_patch(diamond)
    ax.text(7, 4.7, 'done?\nor iter<3?', ha='center', va='center', fontsize=8, fontweight='bold', color='#F57F17')
    
    # Loop back arrow (not done)
    ax.annotate('', xy=(2.0, 9.7), xytext=(2.0, 4.7),
                arrowprops=dict(arrowstyle='->', lw=2, color='#F57F17',
                               connectionstyle='arc3,rad=0.3'))
    ax.text(1.3, 7.2, 'NOT\nDONE\n(refine)', ha='center', va='center', fontsize=7, 
            color='#F57F17', fontweight='bold')
    
    # Done path
    ax.annotate('', xy=(7, 3.2), xytext=(7, 4.1),
                arrowprops=dict(arrowstyle='->', lw=2, color='#2E7D32'))
    ax.text(7.5, 3.6, 'DONE', fontsize=8, color='#2E7D32', fontweight='bold')
    
    # Output
    out_box = FancyBboxPatch((3, 2.2), 8, 0.9, boxstyle="round,pad=0.1",
                              facecolor='#e8eaf6', edgecolor='#3F51B5', linewidth=2)
    ax.add_patch(out_box)
    ax.text(7, 2.85, 'DIRECTION OUTPUT', ha='center', va='center', 
            fontsize=9, fontweight='bold', color='#1A237E')
    ax.text(7, 2.5, 'List of found citations → appended to cumulative findings', 
            ha='center', va='center', fontsize=8, color='#333')
    
    # Arrow to next direction
    ax.annotate('', xy=(7, 1.5), xytext=(7, 2.2),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    ax.text(7, 1.2, '→ Next Direction (or Phase 3 if all directions complete)', 
            ha='center', va='center', fontsize=9, color='#333',
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', edgecolor='#999'))
    
    # Timing
    ax.text(12.5, 2.0, 'Per direction:\n~3-5 sec\n2-3 LLM calls\n2-3 searches', 
            ha='center', va='center', fontsize=8, color='#555',
            bbox=dict(boxstyle='round', facecolor='#fff', edgecolor='#ccc'))
    
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'flow_3_executor_detail.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='#f8f9fa')
    plt.close()
    print(f"Saved: {path}")


if __name__ == '__main__':
    draw_overview()
    draw_planner_detail()
    draw_executor_detail()
    print("\nAll 3 flow diagrams generated!")

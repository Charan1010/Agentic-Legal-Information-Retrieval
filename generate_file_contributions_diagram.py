"""
Generate a diagram showing WHAT each file contributes to the agent's intelligence.
Maps each file to its specific contribution/purpose in the pipeline.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

OUTPUT_DIR = r"c:\Users\6764325\OneDrive - MyFedEx\Desktop\Full Pipeline - RAG Competition\Omnilex-Agentic-Retrieval-Competition"

C = {
    'bg': '#1a1a2e',
    'context_file': '#4FC3F7',
    'prompt_file': '#CE93D8',
    'grammar': '#FFD54F',
    'memory': '#EF5350',
    'output': '#66BB6A',
    'phase_bg': '#16213e',
    'card_bg': '#263238',
    'text': '#ffffff',
    'subtext': '#b0bec5',
    'arrow': '#546E7A',
}


def draw_file_contributions():
    fig, ax = plt.subplots(1, 1, figsize=(22, 16))
    fig.patch.set_facecolor(C['bg'])
    ax.set_facecolor(C['bg'])
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 16)
    ax.axis('off')

    # Title
    ax.text(11, 15.5, "What Each File Contributes to the Agent", fontsize=22, fontweight='bold',
            color=C['text'], ha='center', va='center')
    ax.text(11, 15.0, "Every file has a specific role — here's what intelligence each one provides",
            fontsize=11, color=C['subtext'], ha='center', va='center')

    # Helper: draw a contribution card
    def contrib_card(x, y, filename, size, color, contributions, width=6.2, arrow_target=None):
        # File name box
        file_h = 0.5
        rect = FancyBboxPatch((x, y - file_h/2), width, file_h,
                              boxstyle="round,pad=0.05",
                              facecolor=color, edgecolor='white',
                              linewidth=1.0, alpha=0.9)
        ax.add_patch(rect)
        ax.text(x + 0.15, y, filename, fontsize=9, fontweight='bold',
                color='#1a1a1a', ha='left', va='center')
        ax.text(x + width - 0.15, y, size, fontsize=7,
                color='#37474f', ha='right', va='center')

        # Contribution bullets below
        bullet_y = y - 0.6
        for i, (bullet, detail) in enumerate(contributions):
            line_y = bullet_y - i * 0.38
            ax.text(x + 0.3, line_y, f"→ {bullet}", fontsize=8, fontweight='bold',
                    color=C['text'], va='center')
            if detail:
                ax.text(x + 0.5, line_y - 0.2, detail, fontsize=7,
                        color=C['subtext'], va='center')
        
        return y - 0.6 - len(contributions) * 0.38

    # ========================================================================
    # COLUMN 1: CONTEXT FILES (Knowledge)
    # ========================================================================
    col1_x = 0.5
    ax.text(col1_x + 3.1, 14.3, "CONTEXT FILES", fontsize=12, fontweight='bold',
            color=C['context_file'], ha='center')
    ax.text(col1_x + 3.1, 13.9, "Domain knowledge — makes the agent think like a lawyer",
            fontsize=8, color=C['subtext'], ha='center')

    # swiss_legal_system.txt
    contrib_card(col1_x, 13.2, "swiss_legal_system.txt", "7.7 KB", C['context_file'], [
        ("Legal hierarchy", "BV > Bundesgesetze > Verordnungen > Praxis"),
        ("Court structure", "Which division handles which cases (1B_=Haft, 6B_=Straf...)"),
        ("Cross-references", "StPO+BV+BGG always together for criminal procedure"),
        ("BGE numbering", "BGE 137 IV 122 → Band, Abteilung, Seite mapping"),
        ("Case structure", "E.1=procedural, E.3=substance, always same pattern"),
        ("Subsumtion method", "How lawyers think: Norm→Sachverhalt→Rechtsfolge"),
    ])

    # terminology_bridge.txt
    contrib_card(col1_x, 9.6, "terminology_bridge.txt", "8.5 KB", C['context_file'], [
        ("EN→DE translation", '"pre-trial detention" → "Untersuchungshaft"'),
        ("False friends", '"custody" ≠ Haft (= Sorgerecht in family law)'),
        ("Domain terms", "Maps generic English to precise German Fachbegriffe"),
        ("Concept clusters", "Groups related terms (e.g., all Haft-related words)"),
    ])

    # procedural_defaults.txt
    contrib_card(col1_x, 7.0, "procedural_defaults.txt", "6.1 KB", C['context_file'], [
        ("Always-cited norms", "BGG Art. 42/76/78/82/95/100 — appear in EVERY case"),
        ("Case-type mapping", "Straf→Art.78 BGG, Zivil→Art.72, ÖR→Art.82"),
        ("Default injections", "If case=Straf, always prepend these BGG articles"),
        ("Fills semantic gaps", "These norms are unfindable by embedding search"),
    ])

    # ========================================================================
    # COLUMN 2: PROMPT TEMPLATES (Behavior)
    # ========================================================================
    col2_x = 7.8
    ax.text(col2_x + 3.1, 14.3, "PROMPT TEMPLATES", fontsize=12, fontweight='bold',
            color=C['prompt_file'], ha='center')
    ax.text(col2_x + 3.1, 13.9, "Instructions — define HOW the agent behaves",
            fontsize=8, color=C['subtext'], ha='center')

    # planner_system.txt
    contrib_card(col2_x, 13.2, "planner_system.txt", "8.2 KB", C['prompt_file'], [
        ("Role definition", '"Senior Swiss Attorney, 20 years experience"'),
        ("Output schema", "Enforces JSON: sachverhalt, rechtsfragen, directions[]"),
        ("3 worked examples", "Straf/Familien/Sozialversicherung — teaches by example"),
        ("Rules & constraints", "3-6 directions, always include Verfahrensrecht"),
        ("Code injection slot", "{available_law_codes}, {available_court_codes}"),
        ("Thinking process", "6-step checklist before outputting"),
    ])

    # executor_system.txt
    contrib_card(col2_x, 9.5, "executor_system.txt", "2.0 KB", C['prompt_file'], [
        ("Specialist role", '"Du kennst die Struktur von {rechtsgebiet} im Detail"'),
        ("Search strategy", "Iter1=broad, Iter2=deepen from findings, Iter3=fill gaps"),
        ("Query rules", "3-8 words, German only, no article numbers, no repeats"),
        ("Stop signal", 'Output {"done": true} when direction exhausted'),
        ("7 variable slots", "rechtsgebiet, corpus, filter_codes, reasoning, etc."),
    ])

    # executor_procedural.txt
    contrib_card(col2_x, 6.7, "executor_procedural.txt", "2.4 KB", C['prompt_file'], [
        ("Special P≥90 role", "Only for procedural law direction (always last)"),
        ("Case-type detection", "Reads prior_findings to determine Straf/Zivil/ÖR"),
        ("Pre-built seed queries", "5 categories × 2-3 queries each, ready to use"),
        ("Explains WHY", "These norms always cited but semantically invisible"),
    ])

    # fallback_rules.txt
    contrib_card(col2_x, 4.5, "fallback_rules.txt", "6.4 KB", C['prompt_file'], [
        ("Keyword fallback", "If LLM parse fails 2x → rule-based decomposition"),
        ("Domain heuristics", "Maps keywords to codes without LLM"),
        ("Safety net", "Ensures pipeline NEVER returns 0 results"),
    ])

    # ========================================================================
    # COLUMN 3: GRAMMARS + RUNTIME MEMORIES
    # ========================================================================
    col3_x = 15.3
    ax.text(col3_x + 3.1, 14.3, "GRAMMARS & MEMORIES", fontsize=12, fontweight='bold',
            color=C['grammar'], ha='center')
    ax.text(col3_x + 3.1, 13.9, "Constraints + runtime state that evolves",
            fontsize=8, color=C['subtext'], ha='center')

    # planner.gbnf
    contrib_card(col3_x, 13.2, "planner.gbnf", "890 B", C['grammar'], [
        ("Forces valid JSON", "LLM cannot output free text — only JSON tokens"),
        ("Schema enforcement", "Guarantees sachverhalt, rechtsfragen, directions[]"),
        ("Prevents hallucination", "Can't invent fields or skip required ones"),
    ])

    # executor.gbnf
    contrib_card(col3_x, 11.2, "executor.gbnf", "301 B", C['grammar'], [
        ("Forces thought+query+done", 'Only valid: {"thought":"..","query":"..","done":..}'),
        ("Boolean done signal", "Guarantees parseable stop condition"),
        ("Tiny = fast", "301 bytes → minimal constraint overhead"),
    ])

    # Runtime memories
    ax.text(col3_x + 3.1, 9.7, "RUNTIME MEMORIES", fontsize=10, fontweight='bold',
            color=C['memory'], ha='center')
    ax.text(col3_x + 3.1, 9.35, "(not files — built during execution)",
            fontsize=8, color=C['subtext'], ha='center')

    contrib_card(col3_x, 8.7, "{prior_findings}", "0→450 tok", C['memory'], [
        ("Cross-direction memory", "Citations from ALL previous directions"),
        ("Prevents duplicates", "Executor sees what was already found"),
        ("Guides deepening", "Steers next direction based on gaps"),
        ("Rolling window", "Last 20 citations only → bounded growth"),
    ])

    contrib_card(col3_x, 6.4, "{direction_history}", "0→500 tok", C['memory'], [
        ("Within-direction memory", "All queries + results in THIS direction"),
        ("Prevents repeats", "Executor won't re-ask same query"),
        ("Shows what worked", "Which queries got hits → refine strategy"),
    ])

    contrib_card(col3_x, 4.5, "{plan_summary}", "~100 tok", C['memory'], [
        ("Sachverhalt + Rechtsfragen", "Keeps executor focused on THE question"),
        ("Direction count context", '"This is direction 2 of 4"'),
    ])

    # ========================================================================
    # Bottom summary: data flow
    # ========================================================================
    summary_y = 1.5
    rect = FancyBboxPatch((1.0, summary_y - 0.8), 20.0, 1.8,
                          boxstyle="round,pad=0.15",
                          facecolor=C['card_bg'], edgecolor=C['arrow'],
                          linewidth=1.5)
    ax.add_patch(rect)
    
    ax.text(11, summary_y + 0.7, "DATA FLOW SUMMARY", fontsize=10, fontweight='bold',
            color=C['text'], ha='center')
    
    flow_text = (
        "Question → [swiss_legal + routing_guides + terminology → PLANNER → Plan JSON] → "
        "[seed_queries → SEARCH → results] → [executor_system + taxonomy_section + memories → EXECUTOR → new query → SEARCH] × 3 → "
        "[procedural_defaults + all citations → AGGREGATION → final ranked list]"
    )
    ax.text(11, summary_y + 0.1, flow_text, fontsize=7.5,
            color=C['subtext'], ha='center', family='monospace')
    
    ax.text(11, summary_y - 0.4, 
            "Total files: 5 context (37.7 KB knowledge) + 4 prompts (19.0 KB behavior) + 2 grammars (1.2 KB constraints) + 3 runtime memories (growing)",
            fontsize=8, color=C['text'], ha='center')

    plt.tight_layout()
    out_path = f"{OUTPUT_DIR}/architecture_10_file_contributions.png"
    plt.savefig(out_path, dpi=150, bbox_inches='tight',
                facecolor=C['bg'], edgecolor='none')
    plt.close()
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    draw_file_contributions()

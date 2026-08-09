"""
Generate architecture diagrams for the HyDE retrieval pipeline (Cells 5–8).
Outputs PNG files into notebooks/diagrams/
"""

import graphviz
from pathlib import Path

OUT = Path(__file__).parent / "diagrams"
OUT.mkdir(exist_ok=True)


def diagram1_cell_dependencies():
    """High-Level Cell Dependency Flow (5a → 5b → 6 → 7 → 8)"""

    g = graphviz.Digraph("cell_dependencies", format="png")
    g.attr(rankdir="TB", fontname="Helvetica", fontsize="11",
           bgcolor="white", pad="0.5", nodesep="0.6", ranksep="0.8",
           label="Diagram 1: High-Level Cell Dependencies (Cells 5a → 5b → 6 → 7 → 8)",
           labelloc="t", labelfontsize="14", labelfontname="Helvetica", dpi="150")
    g.attr("node", shape="record", style="filled,rounded", fontname="Helvetica", fontsize="10")
    g.attr("edge", fontname="Helvetica", fontsize="9")

    # --- Earlier cells (inputs) ---
    g.node("indices", label="{Cell 2–3: Corpora & Indices|laws_index (BM25Index)\lcourts_index (BM25Index)\l}",
           fillcolor="#E8E8E8", color="#999999")
    g.node("llm", label="{Cell 4: Load LLM|llm (Llama instance)\l}",
           fillcolor="#E8E8E8", color="#999999")
    g.node("train_csv", label="{External: train.csv|query, gold_citations\l}",
           fillcolor="#FFF3CD", color="#FFBF00", style="filled,rounded,dashed")

    # --- Cell 5a ---
    g.node("cell5a", label="{Cell 5a: Few-Shot Example Bank|"
           "OUTPUTS:\l"
           "• law_few_shot_bank  (type → [3 examples])\l"
           "• court_few_shot_bank  (type → [3 examples])\l"
           "• selected_law_examples  (flat list)\l"
           "• selected_court_examples  (flat list)\l"
           "• Each example has: query, query_en,\l"
           "  citation, text, source\l}",
           fillcolor="#D4EDDA", color="#28A745")

    # --- Cell 5b ---
    g.node("cell5b", label="{Cell 5b: Type Registry & Hierarchical Search|"
           "OUTPUTS:\l"
           "• laws_index.doc_types  (numpy array)\l"
           "• courts_index.doc_types  (numpy array)\l"
           "• LAW_TYPE_REGISTRY / COURT_TYPE_REGISTRY\l"
           "• detect_law_type() / detect_court_type()\l"
           "• detect_dominant_type()\l"
           "• hierarchical_bm25_search()\l"
           "• LAW_TYPES_FOR_PROMPT  (string)\l"
           "• COURT_TYPES_FOR_PROMPT  (string)\l}",
           fillcolor="#CCE5FF", color="#007BFF")

    # --- Cell 6 ---
    g.node("cell6", label="{Cell 6: HyDE — Hypothetical Doc Gen + Enhanced Tools|"
           "OUTPUTS:\l"
           "• select_few_shot_examples()  [uses 5a banks + 5b types]\l"
           "• build_hyde_prompt()  [formats few-shot into Mistral prompt]\l"
           "• generate_hypothetical_document()  [calls LLM]\l"
           "• HyDELawSearchTool  (replaces law_tool)\l"
           "• HyDECourtSearchTool  (replaces court_tool)\l"
           "• TOOLS dict  (overwritten with HyDE tools)\l}",
           fillcolor="#F8D7DA", color="#DC3545")

    # --- Cell 7 ---
    g.node("cell7", label="{Cell 7: ReAct Agent|"
           "OUTPUTS:\l"
           "• AGENT_SYSTEM_PROMPT  (+ type registry injected)\l"
           "• parse_all_agent_actions()\l"
           "• run_agent(query) → (citations, logs)\l"
           "• Calls TOOLS['search_laws'] / TOOLS['search_courts']\l}",
           fillcolor="#E2D9F3", color="#6F42C1")

    # --- Cell 8 ---
    g.node("cell8", label="{Cell 8: Load Test Data|"
           "OUTPUTS:\l"
           "• test_df  (DataFrame of queries)\l}",
           fillcolor="#FDE2E2", color="#E85D75")

    # --- Cell 9 ---
    g.node("cell9", label="{Cell 9: Generate Predictions|"
           "Loops test_df → run_agent() → predictions\l}",
           fillcolor="#FDE2E2", color="#E85D75")

    # --- Edges ---
    g.edge("indices", "cell5a", label="laws_index.documents\lcourts_index.documents")
    g.edge("train_csv", "cell5a", label="gold_citations → corpus text\l(resolve to real passages)")
    g.edge("llm", "cell5a", label="generate_synthetic_query()\ltranslate_query_to_english()")

    g.edge("indices", "cell5b", label="laws_index\lcourts_index\l(attach .doc_types)")

    g.edge("cell5a", "cell6", label="law_few_shot_bank\lcourt_few_shot_bank\lselected_*_examples",
           color="#28A745", fontcolor="#28A745")
    g.edge("cell5b", "cell6", label="detect_law_type()\ldetect_court_type()\lhierarchical_bm25_search()",
           color="#007BFF", fontcolor="#007BFF")
    g.edge("llm", "cell6", label="generate_hypothetical_document()\l(LLM inference)")

    g.edge("cell6", "cell7", label="TOOLS dict\l(HyDE search tools)", color="#DC3545", fontcolor="#DC3545")
    g.edge("cell5b", "cell7", label="LAW_TYPES_FOR_PROMPT\lCOURT_TYPES_FOR_PROMPT\l(injected into prompt)",
           color="#007BFF", fontcolor="#007BFF", style="dashed")
    g.edge("llm", "cell7", label="LLM inference\l(agent reasoning)")

    g.edge("cell8", "cell9", label="test_df")
    g.edge("cell7", "cell9", label="run_agent(query)", color="#6F42C1", fontcolor="#6F42C1")

    g.render(str(OUT / "01_cell_dependencies"), cleanup=True)
    print(f"  Saved: {OUT / '01_cell_dependencies.png'}")


def diagram2_cell6_internal():
    """Cell 6 Internal Wiring — How 5a and 5b Merge Inside HyDE Tools"""

    g = graphviz.Digraph("cell6_internal", format="png")
    g.attr(rankdir="TB", fontname="Helvetica", fontsize="11",
           bgcolor="white", pad="0.5", nodesep="0.5", ranksep="0.8",
           label="Diagram 2: Inside Cell 19 (§6) — HyDELawSearchTool.run() with All Decision Branches",
           labelloc="t", labelfontsize="14", labelfontname="Helvetica", dpi="150")
    g.attr("node", shape="box", style="filled,rounded", fontname="Helvetica", fontsize="9")
    g.attr("edge", fontname="Helvetica", fontsize="8")

    # --- Inputs from Cell 15 / 5a (green) ---
    with g.subgraph(name="cluster_5a") as c:
        c.attr(label="From Cell 15 (§5a: Few-Shot Bank)", style="dashed", color="#28A745",
               fontcolor="#28A745", fontname="Helvetica", fontsize="10")
        c.node("fsb_law", label="law_few_shot_bank\n{type → [up to 3 examples]}\neach has: query, query_en,\ncitation, text, source",
               fillcolor="#D4EDDA", color="#28A745")

    # --- Inputs from Cell 17 / 5b (blue) ---
    with g.subgraph(name="cluster_5b") as c:
        c.attr(label="From Cell 17 (§5b: Type Registry + Hierarchical Search)", style="dashed", color="#007BFF",
               fontcolor="#007BFF", fontname="Helvetica", fontsize="10")
        c.node("detect_type_fn", label="detect_law_type()\nregex: scan query for\nknown abbreviations\n(OR, ZGB, StGB, ...)",
               fillcolor="#CCE5FF", color="#007BFF")
        c.node("hier_search_fn", label="hierarchical_bm25_search()\n2-level: detect type → boost",
               fillcolor="#CCE5FF", color="#007BFF")

    # --- Cell 6 internals ---
    with g.subgraph(name="cluster_c6") as c:
        c.attr(label="Cell 19 (§6): HyDE Pipeline — HyDELawSearchTool.run(query)",
               style="solid", color="#DC3545",
               fontcolor="#DC3545", fontname="Helvetica", fontsize="10", bgcolor="#FFF5F5")

        c.node("query_in", label="Input: query string\ne.g. 'Vertrag Kündigung OR'\nor 'contract requirements'",
               shape="oval", fillcolor="#FFE4B5", color="#FF8C00")

        # Step 1: type detection with branching
        c.node("step1", label="Step 1: detect_law_type(query)",
               fillcolor="#CCE5FF", color="#007BFF")
        c.node("step1_decision", label="type_hint found?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="9")
        c.node("step1_yes", label="type_hint = 'OR'\n(regex matched abbreviation)",
               fillcolor="#D4EDDA", color="#28A745", fontsize="8")
        c.node("step1_no", label="type_hint = None\n(no abbreviation in query)",
               fillcolor="#FFDDD2", color="#E85D75", fontsize="8")

        # Step 2: select_few_shot_examples with 3 priority paths
        c.node("step2_header", label="Step 2: select_few_shot_examples(query, type_hint)",
               fillcolor="#D4EDDA", color="#28A745")
        c.node("step2_p1_check", label="Priority 1 check:\ntype_hint in bank?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="8")
        c.node("step2_p1", label="PATH A: Type-Match\nbank[type_hint][:3]\ne.g. bank['OR'] → 3 OR examples\n(best path — exact domain match)",
               fillcolor="#C3E6CB", color="#155724", fontsize="8")
        c.node("step2_p2_check", label="Priority 2 check:\nkeyword overlap > 0?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="8")
        c.node("step2_p2", label="PATH B: Keyword Overlap\nScore each example's query_en\nagainst input query words\nSort by overlap desc → take top N\ne.g. 'contract' matches 'Contract termination'",
               fillcolor="#D4EDDA", color="#28A745", fontsize="8")
        c.node("step2_p3", label="PATH C: Fallback\nTake first N examples\nfrom largest types\n(rare — only if bank nearly empty)",
               fillcolor="#F5C6CB", color="#721C24", fontsize="8")
        c.node("step2_out", label="Result: 3 matched examples\n(may combine paths:\nA fills 2, B fills 1 more)",
               fillcolor="#D4EDDA", color="#28A745")

        # Step 3-4: HyDE generation
        c.node("step3", label="Step 3: build_hyde_prompt()\nInstruction + 3 few-shot examples\n→ Mistral [INST] prompt",
               fillcolor="#F8D7DA", color="#DC3545")

        c.node("step4_check", label="hyde_enabled?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="8")
        c.node("step4_cache", label="Cache check:\nhash(query:type)\nin _hyde_cache?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="8")
        c.node("step4_hit", label="Cache HIT\n→ return cached hyde_doc",
               fillcolor="#D4EDDA", color="#28A745", fontsize="8")
        c.node("step4_gen", label="Step 4: LLM generates\n~300 char German legal text\n→ store in cache",
               fillcolor="#F8D7DA", color="#DC3545")
        c.node("step4_bypass", label="HyDE DISABLED\n→ hyde_doc = original query\n(ablation mode)",
               fillcolor="#FFDDD2", color="#E85D75", fontsize="8")

        # Step 5: dual search
        c.node("step5a", label="Step 5a: hierarchical_bm25_search()\nquery = hyde_doc\ntype_hint = type_hint\n→ hyde_results",
               fillcolor="#CCE5FF", color="#007BFF")
        c.node("step5b", label="Step 5b: hierarchical_bm25_search()\nquery = original query\ntype_hint = type_hint\n→ keyword_results",
               fillcolor="#CCE5FF", color="#007BFF")

        # Step 6: merge with ranking
        c.node("step6", label="Step 6: Merge & Deduplicate\nFor each citation:\n"
               "  found by BOTH → rank 1st (highest confidence)\n"
               "  found by HyDE only → rank 2nd\n"
               "  found by keyword only → rank 3rd",
               fillcolor="#F8D7DA", color="#DC3545")

        # Step 7: format
        c.node("step7_check", label="type boost\napplied?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="8")
        c.node("step7_header", label="Add header:\n[Type boost: OR (explicit)]",
               fillcolor="#F8D7DA", color="#DC3545", fontsize="8")
        c.node("step7_no_header", label="No header\n(no type detected)",
               fillcolor="#E8E8E8", color="#999999", fontsize="8")
        c.node("step7", label="Step 7: Format each result\n- [OR] Art. 1 OR: Zum Abschluss...\n"
               "- [ZGB] Art. 133 ZGB: Das Gericht...\n(CCH-style type labels for LLM context)",
               fillcolor="#F8D7DA", color="#DC3545")

        c.node("output", label="Output:\n1. Formatted results string → agent conversation\n"
               "2. _last_results list → get_last_citations()",
               shape="oval", fillcolor="#FFE4B5", color="#FF8C00")

    # === EDGES ===

    # Step 1
    g.edge("query_in", "step1")
    g.edge("detect_type_fn", "step1", label="function", color="#007BFF", style="dotted")
    g.edge("step1", "step1_decision")
    g.edge("step1_decision", "step1_yes", label="YES\ne.g. 'OR' found", color="#28A745", fontcolor="#28A745")
    g.edge("step1_decision", "step1_no", label="NO\nno abbreviation", color="#E85D75", fontcolor="#E85D75")

    # Step 2 - priority cascade
    g.edge("step1_yes", "step2_header", style="dashed")
    g.edge("step1_no", "step2_header", style="dashed")
    g.edge("step2_header", "step2_p1_check")
    g.edge("fsb_law", "step2_p1_check", label="lookup", color="#28A745", style="dashed")
    g.edge("step2_p1_check", "step2_p1", label="YES\ntype_hint='OR'\nand 'OR' in bank",
           color="#155724", fontcolor="#155724")
    g.edge("step2_p1_check", "step2_p2_check", label="NO\ntype_hint=None\nor type not in bank",
           color="#E85D75", fontcolor="#E85D75")
    g.edge("step2_p2_check", "step2_p2", label="YES\nsome words match", color="#28A745", fontcolor="#28A745")
    g.edge("step2_p2_check", "step2_p3", label="NO\nno overlap at all", color="#E85D75", fontcolor="#E85D75")
    g.edge("step2_p1", "step2_out", label="got ≥3?\nif not, also\ndo P2 for rest", style="dashed")
    g.edge("step2_p2", "step2_out")
    g.edge("step2_p3", "step2_out")

    # Step 3
    g.edge("step2_out", "step3", label="3 examples")

    # Step 4 - cache/generate/bypass
    g.edge("step3", "step4_check")
    g.edge("step4_check", "step4_bypass", label="NO\n(ablation)", color="#E85D75", fontcolor="#E85D75")
    g.edge("step4_check", "step4_cache", label="YES", color="#28A745", fontcolor="#28A745")
    g.edge("step4_cache", "step4_hit", label="HIT", color="#28A745", fontcolor="#28A745")
    g.edge("step4_cache", "step4_gen", label="MISS", color="#E85D75", fontcolor="#E85D75")

    # Step 5 - dual search (both paths always run)
    g.edge("step4_gen", "step5a", label="hyde_doc")
    g.edge("step4_hit", "step5a", label="cached hyde_doc")
    g.edge("step4_bypass", "step5a", label="original query\n(no HyDE)", style="dashed")
    g.edge("query_in", "step5b", label="original query\n(always)", style="dashed", color="#888888")
    g.edge("hier_search_fn", "step5a", label="function", color="#007BFF", style="dotted")
    g.edge("hier_search_fn", "step5b", label="function", color="#007BFF", style="dotted")

    # Step 6
    g.edge("step5a", "step6", label="hyde_results")
    g.edge("step5b", "step6", label="keyword_results")

    # Step 7
    g.edge("step6", "step7_check")
    g.edge("step7_check", "step7_header", label="YES", color="#28A745", fontcolor="#28A745")
    g.edge("step7_check", "step7_no_header", label="NO", color="#E85D75", fontcolor="#E85D75")
    g.edge("step7_header", "step7")
    g.edge("step7_no_header", "step7")
    g.edge("step7", "output")

    g.render(str(OUT / "02_cell6_internal_wiring"), cleanup=True)
    print(f"  Saved: {OUT / '02_cell6_internal_wiring.png'}")


def diagram3_runtime_call_graph():
    """Runtime Call Graph — Single Query Through the Full Pipeline with All Decision Points"""

    g = graphviz.Digraph("runtime_flow", format="png")
    g.attr(rankdir="TB", fontname="Helvetica", fontsize="11",
           bgcolor="white", pad="0.5", nodesep="0.4", ranksep="0.7",
           label="Diagram 3: Runtime Call Graph — run_agent(query) with All Decision Branches",
           labelloc="t", labelfontsize="14", labelfontname="Helvetica", dpi="150")
    g.attr("node", shape="box", style="filled,rounded", fontname="Helvetica", fontsize="9")
    g.attr("edge", fontname="Helvetica", fontsize="8")

    # --- Entry ---
    g.node("input_query", label='User Query (English)\n"What are the requirements\nfor a valid contract?"',
           shape="oval", fillcolor="#FFE4B5", color="#FF8C00")

    # === Cell 7: Agent Loop ===
    with g.subgraph(name="cluster_agent") as c:
        c.attr(label="Cell 22 (§7): ReAct Agent Loop (max 3 iterations)", style="solid",
               color="#6F42C1", fontcolor="#6F42C1", fontname="Helvetica", fontsize="10",
               bgcolor="#F5F0FF")

        c.node("prompt_build", label="Build conversation prompt\nSYSTEM_PROMPT includes:\n"
               "• Tool descriptions (search_laws, search_courts)\n"
               "• In-context ReAct examples\n"
               "• Type registry from Cell 23:\n"
               "  LAW_TYPES_FOR_PROMPT\n"
               "  COURT_TYPES_FOR_PROMPT",
               fillcolor="#E2D9F3", color="#6F42C1")

        c.node("llm_call", label="LLM Inference (Mistral 7B)\n→ generates Thought + Action + Action Input\n"
               "OR Final Answer",
               fillcolor="#E2D9F3", color="#6F42C1")

        c.node("parse_actions", label="parse_all_agent_actions(response)\n→ list of (action, action_input) tuples",
               fillcolor="#E2D9F3", color="#6F42C1")

        # *** Decision: actions found? ***
        c.node("d_actions_found", label="Actions found\nin response?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="9")

        # *** Decision: Final Answer? ***
        c.node("d_final_answer", label='Contains\n"Final Answer:"?', shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="9")

        # PATH: no actions, no final answer
        c.node("path_extract", label="PATH: No actions, no Final Answer\n→ extract any citations from\n"
               "  raw text (regex fallback)\n→ STOP agent loop",
               fillcolor="#FFDDD2", color="#E85D75", fontsize="8")

        # PATH: Final Answer
        c.node("path_final", label='PATH: Final Answer found\n→ extract "Final Answer: ..."\n'
               "→ STOP agent loop\n→ return all_citations collected so far",
               fillcolor="#C3E6CB", color="#155724", fontsize="8")

        # PATH: actions found → dispatch
        c.node("tool_dispatch", label="PATH: Actions found\n→ TOOLS[action](action_input)\n"
               "dispatches to HyDE tool from Cell 19",
               fillcolor="#E2D9F3", color="#6F42C1")

        c.node("obs_trunc", label="truncate_observation_for_llm()\n→ keep first 1200 chars for LLM\n"
               "(full obs kept in logs)",
               fillcolor="#E2D9F3", color="#6F42C1")

        c.node("cite_collect", label="tool.get_last_citations()\n→ extend all_citations[]",
               fillcolor="#E2D9F3", color="#6F42C1")

        c.node("loop_back", label="Append Observation to conversation\n→ iteration += 1",
               fillcolor="#E2D9F3", color="#6F42C1")

        # *** Decision: max iterations? ***
        c.node("d_max_iter", label="iteration < 3?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="9")

        c.node("path_maxed", label="MAX ITERATIONS hit (3)\n→ STOP, return all_citations\n"
               "collected so far",
               fillcolor="#FFDDD2", color="#E85D75", fontsize="8")

    # === Cell 6: HyDE Tool Execution (summarized) ===
    with g.subgraph(name="cluster_hyde") as c:
        c.attr(label="Cell 19 (§6): HyDE Tool .run(query) — see Diagram 2 for full detail",
               style="solid", color="#DC3545", fontcolor="#DC3545",
               fontname="Helvetica", fontsize="10", bgcolor="#FFF5F5")

        c.node("h_detect", label="1. detect_law_type(query)\n→ type_hint",
               fillcolor="#CCE5FF", color="#007BFF")

        # select_few_shot with 3 priority branches
        c.node("h_select", label="2. select_few_shot_examples()",
               fillcolor="#D4EDDA", color="#28A745")
        c.node("d_select_type", label="type_hint\nin bank?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="8")
        c.node("sel_path_a", label="A: bank[type_hint][:3]\n(exact match)",
               fillcolor="#C3E6CB", color="#155724", fontsize="8")
        c.node("sel_path_b", label="B: keyword overlap\nscoring → top N",
               fillcolor="#D4EDDA", color="#28A745", fontsize="8")
        c.node("sel_path_c", label="C: fallback\nlargest types",
               fillcolor="#F5C6CB", color="#721C24", fontsize="8")

        c.node("h_generate", label="3. generate_hypothetical_document()\n→ ~300 char German text (cached)",
               fillcolor="#F8D7DA", color="#DC3545")

        c.node("h_dual_search", label="4. Dual Search:\nhierarchical_bm25_search() × 2\na) query = hyde_doc\nb) query = original",
               fillcolor="#CCE5FF", color="#007BFF")

        # hierarchical_bm25_search branching
        c.node("d_hier_type", label="type_hint\nprovided?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="8")
        c.node("hier_explicit", label="Explicit type_hint\n→ boost × 1.5",
               fillcolor="#CCE5FF", color="#007BFF", fontsize="8")
        c.node("hier_auto", label="Auto-detect:\ndetect_dominant_type()\ncheck top-20 results",
               fillcolor="#CCE5FF", color="#007BFF", fontsize="8")
        c.node("d_dominant", label="dominant\ntype found?", shape="diamond",
               fillcolor="#FFFACD", color="#DAA520", fontsize="8")
        c.node("hier_boost", label="Apply type boost\nscores × 1.5 for matching docs",
               fillcolor="#CCE5FF", color="#007BFF", fontsize="8")
        c.node("hier_noboost", label="No boost\nraw BM25 scores only",
               fillcolor="#E8E8E8", color="#999999", fontsize="8")

        # merge with ranking clarity
        c.node("h_merge", label="5. Merge & Rank\n┌─────────────────────────┐\n"
               "│ RANK 1: found by BOTH   │\n"
               "│ RANK 2: HyDE only       │\n"
               "│ RANK 3: keyword only    │\n"
               "└─────────────────────────┘\nDeduplicate → format with [type] labels",
               fillcolor="#F8D7DA", color="#DC3545")

    # --- Output ---
    g.node("final_output", label="Final Output:\n• Deduplicated citations list\n"
           "• Execution logs (per iteration)\n→ predictions_df for submission",
           shape="oval", fillcolor="#FFE4B5", color="#FF8C00")

    # ============ EDGES ============

    # Entry → Agent
    g.edge("input_query", "prompt_build")
    g.edge("prompt_build", "llm_call")
    g.edge("llm_call", "parse_actions")

    # Decision: actions found?
    g.edge("parse_actions", "d_actions_found")
    g.edge("d_actions_found", "tool_dispatch",
           label="YES\ne.g. Action: search_laws", color="#28A745", fontcolor="#28A745")
    g.edge("d_actions_found", "d_final_answer",
           label="NO\nno Action: line found", color="#E85D75", fontcolor="#E85D75")

    # Decision: Final Answer?
    g.edge("d_final_answer", "path_final",
           label="YES\nFinal Answer: found", color="#28A745", fontcolor="#28A745")
    g.edge("d_final_answer", "path_extract",
           label="NO\ngarbled output", color="#E85D75", fontcolor="#E85D75")

    # Paths that stop
    g.edge("path_final", "final_output", style="dashed", color="#155724")
    g.edge("path_extract", "final_output", style="dashed", color="#E85D75")

    # Tool dispatch → HyDE
    g.edge("tool_dispatch", "h_detect", label="dispatches to\nHyDE tool", color="#DC3545")

    # HyDE internal flow
    g.edge("h_detect", "h_select", label="type_hint")
    # select_few_shot 3 paths
    g.edge("h_select", "d_select_type")
    g.edge("d_select_type", "sel_path_a", label="YES", color="#155724", fontcolor="#155724")
    g.edge("d_select_type", "sel_path_b", label="NO\nbut keywords match", color="#28A745", fontcolor="#28A745")
    g.edge("sel_path_b", "sel_path_c", label="NO matches\nat all", color="#E85D75", fontcolor="#E85D75", style="dashed")
    g.edge("sel_path_a", "h_generate")
    g.edge("sel_path_b", "h_generate")
    g.edge("sel_path_c", "h_generate")

    g.edge("h_generate", "h_dual_search", label="hyde_doc +\noriginal query")

    # hierarchical_bm25_search branching
    g.edge("h_dual_search", "d_hier_type")
    g.edge("d_hier_type", "hier_explicit", label="YES\nexplicit type", color="#28A745", fontcolor="#28A745")
    g.edge("d_hier_type", "hier_auto", label="NO\ntype_hint=None", color="#E85D75", fontcolor="#E85D75")
    g.edge("hier_auto", "d_dominant")
    g.edge("d_dominant", "hier_boost", label="YES\n≥60% of top-20\nare same type", color="#28A745", fontcolor="#28A745")
    g.edge("d_dominant", "hier_noboost", label="NO\nmixed types", color="#E85D75", fontcolor="#E85D75")
    g.edge("hier_explicit", "h_merge", label="boosted results")
    g.edge("hier_boost", "h_merge", label="auto-boosted results")
    g.edge("hier_noboost", "h_merge", label="raw results")

    # Back to agent
    g.edge("h_merge", "tool_dispatch", label="formatted results\nstring", color="#DC3545", style="dashed",
           constraint="false")
    g.edge("tool_dispatch", "obs_trunc")
    g.edge("tool_dispatch", "cite_collect")
    g.edge("obs_trunc", "loop_back")

    # Loop decision
    g.edge("loop_back", "d_max_iter")
    g.edge("d_max_iter", "llm_call", label="YES\ncontinue loop", color="#28A745", fontcolor="#28A745",
           style="dashed")
    g.edge("d_max_iter", "path_maxed", label="NO\nmax 3 reached", color="#E85D75", fontcolor="#E85D75")
    g.edge("path_maxed", "final_output", style="dashed", color="#E85D75")

    g.edge("cite_collect", "final_output", label="after all\niterations done", style="dashed")

    g.render(str(OUT / "03_runtime_call_graph"), cleanup=True)
    print(f"  Saved: {OUT / '03_runtime_call_graph.png'}")


def diagram4_data_structures():
    """Data Structures — What Each Cell Produces & Consumes"""

    g = graphviz.Digraph("data_structures", format="png")
    g.attr(rankdir="LR", fontname="Helvetica", fontsize="11",
           bgcolor="white", pad="0.5", nodesep="0.3", ranksep="1.2",
           label="Diagram 4: Key Data Structures — What Gets Passed Between Cells",
           labelloc="t", labelfontsize="14", labelfontname="Helvetica", dpi="150")
    g.attr("node", shape="record", style="filled,rounded", fontname="Courier", fontsize="8")
    g.attr("edge", fontname="Helvetica", fontsize="8")

    # --- Cell 5a outputs ---
    with g.subgraph(name="cluster_5a_out") as c:
        c.attr(label="Cell 5a Outputs", style="dashed", color="#28A745",
               fontcolor="#28A745", fontname="Helvetica", fontsize="10")

        c.node("bank_struct", label=(
            "{law_few_shot_bank / court_few_shot_bank|"
            "dict[str, list[dict]]\\l"
            "\\l"
            "\\{\\l"
            '  "OR": [\\l'
            "    \\{\\l"
            '      "query": "Vertrag Kuendigung...",\\l'
            '      "query_en": "Contract termination...",\\l'
            '      "citation": "Art. 1 OR",\\l'
            '      "text": "Zum Abschluss...",\\l'
            '      "source": "train.csv" | "synthetic"\\l'
            "    \\},\\l"
            "    ... (up to 3 per type)\\l"
            "  ],\\l"
            '  "ZGB": [...],\\l'
            "\\}\\l"
            "}"
        ), fillcolor="#D4EDDA", color="#28A745")

    # --- Cell 5b outputs ---
    with g.subgraph(name="cluster_5b_out") as c:
        c.attr(label="Cell 5b Outputs", style="dashed", color="#007BFF",
               fontcolor="#007BFF", fontname="Helvetica", fontsize="10")

        c.node("doc_types_struct", label=(
            "{index.doc_types|"
            "numpy.ndarray (dtype=object)\\l"
            "\\l"
            "Parallel to index.documents:\\l"
            "docs:  [doc0, doc1, doc2, ...]\\l"
            'types: ["OR", "OR", "ZGB", ...]\\l'
            "\\l"
            "len == len(index.documents)\\l"
            "}"
        ), fillcolor="#CCE5FF", color="#007BFF")

        c.node("registry_struct", label=(
            "{LAW_TYPE_REGISTRY|"
            "dict[str, dict]\\l"
            "\\l"
            "\\{\\l"
            '  "OR":  \\{"count": 45000, "example": "Art. 1 OR"\\},\\l'
            '  "ZGB": \\{"count": 32000, "example": "Art. 1 ZGB"\\},\\l'
            '  "StGB": \\{"count": 18000, ...\\},\\l'
            "\\}\\l"
            "}"
        ), fillcolor="#CCE5FF", color="#007BFF")

        c.node("prompt_strings", label=(
            "{LAW_TYPES_FOR_PROMPT|"
            "str\\l"
            "\\l"
            '"OR(45000), ZGB(32000), StGB(18000), ..."\\l'
            "\\l"
            "Injected into AGENT_SYSTEM_PROMPT\\l"
            "so LLM knows what types exist\\l"
            "}"
        ), fillcolor="#CCE5FF", color="#007BFF")

    # --- Cell 6: TOOLS ---
    with g.subgraph(name="cluster_6_out") as c:
        c.attr(label="Cell 6 Outputs", style="dashed", color="#DC3545",
               fontcolor="#DC3545", fontname="Helvetica", fontsize="10")

        c.node("tools_struct", label=(
            "{TOOLS dict|"
            "dict[str, HyDE*SearchTool]\\l"
            "\\l"
            "\\{\\l"
            '  "search_laws": HyDELawSearchTool(\\l'
            "      .index = laws_index,\\l"
            "      .top_k = 40,\\l"
            "  ),\\l"
            '  "search_courts": HyDECourtSearchTool(\\l'
            "      .index = courts_index,\\l"
            "      .top_k = 40,\\l"
            "  ),\\l"
            "\\}\\l"
            "\\l"
            "OVERWRITES Cell 3's plain tools\\l"
            "}"
        ), fillcolor="#F8D7DA", color="#DC3545")

    # --- Cell 7: Agent ---
    with g.subgraph(name="cluster_7_out") as c:
        c.attr(label="Cell 7 Outputs", style="dashed", color="#6F42C1",
               fontcolor="#6F42C1", fontname="Helvetica", fontsize="10")

        c.node("agent_struct", label=(
            "{run_agent(query)|"
            "Returns: (citations, logs)\\l"
            "\\l"
            "citations: list[str]\\l"
            '  ["Art. 1 OR", "BGE 127 III 248 E. 3.1"]\\l'
            "\\l"
            "logs: list[dict]  (per iteration)\\l"
            '  [\\{"type":"llm_response", ...\\},\\l'
            '   \\{"type":"tool_execution",\\l'
            '    "tool":"search_laws",\\l'
            '    "citations_found":[...], ...\\},\\l'
            '   \\{"type":"summary",\\l'
            '    "total_citations": N\\}]\\l'
            "}"
        ), fillcolor="#E2D9F3", color="#6F42C1")

    # --- Edges ---
    g.edge("bank_struct", "tools_struct", label="select_few_shot_examples()\nreads bank by type_hint",
           color="#28A745")
    g.edge("doc_types_struct", "tools_struct", label="hierarchical_bm25_search()\nuses doc_types for boosting",
           color="#007BFF")
    g.edge("registry_struct", "prompt_strings", label="summarized\nfor prompt", color="#007BFF", style="dashed")
    g.edge("prompt_strings", "agent_struct", label="injected into\nAGENT_SYSTEM_PROMPT", color="#007BFF")
    g.edge("tools_struct", "agent_struct", label="TOOLS[action](input)\ndispatched by agent", color="#DC3545")

    g.render(str(OUT / "04_data_structures"), cleanup=True)
    print(f"  Saved: {OUT / '04_data_structures.png'}")


if __name__ == "__main__":
    print("Generating architecture diagrams...")
    diagram1_cell_dependencies()
    diagram2_cell6_internal()
    diagram3_runtime_call_graph()
    diagram4_data_structures()
    print(f"\nAll diagrams saved to: {OUT}")

# Planner-Director Architecture: Swiss Legal Citation Retrieval
## Implementation Specification v2.0

> **Purpose:** This document is the single source of truth for implementing the Planner-Director RAG agent. Every design decision, interface contract, threshold, and error path is specified here. An implementer should be able to code the system from this document alone.

---

## Table of Contents
1. [Design Philosophy](#1-design-philosophy)
2. [System Overview](#2-system-overview)
3. [Phase 1: Planner Agent](#3-phase-1-planner-agent)
4. [Phase 2: Direction Executors](#4-phase-2-direction-executors)
5. [Phase 3: Aggregation & Output](#5-phase-3-aggregation--output)
6. [Interface Contracts](#6-interface-contracts)
7. [GBNF Grammar Specifications](#7-gbnf-grammar-specifications)
8. [Metadata Filter System](#8-metadata-filter-system)
9. [Error Handling & Guardrails](#9-error-handling--guardrails)
10. [Computational Budget](#10-computational-budget)
11. [Implementation Phases](#11-implementation-phases)
12. [Verification & Testing](#12-verification--testing)
13. [Context & Prompt Architecture](#13-context--prompt-architecture)

---

## 1. Design Philosophy

### Think Like a Schweizer Rechtsanwalt

The core insight: **a Swiss lawyer doesn't search semantically — they navigate a known structure.**

When a senior Swiss attorney (Rechtsanwalt) receives a legal question, their thought process is:

```
STEP 1: SACHVERHALT ERFASSEN (Grasp the facts)
        → What happened? What's the dispute about? Who are the parties?

STEP 2: RECHTSFRAGE IDENTIFIZIEREN (Identify the legal question)
        → What's the legal issue buried in these facts?
        → Often 2-5 distinct legal sub-questions

STEP 3: RECHTSGEBIET ZUORDNEN (Classify into legal area)
        → Strafrecht? Zivilrecht? Sozialversicherung? Öffentliches Recht?
        → Which specific statute(s) govern this?

STEP 4: SUBSUMTION (Legal subsumption — the core skill)
        → Match facts to legal norms (statutory articles)
        → "Does this fact pattern satisfy the elements of Art. 41 OR?"
        → This is STRUCTURAL matching, not semantic similarity

STEP 5: BUNDESGERICHTSPRAXIS PRÜFEN (Check Federal Court case law)
        → Which BGE (leading decisions) interpret the relevant articles?
        → What's the current doctrine (herrschende Lehre)?
        → Are there recent unreported decisions that shifted interpretation?

STEP 6: VERFAHRENSRECHTLICHE GRUNDLAGEN (Procedural framework)
        → How did this reach the court? (BGG, appeal, Beschwerde)
        → ALWAYS cited even if not the "point" of the question
        → Art. 29 Abs. 2 BV (right to be heard) — appears in 50%+ of cases
        → Art. 100 Abs. 1 BGG (deadline) — appears in nearly every BGer case

STEP 7: QUERVERWEISE + ALLGEMEINER TEIL (Cross-references + General Part)
        → Swiss law is HEAVILY cross-referenced
        → A divorce case cites: ZGB + ZPO + BGG + BV
        → If ANY OR-specific article found → also check OR Art. 97-109
        → If ANY ZGB area → check ZGB Art. 2 (good faith) + Art. 8 (burden of proof)
```

**This is SEQUENTIAL.** Each step informs the next. Steps 1-3 form the PLANNING phase. Steps 4-7 produce DIRECTIONS that execute sequentially (later directions benefit from earlier findings).

### Alignment with Anthropic/OpenAI Agent Design Standards

| Principle | Implementation |
|-----------|---------------|
| **Structured output** (Anthropic) | GBNF grammar forces valid JSON — no "hope and parse" |
| **Tool use with clear schemas** (OpenAI) | Search tool has typed inputs: `query`, `corpus`, `filter_codes`, `top_k` |
| **ReAct pattern** (Yao et al.) | Executor: Thought → Action (search) → Observation → loop |
| **Graceful degradation** (Anthropic) | Planner failure → keyword fallback; executor failure → skip + continue |
| **Minimal authority** (Anthropic) | Each executor sees only its direction's context, not full state |
| **Hard limits** (OpenAI) | Max 3 iterations, 15s timeout, token cap on context injection |
| **Observation grounding** (Anthropic) | Agent only reasons about actual search results, never hallucinated content |
| **Sequential reasoning** (Chain-of-Thought) | Planner's `sachverhalt` → `rechtsfragen` → `directions` is forced CoT |

### Why Sequential Execution (Not Parallel)

1. **Later directions benefit from earlier findings.** Finding BGE 137 IV 122 in Direction 1 tells Direction 2 to search for "same legal principle in different context"
2. **A lawyer builds understanding progressively.** Finding Art. 221 StPO (Haftgründe) → also look for Art. 212, 226, 227 StPO
3. **Token efficiency.** Sequential = later directions know what's found → no duplicate searches
4. **Adaptive.** If early findings reveal unexpected legal areas, later directions can compensate

---

## 2. System Overview

```
INPUT: English legal question
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: PLANNER (1 LLM call, ~2s)                          │
│ Output: {sachverhalt, rechtsfragen, directions[3-6]}         │
│ Constraint: GBNF grammar + post-parse validation             │
│ Fallback: keyword decomposition if JSON parse fails          │
└────────────────────────┬────────────────────────────────────┘
                         │ sequential, by priority
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: DIRECTION EXECUTORS (3-6 dirs, 2-3 iters each)     │
│                                                              │
│ For each direction (sorted by priority ascending):           │
│   Iter 0: Execute seed_queries[0] directly (NO LLM call)    │
│   Iter 1-3: ReAct loop (Think→Search→Observe→Decide)        │
│   Output: citations found in this direction                  │
│   Hard limits: 3 LLM iterations max, 15s timeout            │
│   Next direction receives prior_findings summary             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: AGGREGATION                                         │
│ 1. Collect all citations from all directions                 │
│ 2. Inject procedural defaults (rule-based, per case type)    │
│ 3. Deduplicate (exact string match, keep highest score)      │
│ 4. Qwen3-Reranker (EN query vs DE documents)                │
│ 5. Score cutoff ≥ 0.2, max 60 citations                     │
│ 6. Prepend regex-extracted citations from query text         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
OUTPUT: Semicolon-separated citation string → submission.csv
```

---

## 3. Phase 1: Planner Agent

### Role & Purpose

The planner embodies Steps 1-3 of the Swiss lawyer's thought process. It receives an English legal question and produces a **structured research plan** in one LLM call.

### Input Assembly

```python
planner_messages = [
    {
        "role": "system",
        "content": load("prompts/planner_system.txt").format(
            available_law_codes=", ".join(sorted(law_code_to_indices.keys())),
            available_court_codes=", ".join(sorted(court_code_to_indices.keys()))
        )
    },
    {
        "role": "user",
        "content": f"""KONTEXT (Schweizerisches Rechtssystem):
{load("context/swiss_legal_system.txt")}

GESETZES-ROUTING (Taxonomie & Klassifikation):
{load("context/routing_guide_laws.txt")}

GERICHTS-ROUTING (Abteilungen & Praefixe):
{load("context/routing_guide_courts.txt")}

TERMINOLOGIE (Englisch → Deutsch):
{load("context/terminology_bridge.txt")}

FRAGE: {english_question}"""
    }
]
```

**Token budget:** ~9,600 tokens context + ~800 tokens output = ~10,400 total. Requires n_ctx≥16384.

### Output Schema (Enforced by GBNF Grammar)

```json
{
  "sachverhalt": "Brief summary of the facts in German (1-2 sentences)",
  "rechtsfragen": ["Legal sub-question 1 in German", "Legal sub-question 2"],
  "directions": [
    {
      "priority": 1,
      "corpus": "laws",
      "rechtsgebiet": "Name of the legal area",
      "filter_codes": ["StPO"],
      "reasoning": "Why this direction (1 sentence)",
      "seed_queries": ["German search terms 3-8 words", "Alternative German query"]
    },
    {
      "priority": 2,
      "corpus": "courts",
      "rechtsgebiet": "Court decisions area",
      "filter_codes": ["1B_", "BGE_IV"],
      "reasoning": "Why search these court divisions",
      "seed_queries": ["German court search terms"]
    },
    {
      "priority": 99,
      "corpus": "both",
      "rechtsgebiet": "Verfahrensrecht",
      "filter_codes": ["BGG", "BV"],
      "reasoning": "Procedural defaults — always cited",
      "seed_queries": ["Beschwerde Bundesgericht Legitimation Frist"]
    }
  ]
}
```

### Field Semantics

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `sachverhalt` | string | 10-100 words, German | Forces fact comprehension (CoT step 1) |
| `rechtsfragen` | string[] | 1-5 items, German | Forces legal issue identification (CoT step 2) |
| `directions` | object[] | 3-6 items | Research directions (CoT step 3) |
| `directions[].priority` | int | 1-99 | Execution order (lower = first). 99 = procedural |
| `directions[].corpus` | enum | `"laws"` \| `"courts"` \| `"both"` | Which corpus to search |
| `directions[].rechtsgebiet` | string | Free text | Legal area name for executor context |
| `directions[].filter_codes` | string[] | 1-4 items, from available list | Metadata filter keys |
| `directions[].reasoning` | string | 1 sentence | Why this direction exists |
| `directions[].seed_queries` | string[] | 1-3 items, 3-10 German words each | Initial search terms |

### Planner Rules (Encoded in Prompt)

1. **Minimum 3 directions** — ensures multi-area coverage
2. **Always include procedural direction** (priority 99) with `["BGG", "BV"]`
3. **Always include both statutes AND court decisions** (at least one `"laws"` and one `"courts"`)
4. **filter_codes must exist** in the provided available list — NEVER invent codes
5. **seed_queries in German legal terminology** — use terminology_bridge, not literal English translation
6. **Allgemeiner Teil rule:** If searching specific OR articles → add direction for OR Art. 97-109. If ZGB → ensure ZGB Art. 2/8 coverage
7. **If <4 directions planned → add unfiltered catch-all direction** as safety net

### Fallback: Keyword-Based Decomposition

If planner JSON fails to parse (after 1 retry):

```python
def fallback_decompose(question: str) -> Plan:
    """Rule-based direction decomposition from fallback_rules.txt"""
    directions = []
    q_lower = question.lower()
    
    # Match keywords → directions (see prompts/fallback_rules.txt for full mapping)
    if any(kw in q_lower for kw in ["detention", "custody", "pre-trial", "remand"]):
        directions.append(Direction(corpus="laws", filter_codes=["StPO"], ...))
        directions.append(Direction(corpus="courts", filter_codes=["1B_"], ...))
    # ... (full keyword mapping in fallback_rules.txt)
    
    # ALWAYS add procedural
    directions.append(Direction(corpus="laws", filter_codes=["BGG", "BV"], priority=99))
    
    # If nothing matched → unfiltered broad search
    if len(directions) <= 1:
        directions.insert(0, Direction(corpus="laws", filter_codes=[]))
        directions.insert(1, Direction(corpus="courts", filter_codes=[]))
    
    return Plan(sachverhalt="", rechtsfragen=[], directions=directions)
```

---

## 4. Phase 2: Direction Executors

### Role & Purpose

Each executor embodies Steps 4-5 of the Swiss lawyer's thought process: deep-diving into one specific legal area with targeted, iterative searches. It is a **specialist** who knows only its domain.

### Execution Model: ReAct with Iteration 0

```
┌─────────────────────────────────────────────────────────────────┐
│ DIRECTION EXECUTION (per direction)                              │
│                                                                  │
│ Iteration 0 (NO LLM call — orchestrator does this):             │
│   → Execute seed_queries[0] with metadata filter                 │
│   → Store results as initial direction_history                   │
│                                                                  │
│ Iteration 1-3 (ReAct LLM calls):                                │
│   THINK: LLM sees results so far, generates reasoning            │
│   ACT:   LLM outputs next query (German, 3-10 words)            │
│   SEARCH: Orchestrator runs filtered_hybrid_search()             │
│   OBSERVE: Top-10 results formatted and fed back to LLM         │
│   DECIDE: LLM sets done=true or continues                        │
│                                                                  │
│ Output: All citations found across all iterations                │
└─────────────────────────────────────────────────────────────────┘
```

### Executor Input Assembly

```python
executor_messages = [
    {
        "role": "system",
        "content": load("prompts/executor_system.txt").format(
            rechtsgebiet=direction.rechtsgebiet,
            corpus=direction.corpus,
            filter_codes=", ".join(direction.filter_codes),
            reasoning=direction.reasoning,
            plan_summary=f"Sachverhalt: {plan.sachverhalt}\n"
                        f"Rechtsfragen: {'; '.join(plan.rechtsfragen)}\n"
                        f"This is direction {i+1} of {len(plan.directions)}",
            prior_findings=format_prior_findings(all_citations_so_far),
            direction_history=format_direction_history(this_direction_results)
        )
    },
    {
        "role": "user",
        "content": "Generiere deine nächste Suchanfrage oder signalisiere done."
    }
]
```

### Executor Output Schema (Enforced by GBNF Grammar)

```json
{"thought": "Reasoning about what to search next", "query": "German search terms 3-10 words", "done": false}
```

Or when finished:
```json
{"thought": "Reasoning about why direction is complete", "query": "", "done": true}
```

### Observation Format (What Executor Sees After Search)

```
SUCHERGEBNISSE (Filter: StPO, 8 Treffer):
1. "Art. 221 Abs. 1 StPO" (0.87) — Haftgründe Flucht Kollusion Wiederholung
2. "Art. 212 StPO" (0.72) — Anordnung und Dauer Untersuchungshaft allgemein
3. "Art. 226 StPO" (0.69) — Entscheid Zwangsmassnahmengericht Haftanordnung
4. "Art. 227 StPO" (0.65) — Verlängerung der Untersuchungshaft Antrag
5. "Art. 222 StPO" (0.61) — Rechte des Beschuldigten während Haft
6. "Art. 228 StPO" (0.58) — Haftentlassungsgesuch Voraussetzungen
7. "Art. 197 StPO" (0.52) — Verhältnismässigkeit Zwangsmassnahmen allgemein
8. "Art. 5 Ziff. 3 EMRK" (0.48) — Recht auf Haftprüfung innert Frist
```

### Executor Strategy (Encoded in Prompt)

- **Iteration 1:** Analyze iteration 0 results → what's found, what's missing
- **Iteration 2:** Search RELATED concepts. If found Art. 221 StPO → search "Haftprüfung Zwangsmassnahmengericht Verhältnismässigkeit"
- **Iteration 3:** Fill gaps — cross-references, Allgemeiner Teil, adjacent articles

### Executor Rules (Encoded in Prompt)

1. **Queries must be in German** — no English terms
2. **3-10 words per query** — longer = less precise with embeddings
3. **No article numbers in queries** — embedding model understands concepts, not numbers
4. **Never repeat a query** already in direction_history
5. **Use structural knowledge** — if found Art. X, think about what Art. Y must exist nearby

### Procedural Direction (Special Case)

The last direction (priority 99) uses `prompts/executor_procedural.txt` instead of `executor_system.txt`. This specialized prompt:
- Determines appeal type from prior findings (1B_ found → criminal procedure)
- Has pre-built seed queries per appeal type
- Knows exactly which BGG/BV/ATSG articles to search for

---

## 5. Phase 3: Aggregation & Output

### Step-by-Step Process

```python
def aggregate_and_output(all_direction_citations, question):
    # 1. Flatten all citations from all directions
    all_citations = []
    for direction_results in all_direction_citations:
        all_citations.extend(direction_results)
    
    # 2. Inject procedural defaults (rule-based)
    case_type = detect_case_type(all_citations)
    defaults = get_procedural_defaults(case_type)
    for default_citation in defaults:
        if default_citation in corpus_citation_set:  # MUST exist in corpus
            all_citations.append((default_citation, 0.3))
    
    # 3. Deduplicate — keep highest score per citation string
    citation_scores = {}
    for citation, score in all_citations:
        if citation not in citation_scores or score > citation_scores[citation]:
            citation_scores[citation] = score
    
    # 4. Rerank with Qwen3-Reranker
    candidates = list(citation_scores.keys())
    rerank_scores = qwen3_reranker(query=question, documents=candidates)
    
    # 5. Apply cutoff + cap
    final = [(cit, score) for cit, score in zip(candidates, rerank_scores) if score >= 0.2]
    final.sort(key=lambda x: x[1], reverse=True)
    final = final[:60]
    
    # SAFETY: never return empty
    if not final:
        final = sorted(zip(candidates, rerank_scores), key=lambda x: x[1], reverse=True)[:10]
    
    # 6. Prepend regex-extracted explicit citations from query
    explicit = regex_extract_citations(question)
    for cit in reversed(explicit):
        if cit in corpus_citation_set and cit not in [f[0] for f in final]:
            final.insert(0, (cit, 1.0))
    
    return ";".join([cit for cit, score in final])
```

### Aggregation Thresholds (SPECIFIED)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Reranker score cutoff | **≥ 0.2** | Qwen3-Reranker sigmoid; 0.2 = weak positive. Conservative |
| Max citations | **60** | Gold sets max 43; safety margin |
| Dedup strategy | Exact string match | Keep highest score |
| Procedural default base score | **0.3** | Survives cutoff, overridable by reranker |
| Safety override | If ALL < 0.2 → return top-10 | Never return empty |

### Procedural Defaults Injection Rules

```python
UNIVERSAL_DEFAULTS = [
    "Art. 42 Abs. 2 BGG", "Art. 95 BGG", "Art. 100 Abs. 1 BGG",
    "Art. 105 Abs. 1 BGG", "Art. 29 Abs. 2 BV"
]

CASE_TYPE_DEFAULTS = {
    "criminal": ["Art. 78 Abs. 1 BGG", "Art. 80 Abs. 1 BGG", "Art. 81 Abs. 1 BGG"],
    "civil": ["Art. 72 Abs. 1 BGG", "Art. 74 Abs. 1 BGG", "Art. 76 Abs. 1 BGG"],
    "public_law": ["Art. 82 BGG", "Art. 89 Abs. 1 BGG"],
    "social_insurance": ["Art. 61 ATSG", "Art. 16 ATSG"],
}

SUBTYPE_DEFAULTS = {
    "1B_": ["Art. 221 Abs. 1 StPO", "Art. 10 Abs. 2 BV", "Art. 31 Abs. 3 BV"],
    "5A_": ["Art. 98 BGG", "Art. 9 BV"],
    "6B_": ["Art. 47 StGB", "Art. 50 StGB"],
    "8C_": ["Art. 4 Abs. 1 IVG", "Art. 16 ATSG"],
}

def detect_case_type(citations):
    prefixes = set()
    for cit, _ in citations:
        if "_" in cit and cit[0].isdigit():
            prefixes.add(cit.split("/")[0].split("_")[0] + "_")
    
    if "6B_" in prefixes or "1B_" in prefixes:
        return "criminal"
    elif "4A_" in prefixes or "5A_" in prefixes:
        return "civil"
    elif "8C_" in prefixes or "9C_" in prefixes:
        return "social_insurance"
    elif "2C_" in prefixes or "1C_" in prefixes:
        return "public_law"
    return "unknown"
```

---

## 6. Interface Contracts

### Contract 1: Planner → Orchestrator

| Field | Consumer | Notes |
|-------|----------|-------|
| `sachverhalt` | Executor `{plan_summary}` | Passed to every executor |
| `rechtsfragen` | Executor `{plan_summary}` | Passed to every executor |
| `directions[].priority` | Orchestrator loop | Determines execution order (ascending) |
| `directions[].corpus` | `filtered_hybrid_search()` | Selects corpus |
| `directions[].filter_codes` | `filtered_hybrid_search()` | Pre-applied to every search |
| `directions[].seed_queries[0]` | Orchestrator iteration 0 | Executed WITHOUT LLM call |
| `directions[].rechtsgebiet` | Executor prompt `{rechtsgebiet}` | Role context |
| `directions[].reasoning` | Executor prompt `{reasoning}` | Direction context |

### Contract 2: Orchestrator → Executor

| Template Variable | Source | Max Size |
|-------------------|--------|----------|
| `{rechtsgebiet}` | `direction.rechtsgebiet` | ~20 tokens |
| `{corpus}` | `direction.corpus` | 1 word |
| `{filter_codes}` | Joined string | ~50 tokens |
| `{reasoning}` | `direction.reasoning` | ~30 tokens |
| `{taxonomy_section}` | `get_taxonomy_section(direction.filter_codes)` | ~150-400 tokens |
| `{plan_summary}` | sachverhalt + rechtsfragen + direction index | ~200 tokens |
| `{prior_findings}` | Last 20 citations from earlier dirs | Max 1000 tokens |
| `{direction_history}` | This direction's queries + results | Max 2000 tokens |

### Contract 3: Executor → Orchestrator

| Field | Type | Semantics |
|-------|------|-----------|
| `thought` | string | Reasoning (logged, not used downstream) |
| `query` | string | Next search query. Empty = done |
| `done` | boolean | true = direction complete |

### Contract 4: Search Tool

```python
def filtered_hybrid_search(
    query: str,           # German, 3-10 words
    corpus: str,          # "laws" | "courts"
    filter_codes: list,   # e.g. ["StPO"] or ["1B_", "BGE_IV"]
    top_k: int = 10
) -> list[tuple[str, float, str]]:
    """Returns: [(citation_string, score, snippet), ...]"""
```

---

## 7. GBNF Grammar Specifications

### Planner Grammar (`prompts/planner.gbnf`)

```gbnf
root ::= "{" ws "\"sachverhalt\"" ws ":" ws string "," ws "\"rechtsfragen\"" ws ":" ws string-array "," ws "\"directions\"" ws ":" ws directions-array ws "}"

string-array ::= "[" ws string (ws "," ws string)* ws "]"

directions-array ::= "[" ws direction (ws "," ws direction){2,5} ws "]"

direction ::= "{" ws "\"priority\"" ws ":" ws integer "," ws "\"corpus\"" ws ":" ws corpus-val "," ws "\"rechtsgebiet\"" ws ":" ws string "," ws "\"filter_codes\"" ws ":" ws string-array "," ws "\"reasoning\"" ws ":" ws string "," ws "\"seed_queries\"" ws ":" ws string-array ws "}"

corpus-val ::= "\"laws\"" | "\"courts\"" | "\"both\""

integer ::= [0-9]+

string ::= "\"" ([^"\\] | "\\" .)* "\""

ws ::= [ \t\n]*
```

**Constraint:** `directions-array` requires 3-6 items (`{2,5}` = 2-5 additional after first).

### Executor Grammar (`prompts/executor.gbnf`)

```gbnf
root ::= "{" ws "\"thought\"" ws ":" ws string "," ws "\"query\"" ws ":" ws string "," ws "\"done\"" ws ":" ws boolean ws "}"

string ::= "\"" ([^"\\] | "\\" .)* "\""

boolean ::= "true" | "false"

ws ::= [ \t\n]*
```

---

## 8. Metadata Filter System

### Filter Code Naming Convention (CANONICAL)

| Corpus | Code Format | Examples |
|--------|-------------|----------|
| Laws | Statute abbreviation | `StGB`, `StPO`, `OR`, `ZGB`, `BGG`, `BV`, `IVG`, `ATSG`, `AIG`, `SchKG`, `KVG`, `UVG`, `AVIG`, `BVG`, `ZPO`, `DBG`, `StBOG`, `RPG`, `USG`, `IPRG` |
| Courts (prefix) | Division prefix | `1B_`, `1C_`, `2C_`, `4A_`, `5A_`, `6B_`, `8C_`, `9C_` |
| Courts (BGE) | `BGE_` + roman | `BGE_I`, `BGE_II`, `BGE_III`, `BGE_IV`, `BGE_V` |

**CRITICAL:** These are the ONLY valid formats. Planner prompt injects the actual available list dynamically. Orchestrator **validates** codes post-parse and removes any invalid ones.

### Implementation

```python
# Built at startup from corpus parsing
law_code_to_indices: dict[str, np.ndarray]    # {"StPO": array([0,1,2,...]), ...}
court_code_to_indices: dict[str, np.ndarray]  # {"1B_": array([...]), "BGE_IV": array([...]), ...}
corpus_citation_set: set[str]                 # All valid citation strings

def filtered_hybrid_search(query, corpus, filter_codes, top_k=10):
    if corpus == "both":
        law_codes = [c for c in filter_codes if c in law_code_to_indices]
        court_codes = [c for c in filter_codes if c in court_code_to_indices]
        r_law = filtered_hybrid_search(query, "laws", law_codes, top_k)
        r_court = filtered_hybrid_search(query, "courts", court_codes, top_k)
        return rrf_merge(r_law, r_court)[:top_k]
    
    # Select index map
    code_map = law_code_to_indices if corpus == "laws" else court_code_to_indices
    
    # Union all valid indices
    if filter_codes:
        arrays = [code_map[c] for c in filter_codes if c in code_map]
        if arrays:
            valid_indices = np.unique(np.concatenate(arrays))
        else:
            valid_indices = None  # unfiltered
    else:
        valid_indices = None  # unfiltered
    
    # FAISS search (with IDSelector if filtered)
    query_vec = embed(query)
    if valid_indices is not None:
        id_selector = faiss.IDSelectorArray(len(valid_indices), 
                                            faiss.swig_ptr(valid_indices))
        params = faiss.SearchParametersIVF(sel=id_selector)
        faiss_scores, faiss_ids = index.search(query_vec, top_k, params=params)
    else:
        faiss_scores, faiss_ids = index.search(query_vec, top_k)
    
    # BM25 post-filter
    bm25_all = bm25_search(query, top_k=top_k * 5)
    if valid_indices is not None:
        valid_set = set(valid_indices.tolist())
        bm25_filtered = [(did, s) for did, s in bm25_all if did in valid_set][:top_k]
    else:
        bm25_filtered = bm25_all[:top_k]
    
    # RRF fusion (k=60)
    combined = rrf_fuse(faiss_results, bm25_filtered, k=60)
    
    # ADAPTIVE FALLBACK: if <5 results, broaden to full corpus
    if len(combined) < 5 and valid_indices is not None:
        combined = filtered_hybrid_search(query, corpus, [], top_k)
    
    return combined[:top_k]
```

---

## 9. Error Handling & Guardrails

### Error Matrix

| Error | Detection | Response | Retry? |
|-------|-----------|----------|--------|
| Planner JSON parse fail | `json.loads()` raises | Append "Output NUR valides JSON" + retry | Yes (1x) |
| Planner retry fails | 2nd parse failure | `fallback_decompose(question)` | No |
| Invalid filter_codes | Code not in index | Remove invalid; if all gone → unfiltered | No |
| <3 directions | `len(dirs) < 3` | Add catch-all + procedural | No |
| Executor JSON parse fail | `json.loads()` raises | Retry with "Output NUR JSON" | Yes (1x) |
| Executor retry fails | 2nd parse failure | Force done, move on | No |
| 0 search results | `len(results) == 0` | Remove filter, retry unfiltered | Yes (1x) |
| Repeated query | Query in history | Force done, next direction | No |
| Exceeds 3 iterations | `iter > 3` | Force done (hard cap) | No |
| Exceeds 15s | Wall-clock | Kill, force done | No |
| `prior_findings` overflow | >1000 tokens | Truncate to last 20 citations | N/A |
| `direction_history` overflow | >2000 tokens | Keep latest iteration only | N/A |
| All reranker scores < 0.2 | Below threshold | Return top-10 anyway | No |

### Main Orchestrator

```python
def run_pipeline(question: str) -> str:
    # PHASE 1
    plan = run_planner(question)
    if plan is None:
        plan = fallback_decompose(question)
    plan = validate_plan(plan)  # remove bad codes, ensure min 3 dirs
    
    # PHASE 2
    all_citations = []
    prior_findings = []
    
    for direction in sorted(plan.directions, key=lambda d: d.priority):
        start = time.time()
        direction_cits = []
        history = []
        
        # Iteration 0: seed query (no LLM)
        if direction.seed_queries:
            results = filtered_hybrid_search(
                direction.seed_queries[0], direction.corpus,
                direction.filter_codes, top_k=10)
            direction_cits.extend(results)
            history.append({"query": direction.seed_queries[0], "results": results})
        
        # Iterations 1-3: ReAct
        for iteration in range(1, 4):
            if time.time() - start > 15:
                break
            
            prompt = select_prompt(direction)  # executor_system or executor_procedural
            response = llm_call(prompt.format(...), grammar="executor.gbnf", max_tokens=200)
            
            parsed = safe_json_parse(response)
            if parsed is None:
                response = llm_call(prompt + "\nOutput NUR JSON.", grammar="executor.gbnf")
                parsed = safe_json_parse(response)
                if parsed is None:
                    break
            
            if parsed["done"] or not parsed["query"].strip():
                break
            if parsed["query"] in [h["query"] for h in history]:
                break
            
            results = filtered_hybrid_search(
                parsed["query"], direction.corpus, direction.filter_codes, top_k=10)
            
            if not results and direction.filter_codes:
                results = filtered_hybrid_search(
                    parsed["query"], direction.corpus, [], top_k=10)
            
            direction_cits.extend(results)
            history.append({"query": parsed["query"], "results": results})
        
        all_citations.extend(direction_cits)
        prior_findings = (prior_findings + direction_cits)[-20:]
    
    # PHASE 3
    return aggregate_and_output(all_citations, question)
```

---

## 10. Computational Budget

### Per-Question Breakdown

| Stage | Time | LLM Calls | Searches |
|-------|------|-----------|----------|
| Phase 1: Planner | ~2s | 1 | 0 |
| Phase 2: Iter 0 (4 dirs) | ~4s | 0 | 4 |
| Phase 2: Iters 1-2 (4 dirs) | ~16s | ~8 | ~8 |
| Phase 3: Rerank | ~5s | 0 | 0 |
| **Per question total** | **~27s** | **~9** | **~12** |
| **40 questions** | **~18 min** | **~360** | **~480** |

### Memory Budget

| Component | Location | Memory |
|-----------|----------|--------|
| Mistral-7B Q4_K_M | GPU 0 | ~4.0 GB |
| Qwen3-Embedding-0.6B (fp16) | GPU 1 | ~1.2 GB |
| Qwen3-Reranker-0.6B | GPU 1 | ~1.2 GB |
| FAISS indices | CPU/RAM | ~800 MB |
| Metadata arrays | CPU/RAM | ~5 MB |
| BM25 indices | CPU/RAM | ~200 MB |
| **Total** | | **~7.4 GB** |

### vs Current Architecture

| Metric | Current (HYDE) | New (Planner-Director) |
|--------|---------------|----------------------|
| Time/question | ~4 min | ~27s (**9x faster**) |
| Total (40 Q) | ~160 min | ~18 min |
| Legal areas searched | 1-2 | 4-6 (**3x coverage**) |
| Search space | Full 200K | Targeted subsets (**20x smaller**) |

---

## 11. Implementation Phases

### Phase A: Metadata Filter Infrastructure [BLOCKING]

```
A1: Parse law codes from laws_de.csv citation column
A2: Parse court codes from court_considerations.csv citation column
A3: Build law_code_to_indices + court_code_to_indices + corpus_citation_set
A4: Implement filtered_hybrid_search() with adaptive fallback
A5: Create .gbnf grammar files
A6: Verify: every doc maps to exactly one code
```

### Phase B: Planner Agent

```
B1: run_planner() — LLM call with grammar
B2: parse_plan() — JSON parse + code validation + min-direction check
B3: fallback_decompose() — keyword rules
B4: Manual test on 5 val.csv questions
```

### Phase C: Direction Executor

```
C1: run_direction() — full loop with iteration 0 + ReAct
C2: format_observation() — search results → standard format
C3: format_prior_findings() — compact list with truncation
C4: Manual test on single direction
```

### Phase D: Orchestration & Integration

```
D1: run_pipeline() — full orchestrator
D2: procedural defaults injection (detect_case_type + get_defaults)
D3: aggregate_and_output() — dedup + rerank + cutoff
D4: Remove HYDE (delete generate_hypothetical_document, prf_hybrid_search)
D5: End-to-end test on 1 question
```

### Phase E: Validation & Tuning

```
E1: Full val.csv run (10 queries) → F1
E2: Ablation: no filters / no planner / no defaults / 1 iter vs 3
E3: Tune thresholds (cutoff, top-N, fallback threshold)
E4: Final submission (40 questions)
```

### Dependency Graph
```
A ──→ B ──→ D ──→ E
A ──→ C ──→ D
```

---

## 12. Verification & Testing

### Unit Tests

| Test | Validates |
|------|-----------|
| Every law doc → exactly one code | A1-A3 |
| Every court doc → exactly one code | A2-A3 |
| Filtered FAISS returns only matching docs | A4 |
| Adaptive fallback broadens on <5 results | A4 |
| Planner GBNF → valid parseable JSON | B1 |
| Fallback produces valid plan from keywords | B3 |
| Executor stops at 3 iterations (mock) | C1 |
| Executor stops on repeated query (mock) | C1 |
| Procedural defaults added for criminal case | D2 |
| End-to-end returns non-empty citations | D5 |

### Success Criteria

| Metric | Baseline | Target | Stretch |
|--------|----------|--------|---------|
| Macro F1 (val) | 0.25-0.35 | **0.45** | 0.55 |
| Runtime (40 Q) | 160 min | **< 30 min** | < 20 min |
| Coverage (areas/Q) | 1-2 | **4-5** | All relevant |

---

## 13. Context & Prompt Architecture

### File Layout

```
prompts/
├── planner_system.txt          German, ~178 lines — planner system prompt
├── executor_system.txt         German, ~47 lines — executor template (has {taxonomy_section})
├── executor_procedural.txt     German, ~65 lines — procedural specialist
├── fallback_rules.txt          English, ~130 lines — keyword decomposition
├── planner.gbnf                Grammar for planner output
└── executor.gbnf               Grammar for executor output

context/
├── swiss_legal_system.txt      ~189 lines — Swiss law structure
├── routing_guide_laws.txt      ~9.3 KB — Per-code taxonomy, keywords, examples (planner + executor)
├── routing_guide_courts.txt    ~6.1 KB — Per-prefix taxonomy, case counts (planner + executor)
├── procedural_defaults.txt     ~113 lines — always-cited articles
└── terminology_bridge.txt      ~165 lines — EN→DE legal mapping

context_en/                     English translations of all context files

data/
├── routing_guide_laws.txt      Original source (also copied to context/)
└── routing_guide_courts.txt    Original source (also copied to context/)
```

### Token Budget by Agent

| Agent | Context Loaded | Tokens | Remaining (16K) |
|-------|---------------|--------|----------|
| Planner | system + swiss_legal + routing_laws + routing_courts + terminology + question + codes | ~9,600 | ~5,600 ✅ |
| Executor | system + plan_summary + taxonomy_section + prior + history | ~2,900 | ~5,100 ✅ |
| Executor (procedural) | procedural + prior_findings | ~1,500 | ~6,500 ✅ |

### Key Decision: Routing Guides IN LLM Context (Updated)
Routing guides provide the lawyer's practical decision-tree (classification rules, per-code keywords,
disambiguation, example searches) that `swiss_legal_system.txt` lacks (which covers only structure).
- **Planner** receives FULL routing guides (~3,850 tokens combined) — enables correct code selection
- **Executor** receives only its direction's per-code taxonomy section (~150-400 tokens) via `get_taxonomy_section(filter_codes)`
- **n_ctx requirement:** ≥16384 (default updated in `src/omnilex/llm/loader.py`)
- Ordering in planner user_msg: swiss_legal → routing_laws → routing_courts → terminology → question

---

## Key Decisions Reference

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| Sequential execution | Yes | Later dirs benefit from prior findings |
| Remove HYDE | Yes | Good German queries replace it; saves 3-5s/search |
| Filter codes: `"BGE_IV"` format | Yes | Explicit, matches prompt examples |
| Seed query = iter 0 (no LLM) | Yes | Saves 1 LLM call/direction |
| BM25: post-filter | Yes | Simpler, fast enough |
| Max 60 citations | Yes | Gold max=43; safety margin |
| Reranker cutoff: 0.2 | Yes | Conservative |
| 3 iterations hard cap | Yes | Prevents loops |
| 15s timeout/direction | Yes | Bounds runtime |
| Catch-all if <4 dirs | Yes | Safety net against over-filtering |
| Routing guides: in Planner + Executor taxonomy | Yes | Provides classification rules, per-code keywords, disambiguation |

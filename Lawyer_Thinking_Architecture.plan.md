# The Legal Mind — Adaptive Research Agent Architecture

> **Design Philosophy**: A lawyer doesn't plan everything upfront then execute rigidly.
> A lawyer **thinks while searching** and **searches while thinking**. It's one continuous
> cognitive loop where each discovery reshapes understanding.

---

## 1. WHY THE CURRENT ARCHITECTURE FAILS

### The Rigidity Problem

```
CURRENT: Plan → Lock → Execute → Hope

  ┌──────────┐     ┌─────────────────────────────┐     ┌────────────┐
  │ PLANNER  │────▶│ EXECUTOR (filter=StPO,LOCKED)│────▶│ AGGREGATOR │
  │ (1 shot) │     │ EXECUTOR (filter=6B_,LOCKED) │     │ (dumb merge)│
  └──────────┘     │ EXECUTOR (filter=BGG,LOCKED) │     └────────────┘
                   └─────────────────────────────┘
```

**Failure modes:**
1. Planner misclassifies → entire pipeline searches wrong domain
2. Executor finds evidence question is about different area → can't pivot
3. No cross-pollination between directions during execution
4. Criminal cases always need both StGB (substantive) + StPO (procedural) + BGG (access) → but if planner only picks one, the others are lost
5. No awareness of "what's missing" — just "what was found"

### What a Lawyer Actually Does

A Swiss federal law attorney reading the question "Wurde die Untersuchungshaft verlängert?" doesn't think:
> "This is StPO. I will ONLY search StPO."

They think:
> "Detention... so StPO Art. 221 for grounds, but also BV Art. 10/31 for constitutional
> rights, and I need to check BGG Art. 78 for federal court jurisdiction. Let me start
> with StPO grounds, see what case law comes up, then follow the BGE citations to find
> the constitutional arguments..."

**Key insight**: The search domain EVOLVES based on what you find. You follow leads.

---

## 2. DESIGN PRINCIPLES (Anthropic + OpenAI Standards)

### From Anthropic's "Building Effective Agents":

| Pattern | How We Apply It |
|---------|----------------|
| **Augmented LLM** | Single agent with search/follow/pivot tools |
| **Orchestrator-Workers** | The agent IS the orchestrator, search tools are workers |
| **Evaluator-Optimizer** | Programmatic gap detector evaluates after each phase |
| **Tool design (ACI)** | Tools designed for how the model naturally thinks |
| **Simplicity** | One agent loop, not 3 separate LLM roles |

**Key Anthropic quote**: *"Search tasks that involve gathering and analyzing information from multiple sources for possible relevant information"* — this is exactly our use case for Orchestrator-Workers.

**Key Anthropic quote**: *"Complex search tasks that require multiple rounds of searching and analysis to gather comprehensive information, where the evaluator decides whether further searches are warranted"* — this is Evaluator-Optimizer, exactly what we're missing.

### From OpenAI's Orchestrating Agents:

| Pattern | How We Apply It |
|---------|----------------|
| **Routines (soft adherence)** | Agent has suggested steps but can deviate |
| **Handoffs** | Agent can "hand off" to different legal domain mid-execution |
| **Tool-in-loop** | Agent decides which tool + parameters each iteration |

### From Lawyer Cognition:

| Thinking Pattern | System Equivalent |
|-----------------|-------------------|
| Form hypothesis | Initial classification (fast, cheap) |
| Search broadly | First search with loose filter |
| Read results, update hypothesis | Observe → Reflect (agent reasons about findings) |
| Follow citation chain | `follow_citation` tool |
| Cross-reference to related domain | `pivot_domain` action |
| Check for gaps | Programmatic coverage rules |
| Conclude when sufficient | `done` action with confidence signal |

---

## 3. THE ARCHITECTURE: "Legal Mind" Agent

### 3.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        THE LEGAL MIND LOOP                                   │
│                                                                              │
│  ┌──────────┐    ┌──────────────────────────────────────────┐               │
│  │HYPOTHESIS│    │         ADAPTIVE RESEARCH LOOP            │               │
│  │FORMATION │───▶│                                          │               │
│  │(1 LLM)   │    │  ┌─────────┐   ┌────────┐   ┌────────┐ │  ┌─────────┐  │
│  └──────────┘    │  │  THINK  │──▶│  ACT   │──▶│OBSERVE │ │  │  GAP    │  │
│                  │  │(reason  │   │(search/│   │(results│ │  │DETECTOR │  │
│                  │  │ about   │   │follow/ │   │+ meta) │ │  │(program-│  │
│                  │  │ what to │   │pivot/  │   │        │ │  │ matic)  │  │
│                  │  │ do next)│   │done)   │   │        │ │  │         │  │
│                  │  └─────────┘   └────────┘   └───┬────┘ │  └────┬────┘  │
│                  │       ▲                         │      │       │        │
│                  │       └─────────────────────────┘      │       │        │
│                  │                                        │       │        │
│                  │    Repeats 5-8 iterations (adaptive)   │       │        │
│                  └───────────────────────────┬────────────┘       │        │
│                                             │                    │        │
│                                             ▼                    │        │
│                                    ┌────────────────┐            │        │
│                                    │  ACCUMULATED   │◀───────────┘        │
│                                    │  CITATIONS     │  (fills gaps)       │
│                                    └───────┬────────┘                     │
│                                            │                              │
│                                            ▼                              │
│                                    ┌────────────────┐                     │
│                                    │   RERANK +     │                     │
│                                    │   OUTPUT       │                     │
│                                    └────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Phase 1: Hypothesis Formation (1 LLM call, ~2s)

**Purpose**: Fast initial classification. NOT a full plan — just a starting point.

**Input**: Question + keyword-selected routing context (existing dynamic selection)

**Output** (GBNF-constrained):
```json
{
  "domain": "STRAFPROZESS",
  "initial_filters": ["StPO", "BV"],
  "initial_corpus": "laws",
  "seed_query": "Untersuchungshaft Haftgründe Verlängerung",
  "confidence": "medium",
  "cross_domains": ["STRAFRECHT", "PROZESSRECHT"]
}
```

**Key difference from current Planner**: This is a HYPOTHESIS, not a locked plan. The agent will update it as it searches. `cross_domains` tells the agent "you might need to look here too" — soft guidance, not commands.

**Why `confidence`?** If confidence is "low", the research loop gets more iterations. If "high", fewer needed.

### 3.3 Phase 2: Adaptive Research Loop (5-8 LLM calls, ~15-20s)

This is the core innovation. **One agent, one loop, multiple tools.**

#### The Agent's Toolset

```python
# The agent can output ONE of these actions per iteration:
{
  "action": "search",
  "query": "Haftgründe Art. 221 StPO",
  "corpus": "laws",           # agent CHOOSES each time
  "filter": ["StPO"],         # agent CHOOSES each time (can be empty = broad)
  "reasoning": "Need procedural basis for detention extension"
}

{
  "action": "search",
  "query": "Verhältnismässigkeit Untersuchungshaft Dauer",
  "corpus": "courts",
  "filter": ["1B_"],          # can target specific court division
  "reasoning": "Looking for BGer case law on proportionality of detention duration"
}

{
  "action": "follow",
  "citation": "BGE 143 IV 9",
  "reasoning": "This leading case likely cites foundational precedents"
}

{
  "action": "broaden",
  "query": "Grundrechte Freiheitsentzug",
  "reasoning": "No results with StPO filter, trying constitutional law broadly"
}

{
  "action": "pivot",
  "new_domain": "OEFFENTLICHES_RECHT",
  "query": "Verhältnismässigkeit Freiheitsentzug BV",
  "reasoning": "Results show this is really a constitutional proportionality case"
}

{
  "action": "done",
  "reasoning": "Found sufficient procedural + substantive + constitutional citations"
}
```

#### What the Agent Sees Each Iteration

The agent's observation after each action includes:

```
AKTUELLER STAND:
  Gefundene Zitate: 12
  Domains abgedeckt: StPO (4), BV (2), BGG (1), 1B_ (5)
  Fehlende Bereiche: Materielles Strafrecht (StGB) — oft relevant bei Haft

LETZTE SUCHE:
  Query: "Haftgründe Art. 221 StPO"
  Filter: StPO | Corpus: laws
  Ergebnisse:
    1. "Art. 221 Abs. 1 StPO" (0.89) — Haftgründe: Flucht, Kollusion, Wiederholung
    2. "Art. 227 StPO" (0.82) — Haftverlängerung
    3. "Art. 212 Abs. 3 StPO" (0.76) — Verhältnismässigkeit

VORHERIGE SUCHEN: [query_1 → 5 hits, query_2 → 3 hits]
```

**Key design**: The observation tells the agent what domains it HAS covered and what it HASN'T. This is soft guidance that lets the model naturally decide to pivot.

#### The GBNF Grammar (Expanded)

```gbnf
root ::= "{" action-body "}"

action-body ::= search-action | follow-action | broaden-action | pivot-action | done-action

search-action ::= "\"action\":\"search\"," 
                  "\"query\":\"" query-text "\","
                  "\"corpus\":\"" corpus-val "\","
                  "\"filter\":[" filter-list "],"
                  "\"reasoning\":\"" reasoning-text "\""

follow-action ::= "\"action\":\"follow\","
                  "\"citation\":\"" citation-text "\","
                  "\"reasoning\":\"" reasoning-text "\""

broaden-action ::= "\"action\":\"broaden\","
                   "\"query\":\"" query-text "\","
                   "\"reasoning\":\"" reasoning-text "\""

pivot-action ::= "\"action\":\"pivot\","
                 "\"new_domain\":\"" domain-val "\","
                 "\"query\":\"" query-text "\","
                 "\"reasoning\":\"" reasoning-text "\""

done-action ::= "\"action\":\"done\","
                "\"reasoning\":\"" reasoning-text "\""

corpus-val ::= "laws" | "courts" | "both"
domain-val ::= "STRAFRECHT" | "STRAFPROZESS" | "ZIVILRECHT" | ...
filter-list ::= "" | "\"" filter-code "\"" ("," "\"" filter-code "\"")*
```

#### How Tools Execute (Python, no LLM)

```python
def execute_action(action: dict, state: ResearchState) -> Observation:
    if action["action"] == "search":
        results = filtered_hybrid_search(
            query=action["query"],
            corpus=action["corpus"],
            filter_codes=action.get("filter", []),  # empty = unfiltered
            top_k=CONFIG["search_top_k"]
        )
        state.add_citations(results)
        return format_observation(results, state)
    
    elif action["action"] == "follow":
        # Find documents that cite or are cited by the given citation
        neighbors = citation_graph_lookup(action["citation"], state)
        state.add_citations(neighbors)
        return format_observation(neighbors, state)
    
    elif action["action"] == "broaden":
        # Search WITHOUT any filter — maximum recall
        results = filtered_hybrid_search(
            query=action["query"],
            corpus="both",
            filter_codes=[],  # intentionally empty
            top_k=CONFIG["search_top_k"] * 2
        )
        state.add_citations(results)
        return format_observation(results, state)
    
    elif action["action"] == "pivot":
        # Update working hypothesis, search new domain
        state.update_hypothesis(action["new_domain"])
        results = filtered_hybrid_search(
            query=action["query"],
            corpus="both",
            filter_codes=get_domain_codes(action["new_domain"]),
            top_k=CONFIG["search_top_k"]
        )
        state.add_citations(results)
        return format_observation(results, state)
    
    elif action["action"] == "done":
        return None  # Exit loop
```

#### Why This Works with Mistral-7B

1. **GBNF constrains output** → model can't produce invalid actions
2. **Each action is simple** → model only decides ONE thing per turn
3. **Rich observations** → model gets domain coverage info, doesn't need to track it mentally
4. **Soft guidance in prompt** → "You started with StPO. Consider also: BV, BGG" (from hypothesis)
5. **No complex multi-tool selection** → one action per turn, structured output

### 3.4 Phase 3: Gap Detector (Programmatic, 0 LLM cost, ~50ms)

After the research loop, a **pure-Python rules engine** checks for systematic gaps that even a good agent might miss.

#### Gap Rules (Encoding Lawyer Heuristics)

```python
GAP_RULES = [
    # Rule: Criminal cases need BOTH substantive + procedural
    {
        "trigger": lambda state: state.has_domain("1B_") or state.has_code("StPO"),
        "requires": ["BV"],  # Constitutional rights always relevant for detention
        "gap_query": "Grundrechte persönliche Freiheit Art. 10 31 BV",
        "gap_corpus": "laws",
        "gap_filter": ["BV"],
    },
    # Rule: Criminal verdicts need sentencing law
    {
        "trigger": lambda state: state.has_domain("6B_"),
        "requires": ["StGB"],
        "gap_query": "Strafzumessung Art. 47 StGB",
        "gap_corpus": "laws",
        "gap_filter": ["StGB"],
    },
    # Rule: Any federal court case needs procedural access provisions
    {
        "trigger": lambda state: state.has_any_court_citation(),
        "requires": ["BGG"],
        "gap_query": "Beschwerde Bundesgericht Zulässigkeit",
        "gap_corpus": "laws",
        "gap_filter": ["BGG"],
    },
    # Rule: Social insurance needs ATSG general part
    {
        "trigger": lambda state: state.has_domain("8C_") or state.has_domain("9C_"),
        "requires": ["ATSG"],
        "gap_query": "Sozialversicherung allgemeiner Teil ATSG",
        "gap_corpus": "laws",
        "gap_filter": ["ATSG"],
    },
    # Rule: Family law needs ZGB civil code
    {
        "trigger": lambda state: state.has_domain("5A_"),
        "requires": ["ZGB"],
        "gap_query": "Familienrecht Scheidung Unterhalt ZGB",
        "gap_corpus": "laws",
        "gap_filter": ["ZGB"],
    },
    # Rule: If only laws found, should also have court decisions (and vice versa)
    {
        "trigger": lambda state: state.corpus_balance() < 0.2,  # <20% from other corpus
        "requires": ["CROSS_CORPUS"],
        "gap_query": state.top_query_reformulated(),
        "gap_corpus": state.underrepresented_corpus(),
        "gap_filter": [],
    },
]
```

#### Gap Fill Execution

```python
def fill_gaps(state: ResearchState) -> None:
    """Run gap rules, execute max 3 extra searches (no LLM needed)."""
    gap_searches_done = 0
    for rule in GAP_RULES:
        if gap_searches_done >= 3:
            break
        if rule["trigger"](state) and not state.has_all_codes(rule["requires"]):
            results = filtered_hybrid_search(
                query=rule["gap_query"],
                corpus=rule["gap_corpus"],
                filter_codes=rule["gap_filter"],
                top_k=5
            )
            state.add_citations(results, source="gap_fill")
            gap_searches_done += 1
```

**Cost**: 0 LLM calls, 1-3 FAISS lookups (~150ms). Pure Python pattern matching.

### 3.5 Phase 4: Final Assembly (Rerank + Output)

Same as current aggregator but with one improvement:

```python
def assemble_output(state: ResearchState, question: str) -> str:
    """Final assembly: deduplicate, rerank, format."""
    # 1. Deduplicate (keep highest score per citation)
    unique_citations = state.get_unique_citations()
    
    # 2. Inject procedural defaults (existing logic)
    case_type, prefixes = detect_case_type(unique_citations)
    defaults = get_procedural_defaults(case_type, prefixes)
    unique_citations.extend([(d, 0.3) for d in defaults])
    
    # 3. Rerank with Qwen3-Reranker
    pairs = [(question, cit) for cit, _ in unique_citations]
    rerank_scores = reranker.predict(pairs, batch_size=CONFIG["rerank_batch_size"])
    
    # 4. Score cutoff + cap
    scored = sorted(zip([c for c,_ in unique_citations], rerank_scores), 
                    key=lambda x: x[1], reverse=True)
    final = [(c, s) for c, s in scored if s >= CONFIG["rerank_score_cutoff"]]
    final = final[:CONFIG["max_final_citations"]]
    
    # 5. Extract explicit citations from question text
    explicit = extract_explicit_citations(question)
    for cit in reversed(explicit):
        if cit in corpus_citation_set and cit not in [f[0] for f in final]:
            final.insert(0, (cit, 1.0))
    
    return ";".join(c for c, _ in final)
```

---

## 4. CITATION GRAPH: "FOLLOW" TOOL IMPLEMENTATION

### How Citation Following Works

When the agent calls `{"action": "follow", "citation": "BGE 143 IV 9"}`:

```python
def citation_graph_lookup(citation: str, state: ResearchState) -> list:
    """Find neighbors of a citation in embedding space.
    
    Since we don't have an explicit citation graph, we use two strategies:
    1. Embedding similarity — find documents closest to this citation's embedding
    2. Text overlap — find documents mentioning this citation string
    """
    results = []
    
    # Strategy 1: Embedding neighbors (same vector space = related content)
    if citation in citation_to_index:
        idx = citation_to_index[citation]
        doc_vec = faiss_index.reconstruct(idx).reshape(1, -1)
        # Search for similar documents (excluding self)
        scores, ids = faiss_index.search(doc_vec, 10)
        for i in range(len(ids[0])):
            if ids[0][i] != idx and ids[0][i] >= 0:
                doc = documents[ids[0][i]]
                results.append((doc["citation"], float(scores[0][i]), doc["text"][:200]))
    
    # Strategy 2: BM25 for the citation string itself
    citation_tokens = tokenize_german(citation)
    bm25_scores = bm25_index.get_scores(citation_tokens)
    top_bm25 = np.argsort(bm25_scores)[::-1][:5]
    for idx in top_bm25:
        doc = documents[int(idx)]
        if doc["citation"] != citation:
            results.append((doc["citation"], float(bm25_scores[idx]), doc["text"][:200]))
    
    return results[:8]  # Cap at 8 neighbors
```

### Why Not a Real Graph Database?

Constraint: Kaggle runtime, no Neo4j. But **embedding proximity IS a graph** — documents close in vector space share legal concepts. BM25 on citation strings catches explicit references. Together, they approximate citation graph traversal without infrastructure.

---

## 5. STATE MANAGEMENT: The "Research Pad"

```python
@dataclass
class ResearchState:
    """The lawyer's notepad — accumulates knowledge across the loop."""
    
    # Working hypothesis (evolves)
    current_domain: str
    hypothesis_confidence: str  # "low" | "medium" | "high"
    
    # Accumulated findings
    citations: list[tuple[str, float, str]]  # (citation, score, source_action)
    
    # Search history (for observation formatting)
    search_history: list[dict]  # [{query, corpus, filter, n_results}, ...]
    
    # Domain coverage tracking
    domains_seen: Counter  # {"StPO": 4, "BV": 2, "1B_": 5, ...}
    corpora_balance: dict  # {"laws": 8, "courts": 5}
    
    # Timing
    start_time: float
    iteration_count: int
    
    def coverage_summary(self) -> str:
        """What the agent sees about its own progress."""
        return (
            f"Zitate: {len(self.citations)} | "
            f"Domains: {dict(self.domains_seen)} | "
            f"Gesetze: {self.corpora_balance.get('laws', 0)}, "
            f"Gerichte: {self.corpora_balance.get('courts', 0)} | "
            f"Iterationen: {self.iteration_count}/{self.max_iterations}"
        )
    
    def missing_domains_hint(self) -> str:
        """Soft guidance about what might be missing."""
        # Based on cross_domain rules
        hints = []
        if "StPO" in self.domains_seen and "BV" not in self.domains_seen:
            hints.append("BV (Grundrechte bei Freiheitsentzug)")
        if "6B_" in self.domains_seen and "StGB" not in self.domains_seen:
            hints.append("StGB (materielles Strafrecht)")
        if self.corpora_balance.get("courts", 0) == 0:
            hints.append("Bundesgerichtsentscheide (Rechtsprechung)")
        return "; ".join(hints) if hints else "Gute Abdeckung"
```

---

## 6. THE PROMPT: Simulating Lawyer Thinking

### Agent System Prompt (Research Loop)

```
Du bist ein erfahrener Schweizer Rechtsanwalt, der relevante Gesetzesartikel und
Bundesgerichtsentscheide für eine Rechtsfrage recherchiert.

DEINE WERKZEUGE:
- search: Suche in Gesetzen oder Gerichtsentscheiden (mit optionalem Filter)
- follow: Folge einer Zitation zu verwandten Dokumenten
- broaden: Suche ohne Filter (breiter)
- pivot: Wechsle den Rechtsbereich
- done: Recherche abgeschlossen

ARBEITSHYPOTHESE: {hypothesis}
VORGESCHLAGENE FILTER: {suggested_filters} (Hinweis — du kannst andere wählen)

DEIN AKTUELLER STAND:
{state.coverage_summary()}

MÖGLICHERWEISE FEHLEND:
{state.missing_domains_hint()}

LETZTE BEOBACHTUNG:
{last_observation}

SUCHHISTORIE:
{search_history_formatted}

Wähle deine nächste Aktion. Denke wie ein Anwalt:
- Hast du genug gefunden? → done
- Fehlt ein Rechtsbereich? → pivot oder search mit neuem Filter
- Gute Treffer, brauche mehr Tiefe? → follow einer wichtigen Zitation
- Zu wenige Ergebnisse? → broaden
```

### Why This Works

1. **"Think like a lawyer"** frames the model's reasoning correctly
2. **Coverage summary** = the model SEE its own gaps (soft evaluator)
3. **"Möglicherweise fehlend"** = programmatic hint, not a command
4. **Suggested filters are SUGGESTIONS** = soft adherence (OpenAI routine pattern)
5. **Clear tool descriptions** = good ACI (Anthropic Appendix 2)

---

## 7. TIME BUDGET ANALYSIS

### Current Architecture: ~27s/question
- 1 Planner call: ~2s
- 3 Directions × 3 iterations × 1 LLM call: ~12-15s  
- FAISS searches: ~2s total
- Reranker: ~5s
- Overhead: ~3s

### New Architecture: ~25-30s/question
| Phase | LLM Calls | FAISS Searches | Time |
|-------|-----------|----------------|------|
| Hypothesis | 1 | 0 | ~2s |
| Research Loop (6 iter avg) | 6 | 6-8 | ~12-15s |
| Gap Detector | 0 | 1-3 | ~0.2s |
| Reranker | 0 | 0 | ~5s |
| Overhead | 0 | 0 | ~2s |
| **TOTAL** | **7** | **7-11** | **~22-25s** |

**Actually FASTER** than current because:
- No separate planner decomposition into 3-6 directions
- Fewer total LLM calls (7 vs 10-13)
- Each call is shorter (one action vs full ReAct reasoning)
- GBNF grammar constrains output length

### Adaptive Iteration Count

```python
MAX_ITERATIONS = {
    "high": 4,     # Confident hypothesis → fewer iterations needed
    "medium": 6,   # Normal case
    "low": 8,      # Uncertain → explore more
}

# Also: early termination if found enough
if len(state.citations) >= 20 and state.domain_coverage() >= 0.8:
    force_done = True
```

---

## 8. COMPARISON: CURRENT vs. LEGAL MIND

| Dimension | Current (Rigid) | Legal Mind (Adaptive) |
|-----------|----------------|----------------------|
| Planning | Full decomposition upfront | Light hypothesis (evolves) |
| Filter control | Locked per-direction | Agent chooses per-query |
| Cross-domain discovery | Impossible | Natural (pivot/broaden tools) |
| Citation following | None | Embedding + BM25 graph |
| Gap awareness | None | Coverage tracking + programmatic rules |
| Reflection | None | Observation summary = implicit self-eval |
| Error recovery | Adaptive fallback (0 results only) | Agent can pivot at any point |
| LLM role | Planner + Executor (separate) | Single researcher (unified) |
| Observation quality | Just citations | Citations + domain stats + hints |
| Anthropic pattern | Prompt Chain (rigid) | Agent + Evaluator-Optimizer hybrid |
| OpenAI pattern | Fixed workflow | Routine with soft adherence |

---

## 9. RISK MITIGATION (Mistral-7B Guardrails)

### Problem: Small model might make bad tool choices

**Solutions:**
1. **GBNF grammar** = physically impossible to produce invalid output
2. **Validation layer** after each action:
   ```python
   def validate_action(action: dict) -> dict:
       # Fix invalid filter codes
       action["filter"] = [c for c in action.get("filter", []) if c in valid_codes]
       # Prevent infinite loops (same query repeated)
       if action.get("query") in recent_queries:
           action["action"] = "done"
       # Timeout enforcement
       if time.time() - state.start_time > 25:
           action["action"] = "done"
       return action
   ```
3. **Max iterations** = hard cap regardless of model output
4. **Minimum citations** = if agent says "done" with <5 citations, force 2 more broaden searches
5. **Fallback** = if research loop produces <3 citations total, fall back to current rigid pipeline

### Problem: Model might always choose same action

**Solutions:**
1. **Observation includes what WAS tried** → model sees "already searched StPO 3 times"
2. **Diminishing returns signal** → "Letzte Suche: 0 neue Treffer" encourages pivot
3. **Explicit count** → "Iterationen: 5/6" creates urgency to conclude

---

## 10. IMPLEMENTATION ROADMAP

### Phase A: Core Loop (Replace Cell 13-14)
1. Define `ResearchState` dataclass
2. Implement expanded GBNF grammar (search/follow/broaden/pivot/done)
3. Implement `execute_action()` dispatcher
4. Implement observation formatting with coverage stats
5. Write hypothesis formation prompt (replaces current planner)
6. Write research loop prompt (replaces current executor)
7. Wire up the main loop with timeout + max iterations

### Phase B: Gap Detector (New Cell after research loop)
1. Implement gap rules (domain pairing heuristics)
2. Wire into pipeline after research loop exits
3. Execute 1-3 targeted searches

### Phase C: Citation Following (Enhancement)
1. Build `citation_to_index` mapping (citation string → FAISS index position)
2. Implement embedding-neighbor lookup
3. Implement BM25 citation-string lookup
4. Add "follow" action to the agent's toolset

### Phase D: Validation + Tuning
1. Run on training set, compare vs. current pipeline
2. Tune: iteration counts, GBNF grammar details, observation formatting
3. Add/remove gap rules based on error analysis
4. Tune early termination thresholds

---

## 11. THE FUNDAMENTAL SHIFT

```
BEFORE: Plan everything → Execute blindly → Hope for the best
AFTER:  Hypothesize → Search → Observe → Adapt → Search → ... → Conclude
```

The current system is a **workflow** (Anthropic's definition): "LLMs and tools orchestrated through predefined code paths."

The new system is an **agent** (Anthropic's definition): "LLMs dynamically direct their own processes and tool usage, maintaining control over how they accomplish tasks."

But with **guardrails** that keep a 7B model from going off-track:
- GBNF grammar (physical output constraints)
- Programmatic gap detector (evaluator without LLM cost)
- Hard timeout + iteration caps (safety stops)
- Fallback to rigid pipeline (if agent underperforms)

This is exactly Anthropic's advice: *"Maintain simplicity in your agent's design. Carefully craft your agent-computer interface (ACI) through thorough tool documentation and testing."*

---

## 12. EXPECTED IMPACT

| Metric | Current | Expected |
|--------|---------|----------|
| Recall (found relevant citations) | ~60-70% | ~80-85% (cross-domain discovery) |
| Precision (citations are relevant) | ~40-50% | ~55-65% (fewer wrong-domain hits) |
| Coverage (domains touched) | 1-2 per question | 2-4 per question |
| Adaptation to surprise | None | Natural pivot |
| Failure on misclassification | Total | Recoverable via pivot |
| Time per question | ~27s | ~22-25s |

The biggest gain: **questions where the current system completely fails** (misclassified domain) will now be recoverable because the agent can pivot mid-execution.

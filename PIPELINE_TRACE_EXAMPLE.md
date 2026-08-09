# Pipeline Trace — Complete Example

**Question:** "Under what conditions can pre-trial detention be extended beyond the initial period?"

---

## FILES LOADED INTO THE PIPELINE

### Context Files (static knowledge — loaded into prompts)

| File | Size | Purpose | Loaded Where |
|------|------|---------|-------------|
| `context/swiss_legal_system.txt` | 7.7KB (~189 lines) | Swiss court structure, SR codes, appeal paths | Planner USER msg |
| `context/routing_guide_laws.txt` | 9.3KB (~180 lines) | Per-code taxonomy, keywords, classification rules | Planner USER msg + Executor taxonomy |
| `context/routing_guide_courts.txt` | 6.1KB (~120 lines) | Per-prefix taxonomy, case counts, keywords | Planner USER msg + Executor taxonomy |
| `context/terminology_bridge.txt` | 8.5KB (~165 lines) | English→German legal term mappings | Planner USER msg |
| `context/procedural_defaults.txt` | 6.1KB (~113 lines) | Always-cited BGG/BV articles by case type | Phase 3 (hardcoded) |

### Prompt Template Files (LLM instructions)

| File | Size | Purpose | Used By |
|------|------|---------|---------|
| `prompts/planner_system.txt` | 8.2KB (~178 lines) | Planner system prompt (role + rules + examples) | Planner LLM |
| `prompts/planner.gbnf` | 890B | Grammar: forces valid JSON output structure | Planner LLM |
| `prompts/executor_system.txt` | 2.0KB (~47 lines) | Executor system prompt (ReAct instructions) | Executor (dirs P1-P89) |
| `prompts/executor_procedural.txt` | 2.4KB (~55 lines) | Special prompt for procedural directions | Executor (P≥90) |
| `prompts/executor.gbnf` | 301B | Grammar: forces `{thought, query, done}` JSON | Executor LLM |
| `prompts/fallback_rules.txt` | 6.4KB | Keyword→code mapping rules | `fallback_decompose()` |

---

## PROMPT GROWTH DIAGRAM

```
PLANNER PROMPT (sent to LLM as 1 call):
┌─────────────────────────────────────────────────────────────────────────┐
│ messages[0] = SYSTEM                                                     │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ planner_system.txt (178 lines)                                       │ │
│ │   - Role: "experienced Swiss lawyer, 20y at Bundesgericht"          │ │
│ │   - Task: create research plan (sachverhalt, rechtsfragen, dirs)    │ │
│ │   - Output format: strict JSON structure                            │ │
│ │   - Rules: 3-6 directions, always procedural, German queries        │ │
│ │   - {available_law_codes} ← INJECTED: 973 codes joined by comma    │ │
│ │   - {available_court_codes} ← INJECTED: 39 codes joined by comma   │ │
│ │   - 3 worked examples (criminal, family, social insurance)          │ │
│ │   - "NIEMALS Codes erfinden!" constraint                            │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ messages[1] = USER                                                       │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ "KONTEXT (Schweizerisches Rechtssystem):"                           │ │
│ │ ← swiss_legal_system.txt (189 lines, ~7.7KB)                        │ │
│ │   [Court hierarchy, SR classification, appeal paths, structure]     │ │
│ │                                                                      │ │
│ │ "GESETZES-ROUTING (Taxonomie & Klassifikation):"                    │ │
│ │ ← routing_guide_laws.txt (~9.3KB)                                   │ │
│ │   [Per-code: content, keywords, examples, common mistakes]          │ │
│ │                                                                      │ │
│ │ "GERICHTS-ROUTING (Abteilungen & Praefixe):"                        │ │
│ │ ← routing_guide_courts.txt (~6.1KB)                                 │ │
│ │   [Per-prefix: case counts, keywords, division scope]               │ │
│ │                                                                      │ │
│ │ "TERMINOLOGIE (Englisch → Deutsch):"                                │ │
│ │ ← terminology_bridge.txt (165 lines, ~8.5KB)                        │ │
│ │   [pre-trial detention→Untersuchungshaft, appeal→Beschwerde, etc.] │ │
│ │                                                                      │ │
│ │ "FRAGE: Under what conditions can pre-trial detention be extended   │ │
│ │  beyond the initial period?"                                         │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ TOTAL TOKENS: ~9,600 (system ~3,200 + user ~6,400)                      │
│ + GBNF grammar (890B) attached as generation constraint                 │
│ Max output tokens: 800                                                   │
└─────────────────────────────────────────────────────────────────────────┘


EXECUTOR PROMPT — Direction 1, Iteration 1 (first LLM call in executor):
┌─────────────────────────────────────────────────────────────────────────┐
│ messages[0] = SYSTEM                                                     │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ executor_system.txt WITH VARIABLES FILLED:                           │ │
│ │                                                                      │ │
│ │ "Du bist ein Schweizer Rechtsanwalt..."                             │ │
│ │ DEINE RICHTUNG:                                                      │ │
│ │   Rechtsgebiet: Strafprozessrecht                    ← {rechtsgebiet}│ │
│ │   Corpus: laws                                       ← {corpus}      │ │
│ │   Filter: StPO                                       ← {filter_codes}│ │
│ │   Begründung: StPO Art. 221-240 regelt die U-Haft   ← {reasoning}   │ │
│ │                                                                      │ │
│ │ TAXONOMIE DIESER RICHTUNG:                           ← {taxonomy_section}
│ │   • StPO (Schweizerische Strafprozessordnung)                       │ │
│ │     Inhalt: Strafverfahrensrecht, Untersuchung, Zwangsmassnahmen... │ │
│ │     Schlüsselwörter: Untersuchungshaft, Haftgrund, Fluchtgefahr...  │ │
│ │     Wichtige Bereiche: Art. 212-240, Art. 382-397                    │ │
│ │   (~150-400 tokens, only for this direction's codes)                 │ │
│ │                                                                      │ │
│ │ DER GESAMTPLAN:                                      ← {plan_summary}│ │
│ │   "Sachverhalt: Frage nach Haftverlängerung..."                     │ │
│ │   "Rechtsfragen: Haftgründe; Verhältnismässigkeit; Verfahren"      │ │
│ │   "Dies ist Richtung 1 von 4."                                      │ │
│ │                                                                      │ │
│ │ BEREITS GEFUNDENE ZITATE:                            ← {prior_findings}
│ │   "Noch keine Funde aus vorherigen Richtungen."                     │ │
│ │   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                    │ │
│ │   (EMPTY for direction 1 — grows with each direction!)              │ │
│ │                                                                      │ │
│ │ [Search strategy rules, VERBOTEN list]                               │ │
│ │                                                                      │ │
│ │ BISHERIGE SUCHEN IN DIESER RICHTUNG:                ← {direction_history}
│ │   "Query: 'Haftgründe Verlängerung Untersuchungshaft'"             │ │
│ │   "  → Funde: Art. 221 Abs. 1 StPO; Art. 227 Abs. 1 StPO;        │ │
│ │       Art. 212 Abs. 3 StPO; Art. 226 Abs. 1 StPO; Art. 220 StPO"  │ │
│ │   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^        │ │
│ │   (This is from iter 0's seed query results!)                        │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ messages[1] = USER                                                       │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ "Generiere deine nächste Suchanfrage oder signalisiere done."       │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ TOTAL TOKENS: ~1,000 (system ~950 + user ~50, incl. taxonomy section)   │
│ + GBNF grammar (301B) → forces {thought, query, done}                   │
│ Max output tokens: 200                                                   │
└─────────────────────────────────────────────────────────────────────────┘


EXECUTOR PROMPT — Direction 1, Iteration 2 (AFTER iter 1 searched):
┌─────────────────────────────────────────────────────────────────────────┐
│ SAME as above but {direction_history} NOW HAS TWO ENTRIES:              │
│                                                                          │
│ "SUCHVERLAUF DIESER RICHTUNG:                                           │
│  Query: 'Haftgründe Verlängerung Untersuchungshaft'                     │
│    → Funde: Art. 221 Abs. 1 StPO; Art. 227 Abs. 1 StPO; ...           │
│  Query: 'Höchstdauer Untersuchungshaft Überhaft Entlassung'            │
│    → Funde: Art. 212 Abs. 1 StPO; Art. 228 StPO; Art. 231 StPO"       │
│                                                                          │
│ The LLM sees ALL previous queries + their results within THIS direction │
│ → avoids repeating queries, knows what gaps remain                      │
│                                                                          │
│ TOTAL TOKENS: ~1,200 (grows ~200/iter due to history)                   │
└─────────────────────────────────────────────────────────────────────────┘


EXECUTOR PROMPT — Direction 2, Iteration 1 (AFTER direction 1 completed):
┌─────────────────────────────────────────────────────────────────────────┐
│ KEY DIFFERENCE: {prior_findings} IS NOW POPULATED!                      │
│                                                                          │
│ "BEREITS GEFUNDENE ZITATE (aus vorherigen Richtungen):                  │
│  BISHERIGE FUNDE:                                                       │
│  - Art. 221 Abs. 1 StPO (0.87)                                         │
│  - Art. 227 Abs. 1 StPO (0.82)                                         │
│  - Art. 212 Abs. 3 StPO (0.79)                                         │
│  - Art. 226 Abs. 1 StPO (0.75)                                         │
│  - Art. 228 StPO (0.72)                                                │
│  - Art. 231 StPO (0.68)                                                │
│  - Art. 225 Abs. 1 StPO (0.65)                                         │
│  - Art. 224 StPO (0.62)                                                │
│  - Art. 229 Abs. 1 StPO (0.60)                                         │
│  - Art. 220 Abs. 1 StPO (0.55)                                         │
│  ... (up to 20 most recent)"                                            │
│                                                                          │
│ AND: {direction_history} = fresh (only has iter 0 seed results)         │
│ AND: {rechtsgebiet} = "Strafprozessrecht", {corpus} = "courts"          │
│ AND: {filter_codes} = "1B_"                                             │
│                                                                          │
│ The LLM now KNOWS what was already found → won't search for same things │
│ → focuses on COURT DECISIONS that APPLY those articles                  │
└─────────────────────────────────────────────────────────────────────────┘


EXECUTOR PROMPT — Direction 4 (P99 Procedural), Iteration 1:
┌─────────────────────────────────────────────────────────────────────────┐
│ USES DIFFERENT TEMPLATE: executor_procedural.txt                        │
│                                                                          │
│ Because priority ≥ 90, switches from executor_system.txt                │
│ to executor_procedural.txt which:                                        │
│                                                                          │
│ - Explains WHY procedural citations matter                              │
│ - Lists specific BGG articles by case type (78/72/82)                   │
│ - Has pre-built seed queries for each case type                         │
│ - Only uses {prior_findings} variable (not the full 7-var template)     │
│                                                                          │
│ {prior_findings} NOW HAS ALL 3 PREVIOUS DIRECTIONS:                     │
│ "BISHERIGE FUNDE:                                                       │
│  - Art. 221 Abs. 1 StPO (0.87)     ← from direction 1 (laws/StPO)     │
│  - 1B_210/2023 E. 4.1 (0.78)       ← from direction 2 (courts/1B_)    │
│  - Art. 10 Abs. 2 BV (0.65)        ← from direction 3 (laws/BV+EMRK)  │
│  - Art. 31 Abs. 1 BV (0.55)        ← from direction 3                 │
│  - BGE 137 IV 122 (0.68)           ← from direction 2                 │
│  ... (last 20)"                                                         │
│                                                                          │
│ The LLM reads "1B_ gefunden" → determines: STRAFBESCHWERDE              │
│ → searches: "Beschwerde Strafsachen Legitimation schutzwürdiges..."     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## PRIOR FINDINGS GROWTH — DIRECTION BY DIRECTION

```
DIRECTION 1 (P1: laws/StPO)     DIRECTION 2 (P2: courts/1B_)
           │                               │
prior_findings = []              prior_findings = [
                                   last 20 from Dir 1
direction_history grows:           ]
  iter0: seed → 10 results       
  iter1: LLM query → 10 results  direction_history grows:
  iter2: LLM query → 10 results    iter0: seed → 10 results
  iter3: done=true                  iter1: LLM query → 10 results
                                    iter2: done=true
OUTPUT: ~25 citations             
                                  OUTPUT: ~18 citations
           │                               │
           ▼                               ▼
    prior_findings grows:          prior_findings grows:
    prior = ([] + dir1_cits)[-20:]  prior = (prev + dir2_cits)[-20:]
    = last 20 of dir 1 results     = last 20 of dir1+dir2 combined


DIRECTION 3 (P3: laws/BV+EMRK)   DIRECTION 4 (P99: both/BGG+BV)
           │                               │
prior_findings = [                prior_findings = [
  last 20 from Dir 1+2 combined     last 20 from Dir 1+2+3 combined
]                                 ]

direction_history grows:          USES executor_procedural.txt!
  iter0: seed → 10 results        (different template, sees all prior)
  iter1: LLM query → 8 results   
  iter2: done=true                direction_history grows:
                                    iter0: seed → 10 results
OUTPUT: ~15 citations               iter1: LLM query → 10 results
                                    iter2: done=true
           │
           ▼                      OUTPUT: ~12 citations
    prior = (prev + dir3_cits)[-20:]
```

---

## THE KEY MECHANISM: `prior_findings` vs `direction_history`

```python
# In pipeline.py — THIS is how feedback flows between directions:

all_citations = []
prior_findings = []  # ← starts EMPTY

for i, direction in enumerate(sorted_directions):
    direction_cits = run_direction(
        direction=direction,
        prior_findings=prior_findings,  # ← passed IN to executor
        ...
    )
    
    all_citations.extend(direction_cits)
    
    # ROLLING WINDOW: keep last 20 citations as context for NEXT direction
    prior_findings = (prior_findings + direction_cits)[-20:]
    #                                                 ^^^^^^
    #                       Only last 20! (token budget constraint)
```

**Two separate contexts inside each executor:**

| Variable | Scope | Purpose | Grows? |
|----------|-------|---------|--------|
| `{prior_findings}` | CROSS-direction | "What OTHER directions already found" → avoid duplication | YES — grows each direction |
| `{direction_history}` | WITHIN-direction | "What THIS direction already searched" → avoid repeated queries | YES — grows each iteration |

---

## PHASE 1: PLANNER

### Input Assembly

```
SYSTEM PROMPT (planner_system.txt):
  - Role: "Swiss lawyer (Rechtsanwalt)"
  - available_law_codes: ["AIG","ATSG","AVIG","BGG","BV","BVG","DSG","EMRK","IVG",
                          "KVG","OR","SchKG","StGB","StPO","UVG","VVG","ZGB","ZPO", ...973 total]
  - available_court_codes: ["1B_","1C_","2C_","4A_","4D_","5A_","5D_","6B_","8C_",
                            "9C_","BGE_I","BGE_II","BGE_III","BGE_IV","BGE_V", ...39 total]

USER MESSAGE:
  KONTEXT: [swiss_legal_system.txt — 189 lines of Swiss legal structure]
  TERMINOLOGIE: [terminology_bridge.txt — EN→DE term mappings]
  FRAGE: "Under what conditions can pre-trial detention be extended beyond the initial period?"
```

### LLM Generation (Mistral-7B + GBNF Grammar)

Grammar forces this JSON structure:
```json
{
  "sachverhalt": "Frage nach den Voraussetzungen der Haftverlängerung über die erste Frist hinaus",
  "rechtsfragen": [
    "Welche Haftgründe erlauben eine Verlängerung?",
    "Wie ist die Verhältnismässigkeit zu prüfen?",
    "Welche Verfahrensschritte sind einzuhalten?"
  ],
  "directions": [
    {
      "priority": 1,
      "corpus": "laws",
      "filter_codes": ["StPO"],
      "seed_queries": ["Haftgründe Verlängerung Untersuchungshaft"],
      "rechtsgebiet": "Strafprozessrecht",
      "reasoning": "StPO Art. 221-240 regelt die Untersuchungshaft"
    },
    {
      "priority": 2,
      "corpus": "courts",
      "filter_codes": ["1B_"],
      "seed_queries": ["Haftverlängerung Verhältnismässigkeit Bundesgericht"],
      "rechtsgebiet": "Strafprozessrecht",
      "reasoning": "1B_ = Bundesgericht Strafrecht Nebenstrafrecht"
    },
    {
      "priority": 3,
      "corpus": "laws",
      "filter_codes": ["BV", "EMRK"],
      "seed_queries": ["Grundrecht persönliche Freiheit Freiheitsentzug"],
      "rechtsgebiet": "Grundrechte",
      "reasoning": "Art. 10 BV und Art. 5 EMRK schützen die persönliche Freiheit"
    },
    {
      "priority": 99,
      "corpus": "both",
      "filter_codes": ["BGG", "BV"],
      "seed_queries": ["Beschwerde Haft Legitimation Frist"],
      "rechtsgebiet": "Verfahrensrecht",
      "reasoning": "Verfahrensrechtlicher Rahmen für Haftbeschwerden"
    }
  ]
}
```

### Validation Step

```python
# For each direction, check filter_codes:
direction[0].filter_codes = ["StPO"]
  → "StPO" in available_law_codes? YES ✓ → keep

direction[2].filter_codes = ["BV", "EMRK"]
  → "BV" in available_law_codes? YES ✓
  → "EMRK" in available_law_codes? YES ✓ → keep both

# If LLM had said filter_codes=["StPO", "FAKE_LAW"]:
  → "StPO" in available_law_codes? YES ✓ → keep
  → "FAKE_LAW" in available_law_codes? NO ✗ → SILENTLY REMOVED
  → result: filter_codes=["StPO"]
```

### Fallback Path (if JSON fails 2x)

```python
# fallback_decompose("...pre-trial detention...")
# Keyword matching:
#   "detention" matches → adds StPO + 1B_
#   nothing else matches → adds catch-all + procedural

# Result: 3 directions:
#   P1: laws, ["StPO"], "Haftrecht"
#   P2: courts, ["1B_"], "Bundesgericht Strafrecht"
#   P99: both, ["BGG","BV"], "Verfahrensrecht"
```

---

## PHASE 2: EXECUTORS (Sequential)

### Direction 1: StPO Laws (priority=1)

#### Iteration 0 (NO LLM — runs seed query directly)

```python
filtered_hybrid_search(
    query = "Haftgründe Verlängerung Untersuchungshaft",
    corpus = "laws",
    filter_codes = ["StPO"],
    top_k = 10
)
```

**Inside `filtered_hybrid_search`:**

```
Step 1: get_valid_filter_indices("laws", ["StPO"])
  → law_code_to_indices["StPO"] exists? YES
  → returns: np.array([45032, 45033, 45034, ..., 46337])  # 1,306 indices

Step 2: FAISS search (IDSelector restricts to those 1,306 rows)
  → embed("Haftgründe Verlängerung Untersuchungshaft") → 768-dim vector
  → index.search(vec, 10, params=IDSelector([1306 indices]))
  → Returns:
    [("Art. 221 Abs. 1 StPO", 0.87),  ← Haftgründe: Flucht/Kollusion/Wiederholung
     ("Art. 227 Abs. 1 StPO", 0.82),  ← Verlängerung der U-Haft
     ("Art. 212 Abs. 3 StPO", 0.79),  ← Verhältnismässigkeit
     ("Art. 226 Abs. 1 StPO", 0.75),  ← Haftprüfung TMG
     ("Art. 220 Abs. 1 StPO", 0.71),  ← Vollzug Haft
     ...]

Step 3: BM25 search (post-filter by same indices)
  → tokens = ["haftgründe", "verlängerung", "untersuchungshaft"]
  → scores = bm25.get_scores(tokens)  # score ALL 175K docs
  → scores[~valid_mask] = 0  # zero out everything not in StPO
  → top-10:
    [("Art. 221 Abs. 1 StPO", 12.4),
     ("Art. 221 Abs. 1 lit. a StPO", 10.8),
     ("Art. 229 Abs. 1 StPO", 9.3),
     ...]

Step 4: RRF Fusion (k=60)
  "Art. 221 Abs. 1 StPO":
    rank_faiss=0 → 1/(60+1) = 0.0164
    rank_bm25=0  → 1/(60+1) = 0.0164
    RRF = 0.0328

  "Art. 227 Abs. 1 StPO":
    rank_faiss=1 → 1/(60+2) = 0.0161
    rank_bm25=4  → 1/(60+5) = 0.0154
    RRF = 0.0315
    ...

Step 5: Adaptive fallback check
  → got 10 results? YES → no fallback needed

RETURNS: [("Art. 221 Abs. 1 StPO", 0.0328, "Die Untersuchungshaft..."),
           ("Art. 227 Abs. 1 StPO", 0.0315, "..."), ...]
```

**direction_citations after iter 0:** 10 citations

#### Iteration 1 (LLM ReAct)

```
EXECUTOR PROMPT:
  System: executor_system.txt (role, rules)
  Variables:
    rechtsgebiet = "Strafprozessrecht"
    corpus = "laws"
    filter_codes = ["StPO"]
    reasoning = "StPO Art. 221-240 regelt die Untersuchungshaft"
    plan_summary = "Frage nach Haftverlängerung..."
    prior_findings = ""  (first direction, no prior)
    direction_history = "ITERATION 0: 'Haftgründe Verlängerung...' → 10 results"

LLM OUTPUT (GBNF-constrained):
{
  "thought": "Iteration 0 covered Haftgründe. Need to explore Dauer/Überhaft limits.",
  "query": "Höchstdauer Untersuchungshaft Überhaft Entlassung",
  "done": false
}
```

**Search:** `filtered_hybrid_search("Höchstdauer Untersuchungshaft Überhaft Entlassung", "laws", ["StPO"], 10)`

```
→ Same filtering process (StPO indices only)
→ Returns new citations:
  [("Art. 212 Abs. 1 StPO", 0.029, "...Verhältnismässigkeit..."),
   ("Art. 228 StPO", 0.027, "...Haftentlassungsgesuch..."),
   ("Art. 231 StPO", 0.025, "...Sicherheitshaft..."),
   ...]
```

**direction_citations after iter 1:** 10 + 10 = 20 (deduplicated later)

#### Iteration 2 (LLM ReAct)

```
LLM OUTPUT:
{
  "thought": "Have Haftgründe + Dauer. Need ZMG (Zwangsmassnahmengericht) procedure.",
  "query": "Zwangsmassnahmengericht Haftverhandlung Verfahren mündlich",
  "done": false
}
```

**Search → adds:** Art. 225 StPO, Art. 226 StPO, Art. 224 StPO...

#### Iteration 3 (LLM ReAct)

```
LLM OUTPUT:
{
  "thought": "All aspects of StPO detention regime covered. Signaling done.",
  "query": "",
  "done": true
}
```

**Direction 1 FINAL OUTPUT:** ~25 unique citations from StPO

---

### Direction 2: Court Decisions (priority=2)

#### Iteration 0 (NO LLM)

```python
filtered_hybrid_search(
    query = "Haftverlängerung Verhältnismässigkeit Bundesgericht",
    corpus = "courts",
    filter_codes = ["1B_"],
    top_k = 10
)
```

**Inside search:**

```
Step 1: get_valid_filter_indices("courts", ["1B_"])
  → court_code_to_indices["1B_"] exists? YES
  → returns: np.array([...])  # 100,934 indices (it's a large chamber)

Step 2: FAISS with IDSelector on those 100K rows
  → returns court decisions about detention

Step 3: BM25 + RRF fusion

RETURNS: [("1B_210/2023 E. 4.1", 0.031, "..."),
           ("1B_42/2022 E. 3.2", 0.028, "..."), ...]
```

**prior_findings now populated:**
```
prior_findings = "Art. 221 Abs. 1 StPO; Art. 227 Abs. 1 StPO; Art. 212 StPO; ..."
(last 20 citations from Direction 1 — prevents repetition)
```

#### Iteration 1 (LLM sees prior findings)

```
LLM OUTPUT:
{
  "thought": "Prior directions found StPO articles. Need BGer Praxis on proportionality test.",
  "query": "Verhältnismässigkeitsprüfung Haftdauer Freiheitsstrafe Überhaft",
  "done": false
}
```

...continues for 2-3 iterations...

---

### Direction 3: Constitutional (priority=3)

```python
filter_codes = ["BV", "EMRK"]  # TWO codes!
```

**Inside `get_valid_filter_indices("laws", ["BV", "EMRK"])`:**

```
Step 1: law_code_to_indices["BV"] → np.array([...]) (248 indices)
Step 2: law_code_to_indices["EMRK"] → np.array([...]) (53 indices)
Step 3: np.unique(np.concatenate([bv_indices, emrk_indices]))
         → 301 total indices (UNION of both codes)
```

FAISS only searches those 301 documents → finds Art. 10 Abs. 2 BV, Art. 31 BV, Art. 5 EMRK...

---

### Direction 4: Procedural (priority=99)

```python
corpus = "both"  # searches BOTH laws and courts!
filter_codes = ["BGG", "BV"]
```

**Inside `search()` with corpus="both":**

```python
# Splits codes by which corpus they belong to:
law_codes = [c for c in ["BGG","BV"] if c in law_code_to_indices]
  → ["BGG", "BV"]  (both exist in laws)

court_codes = [c for c in ["BGG","BV"] if c in court_code_to_indices]
  → []  (neither exists in courts — court codes are like "1B_", "6B_")

# Runs two sub-searches:
r_law = search("Beschwerde Haft Legitimation Frist", "laws", ["BGG","BV"], 10)
r_court = search("Beschwerde Haft Legitimation Frist", "courts", [], 10)
  # ↑ empty filter_codes → UNFILTERED search across all 2.4M court docs

# RRF-merges both result lists → top 10 combined
```

Uses `executor_procedural.txt` (special prompt with BGG article patterns by case type).

---

## PHASE 3: AGGREGATION

### Step 1: Collect All

```python
all_citations = direction_1_cits + direction_2_cits + direction_3_cits + direction_4_cits
# ≈ 25 + 20 + 15 + 15 = 75 raw citations (with duplicates)
```

### Step 2: Detect Case Type

```python
# Scan prefixes of court citations:
#   "1B_210/2023" starts with "1B_" → CRIMINAL
case_type = "criminal"
```

### Step 3: Inject Procedural Defaults

```python
UNIVERSAL_DEFAULTS = [
    "Art. 42 Abs. 2 BGG",   # Begründungspflicht
    "Art. 95 BGG",           # Rügemöglichkeiten
    "Art. 100 Abs. 1 BGG",  # 30-day deadline
    "Art. 105 Abs. 1 BGG",  # Sachverhaltsbindung
    "Art. 29 Abs. 2 BV",    # Rechtliches Gehör
]

CRIMINAL_DEFAULTS = [
    "Art. 78 Abs. 1 BGG",   # Beschwerde in Strafsachen
    "Art. 80 Abs. 1 BGG",   # Letzte kantonale Instanz
    "Art. 81 Abs. 1 lit. a BGG",  # Legitimation
]

DETENTION_SUBTYPE = [  # because "1B_" detected
    "Art. 221 Abs. 1 StPO",  # Haftgründe
    "Art. 10 Abs. 2 BV",     # Persönliche Freiheit
]

# For each default: check if it exists in corpus
for cit in all_defaults:
    if cit in meta.law_citation_set:  # ← THIS is why the test checks existence
        inject(cit, score=0.3)
    # If citation doesn't exist in corpus → SKIP (don't inject phantom)
```

### Step 4: Deduplicate

```python
# Many directions found "Art. 221 Abs. 1 StPO" independently:
#   Direction 1: score 0.87 (FAISS)
#   Direction 3: score 0.45 (BV search also caught it)
#   Default injection: score 0.3
#
# KEEP HIGHEST: {"Art. 221 Abs. 1 StPO": 0.87}

# Before: 75 raw + 10 defaults = 85
# After dedup: ~45 unique citations
```

### Step 5: Reranker

```python
# Qwen3-Reranker-0.6B (GPU 1)
# Input: (English question, German text) pairs
pairs = [
    ("Under what conditions can pre-trial detention be extended?",
     "Die Untersuchungshaft wird angeordnet wenn ein dringender Tatverdacht..."),
    ("Under what conditions can pre-trial detention be extended?",
     "Das Gericht entscheidet über die Beschwerdelegitimation..."),
    ...  # 45 pairs
]

# Output: sigmoid scores [0, 1]
reranker_scores = {
    "Art. 221 Abs. 1 StPO": 0.94,    # very relevant (Haftgründe!)
    "Art. 227 Abs. 1 StPO": 0.89,    # very relevant (Verlängerung!)
    "Art. 212 Abs. 3 StPO": 0.82,    # relevant (Verhältnismässigkeit)
    "1B_210/2023 E. 4.1":   0.78,    # relevant court case
    "Art. 29 Abs. 2 BV":    0.41,    # somewhat relevant (Gehör)
    "Art. 42 Abs. 2 BGG":   0.35,    # procedural, less specific
    "Art. 530 OR":           0.05,    # ← irrelevant! (partnership law)
    ...
}
```

### Step 6: Cutoff + Cap

```python
# Keep only score ≥ 0.2:
kept = [c for c in sorted_results if c.score >= 0.2]
# "Art. 530 OR" (0.05) → DROPPED

# Cap at 60 (usually ~20-35 survive the cutoff)
final = kept[:60]
```

### Step 7: Safety Override

```python
# IF all scores < 0.2 (reranker says nothing is relevant):
if not kept:
    final = sorted_results[:10]  # return top-10 anyway
    # NEVER return empty!
```

### Step 8: Prepend Explicit Citations

```python
# Regex-extract from original question:
explicit = regex_extract_citations("Under what conditions can pre-trial detention...")
# → [] (no explicit citations in this question)

# But if question was:
# "Does Art. 221 Abs. 1 StPO apply when..."
# → explicit = ["Art. 221 Abs. 1 StPO"]
# → prepend to front of list (score=1.0) if exists in corpus
```

---

## FINAL OUTPUT

```python
submission_row = ";".join([
    "Art. 221 Abs. 1 StPO",       # 0.94
    "Art. 227 Abs. 1 StPO",       # 0.89
    "Art. 212 Abs. 3 StPO",       # 0.82
    "1B_210/2023 E. 4.1",         # 0.78
    "Art. 225 Abs. 1 StPO",       # 0.75
    "Art. 226 Abs. 1 StPO",       # 0.72
    "BGE 137 IV 122",             # 0.68
    "Art. 31 Abs. 1 BV",          # 0.55
    "Art. 10 Abs. 2 BV",          # 0.48
    "Art. 5 Ziff. 3 EMRK",       # 0.44
    "Art. 29 Abs. 2 BV",          # 0.41
    "Art. 78 Abs. 1 BGG",         # 0.38
    "Art. 42 Abs. 2 BGG",         # 0.35
    "Art. 95 BGG",                # 0.31
    # ... (20-35 total citations)
])
# → written to submission.csv
```

---

## EDGE CASE TRACES

### Edge Case 1: LLM Hallucinates a Code

```
Planner says: filter_codes = ["StPO", "BÜPF", "MilitärStGB"]

Validation:
  "StPO" in available_law_codes → YES ✓
  "BÜPF" in available_law_codes → NO ✗ (only 12 docs, below threshold) → REMOVED
  "MilitärStGB" in available_law_codes → NO ✗ (doesn't exist at all) → REMOVED

After validation: filter_codes = ["StPO"]
→ search proceeds normally with StPO only
```

### Edge Case 2: ALL Codes Invalid

```
Planner says: filter_codes = ["FAKE1", "FAKE2"]

get_valid_filter_indices("laws", ["FAKE1", "FAKE2"]):
  "FAKE1" not in law_code_to_indices → skip
  "FAKE2" not in law_code_to_indices → skip
  arrays = []  ← empty!
  → returns None

search() receives valid_indices=None
  → NO IDSelector applied → FULL CORPUS search (175K docs)
  → still returns 10 results (just unfiltered)
```

### Edge Case 3: Filter Returns <5 Results

```
filter_codes = ["EMRK"]  # only 53 docs total
query = "very specific obscure topic"

FAISS(53 docs) + BM25(53 docs) → RRF → 3 results

Adaptive fallback triggers:
  len(combined) = 3 < 5 AND valid_indices was not None
  → RE-SEARCH: search(query, "laws", [], 10)  # unfiltered!
  → gets 10 results from full 175K corpus
```

### Edge Case 4: Executor Generates Repeated Query

```
Iter 1 query: "Haftgründe Untersuchungshaft StPO"
Iter 2 query: "Haftgründe Untersuchungshaft StPO"  ← SAME!

→ Detected: query in direction_history
→ Force done=true, stop this direction early
→ Prevents wasting LLM tokens on duplicate searches
```

### Edge Case 5: corpus="both" with Mixed Codes

```
Planner says: corpus="both", filter_codes=["StPO", "1B_", "BGG"]

Inside search(corpus="both"):
  law_codes = ["StPO", "BGG"]  # exist in law_code_to_indices
  court_codes = ["1B_"]         # exists in court_code_to_indices

  search("query", "laws", ["StPO","BGG"], 10)   → 10 law results
  search("query", "courts", ["1B_"], 10)         → 10 court results
  RRF merge both → top 10 combined
```

---

## TIMING BREAKDOWN (Per Question)

```
Phase 1 Planner:
  System prompt assembly:     ~5ms
  LLM generation (500 tok):   ~2s
  JSON parse + validate:      ~1ms
                              ────
  TOTAL:                      ~2s

Phase 2 Executors (4 directions × avg 3 iterations):
  Per search call:            ~50-300ms
  Per LLM call (iter 1-3):   ~1.5s
  Per direction:              ~5s
                              ────
  TOTAL (sequential):         ~20s

Phase 3 Aggregation:
  Collect + dedup:            ~5ms
  Default injection:          ~1ms
  Reranker (35 pairs):        ~4s
  Cutoff + format:            ~1ms
                              ────
  TOTAL:                      ~4s

═══════════════════════════════════
GRAND TOTAL PER QUESTION:     ~26s
× 40 questions:               ~17 minutes
Budget allowed:               30 minutes ✓
```

# Pipeline Deep Analysis — Query 1 (Post-Fix Run)

**Timestamp:** 2026-05-31 07:31:02  
**Result:** F1 = 0.0385 (1/42 gold citations found)  
**Only hit:** Art. 100 Abs. 1 BGG (from procedural defaults)  
**Total time:** 171.3s

---

## ✅ GOOD NEWS: Question Fix Worked

```
Input question: May a court lawfully order a three‑month extension of pre‑trial 
detention under Art. 221 Abs. 1 lit. b StPO (risk of collusion)...
```

The question IS flowing through now. Domain selection correctly identified STRAFPROZESS (score=17).

---

## 🔴 BUG #1 (SHOW-STOPPER): Reranker Gives UNIFORM 0.0039 to ALL 84 Candidates

```
Score range: 0.0039 → 0.0039
Above cutoff (0.2): 0
Below cutoff (dropped): 84
```

**This is the #1 problem.** Even with the correct question flowing through:
- Direction 4 found `Art. 221 Abs. 1 StPO` (GOLD HIT)
- Direction 4 found `Art. 212 Abs. 3 StPO` (GOLD HIT)
- Direction 4 found `Art. 382 Abs. 1 StPO` (GOLD HIT)

ALL were dropped because the reranker scored them 0.0039 (below 0.2 cutoff).

### Root Cause Analysis

The reranker uses Qwen3-Reranker-0.6B with generative P(yes)/P(no) scoring. Every single document gets identical 0.0039 score — this means the model is NOT differentiating at all.

**Possible causes (in order of likelihood):**

1. **Query not being passed to reranker** — The reranker function may be receiving an empty string or the wrong variable as the query
2. **Input format mismatch** — Qwen3-Reranker expects a specific prompt template (e.g., `<|im_start|>user\nIs the following document relevant to the query?\nQuery: ...\nDocument: ...\n<|im_end|>`) and may be getting raw concatenation
3. **Token IDs for "yes"/"no" are wrong** — The logit extraction may be using wrong token IDs for the Qwen3 tokenizer
4. **Model loaded in wrong mode** — If loaded as causal LM but scoring isn't using the right generation approach

### Evidence It's NOT a Query Issue

The question is 200+ words of detailed German legal text about Untersuchungshaft. If the reranker were receiving this, it would CERTAINLY score `Art. 221 Abs. 1 StPO — Untersuchungs- und Sicherheitshaft sind nur zulässig...` higher than random documents about child maintenance.

### 🔧 ACTION REQUIRED

**Must inspect the reranker code** — specifically:
- What query string is passed to the reranker function?
- What prompt template wraps the query + document pairs?
- What token IDs are used for yes/no logit extraction?
- Is the model generating or just doing a forward pass?

---

## 🔴 BUG #2 (CRITICAL): Planner JSON Truncated — max_tokens_planner=800 Too Low

```
LLM response time: 50.57s
...
"filter_codes":
✗ JSON parse error: Expecting value: line 25 column 22 (char 2276)
Attempting retry with correction prompt...
✗ Retry also failed → returning None (will use fallback)
```

The planner's first attempt was **excellent** — it correctly identified:
- Direction 1: StPO for Kollusionsgefahr/Haftverlängerung ✓
- Direction 2: Court decisions (6B_ — wrong code but right idea) 
- Direction 3: Was generating more StPO directions when truncated

But `max_tokens_planner=800` is far too low for a complex question. The sachverhalt alone consumed ~600 tokens (it's a verbatim translation of the full question). The directions started at token ~650 and got cut at ~800.

### Impact

The pipeline fell back to a generic keyword-based plan with:
- NO seed queries (executors don't know what to search for)
- Wrong court codes (6B_ instead of 1B_)
- Generic domain labels instead of targeted reasoning

### 🔧 FIX

Increase `max_tokens_planner` from 800 → **1500-2000**. The planner needs room for:
- sachverhalt (~200 tokens for long questions)
- rechtsfragen (~50 tokens)
- 4 directions × ~100 tokens each = ~400 tokens
- JSON overhead ~100 tokens
- **Total minimum: ~850 tokens, safe buffer: 1200+**

---

## 🔴 BUG #3 (CRITICAL): Direction 5 (1B_ Courts) Crashed Immediately

```
DIRECTION 5/6 — Filter codes: ['1B_']
[Iter 1] LLM time: 7.46s
Raw output: {"thought": "...Untersuchungshaft, Haftprüfung, Haftgrund, Fluchtgefahr, 
  Kollusionsgefahr, Verhältnismässigkeit, Haftentlassung,
✗ JSON parse failed — stopping direction
Direction 5 COMPLETE: 0 citations in 7.5s
```

**This was THE most important direction.** The gold contains 12 court decisions from 1B_ and 7B_ prefixes. Getting 0 citations from the 1B_ search is catastrophic.

### Root Cause

`max_tokens_executor=200` — the executor generated a verbose thought (~450 chars ≈ 110 tokens) then started the query but ran out of tokens before closing the JSON.

### 🔧 FIX

Increase `max_tokens_executor` from 200 → **350-400**.

OR add JSON repair: if output is truncated, extract the last `"query": "..."` substring and use it.

---

## 🟠 BUG #4 (HIGH): Fallback Plan Has Empty Seed Queries

```
Dir 1: corpus=laws, codes=['BGG', 'BV'], reason=Domain match: PROZESSRECHT (score=2)
  Seed queries: []
Dir 2: corpus=laws, codes=['StGB'], reason=Domain match: STRAFRECHT (score=4)  
  Seed queries: []
```

When the planner fails and the fallback kicks in, **all seed queries are empty**. The executors have no idea what the case is about — they just see a domain label like "STRAFRECHT."

### Impact (Direction 2 — StGB)

The executor searched for:
```
"Strafzumessung Freiheitsstrafe Bewährung Vorsatz Fahrlässigkeit"
```

The case is about **Raub/Diebstahl/Nötigung** (Art. 140 StGB is in gold — robbery/assault). But the executor has no context, so it searches generic sentencing law. 0 gold hits from Direction 2.

### Impact (Direction 3 — 6B_ Courts)

Same problem — searched "Strafzumessung Konzepte" instead of anything related to Untersuchungshaft. All 25 citations are about Art. 47 StGB sentencing guidelines. 0 gold hits.

### 🔧 FIX

The fallback plan should extract keywords from the question and use them as seed queries. Example:
```python
# Extract key terms from question for seed queries
keywords = extract_legal_keywords(question)  # "Untersuchungshaft Kollusionsgefahr Haftverlängerung Verhältnismässigkeit"
seed = [" ".join(keywords[:5])]
```

---

## 🟠 BUG #5 (HIGH): Wrong Court Code — 6B_ Instead of 1B_/7B_

The fallback plan assigned `6B_` to "STRAFRECHT" domain. But:

| Code | Division | Covers |
|------|----------|--------|
| `6B_` | Strafrechtliche Abteilung | Substantive criminal law (guilt, sentencing) |
| `1B_` | I. öffentlich-rechtliche Abteilung | **Pre-trial detention**, interim measures |
| `7B_` | Strafrechtliche Beschwerdekammer | **Criminal complaints about detention** |

The gold has **7 decisions from 1B_** and **5 from 7B_**. Zero from 6B_.

### Root Cause

The domain-to-court-code mapping in the fallback logic maps "STRAFRECHT" → `6B_` generically, without considering the sub-topic (Haft vs Strafzumessung).

### Evidence from Domain Scores

```
COURT_STRAFPROZESS → 7  (highest court score!)
```

The keyword matcher correctly identified COURT_STRAFPROZESS (which maps to 1B_), but the fallback plan used the wrong mapping for Direction 3.

### 🔧 FIX

The fallback should use COURT_STRAFPROZESS score (7) to assign `1B_` code, not just the law domain mapping. The court division scores should drive the court corpus filter selection.

---

## 🟠 BUG #6 (HIGH): Direction 4 Found Gold Hits But They Were Killed

Direction 4 (StPO laws) actually retrieved:

| Citation | Score | In Gold? |
|----------|-------|----------|
| Art. 212 Abs. 3 StPO | 0.027 | ✅ YES |
| Art. 221 Abs. 1 StPO | 0.016 | ✅ YES |
| Art. 382 Abs. 1 StPO | 0.016 | ✅ YES |
| Art. 212 Abs. 2 StPO | 0.029 | No (but Abs. 3 is) |
| Art. 221 Abs. 1bis StPO | 0.016 | No (but related) |

**3 gold hits were successfully retrieved** by the vector search — then the reranker scored them all 0.0039 and dropped them.

### Without the Reranker Bug

If the reranker worked correctly, this single direction alone would have produced:
- Art. 221 Abs. 1 StPO ✓
- Art. 212 Abs. 3 StPO ✓  
- Art. 382 Abs. 1 StPO ✓
- Plus Art. 100 Abs. 1 BGG from defaults ✓

That's 4/42 = F1 ≈ 0.17 — still low, but 4.4× better than current.

---

## 🟡 BUG #7 (MEDIUM): Executor Queries Are Generic, Not Case-Specific

Even when the executor IS searching StPO (Direction 4), its queries are generic:
```
"Haftprüfung Haftgrund Verhältnismässigkeit Strafprozessordnung"
"Haftprüfung Haftgrund Verhältnismäßigkeit Artikel 212-240 StPO"
```

It should be generating case-specific queries like:
```
"Kollusionsgefahr Verlängerung Untersuchungshaft Zeugen Beeinflussung"
"Haftverlängerung drei Monate Verhältnismässigkeit Art. 227 StPO"
"Beschwerde Haftverlängerung Kollusionsgefahr StPO Art. 222"
```

### Root Cause

The executor system prompt doesn't include the original question. It only gets:
- The domain/taxonomy context
- Prior findings (citation titles only)
- A generic instruction to search

Without the question, it can't generate targeted queries.

### 🔧 FIX

Pass a condensed version of the question (or the planner's `rechtsfragen`) to the executor prompt.

---

## 🟡 BUG #8 (MEDIUM): 7B_ Court Prefix Never Searched

The gold contains 5 decisions with `7B_` prefix:
- 7B_496/2025 E. 3.2
- 7B_231/2025 E. 4.1
- 7B_69/2024 E. 3.3.2
- 7B_301/2024 E. 2.4
- 7B_12/2025 E. 2.2

No direction searched `7B_`. The fallback plan only has `1B_` and `6B_`.

### Root Cause

The court taxonomy likely doesn't include `7B_` as a filter option, or the COURT_STRAFPROZESS mapping only yields `1B_`.

### 🔧 FIX

Either:
- Add `7B_` alongside `1B_` in STRAFPROZESS court searches
- Or allow wildcard court searching without prefix filter for high-scoring domains

---

## 🟡 BUG #9 (MEDIUM): StBOG (Bundesstrafgericht) Never Searched

Gold contains:
- Art. 37 Abs. 1 StBOG
- Art. 39 Abs. 1 StBOG

No direction searched StBOG. The law taxonomy may not include this code.

### 🔧 FIX

Add StBOG to STRAFPROZESS domain taxonomy or add it as a companion code alongside StPO.

---

## 🟡 BUG #10 (MEDIUM): Duplicate Directions Waste Compute

Directions 1 and 6 both search BGG/BV with nearly identical queries:
- Dir 1: "Prozessrecht Bundesgericht BGG BV rechtliches Gehör Beschwerde Frist"
- Dir 6: "Beschwerde Bundesgericht Legitimation Frist"

Same results, wasted ~24s of LLM time.

---

## 📊 Where the 42 Gold Citations Should Come From

| Source | Gold Count | Pipeline Coverage | Issue |
|--------|-----------|-------------------|-------|
| StPO (laws) | 17 articles | Dir 4 found 3, reranker killed all | Reranker broken |
| 1B_ (courts) | 7 decisions | Dir 5 crashed (0 citations) | max_tokens |
| 7B_ (courts) | 5 decisions | Never searched | Missing code |
| BGE (courts) | 10 decisions | Never searched (no BGE prefix) | Missing direction |
| BGG (laws) | 1 article | Found via defaults ✓ | Working |
| StGB (laws) | 1 article | Dir 2 searched wrong topic | No context |
| StBOG (laws) | 2 articles | Never searched | Missing code |

---

## 🏗️ Priority Fixes (Ordered by Impact)

### P0 — Must Fix (Blocks Everything)

| # | Fix | Impact | Effort |
|---|-----|--------|--------|
| 1 | **Fix reranker** — inspect what query is passed, check prompt format, verify yes/no token IDs | Unblocks ALL correct retrievals from being output | High |
| 2 | **Increase max_tokens_planner** 800→1500 | Prevents fallback to generic plan, enables targeted search | Trivial |
| 3 | **Increase max_tokens_executor** 200→350 | Prevents Direction 5 crash (1B_ courts = 7 gold hits) | Trivial |

### P1 — High Impact

| # | Fix | Impact | Effort |
|---|-----|--------|--------|
| 4 | **Pass question to executor** (or at minimum, seed queries from keywords) | Executors search the right topic instead of generic law | Medium |
| 5 | **Add 7B_ to STRAFPROZESS court search** | Recovers 5 gold hits | Trivial |
| 6 | **Fix fallback seed queries** — extract from question | Executors know what to search even without planner | Medium |

### P2 — Medium Impact

| # | Fix | Impact | Effort |
|---|-----|--------|--------|
| 7 | Add StBOG to STRAFPROZESS companion codes | Recovers 2 gold hits | Trivial |
| 8 | Add BGE prefix search for leading cases | Recovers 10 gold hits | Medium |
| 9 | Add JSON repair for truncated executor output | Prevents direction crashes | Medium |
| 10 | Defaults bypass reranker cutoff | Ensures procedural defaults always in output | Trivial |

---

## 🎯 Theoretical Maximum with All Fixes

If all P0+P1+P2 fixes were applied:
- StPO articles (17): Findable via Direction 4 with better queries + working reranker
- 1B_ courts (7): Findable if Direction 5 doesn't crash
- 7B_ courts (5): Findable if code is added
- BGE cases (10): Partially findable (need BGE prefix support)
- StGB Art. 140 (1): Findable with targeted query
- BGG Art. 100 (1): Already found ✓
- StBOG (2): Findable if code added

**Optimistic estimate with all fixes: 25-35/42 = F1 ≈ 0.55-0.75**

---

## 🔬 Deep Dive: What's Wrong with the Reranker?

The reranker receives 84 candidates and scores them all identically at 0.0039. This is `sigmoid(-5.5)` ≈ 0.004, meaning the model's `logit(yes) - logit(no)` ≈ -5.5 for EVERY pair.

### Hypothesis 1: Empty/Wrong Query Passed to Reranker

Even though the question flows correctly to the planner and executors, the reranker may receive a different variable. Check:
```python
# In the reranking function — what is 'query' here?
scores = rerank(query=???, documents=candidates)
```

### Hypothesis 2: Wrong Prompt Format

Qwen3-Reranker-0.6B likely expects:
```
<|im_start|>user
Given a query and a document, determine if the document is relevant.
Query: {query}
Document: {document}
Is this document relevant to the query? Answer yes or no.
<|im_end|>
<|im_start|>assistant
```

If it's getting just `f"{query} [SEP] {document}"` or similar, it won't work.

### Hypothesis 3: Wrong Token IDs

The code extracts logits for "yes" and "no" tokens. But Qwen3 tokenizer may encode these differently:
- "yes" might be token 9891 (not 3869)
- "Yes" vs "yes" vs "YES" — case matters
- German model might use "ja"/"nein" instead

### Verification Steps

1. Print the exact input string sent to the reranker for 1 candidate
2. Print the raw logits for the first 10 tokens of the model's output
3. Check if the "yes"/"no" token IDs match what the code expects
4. Try scoring a trivially obvious pair (query="Haft", doc="Haft ist...") — if still 0.0039, the model is fundamentally misconfigured

---

## Summary

The pipeline has **one blocking bug** (reranker always returns 0.0039) and **two critical resource limits** (max_tokens too low for planner and executor). Everything else is secondary.

**Fix order:**
1. Reranker (blocks all correct output)
2. max_tokens_planner (blocks intelligent planning)
3. max_tokens_executor (blocks 1B_ court retrieval)
4. Everything else

# Planner Prompt & Context — Detailed Step-by-Step Analysis

**Query 1** | Pre-trial detention extension (Kollusionsgefahr)

---

## STEP 1: The Question Arrives

```
May a court lawfully order a three‑month extension of pre‑trial detention 
under Art. 221 Abs. 1 lit. b StPO (risk of collusion)...
```

**What a lawyer would identify from this question:**
- Topic: **Untersuchungshaft** (pre-trial detention)
- Specific law cited: **Art. 221 Abs. 1 lit. b StPO**
- Legal issues: Kollusionsgefahr (collusion risk), Verhältnismässigkeit (proportionality), Haftverlängerung (detention extension)
- Underlying crime: assault + theft (→ Art. 140 StGB = Raub)
- Procedure: detention extension hearing (Art. 227 StPO)
- Appeal route: Beschwerde → 1B_ / 7B_ at Federal Court (NOT 6B_)

---

## STEP 2: Context Selection (Keyword Router)

The system scores domains by matching keywords in the question.

```
LAW DOMAIN SCORES:
  STRAFPROZESS    → 17 ★   (matched: detention, collusion, witness, evidence, etc.)
  STRAFRECHT      →  4 ★   (matched: assault, theft)
  ZIVILRECHT      →  3     
  PROZESSRECHT    →  2 ★   (matched: court, proportionality)
  OEFFENTL_RECHT  →  2
  FINANZMARKT     →  2     ← WHY? Nothing about finance in this question
```

**Selected domains: {PROZESSRECHT, STRAFRECHT, STRAFPROZESS}**

### Verdict: ✅ CORRECT domain selection
- STRAFPROZESS dominant = correct (this IS a criminal procedure question)
- STRAFRECHT included = correct (underlying offence matters for gold: Art. 140 StGB)
- PROZESSRECHT included = correct (BGG/procedural aspects)

### Issue: FINANZMARKT scored 2
Likely a false positive from generic words like "order" or "risk" that also appear in financial keywords. Not harmful since it wasn't selected, but shows the keyword router has some noise.

---

## STEP 3: Court Division Scoring

```
COURT DIVISION SCORES:
  COURT_STRAFPROZESS  → 7
  All others          → 0
```

### Verdict: ⚠️ INCOMPLETE
Only `COURT_STRAFPROZESS` matched. But what section does this map to in the injected context?

Looking at the injected context, the court section shown is:
```
=== STRAFRECHTLICHE ABTEILUNG ===
Präfixe: 6B_, 6F_
• 6B_ (72'691 Entscheide): Strafrecht materiell und Strafzumessung
```

**PROBLEM:** The `COURT_STRAFPROZESS` keyword domain mapped to the `STRAFRECHTLICHE ABTEILUNG (6B_)` section — but detention cases (Haftbeschwerden) belong to **I. ÖFFENTLICH-RECHTLICHE ABTEILUNG (1B_, 7B_)**. 

The routing system does NOT have a separate court section for "Haftbeschwerden = 1B_/7B_". It lumps "Strafprozess" with "6B_" because both are under "criminal" umbrella. But in Swiss Federal Court structure:
- **6B_** = Criminal Division (substantive criminal law appeals — guilty/not guilty, sentencing)
- **1B_** = Public Law Division handling **criminal procedure interim measures** (detention reviews, seizures)
- **7B_** = Newer designation for same 1B_ matters

This is a **structural bug in the routing taxonomy** — the context shows the LLM `6B_` as the relevant court, when it should be showing `1B_`/`7B_`.

---

## STEP 4: The Injected Context (User Message Part 1)

7,518 chars of routing context is injected. Let me evaluate each section:

### Section A: Classification Rules Header
```
1. STRAFRECHT vs STRAFPROZESS: 
   - Verfahren (Untersuchungshaft, Beschwerde, Berufung, Beweis) → StPO
   - FALLE: "Untersuchungshaft" ist IMMER StPO (Art. 212-240), NICHT StGB
```
**Verdict: ✅ EXCELLENT** — directly tells the LLM that Untersuchungshaft = StPO. This is perfect for this query.

### Section B: Law Taxonomy (STRAFPROZESSRECHT)
```
• StPO — 1'306 Artikel
  Schlüsselwörter: Untersuchungshaft, Sicherheitshaft, Haftgrund, Fluchtgefahr, 
                   Kollusionsgefahr, Wiederholungsgefahr...
  Wichtige Bereiche: Art. 212-240 (Haft), Art. 382-397 (Rechtsmittel)
  KRITISCH: "Haftprüfung", "Haftverlängerung" → IMMER StPO
```
**Verdict: ✅ EXCELLENT** — all the right keywords for this query are listed.

```
• StBOG (Strafbehördenorganisationsgesetz) — 183 Artikel
  Schlüsselwörter: Bundesstrafgericht, Bundesanwaltschaft, Beschwerdekammer
```
**Verdict: ✅ PRESENT** — StBOG is shown. Gold contains Art. 37/39 StBOG. But no guidance that StBOG is relevant for detention cases. The model would need to know that the Beschwerdekammer handles Haftbeschwerden at federal level.

### Section C: Law Taxonomy (PROZESSRECHT)
```
• BGG — 325 Artikel
  KRITISCH: Art. 100 Abs. 1 BGG (30-Tage-Frist) kommt in fast JEDEM Bundesgerichtsfall vor
```
**Verdict: ✅ GOOD** — explicitly tells the LLM that BGG Art. 100 is always cited. (It IS in the gold.)

### Section D: Law Taxonomy (STRAFRECHT materiell)
```
• StGB — 1'239 Artikel
  Schlüsselwörter: ...Körperverletzung, Diebstahl...
```
**Verdict: ✅ PRESENT** — but no guidance that the underlying crime matters for detention (it determines the severity that justifies detention duration).

### Section E: Court Classification Rules
```
2. ABTEILUNGS-ZUORDNUNG:
   - Fragen zu Strafrecht/Strafprozess → BGE IV + 6B_ + 1B_ (Haft)
```
**Verdict: ⚠️ THE KEY LINE** — This says "1B_ (Haft)" explicitly! But:
1. It's buried in a dense list
2. The "(Haft)" annotation is just a parenthetical
3. No further explanation of WHEN to use 1B_ vs 6B_
4. The court section below ONLY shows 6B_ details, not 1B_ details

### Section F: Court Sections (What was actually injected)
```
=== STRAFRECHTLICHE ABTEILUNG ===
Präfixe: 6B_, 6F_
BGE: BGE [Nr] IV [Seite]

• 6B_ (72'691 Entscheide): Strafrecht materiell und Strafzumessung
  Inhalt: Schuldspruch, Strafzumessung, Beweiswürdigung, Landesverweisung
  KRITISCH: "Strafurteil" + "Strafmass" → 6B_
```
**Verdict: ❌ WRONG SECTION INJECTED** 

The log shows `[... gekürzt ...]` after the 6B_ section — meaning the `1B_` section was either:
1. Not part of `COURT_STRAFPROZESS` mapping at all
2. Truncated due to the 7,500 char limit

**This is the root cause of the planner choosing 6B_.** The context ONLY shows `6B_` court details. The LLM never sees a description of `1B_` saying "Haftbeschwerden, Zwangsmassnahmen, Untersuchungshaft".

### What's MISSING from injected context:
```
=== I. ÖFFENTLICH-RECHTLICHE ABTEILUNG ===
Präfixe: 1B_, 1C_
• 1B_ (8'245 Entscheide): Strafprozessuale Zwangsmassnahmen (Haft!)
  Inhalt: Untersuchungshaft, Haftentlassung, Haftprüfung, Beschlagnahme
  KRITISCH: Haftbeschwerden → IMMER 1B_, NICHT 6B_!

=== NEUERE ABTEILUNG ===  
• 7B_ (4'105 Entscheide): Strafprozessuale Beschwerden (ab ~2023)
```

This section either doesn't exist in the taxonomy OR wasn't selected by the router.

---

## STEP 5: The System Prompt (Static Template)

17,867 chars. Contains:

### 5.1 Role + Task Definition
```
Du bist ein erfahrener Schweizer Rechtsanwalt...
DEINE AUFGABE: Recherche-Plan erstellen
```
**Verdict: ✅ Fine** — clear role.

### 5.2 Output Schema
```json
{"sachverhalt": "...", "rechtsfragen": [...], "directions": [...]}
```
**Verdict: ✅ Fine** — well-structured.

### 5.3 Rules for Directions
```
- Mindestens 3, maximal 6 Richtungen
- IMMER eine "Verfahrensrecht"-Richtung einschliessen (BGG/BV/ATSG)
- IMMER sowohl Gesetze ALS AUCH Gerichte abdecken
```
**Verdict: ⚠️ PROBLEM** — says "min 3, max 6" and "ALWAYS cover both laws AND courts". The LLM produced exactly 3 directions but only 1 court direction. Technically it's valid (>=3, has courts), but the rules aren't enforcing ENOUGH court coverage.

### 5.4 Available Codes
```
Gesetze: OR(3662), FINMA(2589), ..., StPO(1306), ..., StBOG(183), ..., BGG(325)...
Gerichte: 6B_(25579), ..., 1B_(8245), 7B_(4105), ..., BGE_IV(1067)...
```
**Verdict: ✅ All necessary codes are listed.** The LLM CAN choose 1B_, 7B_, BGE_IV — they're in the list. It just DIDN'T.

### 5.5 BEISPIEL 1 — THE CRITICAL EXAMPLE
```json
Frage: "Under what conditions can pre-trial detention be extended?"
{
  "directions": [
    {"filter_codes": ["StPO"], ...},
    {"filter_codes": ["1B_"], "reasoning": "Bundesgerichtspraxis zu Haftfragen (Abteilung 1B)"},
    {"filter_codes": ["BGE_IV"], "reasoning": "Publizierte Leitentscheide zu Haft und Strafprozess"},
    {"filter_codes": ["BV", "BGG"], "reasoning": "Verfahrensrechtliche Grundlagen"}
  ]
}
```

**Verdict: ❌ THIS IS THE SMOKING GUN**

The system prompt has an EXACT example for this type of question showing:
- Direction with `1B_` for Haftfragen
- Direction with `BGE_IV` for Leitentscheide
- 4 directions total

**The LLM IGNORED its own few-shot example and produced:**
- Direction with `6B_` (wrong!)
- NO `BGE_IV` direction
- NO `1B_` direction
- Only 3 directions

This means the 7B model is NOT following the few-shot example even though the example is literally about the same legal topic (Haftverlängerung). The model saw the pattern but chose differently.

---

## STEP 6: How the Final Prompt is Assembled

```
[INST] {system_prompt: 17,867 chars}\n\n{context_text: 7,518 chars}\n\nFRAGE: {question: 1,077 chars} [/INST]
```

Total: **26,479 chars (~6,619 tokens)** out of 16,384 ctx = 40% utilization.

### Prompt Structure Issues:

**Issue 1: System prompt + user content in ONE [INST] block**
Mistral-7B's instruction format is `[INST] ... [/INST]`. The code puts EVERYTHING (system prompt + context + question) in a single `[INST]` block:
```
prompt = f"[INST] {system_prompt}\n\n{user_msg} [/INST]"
```

This means there's NO separation between "system instructions" and "user input". The model can't distinguish between role definition, examples, routing context, and the actual question. Everything is one flat instruction.

**Issue 2: Example 1 is DIRECTLY relevant but model ignores it**
The example shows `1B_` for detention but the model chose `6B_`. Possible reasons:
- The injected context section (which shows 6B_ details prominently) comes AFTER the examples in the prompt
- Recency bias: the last thing before the question is the context showing 6B_ details
- The model conflates "Strafprozess" with "Strafrechtliche Abteilung" despite the example

**Issue 3: Context section positions**
The prompt order is:
```
1. System prompt (role + format + codes + examples)  ← 17,867 chars
2. \n\n
3. Context text (routing rules + taxonomy)           ← 7,518 chars
4. \n\nFRAGE: question                              ← 1,077 chars
```

The classification rule "Strafprozess → 1B_ (Haft)" is in the context section at position ~20,000 chars. The 6B_ description is at position ~22,000 chars. The question is at position ~25,400 chars.

**The 6B_ description is CLOSER to the question** than the Example 1 showing 1B_. This likely causes the model to anchor on 6B_.

---

## STEP 7: What the Planner ACTUALLY Produced

```json
{
  "sachverhalt": "...(very long, essentially re-translates the question to German)...",
  "rechtsfragen": ["Kollusionsgefahr bei Untersuchungshaft", "Verhältnismäßigkeit der Haftverlängerung"],
  "directions": [
    {"priority": 1, "corpus": "laws",   "filter_codes": ["StPO"],  ...},
    {"priority": 2, "corpus": "courts", "filter_codes": ["6B_"],   ...},
    {"priority": 3, "corpus": "laws",   "filter_codes": ["BGG"],   ...}
  ]
}
```

### Problems with LLM Output:

| Field | Issue | Severity |
|-------|-------|----------|
| sachverhalt | Way too long (602 chars). Just re-translates the question verbatim instead of summarizing. | Low (doesn't affect search) |
| rechtsfragen | Only 2 questions. Missing: "Beschwerdelegitimation", "amtliche Verteidigung", "Verfahrenskosten", "Straftatbestand Raub" | Medium |
| Direction 1 | ✅ StPO laws — correct | — |
| Direction 2 | ❌ **6B_ instead of 1B_/7B_** — Fatal. 6B_ is sentencing appeals, not detention | **CRITICAL** |
| Direction 3 | ⚠️ BGG laws only — useful but too narrow (just 1 seed query) | Medium |
| Missing | ❌ No 1B_/7B_ direction (Haftbeschwerden) | **CRITICAL** |
| Missing | ❌ No BGE_IV/BGE_I direction (Leitentscheide) | **CRITICAL** |
| Missing | ❌ No StBOG direction | Medium |
| Missing | ❌ No StGB direction (Art. 140 = Raub) | Medium |
| Count | Only 3 directions (minimum allowed) — should have 5-6 | Medium |
| Rule violation | "IMMER sowohl Gesetze ALS AUCH Gerichte abdecken" — has 2 law + 1 court = technically OK but barely | Low |

---

## STEP 8: Root Cause Summary

### Why the LLM chose 6B_ instead of 1B_:

1. **Context showed 6B_ section prominently** — the only detailed court section injected describes 6B_ with keywords "Strafrecht materiell und Strafzumessung"
2. **No 1B_ section was injected** — the LLM never sees a description of 1B_ that says "Haftbeschwerden"
3. **The model conflates "Strafprozess" = "Strafrechtliche Abteilung"** — a natural mistake if you don't know Swiss court structure
4. **The example 1 (showing 1B_) was too far back in the prompt** (position ~2000-4000 in the system prompt, vs the 6B_ section at position ~22000 in user message) — recency bias
5. **No explicit rule saying "Haft → IMMER 1B_, NIEMALS 6B_"** — the "(Haft)" annotation is too subtle

### Why only 3 directions:

1. The model stopped at the minimum (3) because it didn't identify additional legal aspects
2. The rechtsfragen only captured 2 issues — a real lawyer would identify 5-6
3. No "expansion pressure" in the prompt to generate more directions for complex cases

---

## STEP 9: What Should Be Different

### Context that SHOULD have been injected:
```
=== I. ÖFFENTLICH-RECHTLICHE ABTEILUNG (Strafrechtliche Zwangsmassnahmen) ===
Präfixe: 1B_, 7B_

• 1B_ (8'245 Entscheide): Strafprozessuale Zwangsmassnahmen
  Inhalt: Untersuchungshaft, Sicherheitshaft, Haftprüfung, Haftentlassung,
          Beschlagnahme, Überwachung, Entsiegelung
  Schlüsselwörter: Haft, Haftgrund, Kollusionsgefahr, Fluchtgefahr, 
                   Wiederholungsgefahr, Verhältnismässigkeit, Haftverlängerung
  KRITISCH: Jede Frage zu Untersuchungshaft → 1B_ (NICHT 6B_!)
  KRITISCH: Ab ca. 2023 auch unter 7B_ geführt!

• 7B_ (4'105 Entscheide): Neuere Bezeichnung für strafprozessuale Beschwerden
  Inhalt: Gleich wie 1B_, neuere Fälle
  KRITISCH: IMMER zusammen mit 1B_ suchen!
```

### Rules that should be added to system prompt:
```
ABSOLUTE REGEL FÜR HAFT:
- Untersuchungshaft / Haftbeschwerde → Gerichte: 1B_ UND 7B_ (NIEMALS nur 6B_!)
- 6B_ ist NUR für Strafurteile (Schuldspruch, Strafmass)
- 1B_/7B_ ist für VERFAHRENSFRAGEN (Haft, Zwangsmassnahmen, Beweisverwertung)
```

---

## STEP 10: Token Budget Analysis

| Component | Chars | Est. Tokens | % of ctx |
|-----------|-------|-------------|----------|
| System prompt (static) | 17,867 | 4,466 | 27% |
| Injected context (dynamic) | 7,518 | 1,879 | 11% |
| Question | 1,077 | 269 | 2% |
| **Total input** | **26,479** | **6,619** | **40%** |
| Output budget (max_tokens) | — | 1,500 | 9% |
| **Total utilized** | — | **~8,119** | **50%** |
| **Remaining unused** | — | **~8,265** | **50%** |

**The prompt is only using 50% of context window.** There's room to add more guidance, more examples, or longer context.

---

## CONCLUSIONS

| # | Finding | Fixable? | How |
|---|---------|----------|-----|
| 1 | Context router mapped COURT_STRAFPROZESS → 6B_ section only, never showing 1B_/7B_ | YES | Add 1B_/7B_ to the COURT_STRAFPROZESS section, or create a separate mapping |
| 2 | No dedicated taxonomy entry for "1B_ = Haftbeschwerden" in the court sections | YES | Add it to `_COURT_SECTIONS` dict |
| 3 | Example 1 in system prompt correctly shows 1B_ but model ignores it | PARTIAL | Move example closer to question, or add explicit rule |
| 4 | No hard rule "Haft = 1B_ NIEMALS 6B_" | YES | Add as KRITISCH rule in classification section |
| 5 | Only 3 directions for a complex 42-citation question | YES | Add rule: "Bei komplexen Fragen mit >100 Wörtern: MINDESTENS 5 Richtungen" |
| 6 | 50% of context window unused | — | Can fit more guidance |
| 7 | All content in one [INST] block (no system/user separation) | MINOR | Mistral doesn't strongly differentiate anyway |

# Comprehensive Fix Plan — Planner Breadth + Retrieval Coverage

## Current State (v3 log baseline)
- **F1 = 0.038** (with broken reranker) / **0.098** (without reranker, cap 60)
- **Retrieval ceiling: 5/42 gold = 11.9%** — 37 citations NEVER retrieved
- Planner generates 4 near-identical directions (all "Kollusionsgefahr")
- Reranker produces uniform scores (0.0097), nothing passes 0.2 cutoff → fallback top-10
- 7B_ (4,105 docs) never searched — no routing guidance exists
- BGE_IV/BGE_V/BGE_I/BGE_III never get directions — no dictionary wiring
- StGB/StBOG visible in context but LLM doesn't create directions (prompt/example issue)
- Executor rephrases same query 3× instead of diversifying

---

## Architecture Understanding

```
Question
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ select_planner_context(question)                             │
│   1. Score _DOMAIN_KEYWORDS → pick top 2 law domains        │
│   2. Score _COURT_KEYWORDS → pick top 2 court divisions     │
│   3. Map domains → court divisions via _DOMAIN_TO_COURT_DIV │
│   4. Load sections from routing_guide_laws.txt              │
│   5. Load sections from routing_guide_courts.txt            │
│   6. Load sections from terminology_bridge.txt              │
│   7. Concatenate, truncate to max_chars=12000               │
└──────────────────────────────┬──────────────────────────────┘
                               │ context_text
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ run_planner(question)                                        │
│   system_prompt (planner_system.txt) + context + question    │
│   → LLM → JSON plan with 3-6 directions                     │
│   Each direction: corpus, filter_codes, seed_queries         │
└──────────────────────────────┬──────────────────────────────┘
                               │ Plan(directions)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ run_direction(question, direction) × N                        │
│   Seed query → filtered_hybrid_search() → results            │
│   ReAct loop: executor LLM → new query → search → repeat    │
└──────────────────────────────┬──────────────────────────────┘
                               │ all_direction_citations
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ aggregate_and_output()                                        │
│   Flatten → dedup → RERANK → cutoff 0.2 → fallback → cap 60 │
└─────────────────────────────────────────────────────────────┘
```

---

## Bug Inventory

| # | Bug | Where | Severity | Impact |
|---|-----|-------|----------|--------|
| B1 | Reranker produces uniform scores (0.0097) — NOTHING passes cutoff | Cell 16 aggregate | CRITICAL | F1 capped at 0.038 |
| B2 | 7B_ has no routing guide section | routing_guide_courts.txt | HIGH | 5 gold citations invisible |
| B3 | BGE_* codes have no dictionary wiring | _COURT_KEYWORDS, _COURT_TO_SECTIONS, _DOMAIN_TO_COURT_DIVISIONS | HIGH | 11 BGE gold citations invisible |
| B4 | Planner few-shot examples show 4 same-concept directions | planner_system.txt | HIGH | LLM mimics narrow pattern |
| B5 | No diversity rule in prompt — LLM repeats same concept | planner_system.txt | HIGH | 4 directions search same thing |
| B6 | StGB direction never created despite context being loaded | planner_system.txt (example doesn't model it) | MEDIUM | StGB articles missed |
| B7 | StBOG direction never created despite context being loaded | planner_system.txt (example doesn't model it) | MEDIUM | StBOG articles missed |
| B8 | Executor rephrases same query instead of exploring new concepts | executor prompt / no diversification logic | MEDIUM | 3 iterations = same results |
| B9 | No "Rechtsmittel" (appeals Art. 382-396 StPO) direction ever created | planner prompt + no checklist | MEDIUM | Appeals citations missed |
| B10 | No "Kosten" (costs Art. 422-428 StPO) direction ever created | planner prompt + no checklist | MEDIUM | Cost citations missed |
| B11 | No "amtliche Verteidigung" (legal aid Art. 132-135 StPO) direction | planner prompt + no checklist | MEDIUM | Legal aid citations missed |

---

## Fix Plan

### FIX 1: Disable Broken Reranker [B1]

**File:** Notebook Cell 16 (`aggregate_and_output`)  
**Change:** Skip reranker, use RRF scores directly  
**Impact:** F1 0.038 → 0.098 immediately (2.5× improvement)

```python
# BEFORE (broken):
reranked = rerank_with_qwen(candidates, rerank_query)
above_cutoff = [(c, s, sn) for c, s, sn in reranked if s >= CONFIG["rerank_score_cutoff"]]

# AFTER (bypass):
# Reranker disabled — uniform scores make it useless. Use RRF ranking directly.
above_cutoff = candidates  # Already sorted by RRF score from filtered_hybrid_search
```

---

### FIX 2: Add BGE + 7B_ Sections to routing_guide_courts.txt [B2, B3]

**File:** `context/routing_guide_courts.txt`  
**Change:** Add 2 new `===` sections before "HÄUFIGE FEHLER"

**Add after `=== SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN ===` section:**

```
=== BGE LEITENTSCHEIDE (Publizierte Grundsatzentscheide) ===

BGE-Leitentscheide sind publizierte Grundsatzentscheide des Bundesgerichts.
Sie definieren die Rechtsprechung und werden in JEDEM späteren Fall zitiert.
IMMER BGE parallel zu Einzelfällen suchen!

• BGE_I (Öffentliches Recht): Verfassungsrecht, Verwaltungsrecht, Ausländerrecht
  Filter: BGE_I
  Zuständigkeit: Gleiche Rechtsgebiete wie 1B_, 1C_, 2C_
  Schlüsselwörter: Leitentscheid, Grundsatzfrage, Willkür, Verhältnismässigkeit, Grundrecht
  KRITISCH: Parallel zu 1B_/1C_/2C_ → IMMER auch BGE_I suchen
  Beispiel-Suchen: "Grundrecht Verhältnismässigkeit persönliche Freiheit Leitentscheid"

• BGE_II (Öffentliches Recht II): Steuerrecht, Ausländerrecht (z.T.)
  Filter: BGE_II
  Schlüsselwörter: Steuer, Aufenthalt, Grundsatzentscheid
  Beispiel-Suchen: "Doppelbesteuerung Grundsatz Leitentscheid"

• BGE_III (Zivilrecht): Vertragsrecht, Familienrecht, Erbrecht, Sachenrecht
  Filter: BGE_III
  Zuständigkeit: Gleiche Rechtsgebiete wie 4A_, 5A_
  Schlüsselwörter: Vertragsauslegung, Unterhalt, Kindeswohl, Erbrecht, Grundsatz
  KRITISCH: Parallel zu 4A_/5A_ → IMMER auch BGE_III suchen
  Beispiel-Suchen: "Kindesunterhalt Berechnung Grundsatz Leitentscheid Bundesgericht"

• BGE_IV (Strafrecht): Strafrecht materiell, Strafprozessrecht, Haftrecht
  Filter: BGE_IV
  Zuständigkeit: Gleiche Rechtsgebiete wie 6B_, 1B_ (Haft)
  Schlüsselwörter: Strafzumessung, Haftgrund, Beweiswürdigung, Grundsatzentscheid, Leitentscheid
  KRITISCH: Parallel zu 6B_/1B_ → IMMER auch BGE_IV suchen
  KRITISCH: Haftfragen → BGE_IV enthält Grundsätze zu Art. 221 StPO!
  Beispiel-Suchen: "Untersuchungshaft Grundsatz Leitentscheid Kollusionsgefahr"
  Beispiel-Suchen: "Strafzumessung Grundsatz Tatkomponenten Leitentscheid"

• BGE_V (Sozialversicherungsrecht): IV, UV, KV, AHV, BVG
  Filter: BGE_V
  Zuständigkeit: Gleiche Rechtsgebiete wie 8C_, 9C_
  Schlüsselwörter: Invalidität, Begutachtung, Kausalität, Grundsatzentscheid
  KRITISCH: Parallel zu 8C_/9C_ → IMMER auch BGE_V suchen
  Beispiel-Suchen: "Begutachtung Grundsatz Beweiswert polydisziplinär Leitentscheid"

=== BUNDESSTRAFGERICHT (Beschwerdekammer) ===
Präfixe: 7B_
BGE: (keine eigenen BGE — Bundesstrafgericht ist Vorinstanz des BGer)

• 7B_ (4'105 Entscheide): Bundesstrafgericht — Beschwerdekammer & Berufungskammer
  Inhalt: Haft bei Bundesgerichtsbarkeit, Beschlagnahme, Entsiegelung, Rechtshilfe, 
          Verfahrensfragen BStKR, Beschwerden gegen Bundesanwaltschaft
  Zuständigkeit: Organisierte Kriminalität, Terrorismus, Wirtschaftsstraftaten von 
                 nationaler Bedeutung, internationale Rechtshilfe in Strafsachen, 
                 Geldwäscherei, Korruption
  Schlüsselwörter: Bundesstrafgericht, Beschwerdekammer, Bundesgerichtsbarkeit, 
                   Bundesanwaltschaft, organisierte Kriminalität, Rechtshilfe, 
                   BStKR, StBOG, Geldwäscherei, Terrorismus
  KRITISCH: Fragen zu Bundesstrafgericht-Verfahren oder Bundesgerichtsbarkeit → 7B_
  KRITISCH: Internationale Rechtshilfe in Strafsachen → 7B_ (+ IRSG bei Gesetzen)
  Beispiel-Suchen: "Beschwerdekammer Bundesstrafgericht Haft Bundesgerichtsbarkeit"
  Beispiel-Suchen: "Rechtshilfe international Herausgabe Kontosperre"
```

---

### FIX 3: Add BGE + 7B_ to Code Dictionaries [B2, B3]

**File:** Notebook Cell 13 (keyword/section dictionaries)

#### 3a. Add to `_COURT_KEYWORDS`:

```python
# BGE Leitentscheide — criminal/procedural
"COURT_BGE_STRAF": [
    # English
    "leading case", "landmark decision", "precedent", "published decision",
    "federal court precedent", "principle", "fundamental question",
    "bge criminal", "supreme court criminal",
    # German
    "leitentscheid", "grundsatzentscheid", "grundsatzfrage",
    "publizierter entscheid", "bge", "bundesgerichtsentscheid",
    "grundsatz", "praxisänderung", "rechtsprechung",
    "bge_iv",
],

# BGE Leitentscheide — civil
"COURT_BGE_ZIVIL": [
    "leading case", "landmark decision", "precedent", "published decision",
    "bge civil", "supreme court civil",
    "leitentscheid", "grundsatzentscheid", "grundsatzfrage",
    "bge", "bundesgerichtsentscheid", "grundsatz",
    "bge_iii",
],

# BGE Leitentscheide — social insurance
"COURT_BGE_SOZIAL": [
    "leading case", "landmark decision", "precedent", "published decision",
    "bge social", "supreme court social",
    "leitentscheid", "grundsatzentscheid", "grundsatzfrage",
    "bge", "bundesgerichtsentscheid", "grundsatz",
    "bge_v",
],

# BGE Leitentscheide — public law
"COURT_BGE_OEFFENTLICH": [
    "leading case", "landmark decision", "precedent", "published decision",
    "bge public", "supreme court public",
    "leitentscheid", "grundsatzentscheid", "grundsatzfrage",
    "bge", "bundesgerichtsentscheid", "grundsatz",
    "bge_i", "bge_ii",
],

# 7B_ Bundesstrafgericht
"COURT_BUNDESSTRAF": [
    # English
    "federal criminal court", "federal prosecution", "organized crime",
    "terrorism", "money laundering", "mutual legal assistance",
    "international legal assistance", "federal jurisdiction",
    # German
    "bundesstrafgericht", "beschwerdekammer", "bundesanwaltschaft",
    "bundesgerichtsbarkeit", "organisierte kriminalität",
    "rechtshilfe", "internationale rechtshilfe",
    "geldwäscherei", "terrorismus", "stbog", "bstkr",
    "7b_",
],
```

#### 3b. Add to `_COURT_KW_TO_SECTIONS`:

```python
"COURT_BGE_STRAF":       ["BGE LEITENTSCHEIDE (Publizierte Grundsatzentscheide)"],
"COURT_BGE_ZIVIL":       ["BGE LEITENTSCHEIDE (Publizierte Grundsatzentscheide)"],
"COURT_BGE_SOZIAL":      ["BGE LEITENTSCHEIDE (Publizierte Grundsatzentscheide)"],
"COURT_BGE_OEFFENTLICH": ["BGE LEITENTSCHEIDE (Publizierte Grundsatzentscheide)"],
"COURT_BUNDESSTRAF":     ["BUNDESSTRAFGERICHT (Beschwerdekammer)"],
```

#### 3c. Add to `_COURT_TO_SECTIONS`:

```python
"COURT_BGE_STRAF":       ["BGE LEITENTSCHEIDE (Publizierte Grundsatzentscheide)"],
"COURT_BGE_ZIVIL":       ["BGE LEITENTSCHEIDE (Publizierte Grundsatzentscheide)"],
"COURT_BGE_SOZIAL":      ["BGE LEITENTSCHEIDE (Publizierte Grundsatzentscheide)"],
"COURT_BGE_OEFFENTLICH": ["BGE LEITENTSCHEIDE (Publizierte Grundsatzentscheide)"],
"COURT_BUNDESSTRAF":     ["BUNDESSTRAFGERICHT (Beschwerdekammer)"],
```

#### 3d. Update `_DOMAIN_TO_COURT_DIVISIONS`:

```python
_DOMAIN_TO_COURT_DIVISIONS: dict[str, list[str]] = {
    "STRAFRECHT":          ["COURT_STRAF", "COURT_BGE_STRAF"],
    "STRAFPROZESS":        ["COURT_STRAFPROZESS", "COURT_STRAF", "COURT_BGE_STRAF", "COURT_BUNDESSTRAF"],
    "ZIVILRECHT":          ["COURT_VERTRAG", "COURT_FAMILIE", "COURT_BGE_ZIVIL"],
    "PROZESSRECHT":        ["COURT_VERTRAG", "COURT_STRAF", "COURT_BGE_OEFFENTLICH"],
    "SOZIALVERSICHERUNG":  ["COURT_SOZIAL_IV", "COURT_SOZIAL_RENTEN", "COURT_BGE_SOZIAL"],
    "OEFFENTLICHES_RECHT": ["COURT_OEFFENTLICH", "COURT_VERWALTUNG", "COURT_BGE_OEFFENTLICH"],
    "STEUERRECHT":         ["COURT_OEFFENTLICH", "COURT_BGE_OEFFENTLICH"],
    "FINANZMARKTRECHT":    ["COURT_OEFFENTLICH", "COURT_BGE_OEFFENTLICH"],
    "WEITERE":             ["COURT_OEFFENTLICH", "COURT_STRAF", "COURT_BUNDESSTRAF"],
}
```

---

### FIX 4: Make routing_guide_laws.txt Exhaustive [B6, B7, B9, B10, B11]

**File:** `context/routing_guide_laws.txt`  
**Change:** Expand the StPO section to explicitly list sub-areas that need separate directions

The StPO section currently says:
```
Wichtige Bereiche: Art. 212-240 (Haft), Art. 382-397 (Rechtsmittel), Art. 139-141 (Beweis)
```

**Replace with expanded version that calls out each retrieval-worthy sub-area:**

```
=== STRAFPROZESSRECHT ===

• StPO (Schweizerische Strafprozessordnung) — 1'306 Artikel
  Inhalt: Strafverfahrensrecht, Untersuchung, Zwangsmassnahmen, Haft, Beweis, Rechtsmittel

  WICHTIGE TEILBEREICHE (jeweils eigene Richtung erstellen!):
  ┌─────────────────────────────────────────────────────────────────────┐
  │ A) HAFT (Art. 212-240): Untersuchungshaft, Sicherheitshaft         │
  │    Schlüsselwörter: Haftgrund, Fluchtgefahr, Kollusionsgefahr,     │
  │    Wiederholungsgefahr, Verhältnismässigkeit, Überhaft              │
  │                                                                      │
  │ B) RECHTSMITTEL (Art. 382-397): Beschwerde, Berufung, Revision     │
  │    Schlüsselwörter: Beschwerde, Berufung, Revision, Legitimation,  │
  │    Beschwerdefrist, Instanzenzug, reformatio in peius               │
  │    KRITISCH: JEDER Haftfall hat auch Rechtsmittel-Aspekt!          │
  │                                                                      │
  │ C) KOSTEN (Art. 422-428): Verfahrenskosten, Entschädigung          │
  │    Schlüsselwörter: Verfahrenskosten, Entschädigung, Genugtuung,   │
  │    Kostenverlegung, unentgeltliche Rechtspflege                     │
  │    KRITISCH: JEDER Fall hat Kostenfolgen — oft in Erwägungen!       │
  │                                                                      │
  │ D) VERTEIDIGUNG (Art. 127-137): Amtliche Verteidigung, Wahlvert.   │
  │    Schlüsselwörter: amtliche Verteidigung, notwendige Verteidigung,│
  │    Pflichtverteidiger, Honorar, Entschädigung Verteidiger           │
  │    KRITISCH: Bei Haftfragen → IMMER auch Verteidigungsrecht prüfen │
  │                                                                      │
  │ E) BEWEIS (Art. 139-195): Beweiserhebung, Beweisverwertung         │
  │    Schlüsselwörter: Beweisverwertung, Verwertungsverbot,           │
  │    Einvernahme, Zeuge, Sachverständiger, DNA, Gutachten             │
  │                                                                      │
  │ F) ZWANGSMASSNAHMEN (Art. 196-298): Beschlagnahme, Überwachung     │
  │    Schlüsselwörter: Beschlagnahme, Durchsuchung, Überwachung,      │
  │    Entsiegelung, geheime Überwachung, technische Überwachung        │
  └─────────────────────────────────────────────────────────────────────┘

  KRITISCH: Bei Haftfragen NICHT nur Abschnitt A suchen!
  Ein vollständiger Haftfall berührt: A (Haft) + B (Rechtsmittel) + C (Kosten) + D (Verteidigung)
  
  Beispiel-Suchen pro Teilbereich:
  - A: "Untersuchungshaft Kollusionsgefahr Haftgrund Verhältnismässigkeit"
  - B: "Beschwerde Haftentscheid Legitimation Beschwerdefrist Instanzenzug"
  - C: "Verfahrenskosten Haftverfahren Entschädigung Kostenverlegung"
  - D: "amtliche Verteidigung Haft notwendige Verteidigung Pflichtverteidiger"
  - E: "Beweisverwertung Verwertungsverbot Einvernahme rechtswidrig"
  - F: "Beschlagnahme Durchsuchung Entsiegelung Siegelung"

• StBOG (Strafbehördenorganisationsgesetz) — 183 Artikel
  Inhalt: Organisation der Strafbehörden des Bundes, Bundesstrafgericht, Bundesanwaltschaft
  Schlüsselwörter: Bundesstrafgericht, Bundesanwaltschaft, Beschwerdekammer, 
                   Strafkammer, Berufungskammer, Bundesgerichtsbarkeit
  KRITISCH: Bei Fragen zu Bundesstrafgericht → StBOG + 7B_ parallel suchen
  Beispiel-Suchen: "Bundesstrafgericht Zuständigkeit Bundesgerichtsbarkeit Organisation"

• JStPO (Jugendstrafprozessordnung) — 135 Artikel
  [existing content unchanged]

• MStP (Militärstrafprozess) — 589 Artikel
  [existing content unchanged]
```

---

### FIX 5: Rewrite Planner System Prompt [B4, B5, B6, B7, B9, B10, B11]

**File:** `prompts/planner_system.txt`

#### 5a. Add DIVERSITÄTS-REGELN after existing "REGELN FÜR DIRECTIONS":

```
DIVERSITÄTS-REGELN (KRITISCH — NIEMALS überspringen!):
- JEDE direction MUSS ein ANDERES rechtliches Thema abdecken
- VERBOTEN: 3+ directions die denselben Suchbegriff variieren (z.B. alle "Kollusionsgefahr")
- PFLICHT bei 6 Richtungen — decke mindestens 4 VERSCHIEDENE Dimensionen ab:

  a) Materielle Norm — das Gesetz das den Sachverhalt DIREKT regelt
  b) Einzelfallpraxis — Gerichtsabteilung die den Fall beurteilt (1B_, 5A_, 6B_ etc.)
  c) BGE-Leitentscheide — publizierte Grundsatzentscheide (BGE_IV, BGE_III etc.)
  d) Verfahrensrecht — Rechtsmittel, Fristen, Kosten, Verteidigung
  e) Verwandtes Recht — Querverweise (z.B. StGB bei StPO-Fragen, OR bei ZGB-Fragen)
  f) Bundesstrafgericht — bei organisierter Kriminalität/Bundesgerichtsbarkeit: 7B_

CHECKLISTEN PRO RECHTSGEBIET (IMMER prüfen):

• STRAFPROZESS (Haft/Zwangsmassnahmen):
  MUSS abdecken: StPO + 1B_ + BGE_IV + Rechtsmittel (Art. 382-397) + amtl. Verteidigung
  SOLLTE abdecken: StGB (materielles Delikt) + 7B_ (bei Bundesgerichtsbarkeit) + Kosten

• STRAFRECHT (Strafurteil/Strafzumessung):
  MUSS abdecken: StGB + 6B_ + BGE_IV + Rechtsmittel/Berufung
  SOLLTE abdecken: StPO (Beweisverwertung) + 1B_ (bei vorheriger Haft) + Kosten

• FAMILIENRECHT:
  MUSS abdecken: ZGB + 5A_ + BGE_III + Kindesschutz/Unterhalt
  SOLLTE abdecken: SchKG (Vollstreckung) + ZPO (Verfahren) + Kosten

• SOZIALVERSICHERUNG:
  MUSS abdecken: Spezialgesetz (IVG/UVG/KVG) + ATSG + 8C_/9C_ + BGE_V
  SOLLTE abdecken: Gutachtenpraxis + Verfahrensrecht + Kausalitätsprüfung

• ÖFFENTLICHES RECHT:
  MUSS abdecken: Spezialgesetz (AIG/RPG/USG) + BV + 1C_/2C_ + BGE_I
  SOLLTE abdecken: VwVG (Verfahren) + BGG (Beschwerde ans BGer)

IMMER-REGEL: Mindestens EINE Richtung muss BGE-Leitentscheide suchen!
IMMER-REGEL: Bei Strafrecht → IMMER auch materielles Recht (StGB) als eigene Richtung!
```

#### 5b. Rewrite Example 1 (Detention) to show 6 DIVERSE directions:

```json
BEISPIEL 1 (Strafverfahren — Haft):
Frage: "Under what conditions can pre-trial detention be extended?"
{
  "sachverhalt": "Frage nach Voraussetzungen der Haftverlängerung im Strafverfahren",
  "rechtsfragen": [
    "Haftgründe und Haftverlängerung",
    "Verhältnismässigkeit und Überhaft",
    "Rechtsmittel gegen Haftentscheid",
    "Amtliche Verteidigung bei Haft",
    "Grundsatzrechtsprechung zu Haft"
  ],
  "directions": [
    {
      "priority": 1, "corpus": "laws", "rechtsgebiet": "Strafprozessrecht-Haft",
      "filter_codes": ["StPO"],
      "reasoning": "Haftvoraussetzungen Art. 221-228 StPO — materielles Haftrecht",
      "seed_queries": ["Untersuchungshaft Haftgründe Fluchtgefahr Kollusionsgefahr Wiederholungsgefahr", "Haftverlängerung Verhältnismässigkeit Überhaft Haftdauer"]
    },
    {
      "priority": 2, "corpus": "courts", "rechtsgebiet": "Haftpraxis Einzelfälle",
      "filter_codes": ["1B_"],
      "reasoning": "BGer-Praxis Abt. 1B — konkrete Haftfälle",
      "seed_queries": ["Kollusionsgefahr Beweisgefährdung Verdunkelungsgefahr Haftbeschwerde", "Haftdauer Verhältnismässigkeit Überhaft Ersatzmassnahme"]
    },
    {
      "priority": 3, "corpus": "courts", "rechtsgebiet": "Leitentscheide Haft",
      "filter_codes": ["BGE_IV"],
      "reasoning": "Publizierte Grundsatzentscheide zu Haftvoraussetzungen",
      "seed_queries": ["Haft Grundsatz Leitentscheid Voraussetzungen Bundesgericht", "Kollusionsgefahr Grundsatzentscheid Verhältnismässigkeit"]
    },
    {
      "priority": 4, "corpus": "laws", "rechtsgebiet": "Rechtsmittel Haftverfahren",
      "filter_codes": ["StPO"],
      "reasoning": "Beschwerde gegen Haftentscheid Art. 382-397 StPO — Instanzenzug",
      "seed_queries": ["Beschwerde Haftentscheid Legitimation Beschwerdefrist Instanzenzug", "Haftbeschwerde Rechtsmittel Kognition Prüfungsbefugnis"]
    },
    {
      "priority": 5, "corpus": "laws", "rechtsgebiet": "Verteidigung und Kosten",
      "filter_codes": ["StPO"],
      "reasoning": "Amtliche Verteidigung und Kostenfolgen bei Haftverfahren",
      "seed_queries": ["amtliche Verteidigung notwendige Verteidigung Haft Pflichtverteidiger", "Verfahrenskosten Haftverfahren Entschädigung unentgeltliche Rechtspflege"]
    },
    {
      "priority": 6, "corpus": "laws", "rechtsgebiet": "Verfahrensrecht allgemein",
      "filter_codes": ["BV", "BGG"],
      "reasoning": "Verfassungsrechtliche Grundlagen — persönliche Freiheit und Beschwerdeweg",
      "seed_queries": ["persönliche Freiheit Freiheitsentzug Grundrecht Verhältnismässigkeit", "Beschwerde Strafsachen BGG Bundesgericht Legitimation"]
    }
  ]
}
```

---

### FIX 6: Executor Diversification [B8]

**File:** Notebook Cell 14/15 (executor system template)  
**Change:** Add explicit rule to executor prompt preventing repeated queries

**Add to executor system template:**

```
DIVERSITÄTS-REGEL: 
- Deine Suchanfrage MUSS sich INHALTLICH von allen bisherigen Suchen unterscheiden.
- VERBOTEN: Gleiche Begriffe mit anderen Worten wiederholen.
- GEBOT: Suche einen ANDEREN ASPEKT des Rechtsgebiets.
- Wenn bisherige Suchen "Kollusionsgefahr" und "Verdunkelungsgefahr" fanden:
  → Suche jetzt "Fluchtgefahr" oder "Verhältnismässigkeit Haftdauer" oder "Ersatzmassnahmen"
- Wenn 2 Iterationen ähnliche Ergebnisse liefern → signal done=true
```

**Also add to `format_direction_history`:**

```python
# Add dedup hint: list unique query stems already tried
used_concepts = set()
for entry in history:
    for word in entry["query"].split():
        if len(word) > 5:  # skip short words
            used_concepts.add(word.lower())
# Append: f"\nBEREITS GESUCHTE KONZEPTE (NICHT wiederholen): {', '.join(sorted(used_concepts)[:15])}"
```

---

### FIX 7: Sync Routing Laws with Routing Courts Cross-References

**File:** `context/routing_guide_laws.txt`  
**Change:** Add cross-references from law sections to court codes

In each law section, add a "→ PARALLEL SUCHEN:" line:

```
• StPO (Schweizerische Strafprozessordnung) — 1'306 Artikel
  [existing content]
  → PARALLEL SUCHEN: 1B_ (Haftfragen), 6B_ (Strafurteile), 7B_ (Bundesstrafgericht), BGE_IV (Leitentscheide)

• StGB (Schweizerisches Strafgesetzbuch) — 1'239 Artikel
  [existing content]
  → PARALLEL SUCHEN: 6B_ (Strafurteile), BGE_IV (Leitentscheide), 1B_ (bei Haftfällen)

• ZGB (Schweizerisches Zivilgesetzbuch) — 2'395 Artikel
  [existing content]
  → PARALLEL SUCHEN: 5A_ (Familie/Erbrecht), 4A_ (Vertragsrecht), BGE_III (Leitentscheide)

• OR (Obligationenrecht) — 3'662 Artikel
  [existing content]
  → PARALLEL SUCHEN: 4A_ (Verträge/Haftpflicht), BGE_III (Leitentscheide)

• IVG/ATSG — 
  → PARALLEL SUCHEN: 8C_ (IV/UV), 9C_ (AHV/KV), BGE_V (Leitentscheide)
```

---

## Implementation Order

```
Priority │ Fix  │ Files Modified                    │ Est. Impact on F1
─────────┼──────┼───────────────────────────────────┼──────────────────
   1     │ B1   │ Notebook Cell 16                  │ 0.038 → 0.098 (+160%)
   2     │ B2+9 │ routing_guide_courts.txt          │ +5 gold (7B_) + 11 gold (BGE) reachable
   3     │ B3+10│ Notebook Cell 13 (5 dicts)        │ BGE+7B_ wired into keyword/section chain
   4     │ B4,5 │ planner_system.txt                │ 4→6 diverse directions
   5     │ B6,7 │ planner_system.txt (example)      │ StGB/StBOG directions appear
   6     │ B9-11│ routing_guide_laws.txt (FIX 8)    │ Appeals/Costs/Legal-aid/sub-areas exposed
   7     │ 11   │ routing_guide_courts.txt x-refs   │ Courts→Laws cross-refs for planner
   8     │ 10   │ Notebook fallback_decompose       │ _DOMAIN_DEFAULT_CODES includes BGE
   9     │ B8   │ Notebook Cell 14/15 (executor)    │ 3 unique queries per direction
─────────┼──────┼───────────────────────────────────┼──────────────────
TOTAL    │      │ 4 files, 11 fixes                  │ Est. 0.038 → 0.20-0.30
```

---

## Expected Results After All Fixes

| Metric | Before (v3) | After (estimated) |
|--------|:-----------:|:-----------------:|
| Planner directions | 4 (same concept) | 6 (diverse) |
| Unique corpus areas searched | 2 (StPO, 1B_) | 6-8 (StPO, 1B_, BGE_IV, StGB, 7B_, BV, BGG, 6B_) |
| Retrieval ceiling (gold found) | 5/42 (11.9%) | 15-25/42 (35-60%) |
| Output citations | 10 (reranker fallback) | 60 (cap, no reranker) |
| True positives | 1 | 8-15 (est.) |
| F1 | 0.038 | 0.20-0.30 (est.) |

---

## Files to Modify (Summary)

| File | Changes |
|------|---------|
| `context/routing_guide_courts.txt` | +BGE LEITENTSCHEIDE section (5 BGE codes), +BUNDESSTRAFGERICHT section (7B_), +→ BEI GESETZEN cross-refs on all existing entries |
| `context/routing_guide_laws.txt` | Expand StPO into 6 sub-areas (A-F), add → PARALLEL SUCHEN cross-refs on ALL law entries, expand MEHRFACH-SUCHE PFLICHT patterns |
| `prompts/planner_system.txt` | +Diversitäts-Regeln block, +Checklists per Rechtsgebiet, rewrite Example 1 (6 diverse dirs) |
| `notebooks/04_planner_director.ipynb` Cell 13 | +5 _COURT_KEYWORDS entries (BGE_STRAF/ZIVIL/SOZIAL/OEFFENTLICH + BUNDESSTRAF), +5 _COURT_KW_TO_SECTIONS, +5 _COURT_TO_SECTIONS, rewrite _DOMAIN_TO_COURT_DIVISIONS (add BGE+7B_ to every domain), update _DOMAIN_DEFAULT_CODES in fallback_decompose |
| `notebooks/04_planner_director.ipynb` Cell 14/15 | Executor diversification rule in prompt + used_concepts dedup hint |
| `notebooks/04_planner_director.ipynb` Cell 16 | Disable broken reranker (bypass to RRF scores) |

---

---

## FIX 8: Make routing_guide_laws.txt Exhaustive + Add Cross-References [B6, B7, B9-B11]

**File:** `context/routing_guide_laws.txt`

### Current State
The laws routing guide already lists all codes but the StPO section is too brief — it only says
`Wichtige Bereiche: Art. 212-240 (Haft), Art. 382-397 (Rechtsmittel), Art. 139-141 (Beweis)`
with no detail on sub-areas. The planner sees this but doesn't understand it warrants separate directions.

### Changes

#### 8a. Expand StPO into Sub-Area Detail (replace existing StPO entry):

```
• StPO (Schweizerische Strafprozessordnung) — 1'306 Artikel
  Inhalt: Strafverfahrensrecht, Untersuchung, Zwangsmassnahmen, Haft, Beweis, Rechtsmittel
  
  ┌─ TEILBEREICHE (jeweils eigene Such-Richtung erstellen!) ─────────────────────┐
  │                                                                                │
  │ A) HAFT (Art. 212-240): Untersuchungs-/Sicherheitshaft, Haftgründe           │
  │    → Fluchtgefahr, Kollusionsgefahr, Wiederholungsgefahr, Überhaft            │
  │    → "Untersuchungshaft Haftgründe Fluchtgefahr Kollusionsgefahr"             │
  │                                                                                │
  │ B) RECHTSMITTEL (Art. 382-397): Beschwerde, Berufung, Revision                │
  │    → Legitimation, Beschwerdefrist, Instanzenzug, reformatio in peius         │
  │    → "Beschwerde Haftentscheid Legitimation Beschwerdefrist Instanzenzug"     │
  │    KRITISCH: JEDER Haftfall hat Rechtsmittel-Aspekt!                          │
  │                                                                                │
  │ C) KOSTEN & ENTSCHÄDIGUNG (Art. 422-432): Verfahrenskosten, Genugtuung       │
  │    → Kostenverlegung, unentgeltliche Rechtspflege, Parteientschädigung        │
  │    → "Verfahrenskosten Kostenverlegung unentgeltliche Rechtspflege"           │
  │    KRITISCH: JEDER Fall hat Kostenfolgen!                                     │
  │                                                                                │
  │ D) VERTEIDIGUNG (Art. 127-137): Amtliche/notwendige Verteidigung              │
  │    → Pflichtverteidiger, Honorar, Entschädigung, Widerruf                    │
  │    → "amtliche Verteidigung notwendige Verteidigung Pflichtverteidiger"       │
  │    KRITISCH: Bei Haft → IMMER auch Verteidigungsrecht prüfen!                 │
  │                                                                                │
  │ E) BEWEIS (Art. 139-195): Beweiserhebung, Beweisverwertung                   │
  │    → Verwertungsverbot, Einvernahme, Zeuge, Sachverständiger, Gutachten       │
  │    → "Beweisverwertung Verwertungsverbot rechtswidrig erhobener Beweis"       │
  │                                                                                │
  │ F) ZWANGSMASSNAHMEN (Art. 196-298): Beschlagnahme, Überwachung               │
  │    → Durchsuchung, Entsiegelung, geheime/technische Überwachung              │
  │    → "Beschlagnahme Entsiegelung Durchsuchung Überwachung"                   │
  └────────────────────────────────────────────────────────────────────────────────┘
  
  KRITISCH: Bei Haftfragen NICHT nur A suchen! Vollständiger Fall = A+B+C+D
  → PARALLEL SUCHEN: 1B_ (Einzelfälle), 6B_ (Strafurteile), 7B_ (BStGer), BGE_IV (Leitentscheide)
```

#### 8b. Add → PARALLEL SUCHEN cross-references to ALL law entries:

```
• StGB → PARALLEL SUCHEN: 6B_ (Strafurteile), BGE_IV (Leitentscheide), 1B_ (bei Haftfällen)
• StPO → PARALLEL SUCHEN: 1B_ (Haftfragen), 6B_ (Strafurteile), 7B_ (BStGer), BGE_IV (Leitentscheide)
• StBOG → PARALLEL SUCHEN: 7B_ (Bundesstrafgericht), BGE_IV (Leitentscheide)
• ZGB → PARALLEL SUCHEN: 5A_ (Familie/Erb/Sachen), BGE_III (Leitentscheide)
• OR → PARALLEL SUCHEN: 4A_ (Verträge/Haftpflicht), BGE_III (Leitentscheide)
• SchKG → PARALLEL SUCHEN: 5A_ (Vollstreckung), BGE_III (Leitentscheide)
• ZPO → PARALLEL SUCHEN: 4A_ (Vertragsstreitigkeiten), 5A_ (Familienverfahren)
• BGG → PARALLEL SUCHEN: Alle Abteilungen je nach Rechtsgebiet, BGE_I/II/III/IV/V
• IVG/ATSG → PARALLEL SUCHEN: 8C_ (IV/UV), 9C_ (AHV/KV), BGE_V (Leitentscheide)
• UVG → PARALLEL SUCHEN: 8C_ (Unfallversicherung), BGE_V (Leitentscheide)
• KVG → PARALLEL SUCHEN: 9C_ (Krankenversicherung), BGE_V (Leitentscheide)
• BV → PARALLEL SUCHEN: 1C_/2C_ (öffentliches Recht), BGE_I (Leitentscheide)
• AIG → PARALLEL SUCHEN: 2C_ (Ausländerrecht), BGE_I/BGE_II (Leitentscheide)
• IRSG → PARALLEL SUCHEN: 7B_ (Rechtshilfe), BGE_IV (Leitentscheide)
• SVG → PARALLEL SUCHEN: 6B_ (Strafurteile Verkehrsdelikte), 1C_ (Administrativmassnahmen)
```

#### 8c. Add MEHRFACH-SUCHE PFLICHT expanded section (after classification rules):

```
5. MEHRFACH-SUCHE PFLICHT: Die meisten Fragen betreffen 2-3 Gesetze gleichzeitig.
   STRAFPROZESS-MUSTER (IMMER so aufbauen!):
   - Haftfrage → StPO (Haft) + StPO (Rechtsmittel) + StPO (Verteidigung) + StGB + BGG + BV
   - Strafurteil → StGB + StPO (Beweis) + StPO (Rechtsmittel) + BGG
   - Bundesstrafgericht → StBOG + StPO + IRSG (bei Rechtshilfe)
   
   ZIVILRECHT-MUSTER:
   - Scheidung → ZGB + ZPO + BGG
   - Erbstreit → ZGB (Erbrecht) + ZPO + SchKG (Vollstreckung)
   - Vertrag → OR + ZPO + BGG
   
   SOZIALVERSICHERUNG-MUSTER:
   - IV-Rente → IVG + ATSG + BGG
   - Unfall → UVG + ATSG + BGG
```

---

## FIX 9: Make routing_guide_courts.txt Exhaustive [B2, B3]

**File:** `context/routing_guide_courts.txt`

### Current State
Has sections for: 1B_, 1C_, 2C_, 4A_, 5A_, 6B_, 8C_, 9C_
Missing: **BGE_I, BGE_II, BGE_III, BGE_IV, BGE_V, 7B_**

### Add AFTER the 9C_ section and BEFORE "HÄUFIGE FEHLER":

```
=== BGE LEITENTSCHEIDE (Publizierte Grundsatzentscheide) ===

BGE-Leitentscheide sind publizierte Grundsatzentscheide des Bundesgerichts.
Sie definieren die Rechtsprechung und werden in JEDEM späteren Fall zitiert.
IMMER BGE parallel zu Einzelfällen suchen!

• BGE_I (Öffentliches Recht I): Grundrechte, Verwaltungsrecht, Strafprozess (Haft)
  Zuständigkeit: 1B_ (Haft-Grundsätze), 1C_ (Verwaltung), 2C_ (z.T.)
  Schlüsselwörter: Leitentscheid, Grundsatz, Willkürverbot, persönliche Freiheit, 
                   Verhältnismässigkeit, rechtliches Gehör
  KRITISCH: Parallel zu 1B_/1C_ → IMMER BGE_I mitsuchen!
  Beispiel-Suchen: "Grundrecht Verhältnismässigkeit persönliche Freiheit Leitentscheid"

• BGE_II (Öffentliches Recht II): Steuerrecht, Ausländerrecht (z.T.)
  Zuständigkeit: 2C_ (Steuer, Ausländer)
  Schlüsselwörter: Steuer, Doppelbesteuerung, Aufenthalt, Grundsatzentscheid
  Beispiel-Suchen: "Doppelbesteuerung Grundsatz Leitentscheid Steuerrecht"

• BGE_III (Zivilrecht): Vertragsrecht, Familienrecht, Erbrecht, Sachenrecht
  Zuständigkeit: 4A_ (Verträge, Haftpflicht), 5A_ (Familie, Erbrecht)
  Schlüsselwörter: Vertragsauslegung, Unterhalt, Kindeswohl, Erbrecht, Grundsatz
  KRITISCH: Parallel zu 4A_/5A_ → IMMER BGE_III mitsuchen!
  Beispiel-Suchen: "Kindesunterhalt Berechnung Grundsatz Leitentscheid"
  Beispiel-Suchen: "Vertragsauslegung Vertrauensprinzip Grundsatzentscheid"

• BGE_IV (Strafrecht): Strafrecht materiell, Strafprozessrecht, Haftrecht
  Zuständigkeit: 6B_ (Strafurteile), 1B_ (Haftfragen)
  Schlüsselwörter: Strafzumessung, Haftgrund, Kollusionsgefahr, Beweiswürdigung, 
                   Grundsatzentscheid, Leitentscheid
  KRITISCH: Parallel zu 6B_/1B_ → IMMER BGE_IV mitsuchen!
  KRITISCH: Haft-Leitentscheide zu Art. 221 StPO liegen unter BGE_IV!
  Beispiel-Suchen: "Untersuchungshaft Grundsatz Leitentscheid Kollusionsgefahr"
  Beispiel-Suchen: "Strafzumessung Grundsatz Tatkomponenten Leitentscheid"

• BGE_V (Sozialversicherungsrecht): IV, UV, KV, AHV, BVG
  Zuständigkeit: 8C_ (IV/UV/ALV), 9C_ (AHV/KV/EL)
  Schlüsselwörter: Invalidität, Begutachtung, Kausalität, Grundsatzentscheid
  KRITISCH: Parallel zu 8C_/9C_ → IMMER BGE_V mitsuchen!
  Beispiel-Suchen: "Begutachtung Grundsatz Beweiswert polydisziplinär Leitentscheid"

=== BUNDESSTRAFGERICHT (Beschwerdekammer & Berufungskammer) ===
Präfixe: 7B_
BGE: (keine eigenen BGE — Bundesstrafgericht ist Vorinstanz des Bundesgerichts)

• 7B_ (4'105 Entscheide): Bundesstrafgericht — Beschwerdekammer
  Inhalt: Haft bei Bundesgerichtsbarkeit, Beschlagnahme, Entsiegelung, Rechtshilfe,
          Verfahrensfragen, Beschwerden gegen Bundesanwaltschaft
  Zuständigkeit: Organisierte Kriminalität, Terrorismus, Wirtschaftsstraftaten von 
                 nationaler Bedeutung, internationale Rechtshilfe in Strafsachen,
                 Geldwäscherei, Korruption
  Schlüsselwörter: Bundesstrafgericht, Beschwerdekammer, Bundesgerichtsbarkeit,
                   Bundesanwaltschaft, organisierte Kriminalität, Rechtshilfe,
                   BStKR, StBOG, Geldwäscherei, Terrorismus
  KRITISCH: Fragen zu Bundesstrafgericht/Bundesgerichtsbarkeit → 7B_ suchen
  KRITISCH: Internationale Rechtshilfe in Strafsachen → 7B_ (+ IRSG bei Gesetzen)
  → PARALLEL SUCHEN: StBOG (Gesetz), IRSG (Rechtshilfe), StPO (Verfahren), BGE_IV (Grundsätze)
  Beispiel-Suchen: "Beschwerdekammer Bundesstrafgericht Haft Bundesgerichtsbarkeit"
  Beispiel-Suchen: "Rechtshilfe international Herausgabe Kontosperre"
```

---

## FIX 10: Complete Dictionary Sync Table [B2, B3, B6, B7]

### THE MASTER SYNC: Routing Guide ↔ Code Dictionaries

Every court code must be reachable through ALL 4 paths:

```
PATH 1: Question keywords → _COURT_KEYWORDS[division] → hits
PATH 2: _COURT_KW_TO_SECTIONS[division] → routing guide section loaded
PATH 3: _COURT_TO_SECTIONS[division] → routing guide section loaded (via domain mapping)
PATH 4: _DOMAIN_TO_COURT_DIVISIONS[law_domain] → [divisions] → _COURT_TO_SECTIONS
```

| Court Code | Routing Guide Section | _COURT_KEYWORDS key | _COURT_KW_TO_SECTIONS | _COURT_TO_SECTIONS | _DOMAIN_TO_COURT_DIVISIONS (from which domain) |
|------------|----------------------|--------------------|-----------------------|-------------------|----------------------------------------------|
| **1B_** | I. ÖFFENTLICH-RECHTLICHE ABTEILUNG | COURT_STRAFPROZESS ✓ | ✓ | ✓ | STRAFPROZESS ✓ |
| **1C_** | I. ÖFFENTLICH-RECHTLICHE ABTEILUNG | COURT_VERWALTUNG ✓ | ✓ | ✓ | OEFFENTLICHES_RECHT ✓ |
| **2C_** | II. ÖFFENTLICH-RECHTLICHE ABTEILUNG | COURT_OEFFENTLICH ✓ | ✓ | ✓ | OEFFENTLICHES_RECHT, STEUERRECHT ✓ |
| **4A_** | ZIVILRECHTLICHE ABTEILUNGEN | COURT_VERTRAG ✓ | ✓ | ✓ | ZIVILRECHT ✓ |
| **5A_** | ZIVILRECHTLICHE ABTEILUNGEN | COURT_FAMILIE ✓ | ✓ | ✓ | ZIVILRECHT ✓ |
| **6B_** | STRAFRECHTLICHE ABTEILUNG | COURT_STRAF ✓ | ✓ | ✓ | STRAFRECHT ✓ |
| **8C_** | SOZIALVERSICHERUNGSRECHTLICHE ABT. | COURT_SOZIAL_IV ✓ | ✓ | ✓ | SOZIALVERSICHERUNG ✓ |
| **9C_** | SOZIALVERSICHERUNGSRECHTLICHE ABT. | COURT_SOZIAL_RENTEN ✓ | ✓ | ✓ | SOZIALVERSICHERUNG ✓ |
| **7B_** | ~~MISSING~~ → ADD "BUNDESSTRAFGERICHT" | ~~MISSING~~ → ADD COURT_BUNDESSTRAF | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD to STRAFPROZESS, WEITERE |
| **BGE_I** | ~~MISSING~~ → ADD "BGE LEITENTSCHEIDE" | ~~MISSING~~ → ADD COURT_BGE_OEFFENTLICH | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD to OEFFENTLICHES_RECHT, PROZESSRECHT |
| **BGE_II** | ~~MISSING~~ → ADD "BGE LEITENTSCHEIDE" | ~~MISSING~~ → ADD COURT_BGE_OEFFENTLICH | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD to STEUERRECHT |
| **BGE_III** | ~~MISSING~~ → ADD "BGE LEITENTSCHEIDE" | ~~MISSING~~ → ADD COURT_BGE_ZIVIL | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD to ZIVILRECHT |
| **BGE_IV** | ~~MISSING~~ → ADD "BGE LEITENTSCHEIDE" | ~~MISSING~~ → ADD COURT_BGE_STRAF | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD to STRAFRECHT, STRAFPROZESS |
| **BGE_V** | ~~MISSING~~ → ADD "BGE LEITENTSCHEIDE" | ~~MISSING~~ → ADD COURT_BGE_SOZIAL | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD | ~~MISSING~~ → ADD to SOZIALVERSICHERUNG |

### Also sync the LAW-side fallback `_DOMAIN_DEFAULT_CODES`:

| Domain | Current codes | Should be |
|--------|--------------|-----------|
| STRAFRECHT | `[("laws", ["StGB"]), ("courts", ["6B_"])]` | `[("laws", ["StGB"]), ("courts", ["6B_", "BGE_IV"])]` |
| STRAFPROZESS | `[("laws", ["StPO"]), ("courts", ["1B_"])]` | `[("laws", ["StPO", "StBOG"]), ("courts", ["1B_", "BGE_IV", "7B_"])]` |
| ZIVILRECHT | `[("laws", ["OR", "ZGB"]), ("courts", ["4A_", "5A_"])]` | `[("laws", ["OR", "ZGB"]), ("courts", ["4A_", "5A_", "BGE_III"])]` |
| PROZESSRECHT | `[("laws", ["BGG", "BV"]), ("courts", [])]` | `[("laws", ["BGG", "BV"]), ("courts", ["BGE_I"])]` |
| SOZIALVERSICHERUNG | `[("laws", ["IVG", "ATSG"]), ("courts", ["8C_", "9C_"])]` | `[("laws", ["IVG", "ATSG"]), ("courts", ["8C_", "9C_", "BGE_V"])]` |
| OEFFENTLICHES_RECHT | `[("laws", ["AIG", "BV"]), ("courts", ["2C_"])]` | `[("laws", ["AIG", "BV"]), ("courts", ["2C_", "BGE_I"])]` |
| STEUERRECHT | `[("laws", ["DBG"]), ("courts", ["2C_"])]` | `[("laws", ["DBG"]), ("courts", ["2C_", "BGE_II"])]` |
| FINANZMARKTRECHT | `[("laws", ["FIDLEG", "FINMAG"]), ("courts", ["2C_"])]` | `[("laws", ["FIDLEG", "FINMAG"]), ("courts", ["2C_"])]` (no change) |
| WEITERE | `[("laws", ["SVG"]), ("courts", ["6B_", "1C_"])]` | `[("laws", ["SVG"]), ("courts", ["6B_", "1C_", "7B_"])]` |

---

## FIX 11: Make routing_guide_courts.txt Cross-Reference Back to Laws

Add a "→ BEI GESETZEN:" line to each court section:

```
• 1B_ (26'275 Entscheide): Strafprozessuale Zwangsmassnahmen
  [existing content]
  → BEI GESETZEN: StPO (Haft Art. 212-240, Rechtsmittel Art. 382-397), BV (persönliche Freiheit), BGG (Beschwerde)

• 6B_ (72'691 Entscheide): Strafrecht materiell
  [existing content]
  → BEI GESETZEN: StGB (materielles Strafrecht), StPO (Beweis, Rechtsmittel), BGG (Beschwerde)

• 4A_ (39'088 Entscheide): Vertragsrecht
  [existing content]
  → BEI GESETZEN: OR (Verträge), ZPO (Verfahren), BGG (Beschwerde)

• 5A_ (55'882 Entscheide): Familienrecht
  [existing content]
  → BEI GESETZEN: ZGB (Familienrecht, Erbrecht), ZPO (Verfahren), SchKG (Vollstreckung), BGG

• 8C_/9C_: Sozialversicherung
  [existing content]
  → BEI GESETZEN: IVG/UVG/KVG/AVIG/AHVG + ATSG + BGG

• 7B_ (4'105 Entscheide): Bundesstrafgericht
  [existing content]
  → BEI GESETZEN: StBOG (Organisation), StPO (Verfahren), IRSG (Rechtshilfe)
```

---

## COMPLETE COVERAGE CHECKLIST

| Original Change # | Description | Plan Fix # | Status |
|:-----------------:|-------------|:----------:|:------:|
| 1 | Add 7B_ to routing guide | FIX 9 | ✓ Covered |
| 2 | Add 7B_ to _COURT_KEYWORDS | FIX 3a | ✓ Covered |
| 3 | Rewrite Example 1 (diverse) | FIX 5b | ✓ Covered |
| 4 | Add DIVERSIFICATION RULES | FIX 5a | ✓ Covered |
| 5 | Grammar (already 6 dirs) | No change needed | ✓ Already OK |
| — | Disable broken reranker | FIX 1 | ✓ Covered |
| — | BGE codes in all dicts | FIX 3a-3d, FIX 10 | ✓ Covered |
| — | routing_guide_laws exhaustive | FIX 8 | ✓ Covered |
| — | routing_guide_courts exhaustive | FIX 9 | ✓ Covered |
| — | Cross-refs courts→laws | FIX 11 | ✓ Covered |
| — | Cross-refs laws→courts | FIX 8b | ✓ Covered |
| — | Sync dicts with routing | FIX 10 (sync table) | ✓ Covered |
| — | Fallback codes updated | FIX 10 (_DOMAIN_DEFAULT_CODES) | ✓ Covered |
| — | Executor diversification | FIX 6 | ✓ Covered |

---

## Verification After Implementation

1. Re-run pipeline on same question → check v4 log
2. Confirm planner outputs 6 directions covering StPO + 1B_ + BGE_IV + StGB + 7B_ + BV
3. Confirm executor uses different queries per iteration
4. Confirm no reranker bottleneck (all candidates pass through)
5. Count TP/gold-in-output → compute F1
6. If F1 > 0.15, proceed to next competition question; if not, diagnose remaining gaps
7. Verify sync: run `select_planner_context("detention pre-trial")` → confirm BGE_IV and 7B_ sections appear
8. Verify fallback: break JSON intentionally → confirm `fallback_decompose` now includes BGE codes

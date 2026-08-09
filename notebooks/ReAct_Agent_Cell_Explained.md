# Understanding the ReAct Agent — From Zero to Full Clarity

---

## The One-Sentence Summary

This cell creates a **robot research assistant** that, given a legal question, repeatedly searches a database of Swiss laws and court decisions, collects all the citations it finds, and returns them.

---

## The Analogy: Think of a Research Librarian

Imagine you walk into a Swiss law library and ask the librarian:

> "What are the legal requirements for a valid contract?"

The librarian doesn't just guess. They:

1. **Think**: "Okay, contracts are in the Code of Obligations. Let me search for that."
2. **Act**: Walk to the shelf, look up "Contract formation" in the index.
3. **Observe**: "Found Art. 1 OR, Art. 2 OR... good."
4. **Think again**: "But I should also check what courts have said about this."
5. **Act again**: Walk to the court decisions section, search "contract validity."
6. **Observe**: "Found BGE 127 III 248... great."
7. **Done**: Hand you a list of all the citations they found.

**That's exactly what this code does** — except the librarian is an LLM (Mistral-7B), the "shelves" are BM25 search indices, and the "walking to the shelf" is a function call.

---

## End-to-End Walkthrough: One Query, Start to Finish

Let's trace what happens when we call:
```python
citations, logs = run_agent("What are the requirements for a valid contract?")
```

### Step 1: Build the Initial Prompt (BEFORE Iteration 0)

The code builds this exact string and sends it to the LLM:

```python
conversation = f"[INST] {AGENT_SYSTEM_PROMPT}\n\nQuery: {query}\n\nThought: [/INST]"
```

Here is **exactly** what the LLM receives (with prompt abbreviated for readability):

```
┌─────────────────────────────────────────────────────────────────────┐
│ EXACT PROMPT SENT TO LLM — ITERATION 0                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [INST] Du bist ein Schweizer Rechtsrecherche-Assistent mit         │
│  Zugang zu zwei Such-Tools:                                          │
│                                                                     │
│  1. search_laws(query): Durchsuche Schweizer Bundesgesetze...        │
│  2. search_courts(query): Durchsuche Schweizer Bundesgerichts...     │
│                                                                     │
│  WICHTIG: Suche IMMER auf Deutsch...                                │
│                                                                     │
│  (... 4 few-shot examples ...)                                       │
│                                                                     │
│  Suche IMMER auf Deutsch. Rufe beide Tools auf.                      │
│                                                                     │
│  Query: What are the requirements for a valid contract?              │
│                                                                     │
│  Thought: [/INST]                                                    │
│                                                                     │
│  ▲                                                                   │
│  │ Everything between [INST] and [/INST] is THE INSTRUCTION.         │
│  │ "Thought:" is the LAST word inside [INST].                        │
│  │ The model generates text AFTER [/INST].                           │
│  │ So it "completes" the thought by writing its reasoning.           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why is `Thought:` inside `[INST]`?** It's a forcing trick. The model sees the instruction ends mid-sentence with "Thought:" and immediately writes the continuation — its reasoning — as the first generated text.

### Step 2: LLM Generates Text (Iteration 0 Output)

The model generates everything AFTER `[/INST]`:

```
Ich suche nach Vertragsvoraussetzungen im Obligationenrecht.
Action: search_laws
Action Input: Vertrag Abschluss Voraussetzungen OR
```

**How does it know to write German?** Three reasons:
1. The prompt **explicitly says** "ALWAYS search in German"
2. The prompt contains **4 examples** showing English question → German search query
3. Mistral was **pre-trained on German text** so it knows the vocabulary

The model is doing **pattern matching** — it saw the examples and mimics the format exactly.

### Step 3: Parse the Tool Call

The code uses regex to extract:
- **Tool**: `search_laws`
- **Query**: `Vertrag Abschluss Voraussetzungen OR`

(meaning: "Contract conclusion requirements Code-of-Obligations")

### Step 4: Execute the Search

The code calls:
```python
law_tool("Vertrag Abschluss Voraussetzungen OR")
```

This runs BM25 keyword search over 269,000 law documents and returns the top 40 matches with their citations (like "SR 220 Art. 1").

### Step 5: Collect Citations

From the search results, we grab all the citation strings:
```
["SR 220 Art. 1", "SR 220 Art. 2", "SR 220 Art. 7", ...]
```

These go into our `all_citations` bucket.

### Step 6: Rebuild Conversation (AFTER Iteration 0)

Now the code **restructures** the conversation. Here's the key code:

```python
# This runs ONLY after iteration 0:
conversation = f"[INST] {AGENT_SYSTEM_PROMPT}\n\nQuery: {query} [/INST]\n\nThought:{response}"

# Then tool observations are appended:
conversation += "\n" + observations + "\n\n[INST] Continue your analysis. [/INST]\n\nThought:"
```

Here is **exactly** what the LLM receives on iteration 1:

```
┌─────────────────────────────────────────────────────────────────────┐
│ EXACT PROMPT SENT TO LLM — ITERATION 1                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [INST] Du bist ein Schweizer Rechtsrecherche-Assistent...           │
│  (... full system prompt + examples ...)                             │
│                                                                     │
│  Query: What are the requirements for a valid contract? [/INST]      │
│                                                                     │
│  Thought: Ich suche nach Vertragsvoraussetzungen im                  │
│  Obligationenrecht.                                                  │
│  Action: search_laws                                                 │
│  Action Input: Vertrag Abschluss Voraussetzungen OR                  │
│                                                                     │
│  Tool search_laws: - SR 220 Art. 1: Zum Abschluss eines              │
│  Vertrages ist die übereinstimmende gegenseitige                     │
│  Willensäusserung der Parteien erforderlich...                       │
│  - SR 220 Art. 2: Haben die Parteien sich über alle                  │
│  wesentlichen Punkte geeinigt...                                     │
│  - SR 220 Art. 7: Der Antragsteller wird nicht gebunden...            │
│  ... (truncated, 10800 chars remaining)                              │
│                                                                     │
│  [INST] Continue your analysis. [/INST]                              │
│                                                                     │
│  Thought:                                                            │
│                                                                     │
│  ▲                                                                   │
│  │ KEY DIFFERENCES FROM ITERATION 0:                                 │
│  │                                                                   │
│  │ 1. [/INST] is now AFTER the query (not after "Thought:")          │
│  │ 2. The model's previous output appears OUTSIDE [INST]             │
│  │ 3. Tool observations are injected as a new block                  │
│  │ 4. A second [INST]...[/INST] pair says "Continue"                 │
│  │ 5. "Thought:" at the end forces the model to keep reasoning       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Notice the structural shift:**
- Iteration 0: `[INST] prompt + query + Thought: [/INST]` → model completes the thought
- Iteration 1+: `[INST] prompt + query [/INST] Thought: {previous} Observation: {results} [INST] Continue [/INST] Thought:` → model sees full history and continues

### Why Is Iteration 1's Prompt Structured This Way?

Let's break down **every structural choice** and why it has to be that way:

**1. Why did `[/INST]` move from after `Thought:` to after the query?**

In iteration 0, we needed the trick of putting `Thought:` inside `[INST]` to force the model to start reasoning. But now the model has *already* generated a response. We need to show that response as something the model **said** (outside `[INST]`), not something the user **instructed** (inside `[INST]`). 

Mistral's format rule: everything inside `[INST]...[/INST]` = user/system input. Everything outside = the model's own output. If we left the model's previous response inside `[INST]`, Mistral would think *the user* said "Ich suche nach Vertragsvoraussetzungen..." which makes no sense.

So we move `[/INST]` to right after the query, and the model's previous `Thought: ... Action: ...` text sits outside — correctly positioned as model-generated text.

**2. Why is the model's previous output placed outside `[INST]`?**

```
Query: What are the requirements...? [/INST]    ← user's turn ends

Thought: Ich suche nach...                      ← model's turn (iteration 0 output)
Action: search_laws
Action Input: Vertrag Abschluss OR
```

This creates a realistic **conversation history**. The model can see: "I previously decided to search for X." This continuity is critical — without it, the model wouldn't know what it already searched for and might repeat the same search.

**3. Why are tool observations placed outside `[INST]` too?**

```
Tool search_laws: - SR 220 Art. 1: Zum Abschluss...    ← injected results
```

The observations sit between the model's previous output and the next `[INST]` block. They're NOT inside any `[INST]` tags because they're not user instructions — they're **environment feedback**. Think of it like a chatbot where the system inserts data between user and assistant turns. The model reads them as "this is what happened in the world after my action."

**4. Why is there a second `[INST] Continue your analysis. [/INST]`?**

```
[INST] Continue your analysis. [/INST]
```

This is a **new user turn**. Mistral's format is strictly alternating: `[INST] user [/INST] assistant [INST] user [/INST] assistant...`. After showing the model its own previous output + observations, we need to "hand the mic back" to the user to say "keep going." Without this, the model has no clear signal that it should generate more text.

The message "Continue your analysis" is minimal on purpose — it doesn't add new instructions (the system prompt already covers everything), it just says "your turn again."

**5. Why does it end with bare `Thought:` outside `[/INST]`?**

```
[INST] Continue your analysis. [/INST]

Thought:
```

Same forcing trick as iteration 0, but now **outside** `[INST]`. This is the start of the model's response that we're pre-filling. By writing `Thought:` we constrain the model to immediately continue in the Thought/Action/Action Input format instead of potentially generating something off-format like "Sure, I'll search for..."

### The Full Structure Visualized as a Conversation

```
TURN 1 (User):     [INST] system prompt + query [/INST]
TURN 1 (Model):    Thought: ... Action: search_laws Action Input: ...
INJECTED:          Tool search_laws: - SR 220 Art. 1: ...
TURN 2 (User):     [INST] Continue your analysis. [/INST]
TURN 2 (Model):    Thought: ← model generates from here
```

This is a standard **multi-turn Mistral conversation** with tool results injected between turns. The model sees a clean history: "I was asked a question → I searched → here are results → I'm told to continue → I think about what to search next."

### Step 7: LLM Thinks Again (Iteration 1)

The model sees the results and generates:

```
Jetzt suche ich nach BGE-Entscheiden.
Action: search_courts
Action Input: Vertragsabschluss Gültigkeit
```

("Now I'm searching for court decisions on contract formation validity")

### Step 8: Execute Second Search, Collect More Citations

Same as steps 3-5, but now searching the court decisions index.

### Step 9: Loop Ends (Iteration 3 or "Final Answer")

After 3 iterations (configurable), or when the model says "Final Answer:", the loop stops.

### Step 10: Return Deduplicated Citations

```python
return list(set(all_citations))  
# e.g., ["SR 220 Art. 1", "SR 220 Art. 7", "BGE 127 III 248", ...]
```

---

## The Four Building Blocks

Now that you've seen the full flow, here's what each piece of code does:

```
┌─────────────────────────────────────────────────────────────┐
│                     run_agent()                              │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ System Prompt │    │ Action Parser │    │ Citation      │   │
│  │ (instructions │    │ (regex that   │    │ Extractor     │   │
│  │  to the LLM)  │    │  reads tool   │    │ (regex that   │   │
│  │               │    │  calls from   │    │  finds legal  │   │
│  │               │    │  text)        │    │  references)  │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Truncation Helpers (keep conversation within limits)  │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## Block 1: The System Prompt

### What It Is

A long German text that acts as the LLM's **instruction manual**. It tells the model:
- What role to play (Swiss legal researcher)
- What tools are available (search_laws, search_courts)
- What format to respond in (Thought → Action → Action Input)
- Examples of correct behavior

### Why It's in German

The model searches a **German corpus**. If the prompt were English, the model might try English search terms, which would find nothing. The German prompt keeps the model "thinking in German."

### How It Teaches the Model to Generate German Queries

The prompt uses **few-shot learning** (teaching by example):

| English Question | → Model Generates German Query | Meaning |
|-----------------|-------------------------------|---------|
| "Requirements for a valid contract?" | `Vertrag Abschluss Voraussetzungen OR` | "Contract conclusion requirements [Code of Obligations]" |
| "Negligent homicide liability?" | `fahrlässige Tötung StGB` | "Negligent killing [Criminal Code]" |
| "Child custody after divorce?" | `Scheidung Sorgerecht Kinder ZGB` | "Divorce custody children [Civil Code]" |
| "When can landlord terminate lease?" | `Mietvertrag Kündigung Vermieter OR` | "Lease termination landlord [Code of Obligations]" |

The model sees this pattern and copies it for new questions. It already knows German legal terms from pre-training — the examples just show it **how to format them as search queries**.

### Full Prompt — Complete English Translation

Below is the **entire** German system prompt translated into English, including all 4 few-shot examples exactly as the LLM sees them:

---

> You are a Swiss legal research assistant with access to two search tools:
>
> 1. **search_laws(query):** Search Swiss federal laws (SR / Systematic Collection of Federal Law)
>    - Returns relevant legal provisions with citations and text excerpts
>    - Use for statutory law: codes, laws, ordinances
>
> 2. **search_courts(query):** Search Swiss Federal Court decisions (BGE)
>    - Returns relevant case law with citations and excerpts
>    - Use for court decisions and precedents
>
> **IMPORTANT:** ALWAYS search in German, since the documents are in German.
>
> **Your task:** Call the search tools to find relevant Swiss legal citations.
>
> **Instructions:**
> - Search BOTH: laws AND court decisions
> - Use multiple search queries with German legal terms
> - Call the tools until all relevant sources have been found
>
> **Response format:**
> ```
> Thought: [Your reasoning about the next search]
> Action: [tool_name]
> Action Input: [German search query]
> ```
>
> === EXAMPLES ===
>
> **Example 1 — Contract Law:**
> Query: What are the requirements for a valid contract?
>
> Thought: I'm searching for contract requirements in the Code of Obligations.
> Action: search_laws
> Action Input: Vertrag Abschluss Voraussetzungen OR
>
> Observation: - Art. 1 Abs. 1 OR: For the conclusion of a contract...
>
> Thought: Now I'm searching for Federal Court decisions on contract formation.
> Action: search_courts
> Action Input: Vertragsabschluss Gültigkeit Voraussetzungen
>
> Observation: - BGE 127 III 248 E. 3.1: The requirements...
>
> Thought: I'm searching for further aspects like defects of consent.
> Action: search_laws
> Action Input: Irrtum Täuschung Vertrag OR
>
> **Example 2 — Criminal Law:**
> Query: Under what conditions can someone be held liable for negligent homicide?
>
> Thought: I'm searching for negligent homicide in the Criminal Code.
> Action: search_laws
> Action Input: fahrlässige Tötung StGB
>
> Observation: - Art. 117 StGB: Whoever negligently causes death...
>
> Thought: I'm searching for case law on the duty of care.
> Action: search_courts
> Action Input: fahrlässige Tötung Sorgfaltspflicht
>
> Observation: - BGE 135 IV 56 E. 2.1: The duty of care...
>
> Thought: I'm searching for more court decisions on standards of negligence.
> Action: search_courts
> Action Input: Fahrlässigkeit Verschulden Massstab
>
> **Example 3 — Family Law:**
> Query: How is child custody determined after divorce?
>
> Thought: I'm searching for custody rights in divorce under the Civil Code.
> Action: search_laws
> Action Input: Scheidung Sorgerecht Kinder ZGB
>
> Observation: - Art. 133 Abs. 1 ZGB: The court shall regulate...
>
> Thought: I'm searching for Federal Court decisions on the child's best interest.
> Action: search_courts
> Action Input: Kindeswohl Obhut Zuteilung
>
> Observation: - BGE 142 III 481 E. 2.6: The child's best interest...
>
> Thought: I'm searching for further provisions on parental authority.
> Action: search_laws
> Action Input: elterliche Sorge Zuteilung ZGB
>
> **Example 4 — Tenancy Law:**
> Query: When can a landlord terminate a lease?
>
> Thought: I'm searching for termination rights in tenancy law.
> Action: search_laws
> Action Input: Mietvertrag Kündigung Vermieter OR
>
> Observation: - Art. 266a OR: The termination is...
>
> Thought: I'm searching for court decisions on abusive termination.
> Action: search_courts
> Action Input: Miete Kündigung missbräuchlich
>
> Observation: - BGE 140 III 496 E. 4.1: A termination is...
>
> Thought: I'm searching for termination protection.
> Action: search_laws
> Action Input: Kündigungsschutz Miete OR
>
> === END EXAMPLES ===
>
> ALWAYS search in German. Call both tools (search_laws AND search_courts).

---

### All 4 Examples Translated

**Example 1 — Contract Law:**
*Query: "What are the requirements for a valid contract?"*

| Step | Model Output | English Meaning |
|------|-------------|-----------------|
| Thought | "Ich suche nach Vertragsvoraussetzungen im Obligationenrecht." | "I'm searching for contract requirements in the Code of Obligations." |
| Action Input | `Vertrag Abschluss Voraussetzungen OR` | "Contract conclusion requirements OR" |
| Thought | "Jetzt suche ich nach BGE-Entscheiden zum Vertragsschluss." | "Now I'm searching for court decisions on contract formation." |
| Action Input | `Vertragsabschluss Gültigkeit Voraussetzungen` | "Contract-formation validity requirements" |
| Thought | "Ich suche nach weiteren Aspekten wie Willensmängel." | "I'm searching for additional aspects like defects of consent." |
| Action Input | `Irrtum Täuschung Vertrag OR` | "Error deception contract OR" |

**Example 2 — Criminal Law:**
*Query: "Under what conditions can someone be held liable for negligent homicide?"*

| Step | Model Output | English Meaning |
|------|-------------|-----------------|
| Action Input | `fahrlässige Tötung StGB` | "Negligent homicide Criminal Code" |
| Action Input | `fahrlässige Tötung Sorgfaltspflicht` | "Negligent homicide duty of care" |
| Action Input | `Fahrlässigkeit Verschulden Massstab` | "Negligence fault standard" |

**Example 3 — Family Law:**
*Query: "How is child custody determined after divorce?"*

| Step | Model Output | English Meaning |
|------|-------------|-----------------|
| Action Input | `Scheidung Sorgerecht Kinder ZGB` | "Divorce custody children Civil Code" |
| Action Input | `Kindeswohl Obhut Zuteilung` | "Child welfare custody allocation" |
| Action Input | `elterliche Sorge Zuteilung ZGB` | "Parental authority allocation Civil Code" |

**Example 4 — Tenancy Law:**
*Query: "When can a landlord terminate a lease?"*

| Step | Model Output | English Meaning |
|------|-------------|-----------------|
| Action Input | `Mietvertrag Kündigung Vermieter OR` | "Lease termination landlord OR" |
| Action Input | `Miete Kündigung missbräuchlich` | "Rent termination abusive" |
| Action Input | `Kündigungsschutz Miete OR` | "Termination-protection rent OR" |

---

## Block 2: The Action Parser

### The Problem

The LLM outputs plain text. It can't actually "call" a function. It just writes:

```
Action: search_laws
Action Input: Vertrag Abschluss Voraussetzungen OR
```

### The Solution

`parse_all_agent_actions()` uses regex to extract tool calls from the text:

```
Input text:  "...Action: search_laws\nAction Input: Vertrag..."
                         ^^^^^^^^^^^              ^^^^^^^^^^^^^^^
Output:      [("search_laws", "Vertrag Abschluss Voraussetzungen OR")]
```

It finds **all** Action/Input pairs in one response (the model sometimes generates multiple in one go).

### Why This Works

Because the system prompt **forces** the model to output in this exact format. The regex knows exactly what pattern to look for. It's like a contract: the prompt says "write it like THIS" and the parser says "I'll read it like THIS."

---

## Block 3: The Citation Extractor

### The Problem

We need to collect every legal citation mentioned anywhere — in tool results, in the model's thoughts, in its final answer.

### The Solution

`extract_citations_from_text()` uses three regex patterns:

| What | Pattern Matches | Example |
|------|----------------|---------|
| Law collection number | `SR 220`, `SR 311.0 Art. 1a` | Identifies which law book |
| Court decision | `BGE 135 IV 56 E. 2.1` | Federal court case reference |
| Article reference | `Art. 41 OR`, `Art. 133 Abs. 1 ZGB` | Specific law article + which code |

### When Is This Used?

- **Primary source**: `tool.get_last_citations()` — citations from actual BM25 search results. These are **reliable** because they come from real documents in the corpus.
- **Backup source**: `extract_citations_from_text()` — scrapes citations from the LLM's own text. This mostly catches:
  1. **Echoed citations**: The model repeats citations it saw in tool results (e.g., "I found Art. 1 OR, now searching for more..."). These are just duplicates — already collected from the tool.
  2. **Hallucinated citations**: The model generates a citation from pre-training memory (e.g., "Art. 41 OR") without ever searching for it. These are **unreliable** — they might not exist in the corpus.

**Bottom line**: The tools are the real source of truth. The text regex is a low-cost safety net that mostly produces duplicates, and occasionally adds a lucky (or garbage) citation.

---

## Block 4: Truncation Helpers

### The Problem

The LLM has a **fixed memory** (16384 tokens ≈ 56,000 characters). Each iteration adds more text to the conversation. After 2-3 iterations with 40 search results each, we'd blow past the limit.

### The Solution: Two Truncation Functions

**`truncate_observation_for_llm()`** — Caps each search result at 1200 characters for the LLM.

```
Full search result:     12,000 chars (40 results × 300 chars)
What the LLM sees:       1,200 chars (first few results + "...truncated")
What's saved in logs:   12,000 chars (nothing lost for citation extraction)
```

**`truncate_conversation()`** — If the whole conversation gets too long:

```
ALWAYS KEPT:  System prompt (the agent's brain — can't lose this)
TRIMMED:      Older search results and thoughts (stale context)
ALWAYS KEPT:  Most recent exchange (current working memory)
```

It's like a person who remembers their training and what just happened, but forgets the details of what they did 10 minutes ago.

---

## The Main Loop: `run_agent()` as a Flowchart

```
START
  │
  ▼
╔═══════════════════════════════════╗
║ Build prompt:                     ║
║ [INST] instructions + query [/INST] ║
╚═══════════════╤═══════════════════╝
                │
                ▼
        ┌──────────────┐
   ┌───►│  Iteration   │◄─── max 3 times
   │    │  (one cycle)  │
   │    └──────┬───────┘
   │           │
   │           ▼
   │    ┌──────────────┐
   │    │ LLM generates │  "Thought... Action: X  Action Input: Y"
   │    │ text response  │
   │    └──────┬───────┘
   │           │
   │           ▼
   │    ┌──────────────┐
   │    │ Parse actions │  Extract (tool_name, query) pairs
   │    └──────┬───────┘
   │           │
   │           ├── No actions found? ──► STOP (extract citations from text)
   │           │
   │           ▼
   │    ┌──────────────┐
   │    │ Run each tool │  BM25 search → get results + citations
   │    └──────┬───────┘
   │           │
   │           ├──► Add citations to collection
   │           │
   │           ▼
   │    ┌──────────────────────────────────┐
   │    │ Append results to conversation    │
   │    │ "Observation: ... [INST] Continue │
   │    │ your analysis [/INST] Thought:"   │
   │    └──────┬───────────────────────────┘
   │           │
   │           ├── "Final Answer:" seen? ──► STOP
   │           │
   └───────────┘  (loop back for next iteration)

                │
                ▼
╔═══════════════════════════════╗
║ Deduplicate all citations     ║
║ Return (citations, logs)      ║
╚═══════════════════════════════╝
```

---

## Why Each Design Decision Was Made

| What | Why |
|------|-----|
| **German prompt & examples** | Corpus is German. English searches would return nothing. |
| **4 few-shot examples** | Model needs to see the pattern to reliably follow it. More examples = more reliable. |
| **Stop token = `Observation:`** | Prevents the model from inventing fake search results. Forces it to wait for real data. |
| **Temperature = 0.1** | We want consistent, predictable tool calls — not creative writing. |
| **Parse multiple actions** | Model sometimes writes 2-3 actions at once. We execute all of them. |
| **Truncate observations** | 40 results × 300 chars = too much for the LLM's context. But we keep full data in logs. |
| **Always preserve system prompt** | If truncation removes the instructions, the model forgets how to use tools. |
| **Collect citations from BOTH tools AND text** | Tools give structured results; text regex catches anything else the model mentions. |
| **Max 3 iterations** | Balances thoroughness vs. speed. More iterations = more searches but slower. |
| **Error handling for context overflow** | If conversation still too long after truncation, gracefully return whatever citations were found. |

---

## FAQ

### Q: What is "OR", "ZGB", "StGB" in the Action Inputs?

These are abbreviations for Swiss law codes:
- **OR** = Obligationenrecht (Code of Obligations — contracts, torts, commercial law)
- **ZGB** = Zivilgesetzbuch (Civil Code — family, property, inheritance)
- **StGB** = Strafgesetzbuch (Criminal Code)
- **SR** = Systematische Rechtssammlung (Systematic Collection — the numbering system for all Swiss federal law)
- **BGE** = Bundesgerichtsentscheid (Federal Court Decision)

### Q: What if the model generates garbage instead of a proper Action?

The code handles this: if no `Action:` pattern is found in the response, it extracts whatever citations the model mentioned in its text and stops. No crash.

### Q: Why not just use the LLM to generate citations directly (without tools)?

Because LLMs **hallucinate**. They'll confidently cite "BGE 999 III 123" which doesn't exist. By forcing the model to search a real database, every citation returned is guaranteed to exist in the corpus.

### Q: Why BM25 and not semantic/embedding search?

BM25 is fast, simple, and works well for keyword-heavy legal text. The notebook suggests semantic search as a future improvement (see the "Potential Improvements" section at the end of the notebook).

### Q: What happens if the LLM's context window overflows?

Two-level defense:
1. **Proactive**: `truncate_conversation()` runs every iteration to keep things under 28,000 chars
2. **Reactive**: If the LLM call still fails, aggressively truncate to 20,000 chars and retry once. If that fails too, return whatever citations were collected so far.

---

## The Complete Picture in One Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR QUESTION                             │
│          "What are the requirements for a valid contract?"       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SYSTEM PROMPT (German)                         │
│  "You are a Swiss legal researcher. Use these tools..."          │
│  + 4 examples showing how to search                              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MISTRAL-7B (Local LLM)                         │
│                                                                   │
│  Input: prompt + question                                         │
│  Output: "Thought: ... Action: search_laws                        │
│           Action Input: Vertrag Abschluss OR"                     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │   ACTION PARSER     │
                    │   (regex extract)   │
                    └─────────┬──────────┘
                              │
                    tool = "search_laws"
                    query = "Vertrag Abschluss OR"
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌──────────────────────┐       ┌──────────────────────┐
│    LAWS INDEX         │       │    COURTS INDEX       │
│  (269K documents)     │       │  (2.5M documents)     │
│                       │       │                       │
│  BM25 keyword search  │       │  BM25 keyword search  │
│  Returns top 40 hits  │       │  Returns top 40 hits  │
└──────────┬───────────┘       └──────────┬───────────┘
           │                               │
           └───────────┬───────────────────┘
                       │
                       ▼
        ┌──────────────────────────┐
        │   CITATION COLLECTION     │
        │                           │
        │   From tools:             │
        │   "SR 220 Art. 1"         │
        │   "SR 220 Art. 7"         │
        │   "BGE 127 III 248"       │
        │                           │
        │   From text (backup):     │
        │   Any regex matches in    │
        │   the LLM's own words     │
        └──────────────┬───────────┘
                       │
                       ▼
        ┌──────────────────────────┐
        │   DEDUPLICATE & RETURN    │
        │                           │
        │   ["SR 220 Art. 1",       │
        │    "SR 220 Art. 7",       │
        │    "BGE 127 III 248"]     │
        └──────────────────────────┘
```

---

## TL;DR

1. **Prompt teaches the model** to think in German and output `Action: tool_name / Action Input: query`
2. **Parser extracts** the tool name and query from the model's text
3. **Tool executes** a BM25 search over real Swiss law documents
4. **Citations are collected** from search results (+ fallback regex on model text)
5. **Loop repeats** up to 3 times (laws search + courts search + maybe one more)
6. **Return** all unique citations found

---

## All Jobs the LLM Is Currently Doing (Decoupling Candidates)

Right now, Mistral-7B is a **one-man band** — it handles every cognitive task in a single generation call. Here's every job it's doing, whether it's good at it, and what you could replace it with:

### The Full Job List

| # | Job | What It Does | Example | Could Replace With |
|---|-----|-------------|---------|-------------------|
| 1 | **Query Translation** | Translates English question → German search keywords | "valid contract requirements" → "Vertrag Abschluss Voraussetzungen" | Translation API (DeepL, Google Translate), bilingual embedding model |
| 2 | **Legal Domain Mapping** | Maps general concepts to Swiss legal domain terms and abbreviations | Knows "contract law" → "Obligationenrecht" (OR), "criminal code" → "StGB" | Legal ontology / lookup table of Swiss law terms |
| 3 | **Query Formulation** | Crafts BM25-effective keyword queries (picks good search terms, adds law code abbreviations) | Adds "OR" to contract queries, "StGB" to criminal queries | Query expansion (synonyms, stemming), predefined legal query templates |
| 4 | **Tool Selection** | Decides whether to call `search_laws` or `search_courts` | "I need case law now" → picks `search_courts` | Rule-based: always call BOTH tools for every query (cheaper, more reliable) |
| 5 | **Search Strategy** | Plans multi-step search: what to search first, what angles to try next | First: "Vertrag Abschluss OR", then: "Irrtum Täuschung Vertrag OR" | Predefined query templates per legal domain, or a query expansion model |
| 6 | **Result Interpretation** | Reads truncated search results and decides if they're relevant / if more searching is needed | Sees contract results → decides to also search for "defects of consent" | Not needed if we just run all predefined queries. Or: a small classifier for relevance |
| 7 | **Iteration Control** | Decides when to stop searching (writes "Final Answer" or keeps going) | After 2 searches, decides "I have enough" | Fixed schedule: always run exactly N searches. No LLM decision needed |
| 8 | **Format Compliance** | Outputs text in the exact `Thought/Action/Action Input` format so the regex parser can read it | Must write `Action: search_laws` not `I'll search laws` | Function calling / structured output (tool_use API), or a constrained decoder |
| 9 | **Prompt Self-Construction** | By generating `Thought:...Action:...`, it's effectively writing its own next prompt — its output becomes part of the next iteration's input | The model's iteration 0 output becomes conversation history in iteration 1 | Orchestrator code that builds prompts from templates, not from LLM output |

### Which Jobs Are Wasteful?

```
ESSENTIAL (LLM adds real value):
  ├── Job 1: Query Translation     — needs language understanding
  ├── Job 2: Legal Domain Mapping  — needs legal knowledge
  └── Job 5: Search Strategy       — needs reasoning about gaps

AUTOMATABLE (don't need an LLM):
  ├── Job 4: Tool Selection        — just call both tools every time
  ├── Job 7: Iteration Control     — fixed schedule (3 iterations)
  └── Job 8: Format Compliance     — use structured output / function calling

QUESTIONABLE (LLM does it but barely uses it):
  ├── Job 3: Query Formulation     — could be keyword expansion + templates
  ├── Job 6: Result Interpretation — LLM only sees 4 of 40 results anyway
  └── Job 9: Prompt Self-Construction — an orchestrator could do this
```

### Decoupling Ideas

**Simplest win — remove Jobs 4, 7, 8:**
```
Instead of:  LLM decides which tool → LLM decides when to stop → parse LLM text
Do this:     Always call both tools → always run 3 iterations → use function calling

This removes 3 jobs from the LLM, making it simpler and more reliable.
```

**Medium effort — replace Job 1 with a translator:**
```
Instead of:  LLM translates "valid contract" → "Vertrag Abschluss" (hoping it gets it right)
Do this:     DeepL API translates query → use translated text as search keywords

This gives professional-grade translation instead of hoping a 7B model 
gets German legal terms right.
```

**Bigger refactor — replace Jobs 1, 2, 3, 5 with query expansion:**
```
Instead of:  LLM generates 1 search query per iteration (3 total)
Do this:     
  1. Translate query to German (DeepL)
  2. Expand with legal synonyms (ontology/lookup table)
  3. Generate 6-10 queries from templates
  4. Run ALL queries against BOTH indices in parallel
  5. Collect all citations

No LLM needed at all for retrieval. LLM only needed later for 
relevance filtering or answer generation.
```

**Nuclear option — remove the LLM from retrieval entirely:**
```
Pipeline:
  English query 
    → translate to German (API)
    → extract legal concepts (NER or keyword extraction)
    → expand with synonyms + law code abbreviations (lookup table)
    → BM25 search both indices with all expanded queries
    → deduplicate citations
    → done

LLM is only used AFTER retrieval to rank/filter/explain results.
This is faster, cheaper, deterministic, and reproducible.
```

### Summary Table: What To Decouple First

| Priority | Job | Current Owner | Move To | Effort | Impact |
|----------|-----|--------------|---------|--------|--------|
| 1 | Tool Selection | LLM | Hard-coded "call both" | 5 min | Eliminates wasted iterations where LLM only calls one tool |
| 2 | Iteration Control | LLM | Fixed 3 iterations | 5 min | No more early stops or runaway loops |
| 3 | Format Compliance | LLM | Function calling API | 30 min | Eliminates regex parsing failures |
| 4 | Query Translation | LLM | DeepL / Google Translate | 1 hour | Better German translations than a 7B model |
| 5 | Query Formulation | LLM | Template + expansion | 2 hours | More queries, better recall, deterministic |
| 6 | Search Strategy | LLM | Predefined multi-query plan | 2 hours | Covers more legal angles systematically |
| 7 | Result Interpretation | LLM | Remove (not needed) | 0 min | LLM only sees 4/40 results — this job is mostly theater |

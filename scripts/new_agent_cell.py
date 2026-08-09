# === CELL 10: STRUCTURED REACT AGENT (GBNF grammar + Pydantic) ===
# Fixes from Run 1 analysis:
# - GBNF grammar forces exactly ONE action per LLM turn (no multi-action garbage)
# - JSON output = clean parse (no regex fragility, no "Action Input:" leaking)
# - Observations fed back as summary (count + top-5 IDs) — no raw text contamination
# - Citations collected ONLY from tool results — never from agent's free text

from pydantic import BaseModel, field_validator
from typing import Literal
from llama_cpp import LlamaGrammar
import json as _json

# ---- Pydantic model for agent output ----
class AgentAction(BaseModel):
    thought: str
    action: Literal["search_laws", "search_courts", "done"]
    query: str = ""

    @field_validator("query")
    @classmethod
    def clean_query(cls, v):
        # Strip any leaked syntax that somehow got through
        v = re.sub(r"Action\s*Input\s*:.*", "", v, flags=re.I).strip()
        v = re.sub(r"Tool\s+search_\w+:.*", "", v, flags=re.I).strip()
        v = re.sub(r"\[INST\].*", "", v).strip()
        # Limit length (no query should be > 200 chars)
        return v[:200]


# ---- GBNF Grammar: forces valid JSON with exactly one action per turn ----
# Grammar ensures output is always: {"thought":"...","action":"search_laws|search_courts|done","query":"..."}
_GBNF_LINES = [
    r'root ::= "{" ws "\"thought\"" ws ":" ws string "," ws "\"action\"" ws ":" ws action-val "," ws "\"query\"" ws ":" ws string "}" ws',
    r'action-val ::= "\"search_laws\"" | "\"search_courts\"" | "\"done\""',
    r'string ::= "\"" chars "\""',
    r'chars ::= char*',
    r'char ::= [^"\\] | "\\" escape-char',
    r'escape-char ::= "\"" | "\\" | "/" | "n" | "t" | "r"',
    r'ws ::= [ \t\n]*',
]
AGENT_GRAMMAR_STR = "\n".join(_GBNF_LINES)
AGENT_GRAMMAR = LlamaGrammar.from_string(AGENT_GRAMMAR_STR)


# ---- System prompt (JSON-format examples, much shorter) ----
AGENT_SYSTEM_PROMPT = f"""You are a Swiss legal citation retrieval agent. Your job: generate search queries to find relevant Swiss legal citations.

You have 2 tools:
- search_laws: searches Swiss federal statutes (SR collection)
- search_courts: searches Swiss Federal Court decisions (BGE)

You MUST respond with a single JSON object on each turn:
{{"thought": "your reasoning", "action": "search_laws|search_courts|done", "query": "English search terms"}}

When action is "done", set query to "" — this signals you are finished searching.

Strategy:
- Search BOTH laws and courts (alternate between them)
- Use specific English legal terminology in queries
- Each query should target a different aspect of the legal question
- After 4-5 searches covering both sources, use action "done"

Available law types: {LAW_TYPES_FOR_PROMPT}
Court types: {COURT_TYPES_FOR_PROMPT}

Example turns for query "What are requirements for a valid contract?":
Turn 1: {{"thought": "Search for contract formation requirements in obligations law", "action": "search_laws", "query": "contract formation requirements mutual consent obligations"}}
Turn 2: {{"thought": "Now search court precedents on contract validity", "action": "search_courts", "query": "valid contract requirements consent BGE"}}
Turn 3: {{"thought": "Check for defects of consent provisions", "action": "search_laws", "query": "defects consent error fraud duress contract"}}
Turn 4: {{"thought": "Look for court decisions on contract nullity", "action": "search_courts", "query": "contract nullity void voidable consent"}}
Turn 5: {{"thought": "Covered both sources sufficiently", "action": "done", "query": ""}}"""


# ---- Observation formatting (summary only — no raw text) ----
def format_observation(tool_name, results, top_n=5):
    """Format tool results as a compact summary for the agent context."""
    count = len(results)
    if count == 0:
        return f"[{tool_name}: 0 results]"
    top_citations = [r.get("citation", "?")[:40] for r in results[:top_n]]
    cit_str = ", ".join(f'"{c}"' for c in top_citations)
    return f"[{tool_name}: {count} results. Top {min(top_n, count)}: {cit_str}]"


# ---- Main agent loop ----
def run_agent(query, verbose=False):
    """Run structured ReAct agent. Returns (citations_list, logs_list)."""
    all_citations = []
    logs = []
    history = []  # list of (action_str, observation_summary) tuples

    for iteration in range(CONFIG["max_iterations"]):
        # Build prompt
        prompt = f"[INST] {AGENT_SYSTEM_PROMPT}\n\nQuery: {query}\n\n"
        if history:
            prompt += "Previous searches:\n"
            for h_action, h_obs in history:
                prompt += f"- {h_action} -> {h_obs}\n"
            prompt += "\n"
        prompt += "Respond with your next action as JSON: [/INST]\n"

        # Truncate if needed (keep system + query + last 3 history items)
        if len(prompt) > CONFIG["max_conversation_chars"]:
            prompt = f"[INST] {AGENT_SYSTEM_PROMPT}\n\nQuery: {query}\n\n"
            if history:
                prompt += "Previous searches (recent):\n"
                for h_action, h_obs in history[-3:]:
                    prompt += f"- {h_action} -> {h_obs}\n"
                prompt += "\n"
            prompt += "Respond with your next action as JSON: [/INST]\n"

        # Generate with grammar constraint
        try:
            response = llm(
                prompt,
                max_tokens=CONFIG["max_tokens"],
                temperature=CONFIG["temperature"],
                grammar=AGENT_GRAMMAR,
                stop=["[INST]", "</s>"],
            )["choices"][0]["text"].strip()
        except Exception as e:
            if verbose:
                print(f"    [ERROR] LLM generation failed: {e}")
            break

        # Parse JSON (grammar guarantees valid JSON structure)
        try:
            parsed = _json.loads(response)
            action = AgentAction(**parsed)
        except (ValueError, Exception) as e:
            if verbose:
                print(f"    [ERROR] Parse failed: {e} | raw: {response[:100]}")
            # Fallback: try to extract just the action field
            break

        if verbose:
            print(f"  [Iter {iteration+1}] thought=\"{action.thought[:80]}\" "
                  f"action={action.action} query=\"{action.query[:60]}\"")

        # Handle "done" action
        if action.action == "done":
            if verbose:
                print(f"    -> Agent signaled done after {iteration+1} iterations")
            break

        # Execute tool
        tool = TOOLS.get(action.action)
        if not tool:
            if verbose:
                print(f"    [WARN] Unknown tool: {action.action}")
            break

        observation = tool(action.query)
        obs_citations = tool.get_last_citations()
        all_citations.extend(obs_citations)

        # Format compact observation for history
        obs_summary = format_observation(action.action, tool._last_results, top_n=5)
        history.append((f'{action.action}("{action.query[:50]}")', obs_summary))

        if verbose:
            print(f"    [{action.action}] -> {len(obs_citations)} citations")

        logs.append({
            "iteration": iteration,
            "thought": action.thought,
            "action": action.action,
            "query": action.query,
            "n_citations": len(obs_citations),
        })

    # Deduplicate citations (preserve order)
    seen = set()
    deduped = []
    for c in all_citations:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    return deduped, logs


# Quick sanity check
print(f"Agent system prompt: {len(AGENT_SYSTEM_PROMPT):,} chars")
print(f"Agent grammar: GBNF constrained (search_laws|search_courts|done)")
print(f"Agent ready — max {CONFIG['max_iterations']} iterations, 1 tool/iter")

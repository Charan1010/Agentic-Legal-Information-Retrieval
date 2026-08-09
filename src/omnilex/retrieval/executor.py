"""Direction Executor — ReAct loop for a single research direction.

Phase C: Iteration 0 (no LLM) + up to 3 ReAct iterations with GBNF-constrained output.
"""

import json
import re
import time
from pathlib import Path
from typing import Callable, Optional

from .planner import Direction, Plan


PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"
CONTEXT_DIR = Path(__file__).parent.parent.parent.parent / "context"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Taxonomy section extraction (per-code keyword blocks from routing guides)
# ---------------------------------------------------------------------------

_TAXONOMY_CACHE: dict[str, str] = {}


def _build_taxonomy_cache() -> dict[str, str]:
    """Parse routing guides into per-code taxonomy sections.

    Extracts the bullet-point block for each code (e.g., StPO, OR, 1B_, 6B_).
    Returns dict mapping code -> taxonomy text (~100-200 tokens each).
    """
    if _TAXONOMY_CACHE:
        return _TAXONOMY_CACHE

    for filename in ("routing_guide_laws.txt", "routing_guide_courts.txt"):
        path = CONTEXT_DIR / filename
        if not path.exists():
            continue
        text = _load_text(path)

        # Split into per-code sections by "• CODE (" pattern
        current_code = None
        current_lines: list[str] = []

        for line in text.split("\n"):
            # Match lines like "• StPO (Schweizerische Strafprozessordnung)"
            # or "• 1B_ (26'275 Entscheide): ..."
            m = re.match(r"[•·]\s*(\S+)\s*\(", line)
            if m:
                # Save previous section
                if current_code and current_lines:
                    _TAXONOMY_CACHE[current_code] = "\n".join(current_lines)
                current_code = m.group(1)
                current_lines = [line]
            elif current_code:
                # Lines belonging to current code section
                if line.startswith("• ") or line.startswith("· "):
                    # New code starts — save current
                    if current_lines:
                        _TAXONOMY_CACHE[current_code] = "\n".join(current_lines)
                    current_code = None
                    current_lines = []
                elif line.startswith("=== ") or line.startswith("--- "):
                    # Section header — save and reset
                    if current_lines:
                        _TAXONOMY_CACHE[current_code] = "\n".join(current_lines)
                    current_code = None
                    current_lines = []
                else:
                    current_lines.append(line)

        # Save last section
        if current_code and current_lines:
            _TAXONOMY_CACHE[current_code] = "\n".join(current_lines)

    return _TAXONOMY_CACHE


def get_taxonomy_section(filter_codes: list[str]) -> str:
    """Get combined taxonomy section for given filter codes.

    Args:
        filter_codes: List of codes (e.g., ["StPO", "BV"])

    Returns:
        Combined taxonomy text for all matching codes, or empty string.
    """
    cache = _build_taxonomy_cache()
    sections = []
    for code in filter_codes:
        if code in cache:
            sections.append(cache[code])
    if not sections:
        return ""
    return "TAXONOMIE DIESER RICHTUNG:\n" + "\n\n".join(sections)


def format_observation(results: list[tuple[str, float, str]], filter_codes: list[str]) -> str:
    """Format search results into the standard observation string for executor.

    Args:
        results: List of (citation, score, snippet) from filtered_hybrid_search
        filter_codes: Active filter codes for display

    Returns:
        Formatted observation string
    """
    if not results:
        return "SUCHERGEBNISSE: Keine Treffer."

    filter_str = ", ".join(filter_codes) if filter_codes else "unfiltered"
    lines = [f"SUCHERGEBNISSE (Filter: {filter_str}, {len(results)} Treffer):"]

    for i, (citation, score, snippet) in enumerate(results[:10], 1):
        # Truncate snippet to key terms
        snippet_short = snippet[:80].replace("\n", " ").strip()
        lines.append(f"{i}. \"{citation}\" ({score:.2f}) — {snippet_short}")

    return "\n".join(lines)


def format_prior_findings(
    all_citations: list[tuple[str, float, str]],
    max_citations: int = 20,
    max_tokens: int = 1000,
) -> str:
    """Format prior findings from earlier directions (compact).

    Args:
        all_citations: All citations found so far
        max_citations: Maximum number to include
        max_tokens: Approximate token budget

    Returns:
        Formatted string for {prior_findings} template variable
    """
    if not all_citations:
        return "Noch keine Funde aus vorherigen Richtungen."

    # Take last N citations (most recent = most relevant)
    recent = all_citations[-max_citations:]

    lines = ["BISHERIGE FUNDE:"]
    total_chars = 0
    for citation, score, _ in recent:
        line = f"- {citation} ({score:.2f})"
        total_chars += len(line)
        if total_chars > max_tokens * 4:  # ~4 chars per token
            break
        lines.append(line)

    return "\n".join(lines)


def format_direction_history(history: list[dict], max_tokens: int = 2000) -> str:
    """Format this direction's search history for context.

    Args:
        history: List of {query, results} dicts
        max_tokens: Approximate token budget

    Returns:
        Formatted string for {direction_history} template variable
    """
    if not history:
        return "Keine bisherigen Suchen in dieser Richtung."

    lines = ["SUCHVERLAUF DIESER RICHTUNG:"]
    total_chars = 0

    for entry in history:
        query_line = f"Query: \"{entry['query']}\""
        result_cits = [r[0] for r in entry["results"][:5]]
        result_line = f"  → Funde: {'; '.join(result_cits)}" if result_cits else "  → Keine Treffer"

        chunk = f"{query_line}\n{result_line}"
        total_chars += len(chunk)
        if total_chars > max_tokens * 4:
            lines.append("... (gekürzt)")
            break
        lines.append(chunk)

    return "\n".join(lines)


def run_direction(
    direction: Direction,
    plan: Plan,
    direction_index: int,
    total_directions: int,
    prior_findings: list[tuple[str, float, str]],
    search_fn: Callable,
    llm_fn: Callable,
    grammar_path: Optional[Path] = None,
    max_iterations: int = 3,
    timeout_seconds: float = 15.0,
) -> list[tuple[str, float, str]]:
    """Execute a single direction with ReAct loop.

    Args:
        direction: Direction object from planner
        plan: Full plan (for context injection)
        direction_index: 0-based index of this direction
        total_directions: Total number of directions
        prior_findings: Citations from earlier directions
        search_fn: filtered_hybrid_search(query, corpus, filter_codes, top_k) -> results
        llm_fn: Callable(messages, grammar_path, max_tokens) -> str
        grammar_path: Path to executor.gbnf
        max_iterations: Hard cap on LLM iterations (default 3)
        timeout_seconds: Wall-clock timeout per direction (default 15s)

    Returns:
        List of (citation, score, snippet) tuples found in this direction
    """
    if grammar_path is None:
        grammar_path = PROMPTS_DIR / "executor.gbnf"

    start_time = time.time()
    direction_citations: list[tuple[str, float, str]] = []
    history: list[dict] = []

    # --- Iteration 0: seed query (NO LLM call) ---
    if direction.seed_queries:
        seed_query = direction.seed_queries[0]
        results = search_fn(seed_query, direction.corpus, direction.filter_codes, top_k=10)
        direction_citations.extend(results)
        history.append({"query": seed_query, "results": results})

    # --- Iterations 1-N: ReAct loop ---
    # Select prompt template
    is_procedural = direction.priority >= 90
    if is_procedural:
        prompt_template = _load_text(PROMPTS_DIR / "executor_procedural.txt")
    else:
        prompt_template = _load_text(PROMPTS_DIR / "executor_system.txt")

    for iteration in range(1, max_iterations + 1):
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            break

        # Build executor prompt
        plan_summary = (
            f"Sachverhalt: {plan.sachverhalt}\n"
            f"Rechtsfragen: {'; '.join(plan.rechtsfragen)}\n"
            f"Dies ist Richtung {direction_index + 1} von {total_directions}."
        )

        if is_procedural:
            # Procedural template uses {prior_findings} directly
            system_content = prompt_template.format(
                prior_findings=format_prior_findings(prior_findings + direction_citations),
            )
        else:
            system_content = prompt_template.format(
                rechtsgebiet=direction.rechtsgebiet,
                corpus=direction.corpus,
                filter_codes=", ".join(direction.filter_codes),
                reasoning=direction.reasoning,
                taxonomy_section=get_taxonomy_section(direction.filter_codes),
                plan_summary=plan_summary,
                prior_findings=format_prior_findings(prior_findings),
                direction_history=format_direction_history(history),
            )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": "Generiere deine nächste Suchanfrage oder signalisiere done."},
        ]

        # LLM call with grammar
        response = llm_fn(messages, grammar_path, max_tokens=200)
        parsed = _safe_json_parse(response)

        if parsed is None:
            # Retry once
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": "Output NUR JSON: {\"thought\":..., \"query\":..., \"done\":...}"})
            response = llm_fn(messages, grammar_path, max_tokens=200)
            parsed = _safe_json_parse(response)
            if parsed is None:
                break  # give up on this direction

        # Check if done
        if parsed.get("done", False) or not parsed.get("query", "").strip():
            break

        query = parsed["query"].strip()

        # Check for repeated query
        if query in [h["query"] for h in history]:
            break

        # Execute search
        results = search_fn(query, direction.corpus, direction.filter_codes, top_k=10)

        # Adaptive fallback: no results with filter → try unfiltered
        if not results and direction.filter_codes:
            results = search_fn(query, direction.corpus, [], top_k=10)

        direction_citations.extend(results)
        history.append({"query": query, "results": results})

    return direction_citations


def _safe_json_parse(response: str) -> Optional[dict]:
    """Safely parse executor JSON response.

    Args:
        response: Raw LLM output

    Returns:
        Parsed dict or None
    """
    # Try direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from surrounding text
    match = re.search(r"\{.*?\}", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None

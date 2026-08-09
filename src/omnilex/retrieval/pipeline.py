"""Main orchestration pipeline — Planner-Director RAG Agent.

Phase D: Connects planner → executor → aggregation into a single run_pipeline() call.
"""

import re
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .planner import Plan, run_planner, fallback_decompose
from .executor import run_direction, format_prior_findings
from .metadata_filter import (
    MetadataIndex,
    FilteredHybridSearch,
    build_metadata_index,
    regex_extract_citations,
)


# ---------------------------------------------------------------------------
# Procedural Defaults
# ---------------------------------------------------------------------------

UNIVERSAL_DEFAULTS = [
    "Art. 42 Abs. 2 BGG",
    "Art. 95 BGG",
    "Art. 100 Abs. 1 BGG",
    "Art. 105 Abs. 1 BGG",
    "Art. 29 Abs. 2 BV",
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
    "9C_": ["Art. 61 ATSG"],
    "2C_": ["Art. 96 AIG"],
    "4A_": ["Art. 97 Abs. 1 BGG"],
}


def detect_case_type(citations: list[tuple[str, float, str]]) -> str:
    """Detect case type from court citation prefixes.

    Args:
        citations: All citations found

    Returns:
        Case type string: "criminal", "civil", "public_law", "social_insurance", or "unknown"
    """
    prefixes = set()
    for cit, _, _ in citations:
        # Match court case numbers like "6B_1234/2023 E. 2"
        m = re.match(r"(\d[A-Z]_)", cit)
        if m:
            prefixes.add(m.group(1))
        # Match BGE citations
        if cit.startswith("BGE"):
            bge_m = re.match(r"BGE \d+ ([IVX]+)", cit)
            if bge_m:
                roman = bge_m.group(1)
                if roman == "IV":
                    prefixes.add("6B_")  # BGE IV = criminal
                elif roman in ("I", "II"):
                    prefixes.add("1C_")  # public law
                elif roman == "III":
                    prefixes.add("4A_")  # civil
                elif roman == "V":
                    prefixes.add("8C_")  # social insurance

    if "6B_" in prefixes or "1B_" in prefixes:
        return "criminal"
    elif "4A_" in prefixes or "5A_" in prefixes:
        return "civil"
    elif "8C_" in prefixes or "9C_" in prefixes:
        return "social_insurance"
    elif "2C_" in prefixes or "1C_" in prefixes:
        return "public_law"
    return "unknown"


def get_procedural_defaults(case_type: str, citations: list[tuple[str, float, str]]) -> list[str]:
    """Get procedural default citations for a case type.

    Args:
        case_type: Detected case type
        citations: All citations (to detect subtypes)

    Returns:
        List of default citation strings to inject
    """
    defaults = list(UNIVERSAL_DEFAULTS)

    # Case-type defaults
    if case_type in CASE_TYPE_DEFAULTS:
        defaults.extend(CASE_TYPE_DEFAULTS[case_type])

    # Subtype defaults (based on detected prefixes)
    for cit, _, _ in citations:
        m = re.match(r"(\d[A-Z]_)", cit)
        if m:
            prefix = m.group(1)
            if prefix in SUBTYPE_DEFAULTS:
                defaults.extend(SUBTYPE_DEFAULTS[prefix])
                break  # one subtype is enough

    return list(dict.fromkeys(defaults))  # deduplicate preserving order


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_and_output(
    all_citations: list[tuple[str, float, str]],
    question: str,
    corpus_citation_set: set[str],
    reranker_fn: Optional[Callable] = None,
    score_cutoff: float = 0.2,
    max_citations: int = 60,
) -> str:
    """Aggregate all citations → dedup → rerank → format output.

    Args:
        all_citations: All (citation, score, snippet) from all directions
        question: Original English question
        corpus_citation_set: Set of all valid citations in corpus
        reranker_fn: Optional reranker(query, documents) -> scores
        score_cutoff: Minimum reranker score (default 0.2)
        max_citations: Maximum output citations (default 60)

    Returns:
        Semicolon-separated citation string for submission
    """
    if not all_citations:
        return ""

    # 1. Detect case type and inject procedural defaults
    case_type = detect_case_type(all_citations)
    defaults = get_procedural_defaults(case_type, all_citations)

    for default_cit in defaults:
        # Only inject if citation exists in corpus
        if default_cit in corpus_citation_set:
            all_citations.append((default_cit, 0.3, ""))

    # 2. Deduplicate — keep highest score per citation string
    citation_scores: dict[str, float] = {}
    citation_snippets: dict[str, str] = {}
    for cit, score, snippet in all_citations:
        if cit not in citation_scores or score > citation_scores[cit]:
            citation_scores[cit] = score
            citation_snippets[cit] = snippet

    candidates = list(citation_scores.keys())

    if not candidates:
        return ""

    # 3. Rerank (if reranker available)
    if reranker_fn is not None and candidates:
        rerank_scores = reranker_fn(question, candidates)
        scored = list(zip(candidates, rerank_scores))
    else:
        # Use original scores as fallback
        scored = [(cit, citation_scores[cit]) for cit in candidates]

    # 4. Apply cutoff + cap
    final = [(cit, score) for cit, score in scored if score >= score_cutoff]
    final.sort(key=lambda x: x[1], reverse=True)
    final = final[:max_citations]

    # SAFETY: never return empty if we had candidates
    if not final:
        scored.sort(key=lambda x: x[1], reverse=True)
        final = scored[:10]

    # 5. Prepend regex-extracted explicit citations from query
    explicit = regex_extract_citations(question)
    final_cits = [cit for cit, _ in final]
    for cit in reversed(explicit):
        if cit in corpus_citation_set and cit not in final_cits:
            final_cits.insert(0, cit)

    # Remove any that aren't in final_cits list already
    if not final_cits:
        final_cits = [cit for cit, _ in final]

    return ";".join(final_cits[:max_citations])


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

class PlannerDirectorPipeline:
    """Full Planner-Director RAG pipeline."""

    def __init__(
        self,
        metadata_index: MetadataIndex,
        search_engine: FilteredHybridSearch,
        llm_fn: Callable,
        reranker_fn: Optional[Callable] = None,
        prompts_dir: Optional[Path] = None,
    ):
        """Initialize pipeline.

        Args:
            metadata_index: Built MetadataIndex
            search_engine: Configured FilteredHybridSearch
            llm_fn: LLM callable(messages, grammar_path, max_tokens) -> str
            reranker_fn: Optional reranker(query, documents) -> scores
            prompts_dir: Path to prompts/ directory
        """
        self.meta = metadata_index
        self.search = search_engine
        self.llm_fn = llm_fn
        self.reranker_fn = reranker_fn
        self.prompts_dir = prompts_dir or Path(__file__).parent.parent.parent.parent / "prompts"

    def run(self, question: str, verbose: bool = False) -> str:
        """Run full pipeline on a single question.

        Args:
            question: English legal question
            verbose: Print progress

        Returns:
            Semicolon-separated citation string
        """
        start = time.time()

        # --- PHASE 1: Planner ---
        if verbose:
            print(f"[Pipeline] Phase 1: Planning...")

        plan = run_planner(
            question=question,
            llm_fn=self.llm_fn,
            available_law_codes=self.meta.available_law_codes,
            available_court_codes=self.meta.available_court_codes,
            grammar_path=self.prompts_dir / "planner.gbnf",
        )

        if plan is None:
            if verbose:
                print("[Pipeline] Planner failed → using fallback decomposition")
            plan = fallback_decompose(question)

        if verbose:
            print(f"[Pipeline] Plan: {len(plan.directions)} directions")
            for d in sorted(plan.directions, key=lambda x: x.priority):
                print(f"  P{d.priority}: {d.rechtsgebiet} [{d.corpus}] "
                      f"filters={d.filter_codes}")

        # --- PHASE 2: Direction Executors ---
        if verbose:
            print(f"[Pipeline] Phase 2: Executing directions...")

        all_citations: list[tuple[str, float, str]] = []
        prior_findings: list[tuple[str, float, str]] = []
        sorted_directions = sorted(plan.directions, key=lambda d: d.priority)

        for i, direction in enumerate(sorted_directions):
            if verbose:
                print(f"  Direction {i+1}/{len(sorted_directions)}: "
                      f"{direction.rechtsgebiet} (P{direction.priority})")

            direction_cits = run_direction(
                direction=direction,
                plan=plan,
                direction_index=i,
                total_directions=len(sorted_directions),
                prior_findings=prior_findings,
                search_fn=self.search.search,
                llm_fn=self.llm_fn,
                grammar_path=self.prompts_dir / "executor.gbnf",
                max_iterations=3,
                timeout_seconds=15.0,
            )

            if verbose:
                print(f"    → {len(direction_cits)} citations found")

            all_citations.extend(direction_cits)
            # Rolling window of prior findings for next direction
            prior_findings = (prior_findings + direction_cits)[-20:]

        # --- PHASE 3: Aggregation ---
        if verbose:
            print(f"[Pipeline] Phase 3: Aggregating {len(all_citations)} raw citations...")

        # Combine both corpus citation sets
        corpus_citation_set = self.meta.law_citation_set | self.meta.court_citation_set

        result = aggregate_and_output(
            all_citations=all_citations,
            question=question,
            corpus_citation_set=corpus_citation_set,
            reranker_fn=self.reranker_fn,
            score_cutoff=0.2,
            max_citations=60,
        )

        elapsed = time.time() - start
        if verbose:
            n_output = len(result.split(";")) if result else 0
            print(f"[Pipeline] Done: {n_output} citations in {elapsed:.1f}s")

        return result

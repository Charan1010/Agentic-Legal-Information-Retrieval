"""Planner agent — decomposes a legal question into research directions.

Phase B: Single LLM call with GBNF grammar → structured plan.
Falls back to keyword decomposition if JSON parse fails.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Direction:
    """A single research direction from the planner."""
    priority: int
    corpus: str  # "laws" | "courts" | "both"
    rechtsgebiet: str
    filter_codes: list[str]
    reasoning: str
    seed_queries: list[str]


@dataclass
class Plan:
    """Structured research plan from the planner."""
    sachverhalt: str = ""
    rechtsfragen: list[str] = field(default_factory=list)
    directions: list[Direction] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"
CONTEXT_DIR = Path(__file__).parent.parent.parent.parent / "context"


def _load_text(path: Path) -> str:
    """Load a text file."""
    return path.read_text(encoding="utf-8")


def run_planner(
    question: str,
    llm_fn,
    available_law_codes: list[str],
    available_court_codes: list[str],
    grammar_path: Optional[Path] = None,
) -> Optional[Plan]:
    """Run the planner agent to decompose a question into directions.

    Args:
        question: English legal question
        llm_fn: Callable(messages, grammar_path, max_tokens) -> str
        available_law_codes: Valid law codes for filter
        available_court_codes: Valid court codes for filter
        grammar_path: Path to planner.gbnf

    Returns:
        Plan object, or None if both attempts fail
    """
    if grammar_path is None:
        grammar_path = PROMPTS_DIR / "planner.gbnf"

    # Build system prompt
    system_prompt = _load_text(PROMPTS_DIR / "planner_system.txt").format(
        available_law_codes=", ".join(available_law_codes),
        available_court_codes=", ".join(available_court_codes),
    )

    # Build user message
    swiss_legal = _load_text(CONTEXT_DIR / "swiss_legal_system.txt")
    routing_laws = _load_text(CONTEXT_DIR / "routing_guide_laws.txt")
    routing_courts = _load_text(CONTEXT_DIR / "routing_guide_courts.txt")
    terminology = _load_text(CONTEXT_DIR / "terminology_bridge.txt")

    user_msg = (
        f"KONTEXT (Schweizerisches Rechtssystem):\n{swiss_legal}\n\n"
        f"GESETZES-ROUTING (Taxonomie & Klassifikation):\n{routing_laws}\n\n"
        f"GERICHTS-ROUTING (Abteilungen & Präfixe):\n{routing_courts}\n\n"
        f"TERMINOLOGIE (Englisch → Deutsch):\n{terminology}\n\n"
        f"FRAGE: {question}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    # First attempt
    response = llm_fn(messages, grammar_path, max_tokens=800)
    plan = _parse_plan_response(response, available_law_codes, available_court_codes)

    if plan is not None:
        return plan

    # Retry with explicit JSON instruction
    messages.append({"role": "assistant", "content": response})
    messages.append({"role": "user", "content": "Output NUR valides JSON. Keine Erklärung."})

    response = llm_fn(messages, grammar_path, max_tokens=800)
    plan = _parse_plan_response(response, available_law_codes, available_court_codes)

    return plan  # May be None → caller uses fallback_decompose


def _parse_plan_response(
    response: str,
    available_law_codes: list[str],
    available_court_codes: list[str],
) -> Optional[Plan]:
    """Parse LLM JSON response into a Plan object.

    Validates filter codes and ensures minimum direction count.
    """
    # Extract JSON from response (handle possible text wrapping)
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if not json_match:
        return None

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        return None

    # Validate required fields
    if "directions" not in data or not isinstance(data["directions"], list):
        return None

    sachverhalt = data.get("sachverhalt", "")
    rechtsfragen = data.get("rechtsfragen", [])
    if isinstance(rechtsfragen, str):
        rechtsfragen = [rechtsfragen]

    # Parse directions
    valid_codes = set(available_law_codes) | set(available_court_codes)
    directions = []

    for d in data["directions"]:
        if not isinstance(d, dict):
            continue

        # Validate and clean filter_codes
        raw_codes = d.get("filter_codes", [])
        if isinstance(raw_codes, str):
            raw_codes = [raw_codes]
        clean_codes = [c for c in raw_codes if c in valid_codes]

        # Validate corpus
        corpus = d.get("corpus", "both")
        if corpus not in ("laws", "courts", "both"):
            corpus = "both"

        # Validate seed_queries
        seed_queries = d.get("seed_queries", [])
        if isinstance(seed_queries, str):
            seed_queries = [seed_queries]

        directions.append(Direction(
            priority=int(d.get("priority", 50)),
            corpus=corpus,
            rechtsgebiet=d.get("rechtsgebiet", ""),
            filter_codes=clean_codes,
            reasoning=d.get("reasoning", ""),
            seed_queries=seed_queries[:3],  # max 3
        ))

    if not directions:
        return None

    plan = Plan(
        sachverhalt=sachverhalt,
        rechtsfragen=rechtsfragen,
        directions=directions,
    )

    # Post-validation: ensure minimum 3 directions
    plan = _ensure_minimum_directions(plan)

    return plan


def _ensure_minimum_directions(plan: Plan) -> Plan:
    """Ensure plan has at least 3 directions including procedural."""
    # Check if procedural direction exists
    has_procedural = any(d.priority >= 90 for d in plan.directions)

    if not has_procedural:
        plan.directions.append(Direction(
            priority=99,
            corpus="both",
            rechtsgebiet="Verfahrensrecht",
            filter_codes=["BGG", "BV"],
            reasoning="Verfahrensrechtliche Grundlagen — immer zitiert",
            seed_queries=["Beschwerde Bundesgericht Legitimation Frist"],
        ))

    # If still <3, add unfiltered catch-all
    while len(plan.directions) < 3:
        plan.directions.insert(-1, Direction(  # before procedural
            priority=50,
            corpus="both",
            rechtsgebiet="Allgemein",
            filter_codes=[],
            reasoning="Ungefilterter Sicherheitsnetz-Suchvorgang",
            seed_queries=["Bundesgericht Rechtsprechung"],
        ))

    return plan


# ---------------------------------------------------------------------------
# Fallback: Keyword-based decomposition
# ---------------------------------------------------------------------------

# Keyword patterns → (corpus, filter_codes, rechtsgebiet, seed_queries)
_FALLBACK_RULES: list[tuple[list[str], str, list[str], str, list[str]]] = [
    # Criminal procedure / detention
    (["detention", "custody", "pre-trial", "remand", "haft", "untersuchungshaft"],
     "laws", ["StPO"], "Strafprozessrecht",
     ["Untersuchungshaft Haftgründe Verhältnismässigkeit Dauer"]),
    (["detention", "custody", "pre-trial", "remand"],
     "courts", ["1B_"], "Haftbeschwerde",
     ["Haftentlassungsgesuch Kollusionsgefahr Fluchtgefahr"]),

    # Criminal law
    (["murder", "assault", "theft", "fraud", "criminal", "offense", "penalty", "sentence"],
     "laws", ["StGB"], "Strafrecht",
     ["Strafzumessung Schuld Verschulden Tatbestand"]),
    (["criminal", "sentence", "penalty", "conviction"],
     "courts", ["6B_"], "Strafrecht BGer",
     ["Strafzumessung Ermessen Bundesgericht Willkür"]),

    # Contract / obligations
    (["contract", "breach", "damages", "liability", "obligation", "tort"],
     "laws", ["OR"], "Obligationenrecht",
     ["Vertragsverletzung Schadenersatz Haftung Verschulden"]),
    (["contract", "breach", "liability"],
     "courts", ["4A_"], "Zivilrecht BGer",
     ["Vertrag Schadenersatz Haftung Beweislast"]),

    # Family / divorce / custody
    (["divorce", "custody", "child", "alimony", "marriage", "parental"],
     "laws", ["ZGB"], "Familienrecht",
     ["Scheidung Kindeswohl elterliche Sorge Unterhalt"]),
    (["divorce", "custody", "child", "family"],
     "courts", ["5A_"], "Familienrecht BGer",
     ["Kindesunterhalt Obhut Besuchsrecht Scheidung"]),

    # Social insurance
    (["disability", "insurance", "pension", "invalidity", "social security", "IV"],
     "laws", ["IVG", "ATSG"], "Sozialversicherungsrecht",
     ["Invalidität Arbeitsunfähigkeit Rentenanspruch Eingliederung"]),
    (["disability", "insurance", "invalidity", "IV"],
     "courts", ["8C_", "9C_"], "Sozialversicherung BGer",
     ["Invalidenrente Arbeitsfähigkeit medizinische Abklärung"]),

    # Immigration / foreign nationals
    (["immigration", "residence", "deportation", "asylum", "foreigner", "permit"],
     "laws", ["AIG"], "Ausländerrecht",
     ["Aufenthaltsbewilligung Niederlassungsbewilligung Widerruf Integration"]),
    (["immigration", "residence", "deportation"],
     "courts", ["2C_"], "Migrationsrecht BGer",
     ["Aufenthaltsbewilligung Widerruf Integration Verhältnismässigkeit"]),

    # Public law / administrative
    (["planning", "building", "environment", "zoning", "permit"],
     "courts", ["1C_"], "Öffentliches Recht BGer",
     ["Baubewilligung Raumplanung Nutzungsplanung Beschwerde"]),

    # Debt enforcement / bankruptcy
    (["debt", "bankruptcy", "enforcement", "insolvency", "collection"],
     "laws", ["SchKG"], "Schuldbetreibung",
     ["Betreibung Konkurs Pfändung Rechtsvorschlag"]),
]


def fallback_decompose(question: str) -> Plan:
    """Rule-based direction decomposition when planner fails.

    Args:
        question: English legal question

    Returns:
        Plan with keyword-matched directions + procedural default
    """
    q_lower = question.lower()
    directions = []
    priority = 1

    for keywords, corpus, codes, rechtsgebiet, seed_queries in _FALLBACK_RULES:
        if any(kw in q_lower for kw in keywords):
            directions.append(Direction(
                priority=priority,
                corpus=corpus,
                filter_codes=codes,
                rechtsgebiet=rechtsgebiet,
                reasoning=f"Keyword match: {', '.join(kw for kw in keywords if kw in q_lower)}",
                seed_queries=seed_queries,
            ))
            priority += 1

    # Deduplicate by (corpus, frozenset(filter_codes))
    seen = set()
    unique_dirs = []
    for d in directions:
        key = (d.corpus, tuple(sorted(d.filter_codes)))
        if key not in seen:
            seen.add(key)
            unique_dirs.append(d)
    directions = unique_dirs

    # Always add procedural
    directions.append(Direction(
        priority=99,
        corpus="both",
        rechtsgebiet="Verfahrensrecht",
        filter_codes=["BGG", "BV"],
        reasoning="Verfahrensrechtliche Grundlagen — immer zitiert",
        seed_queries=["Beschwerde Bundesgericht Legitimation Frist Zulässigkeit"],
    ))

    # If nothing matched → broad unfiltered search
    if len(directions) <= 1:
        directions.insert(0, Direction(
            priority=1, corpus="laws", filter_codes=[],
            rechtsgebiet="Allgemein (Gesetze)",
            reasoning="No keyword match — broad law search",
            seed_queries=["Bundesrecht Gesetzesartikel Voraussetzungen Rechtsfolge"],
        ))
        directions.insert(1, Direction(
            priority=2, corpus="courts", filter_codes=[],
            rechtsgebiet="Allgemein (Entscheide)",
            reasoning="No keyword match — broad court search",
            seed_queries=["Bundesgericht Rechtsprechung Grundsatz Auslegung"],
        ))

    return Plan(sachverhalt="", rechtsfragen=[], directions=directions)

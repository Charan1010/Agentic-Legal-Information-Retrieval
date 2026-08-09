"""Retrieval tools and indexing for Swiss legal documents."""

from .bm25_index import BM25Index, build_index, load_jsonl_corpus, search
from .tools import CourtSearchTool, LawSearchTool
from .metadata_filter import (
    MetadataIndex,
    FilteredHybridSearch,
    build_metadata_index,
    regex_extract_citations,
)
from .planner import Plan, Direction, run_planner, fallback_decompose
from .executor import run_direction
from .pipeline import PlannerDirectorPipeline, aggregate_and_output

__all__ = [
    "BM25Index",
    "build_index",
    "load_jsonl_corpus",
    "search",
    "LawSearchTool",
    "CourtSearchTool",
    "MetadataIndex",
    "FilteredHybridSearch",
    "build_metadata_index",
    "regex_extract_citations",
    "Plan",
    "Direction",
    "run_planner",
    "fallback_decompose",
    "run_direction",
    "PlannerDirectorPipeline",
    "aggregate_and_output",
]

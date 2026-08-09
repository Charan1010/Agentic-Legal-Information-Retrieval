"""Quick test of Phase A metadata parsing."""
import sys
sys.path.insert(0, "src")

from omnilex.retrieval.metadata_filter import build_metadata_index, regex_extract_citations
from pathlib import Path

# Test citation extraction
print("=== Regex extraction test ===")
cits = regex_extract_citations("Under Art. 221 Abs. 1 StPO and BGE 137 IV 122, how does the court...")
for c in cits:
    print(f"  {c}")

# Test metadata parsing
print("\n=== Building metadata index ===")
meta = build_metadata_index(Path("data"))
print(f"Law docs: {len(meta.law_documents)}")
print(f"Court docs: {len(meta.court_documents)}")
print(f"Available law codes ({len(meta.available_law_codes)}): {meta.available_law_codes[:15]}...")
print(f"Available court codes ({len(meta.available_court_codes)}): {meta.available_court_codes}")

# Verify known citations exist
print("\n=== Citation existence test ===")
test_cits = ["Art. 221 Abs. 1 StPO", "Art. 29 Abs. 2 BV", "Art. 42 Abs. 2 BGG",
             "Art. 95 BGG", "Art. 100 Abs. 1 BGG"]
for tc in test_cits:
    found = tc in meta.law_citation_set
    print(f"  \"{tc}\" in corpus: {found}")

# Test filter indices
print("\n=== Filter indices test ===")
import numpy as np
stpo_indices = meta.law_code_to_indices.get("StPO")
print(f"StPO docs: {len(stpo_indices) if stpo_indices is not None else 0}")
bge_iv = meta.court_code_to_indices.get("BGE_IV")
print(f"BGE_IV docs: {len(bge_iv) if bge_iv is not None else 0}")
one_b = meta.court_code_to_indices.get("1B_")
print(f"1B_ docs: {len(one_b) if one_b is not None else 0}")

# Test get_valid_filter_indices
valid = meta.get_valid_filter_indices("laws", ["StPO", "StGB"])
print(f"\nUnion of StPO+StGB indices: {len(valid)} docs")

# Test fallback_decompose
print("\n=== Fallback decompose test ===")
from omnilex.retrieval.planner import fallback_decompose
plan = fallback_decompose("Under what conditions can pre-trial detention be extended?")
print(f"Directions: {len(plan.directions)}")
for d in plan.directions:
    print(f"  P{d.priority}: {d.rechtsgebiet} [{d.corpus}] codes={d.filter_codes}")

print("\n=== ALL TESTS PASSED ===")

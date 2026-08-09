"""Metadata filter infrastructure for Planner-Director RAG agent.

Phase A: Parse corpora, build code-to-indices mappings, implement filtered hybrid search.
"""

import csv
import re
import time
from pathlib import Path
from typing import Optional

import numpy as np

# Lazy imports for heavy libraries (FAISS, embeddings)
# These are initialized in build_indices()


# ---------------------------------------------------------------------------
# A1/A2: Citation Code Parsers
# ---------------------------------------------------------------------------

def parse_law_code(citation: str) -> str:
    """Extract law code from a laws_de.csv citation.

    Format: "Art. 221 Abs. 1 StPO" -> last token is the code.
    Some citations end with SR numbers like "641.711" -- kept as-is.

    Args:
        citation: Raw citation string from laws_de.csv

    Returns:
        Law code string (e.g. "StPO", "OR", "ZGB", "641.711")
    """
    parts = citation.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[-1]
    return citation


def parse_court_code(citation: str) -> str:
    """Extract court code from court_considerations.csv citation.

    Formats:
        "BGE 139 IV 122 E. 3.1" -> "BGE_IV"
        "1B_210/2023 E. 4.1"    -> "1B_"
        "6B_1234/2021 E. 2"     -> "6B_"

    Args:
        citation: Raw citation string from court_considerations.csv

    Returns:
        Court code string (e.g. "BGE_IV", "1B_", "6B_")
    """
    if citation.startswith("BGE"):
        m = re.match(r"BGE \d+ ([IVX]+)", citation)
        if m:
            return f"BGE_{m.group(1)}"
        return "BGE_other"
    else:
        m = re.match(r"(\d[A-Z]_)", citation)
        if m:
            return m.group(1)
        return "unknown"


# ---------------------------------------------------------------------------
# A3: Index Builder
# ---------------------------------------------------------------------------

class MetadataIndex:
    """Holds code-to-indices mappings and corpus data for filtered search."""

    def __init__(self):
        self.law_documents: list[dict] = []  # [{citation, text, title}, ...]
        self.court_documents: list[dict] = []  # [{citation, text}, ...]

        # code -> numpy array of document indices
        self.law_code_to_indices: dict[str, np.ndarray] = {}
        self.court_code_to_indices: dict[str, np.ndarray] = {}

        # All valid citation strings (for checking procedural defaults exist)
        self.law_citation_set: set[str] = set()
        self.court_citation_set: set[str] = set()

        # Available codes (for planner prompt injection)
        self.available_law_codes: list[str] = []
        self.available_court_codes: list[str] = []

    def build_from_csvs(self, laws_path: Path, courts_path: Path,
                        min_law_count: int = 50, min_court_count: int = 100):
        """Parse CSV files and build code-to-indices mappings.

        Args:
            laws_path: Path to laws_de.csv
            courts_path: Path to court_considerations.csv
            min_law_count: Minimum docs for a law code to be "available" (exposed to planner)
            min_court_count: Minimum docs for a court code to be "available"
        """
        print("[MetadataIndex] Parsing laws_de.csv...")
        self._parse_laws(laws_path, min_law_count)
        print(f"[MetadataIndex] Laws: {len(self.law_documents)} docs, "
              f"{len(self.law_code_to_indices)} codes, "
              f"{len(self.available_law_codes)} available codes")

        print("[MetadataIndex] Parsing court_considerations.csv...")
        self._parse_courts(courts_path, min_court_count)
        print(f"[MetadataIndex] Courts: {len(self.court_documents)} docs, "
              f"{len(self.court_code_to_indices)} codes, "
              f"{len(self.available_court_codes)} available codes")

    def _parse_laws(self, path: Path, min_count: int):
        """Parse laws CSV and build law_code_to_indices."""
        code_indices: dict[str, list[int]] = {}

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header: citation, text, title
            for idx, row in enumerate(reader):
                if len(row) < 2:
                    continue
                citation = row[0]
                text = row[1]
                title = row[2] if len(row) > 2 else ""

                self.law_documents.append({
                    "citation": citation,
                    "text": text,
                    "title": title,
                    "idx": idx
                })
                self.law_citation_set.add(citation)

                code = parse_law_code(citation)
                if code not in code_indices:
                    code_indices[code] = []
                code_indices[code].append(idx)

        # Convert to numpy arrays
        for code, indices in code_indices.items():
            self.law_code_to_indices[code] = np.array(indices, dtype=np.int64)

        # Available codes = those with enough documents (for planner to pick from)
        self.available_law_codes = sorted([
            code for code, arr in self.law_code_to_indices.items()
            if len(arr) >= min_count
        ])

    def _parse_courts(self, path: Path, min_count: int):
        """Parse court CSV and build court_code_to_indices."""
        code_indices: dict[str, list[int]] = {}

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header: citation, text
            for idx, row in enumerate(reader):
                if len(row) < 2:
                    continue
                citation = row[0]
                text = row[1]

                self.court_documents.append({
                    "citation": citation,
                    "text": text,
                    "idx": idx
                })
                self.court_citation_set.add(citation)

                code = parse_court_code(citation)
                if code not in code_indices:
                    code_indices[code] = []
                code_indices[code].append(idx)

        # Convert to numpy arrays
        for code, indices in code_indices.items():
            self.court_code_to_indices[code] = np.array(indices, dtype=np.int64)

        # Available codes
        self.available_court_codes = sorted([
            code for code, arr in self.court_code_to_indices.items()
            if len(arr) >= min_count
        ])

    def get_valid_filter_indices(self, corpus: str, filter_codes: list[str]) -> Optional[np.ndarray]:
        """Get union of all valid indices for given filter codes.

        Args:
            corpus: "laws" or "courts"
            filter_codes: List of code strings

        Returns:
            numpy array of valid doc indices, or None if unfiltered
        """
        if not filter_codes:
            return None

        code_map = self.law_code_to_indices if corpus == "laws" else self.court_code_to_indices

        arrays = [code_map[c] for c in filter_codes if c in code_map]
        if not arrays:
            return None  # no valid codes → unfiltered fallback

        return np.unique(np.concatenate(arrays))


# ---------------------------------------------------------------------------
# A4: Filtered Hybrid Search
# ---------------------------------------------------------------------------

class FilteredHybridSearch:
    """Hybrid FAISS + BM25 search with metadata filtering and RRF fusion."""

    def __init__(self, metadata_index: MetadataIndex):
        self.meta = metadata_index

        # These are set after embeddings are built
        self.law_faiss_index = None  # faiss.IndexFlatIP
        self.court_faiss_index = None
        self.law_bm25: Optional[object] = None  # BM25Okapi instance
        self.court_bm25: Optional[object] = None
        self.embed_fn = None  # function: str -> np.ndarray (1D)

    def search(
        self,
        query: str,
        corpus: str,
        filter_codes: list[str],
        top_k: int = 10,
    ) -> list[tuple[str, float, str]]:
        """Execute filtered hybrid search.

        Args:
            query: German search query (3-10 words)
            corpus: "laws" | "courts" | "both"
            filter_codes: Metadata filter codes
            top_k: Number of results

        Returns:
            List of (citation_string, score, text_snippet) tuples
        """
        if corpus == "both":
            law_codes = [c for c in filter_codes if c in self.meta.law_code_to_indices]
            court_codes = [c for c in filter_codes if c in self.meta.court_code_to_indices]
            r_law = self.search(query, "laws", law_codes, top_k)
            r_court = self.search(query, "courts", court_codes, top_k)
            return self._rrf_merge(r_law, r_court)[:top_k]

        # Get valid indices for filtering
        valid_indices = self.meta.get_valid_filter_indices(corpus, filter_codes)

        # Select corpus data
        if corpus == "laws":
            documents = self.meta.law_documents
            faiss_index = self.law_faiss_index
            bm25_index = self.law_bm25
        else:
            documents = self.meta.court_documents
            faiss_index = self.court_faiss_index
            bm25_index = self.court_bm25

        # FAISS semantic search
        faiss_results = self._faiss_search(query, faiss_index, documents,
                                           valid_indices, top_k)

        # BM25 keyword search (post-filter)
        bm25_results = self._bm25_search(query, bm25_index, documents,
                                         valid_indices, top_k)

        # RRF fusion
        combined = self._rrf_merge(faiss_results, bm25_results)[:top_k]

        # ADAPTIVE FALLBACK: if <5 results with filter, retry unfiltered
        if len(combined) < 5 and valid_indices is not None:
            combined = self.search(query, corpus, [], top_k)

        return combined[:top_k]

    def _faiss_search(
        self,
        query: str,
        index,
        documents: list[dict],
        valid_indices: Optional[np.ndarray],
        top_k: int,
    ) -> list[tuple[str, float, str]]:
        """FAISS semantic search with optional ID filtering."""
        if index is None or self.embed_fn is None:
            return []

        query_vec = self.embed_fn(query)
        if query_vec.ndim == 1:
            query_vec = query_vec.reshape(1, -1)

        if valid_indices is not None:
            # Use IDSelector for filtered search
            try:
                import faiss
                id_selector = faiss.IDSelectorArray(valid_indices)
                params = faiss.SearchParameters(sel=id_selector)
                scores, ids = index.search(query_vec, top_k, params=params)
            except (ImportError, AttributeError):
                # Fallback: search more, then filter
                scores, ids = index.search(query_vec, top_k * 10)
                valid_set = set(valid_indices.tolist())
                mask = np.array([i in valid_set for i in ids[0]])
                scores = scores[0][mask][:top_k]
                ids_filtered = ids[0][mask][:top_k]
                scores = scores.reshape(1, -1)
                ids = ids_filtered.reshape(1, -1)
        else:
            scores, ids = index.search(query_vec, top_k)

        results = []
        for score, doc_id in zip(scores[0], ids[0]):
            if doc_id < 0:
                continue
            doc_id = int(doc_id)
            if doc_id >= len(documents):
                continue
            doc = documents[doc_id]
            snippet = doc["text"][:200] if doc.get("text") else ""
            results.append((doc["citation"], float(score), snippet))

        return results

    def _bm25_search(
        self,
        query: str,
        bm25_index,
        documents: list[dict],
        valid_indices: Optional[np.ndarray],
        top_k: int,
    ) -> list[tuple[str, float, str]]:
        """BM25 keyword search with post-filtering."""
        if bm25_index is None:
            return []

        # Tokenize query
        query_tokens = re.split(r"\W+", query.lower())
        query_tokens = [t for t in query_tokens if t]

        if not query_tokens:
            return []

        # Get all BM25 scores
        scores = bm25_index.get_scores(query_tokens)

        if valid_indices is not None:
            # Zero out non-matching indices
            mask = np.zeros(len(scores), dtype=bool)
            mask[valid_indices] = True
            scores = scores * mask

        # Top-k
        top_ids = np.argsort(scores)[-top_k:][::-1]

        results = []
        for doc_id in top_ids:
            if scores[doc_id] <= 0:
                break
            doc = documents[doc_id]
            snippet = doc["text"][:200] if doc.get("text") else ""
            results.append((doc["citation"], float(scores[doc_id]), snippet))

        return results

    def _rrf_merge(
        self,
        results_a: list[tuple[str, float, str]],
        results_b: list[tuple[str, float, str]],
        k: int = 60,
    ) -> list[tuple[str, float, str]]:
        """Reciprocal Rank Fusion of two result lists.

        Args:
            results_a, results_b: Search results (citation, score, snippet)
            k: RRF constant (default 60)

        Returns:
            Merged results sorted by RRF score
        """
        rrf_scores: dict[str, float] = {}
        snippets: dict[str, str] = {}

        for rank, (cit, score, snippet) in enumerate(results_a):
            rrf_scores[cit] = rrf_scores.get(cit, 0.0) + 1.0 / (k + rank + 1)
            if cit not in snippets:
                snippets[cit] = snippet

        for rank, (cit, score, snippet) in enumerate(results_b):
            rrf_scores[cit] = rrf_scores.get(cit, 0.0) + 1.0 / (k + rank + 1)
            if cit not in snippets:
                snippets[cit] = snippet

        # Sort by RRF score descending
        merged = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        return [(cit, score, snippets.get(cit, "")) for cit, score in merged]


# ---------------------------------------------------------------------------
# Utility: Citation extraction from question text
# ---------------------------------------------------------------------------

def regex_extract_citations(text: str) -> list[str]:
    """Extract explicit citations mentioned in question text.

    Handles:
        "Art. 221 Abs. 1 StPO" -> "Art. 221 Abs. 1 StPO"
        "BGE 137 IV 122"       -> "BGE 137 IV 122"
        "Art. 29 Abs. 2 BV"    -> "Art. 29 Abs. 2 BV"

    Args:
        text: Question text (English, but citations are in standard format)

    Returns:
        List of citation strings found
    """
    citations = []

    # Pattern: Art. <num> [Abs. <num>] [lit. <letter>] [Ziff. <num>] <CODE>
    art_pattern = re.compile(
        r"Art\.?\s+(\d+[a-z]?)"
        r"(?:\s+Abs\.?\s+(\d+))?"
        r"(?:\s+lit\.?\s+([a-z]))?"
        r"(?:\s+Ziff\.?\s+(\d+))?"
        r"\s+([A-Z][A-Za-z]+)"
    )
    for m in art_pattern.finditer(text):
        # Reconstruct normalized citation
        parts = [f"Art. {m.group(1)}"]
        if m.group(2):
            parts.append(f"Abs. {m.group(2)}")
        if m.group(3):
            parts.append(f"lit. {m.group(3)}")
        if m.group(4):
            parts.append(f"Ziff. {m.group(4)}")
        parts.append(m.group(5))
        citations.append(" ".join(parts))

    # Pattern: BGE <vol> <roman> <page>
    bge_pattern = re.compile(r"BGE\s+(\d+)\s+([IVX]+)\s+(\d+)")
    for m in bge_pattern.finditer(text):
        citations.append(f"BGE {m.group(1)} {m.group(2)} {m.group(3)}")

    return citations


# ---------------------------------------------------------------------------
# Builder function (called once at startup)
# ---------------------------------------------------------------------------

def build_metadata_index(data_dir: Path) -> MetadataIndex:
    """Build metadata index from data directory.

    Args:
        data_dir: Path to data/ directory containing CSVs

    Returns:
        Populated MetadataIndex
    """
    meta = MetadataIndex()
    meta.build_from_csvs(
        laws_path=data_dir / "laws_de.csv",
        courts_path=data_dir / "court_considerations.csv",
        min_law_count=50,
        min_court_count=100,
    )
    return meta

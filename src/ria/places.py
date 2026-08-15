#!/usr/bin/env python3
"""Find points of interest (POIs) around the globe that are similar to a named
POI, using the ``poi.csv`` dataset from the bronze data layer.

Approach
--------
This is a lightweight similarity (information-retrieval / machine-learning)
engine built on **TF-IDF + cosine similarity**. Each POI's ``categories``
column is tokenized into words. Distinctive, rare words (e.g. ``glacier``,
``chaldoran``) are up-weighted while common words (e.g. ``united``,
``states``) are down-weighted. The named POI is then compared against every
other POI and the top-N most similar are returned.

It runs entirely locally on the Python standard library -- no external
services, model downloads, or API keys are required.

Usage
-----
    python -m ria.places "Eiffel Tower"
    python -m ria.places "Pemba Island" -n 10
    python -m ria.places --csv /path/to/poi.csv "Mount Fiske Glacier"
    python -m ria.places            # interactive mode
"""

import argparse
import csv
import heapq
import math
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

DEFAULT_CSV = "~/data/bronze/poi.csv"

# Articles, prepositions, and conjunctions that carry little semantic signal.
# Genuinely generic terms are left in on purpose -- IDF down-weights them.
STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "by",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "into",
        "over",
        "under",
        "between",
        "among",
        "de",
        "la",
        "le",
        "les",
        "des",
        "du",
        "et",
        "el",
        "los",
        "las",
        "del",
        "und",
        "der",
        "die",
        "das",
        "den",
        "van",
        "von",
        "da",
        "di",
        "do",
        "dos",
        "uma",
        "umas",
        "na",
        "no",
        "em",
        "ao",
        "aos",
        "en",
        "al",
    ]
)


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    """Normalize text and return a list of meaningful word tokens."""
    text = _strip_accents(text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    out: list[str] = []
    for word in text.split():
        if word in STOPWORDS or len(word) < 2:
            continue
        out.append(word)
    return out


def _coord(rad: float, is_lat: bool) -> str:
    deg = math.degrees(rad)
    if is_lat:
        hemi = "N" if deg >= 0 else "S"
    else:
        hemi = "E" if deg >= 0 else "W"
    return f"{abs(deg):.4f}\u00b0 {hemi}"


class POISimilarityEngine:
    """Loads the POI dataset and ranks POIs by category similarity."""

    def __init__(self, csv_path: str, quiet: bool = False):
        self.csv_path = csv_path
        self.quiet = quiet
        self.names: list[str] = []
        self.lat: list[float] = []
        self.lon: list[float] = []
        self.num_categories: list[int] = []
        self.categories_raw: list[str] = []
        self.doc_tokens: list[list[int]] = []
        self.vocab: dict[str, int] = {}
        self.df: dict[int, int] = {}
        self.idf: list[float] = []
        self._load()

    def _load(self) -> None:
        path = Path(self.csv_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"POI dataset not found: {path}")

        if not self.quiet:
            print(f"Loading POI dataset from {path} ...", file=sys.stderr)

        start = time.time()
        with path.open(newline="", encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    continue

                categories = row.get("categories") or ""
                tokens = tokenize(categories)
                if not tokens:
                    # Fall back to link titles when categories are empty.
                    tokens = tokenize(row.get("links") or "")

                self.names.append(name)
                try:
                    self.lat.append(float(row["latitude_radian"]))
                    self.lon.append(float(row["longitude_radian"]))
                except (KeyError, TypeError, ValueError):
                    self.lat.append(0.0)
                    self.lon.append(0.0)
                try:
                    self.num_categories.append(
                        int(row.get("num_categories") or 0)
                    )
                except ValueError:
                    self.num_categories.append(0)
                self.categories_raw.append(categories)

                ids: list[int] = []
                seen: set[int] = set()
                for tok in tokens:
                    tid = self.vocab.get(tok)
                    if tid is None:
                        tid = len(self.vocab)
                        self.vocab[tok] = tid
                        self.df[tid] = 0
                    ids.append(tid)
                    if tid not in seen:
                        seen.add(tid)
                        self.df[tid] += 1
                self.doc_tokens.append(ids)

        n = len(self.names)
        # Smooth inverse document frequency.
        self.idf = [
            math.log((n + 1) / (self.df[i] + 1)) + 1.0
            for i in range(len(self.vocab))
        ]

        if not self.quiet:
            elapsed = time.time() - start
            print(
                f"Loaded {n:,} POIs, {len(self.vocab):,} unique terms "
                f"({elapsed:.2f}s).",
                file=sys.stderr,
            )

    def _query_weights(
        self, tokens: list[int]
    ) -> tuple[dict[int, float], float]:
        tf = Counter(tokens)
        weights = {t: c * self.idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(w * w for w in weights.values()))
        return weights, norm

    def _cosine(
        self, q_weights: dict[int, float], q_norm: float, doc_tokens: list[int]
    ) -> float:
        tf = Counter(doc_tokens)
        idf = self.idf
        doc_norm_sq = 0.0
        for t, c in tf.items():
            w = c * idf[t]
            doc_norm_sq += w * w
        if doc_norm_sq == 0.0:
            return 0.0
        dot = 0.0
        for t, qw in q_weights.items():
            c = tf.get(t)
            if c:
                dot += qw * c * idf[t]
        return dot / (q_norm * math.sqrt(doc_norm_sq))

    def _matches(self, name: str) -> list[int]:
        q = name.strip().lower()
        if not q:
            return []

        exact = [i for i, n in enumerate(self.names) if n.strip().lower() == q]
        if exact:
            return exact

        sub = [i for i, n in enumerate(self.names) if q in n.strip().lower()]
        if sub:
            return sub

        words = [w for w in tokenize(name) if len(w) >= 3]
        if words:
            word_hits = [
                i
                for i, n in enumerate(self.names)
                if all(w in n.strip().lower() for w in words)
            ]
            if word_hits:
                return word_hits

        return []

    def _pick_best(self, matches: list[int]) -> int:
        # Prefer the most descriptive match (most categories) on ties.
        return max(matches, key=lambda i: self.num_categories[i])

    def _cat_set(self, idx: int) -> set[str]:
        return {
            c.strip().lower()
            for c in self.categories_raw[idx].split(";")
            if c.strip()
        }

    def _result(self, idx: int, score: float, query_idx: int) -> dict:
        shared = sorted(self._cat_set(query_idx) & self._cat_set(idx))
        return {
            "name": self.names[idx],
            "lat": self.lat[idx],
            "lon": self.lon[idx],
            "similarity": score,
            "categories": self.categories_raw[idx],
            "shared_categories": shared,
        }

    def search(self, name: str, top_n: int = 10) -> tuple[dict, list[dict]]:
        matches = self._matches(name)
        if not matches:
            raise ValueError(
                f"No point of interest matching {name!r} was found."
            )

        idx = self._pick_best(matches)
        q_weights, q_norm = self._query_weights(self.doc_tokens[idx])
        if q_norm == 0.0:
            raise ValueError(
                f"{self.names[idx]!r} has no usable category information."
            )

        scored: list[tuple[float, int]] = []
        for i, tokens in enumerate(self.doc_tokens):
            if i == idx:
                continue
            score = self._cosine(q_weights, q_norm, tokens)
            if score > 0.0:
                scored.append((score, i))

        top = heapq.nlargest(top_n, scored, key=lambda x: x[0])
        results = [self._result(i, score, idx) for score, i in top]
        query = self._result(idx, 1.0, idx)
        return query, results


def _print(query: dict, results: list[dict], verbose: bool) -> None:
    def coord(r: dict) -> str:
        return f"{_coord(r['lat'], True)}, {_coord(r['lon'], False)}"

    print(f"Query POI: {query['name']}")
    print(f"  Location:    {coord(query)}")
    print(f"  Categories:  {query['categories'] or '(none)'}")
    if verbose and query["shared_categories"]:
        print("  (all categories shown below)")
    print()
    print(
        f"Top {len(results)} similar points of interest (by category similarity):"
    )
    print(
        f"{'#':>3}  {'Name':<46}  {'Similarity':>10}  {'Location':<24}  Shared"
    )
    print("-" * 100)
    for rank, r in enumerate(results, 1):
        shared = len(r["shared_categories"])
        print(
            f"{rank:>3}  {r['name'][:46]:<46}  {r['similarity'] * 100:>9.2f}%  "
            f"{coord(r):<24}  {shared}"
        )
        if verbose:
            if r["categories"]:
                print(f"       categories: {r['categories']}")
            if r["shared_categories"]:
                print(
                    f"       shared:     {'; '.join(r['shared_categories'])}"
                )


def _interactive(
    engine: POISimilarityEngine, top_n: int, verbose: bool
) -> None:
    print("Enter a POI name to find similar places ('quit' to exit).")
    while True:
        try:
            line = input("POI> ").strip()
        except EOFError:
            print()
            break
        if not line:
            continue
        if line.lower() in {"quit", "exit", "q"}:
            break
        try:
            query, results = engine.search(line, top_n)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            continue
        print()
        _print(query, results, verbose)
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Find points of interest similar to a named place by category."
    )
    parser.add_argument(
        "name", nargs="?", help="POI name to find similar places for"
    )
    parser.add_argument(
        "-n", "--top", type=int, default=10, help="number of results"
    )
    parser.add_argument(
        "--csv", help="path to poi.csv (default ~/data/bronze/poi.csv)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show categories"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="suppress progress"
    )
    args = parser.parse_args(argv)

    csv_path = args.csv or os.environ.get("POI_CSV") or DEFAULT_CSV
    try:
        engine = POISimilarityEngine(csv_path, quiet=args.quiet)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.name:
        try:
            query, results = engine.search(args.name, args.top)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        _print(query, results, args.verbose)
    else:
        _interactive(engine, args.top, args.verbose)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

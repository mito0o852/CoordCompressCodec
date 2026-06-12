"""Candidate selection for coordinate universe construction."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Candidate:
    """Potential coordinate fold discovered from training data.

    Args:
        expansion: Symbol sequence that may be replaced by one coordinate ID.
        frequency: Number of times the expansion appears before active pruning.
        score: Deterministic profitability score used for ranking candidates.
    """

    expansion: tuple[int, ...]
    frequency: int
    score: float


def count_ngrams(sequences: Sequence[Sequence[int]], *, max_ngram: int) -> Counter[tuple[int, ...]]:
    """Count repeated n-grams in symbol sequences.

    Args:
        sequences: Training sequences for the current coordinate layer.
        max_ngram: Maximum expansion length to count. Values below ``2`` cannot
            create useful folds.

    Returns:
        Counter mapping n-gram tuples to observed frequencies.
    """

    counts: Counter[tuple[int, ...]] = Counter()
    if max_ngram < 2:
        return counts
    for sequence in sequences:
        size = len(sequence)
        for n in range(2, max_ngram + 1):
            if size < n:
                break
            for index in range(size - n + 1):
                counts[tuple(sequence[index:index + n])] += 1
    return counts


def score_candidate(expansion: tuple[int, ...], frequency: int) -> float:
    """Estimate how useful a coordinate candidate is.

    The score is intentionally simple and deterministic. It rewards repeated
    token savings and gives a small preference to longer phrases when frequency
    is equal.

    Args:
        expansion: Candidate expansion sequence.
        frequency: Number of observed occurrences.

    Returns:
        Positive score for useful candidates; non-positive values should be
        ignored.
    """

    saved_symbols = frequency * (len(expansion) - 1)
    length_bonus = 0.02 * frequency * len(expansion)
    return saved_symbols + length_bonus


def select_candidates(
    sequences: Sequence[Sequence[int]],
    *,
    max_nodes: int,
    max_ngram: int,
    min_count: int,
) -> list[Candidate]:
    """Select top coordinate candidates by estimated symbol savings.

    Args:
        sequences: Training sequences for one coordinate layer.
        max_nodes: Maximum number of candidates to return.
        max_ngram: Maximum expansion length to consider.
        min_count: Minimum occurrence count required before a candidate can be
            selected.

    Returns:
        Candidate list sorted from strongest to weakest. Ties are deterministic.
    """

    counts = count_ngrams(sequences, max_ngram=max_ngram)
    candidates: list[Candidate] = []
    for expansion, frequency in counts.items():
        if frequency < min_count:
            continue
        score = score_candidate(expansion, frequency)
        if score <= 0:
            continue
        candidates.append(Candidate(expansion=expansion, frequency=frequency, score=score))
    candidates.sort(key=lambda item: (-item.score, -item.frequency, -len(item.expansion), item.expansion))
    return candidates[:max_nodes]

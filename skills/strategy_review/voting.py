"""
Borda count voting + diversity constraint.

Implements Section 3.5: each agent submits a top-5 (5,4,3,2,1 pts excluding self)
and a single bottom flag (-2 pts). The vote totals are blended with a quantitative
metric using a regime-dependent weight, then the diversity constraint requires the
top-5 shortlist to include at least three of the four families.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np


@dataclass
class Ballot:
    voter: str
    top5: List[str]                        # ordered, length up to 5
    bottom: str = ""
    rationale: str = ""


@dataclass
class VoteTally:
    points: Dict[str, int] = field(default_factory=dict)
    metric: Dict[str, float] = field(default_factory=dict)
    composite: Dict[str, float] = field(default_factory=dict)
    rank: List[str] = field(default_factory=list)


def assign_review_targets(
    candidates: List[dict],
    seed: int = 2026,
) -> Dict[str, List[Tuple[str, bool]]]:
    """Each candidate reviews 2 peers: 1 same-category, 1 different-category."""
    rng = random.Random(seed)
    by_cat: Dict[str, List[str]] = {}
    for c in candidates:
        by_cat.setdefault(c["category"], []).append(c["slug"])
    out: Dict[str, List[Tuple[str, bool]]] = {}
    for c in candidates:
        slug = c["slug"]
        cat = c["category"]
        same = [s for s in by_cat[cat] if s != slug]
        cross = [s for s in (sum(by_cat.values(), [])) if s != slug and s not in same]
        if not same:
            same = cross
        if not cross:
            cross = same
        intra = rng.choice(same)
        inter = rng.choice(cross)
        out[slug] = [(intra, True), (inter, False)]
    return out


def borda_count(ballots: List[Ballot]) -> Dict[str, int]:
    points: Dict[str, int] = {}
    for b in ballots:
        for i, slug in enumerate(b.top5[:5]):
            pts = 5 - i
            points[slug] = points.get(slug, 0) + pts
        if b.bottom:
            points[b.bottom] = points.get(b.bottom, 0) - 2
    return points


def regime_weight(regime: str) -> float:
    """Blend weight on votes vs metric score (vote_weight)."""
    return {
        "expansion":  0.45,
        "late-cycle": 0.55,
        "recession":  0.65,
        "recovery":   0.50,
    }.get(regime, 0.50)


def composite_score(
    vote_points: Dict[str, int],
    metric_scores: Dict[str, float],
    regime: str,
) -> Dict[str, float]:
    if not vote_points and not metric_scores:
        return {}
    # Normalize each to 0-1
    vp_min = min(vote_points.values()) if vote_points else 0
    vp_max = max(vote_points.values()) if vote_points else 0
    spread = (vp_max - vp_min) or 1
    vp_norm = {k: (v - vp_min) / spread for k, v in vote_points.items()}
    m_min = min(metric_scores.values()) if metric_scores else 0
    m_max = max(metric_scores.values()) if metric_scores else 1
    mspread = (m_max - m_min) or 1
    m_norm = {k: (v - m_min) / mspread for k, v in metric_scores.items()}
    w_vote = regime_weight(regime)
    w_metric = 1.0 - w_vote
    keys = set(vp_norm) | set(m_norm)
    composite = {k: w_vote * vp_norm.get(k, 0.0) + w_metric * m_norm.get(k, 0.0) for k in keys}
    return composite


def apply_diversity(
    ranked: List[str],
    candidate_meta: Dict[str, str],   # slug -> category
    min_families: int = 3,
) -> List[str]:
    """Ensure top-5 includes ≥ `min_families` distinct categories."""
    chosen: List[str] = []
    cats: set = set()
    for s in ranked:
        if len(chosen) < 5:
            chosen.append(s)
            cats.add(candidate_meta.get(s, ""))
        else:
            break
    if len(cats) >= min_families:
        return chosen
    # Backfill: bump in next-ranked candidate from a missing family.
    extras = [s for s in ranked if s not in chosen]
    while len(cats) < min_families and extras:
        for s in extras:
            cat = candidate_meta.get(s, "")
            if cat not in cats:
                # Replace the lowest-ranked element from the most-represented category.
                from collections import Counter
                cat_count = Counter(candidate_meta.get(c, "") for c in chosen)
                drop_cat, _ = cat_count.most_common(1)[0]
                # remove the last chosen with that category
                for j in range(len(chosen) - 1, -1, -1):
                    if candidate_meta.get(chosen[j], "") == drop_cat:
                        chosen.pop(j)
                        break
                chosen.append(s)
                cats = set(candidate_meta.get(c, "") for c in chosen)
                extras.remove(s)
                break
        else:
            break
    return chosen


def tally(
    ballots: List[Ballot],
    metric_scores: Dict[str, float],
    candidate_meta: Dict[str, str],
    regime: str,
) -> VoteTally:
    pts = borda_count(ballots)
    comp = composite_score(pts, metric_scores, regime)
    ranked = sorted(comp.keys(), key=lambda k: comp[k], reverse=True)
    top5 = apply_diversity(ranked, candidate_meta)
    rest = [s for s in ranked if s not in top5]
    final = top5 + rest
    return VoteTally(points=pts, metric=metric_scores, composite=comp, rank=final)

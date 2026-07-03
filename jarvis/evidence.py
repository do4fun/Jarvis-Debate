import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Evidence:
    """Preuve domain-agnostic attachée à un claim de l'argument graph."""
    source_type: str
    reference: str
    content: str
    reliability: float = 0.5   # r(e_j) ∈ [0,1]
    date: Optional[str] = None  # "YYYY-MM-DD"


_DEFAULT_HALF_LIFE_DAYS = 180.0  # ~1 trimestre, constante phase 1 non exposée en config


def freshness_decay(
    evidence_date: Optional[str],
    reference_date: Optional[str] = None,
    half_life_days: float = _DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """h(e_j) : décroissance exponentielle par âge. 1.0 (neutre) si date absente/invalide."""
    if not evidence_date:
        return 1.0
    try:
        d = datetime.strptime(evidence_date, "%Y-%m-%d").date()
    except ValueError:
        return 1.0
    ref = datetime.strptime(reference_date, "%Y-%m-%d").date() if reference_date else date.today()
    age_days = max(0, (ref - d).days)
    return math.exp(-math.log(2) * age_days / half_life_days)


def argument_credibility(
    evidence_list: list[Evidence],
    source_weights: dict[str, float],
    reference_date: Optional[str] = None,
) -> float:
    """C(a_i) = (1/m) * sum_j( w_s(e_j) * r(e_j) * h(e_j) ). 0.0 si aucune preuve (m=0)."""
    if not evidence_list:
        return 0.0
    total = sum(
        source_weights.get(e.source_type, 1.0) * e.reliability * freshness_decay(e.date, reference_date)
        for e in evidence_list
    )
    return total / len(evidence_list)

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from jarvis.argument_graph import Claim


@dataclass
class ConsensusResult:
    decision_options: list[str] = field(default_factory=list)
    stances: dict[str, dict[str, int]] = field(default_factory=dict)   # agent_name -> option -> v_i(o) ∈ {-1,0,1}
    scores: dict[str, float] = field(default_factory=dict)             # option -> S(o)
    theta: float = 0.0
    accepted_options: list[str] = field(default_factory=list)          # options avec S(o) >= theta
    winning_option: Optional[str] = None                               # max S(o) parmi les acceptées, sinon None


def derive_decision_options(claims: list["Claim"]) -> list[str]:
    """Positions distinctes des claims (dédoublonnage par lower/strip), ordre d'apparition."""
    seen: dict[str, str] = {}
    for c in claims:
        key = c.position.strip().lower()
        seen.setdefault(key, c.position.strip())
    return list(seen.values())


def compute_stance(criterion_scores: dict[str, float], lambda_weights: dict[str, float]) -> int:
    """v_i(o) = sign(sum_k lambda_k * s_{i,k}(o))"""
    total = sum(lambda_weights.get(k, 1.0) * v for k, v in criterion_scores.items())
    if total > 0:
        return 1
    if total < 0:
        return -1
    return 0


def compute_consensus(
    claims: list["Claim"],
    trust_weights: dict[str, float],
    lambda_weights: dict[str, float],
    theta: float,
) -> ConsensusResult:
    """
    Pour chaque option (position de claim), calcule v_i(o) par agent (moyenne des
    criterion_scores si plusieurs claims du même agent pour la même option ; 0 si l'agent
    n'a pas de claim sur cette option), puis S(o) = sum_i(w_i*v_i(o)) / sum_i(w_i).

    Le dénominateur sum_i(w_i) porte sur TOUS les participants du débat (trust_weights),
    pas seulement ceux ayant une claim sur o — sinon S(o) ne serait pas comparable entre
    options. accepted_options = options avec S(o) >= theta ; winning_option = max(S(o))
    parmi les acceptées, None si aucune.
    """
    options = derive_decision_options(claims)
    stances: dict[str, dict[str, int]] = {agent: {} for agent in trust_weights}

    for option in options:
        key = option.strip().lower()
        by_agent: dict[str, list[dict[str, float]]] = {}
        for c in claims:
            if c.position.strip().lower() == key:
                by_agent.setdefault(c.agent_name, []).append(c.criterion_scores)

        for agent in trust_weights:
            if agent in by_agent:
                scores_list = by_agent[agent]
                keys = {k for s in scores_list for k in s}
                avg = {k: sum(s.get(k, 0.0) for s in scores_list) / len(scores_list) for k in keys}
                stances[agent][option] = compute_stance(avg, lambda_weights)
            else:
                stances[agent][option] = 0

    total_w = sum(trust_weights.values()) or 1.0
    scores = {
        option: sum(trust_weights[a] * stances[a][option] for a in trust_weights) / total_w
        for option in options
    }
    accepted = [o for o in options if scores[o] >= theta]
    winning = max(accepted, key=lambda o: scores[o]) if accepted else None

    return ConsensusResult(
        decision_options=options,
        stances=stances,
        scores=scores,
        theta=theta,
        accepted_options=accepted,
        winning_option=winning,
    )


def update_trust_weights(
    current_weights: dict[str, float],
    accuracy_signals: dict[str, float],  # a_i(t), pre-résolu (0.5 par défaut ou valeur de feedback)
    alpha: float,
) -> dict[str, float]:
    """w_i(t+1) = (1-alpha)*w_i(t) + alpha*a_i(t)"""
    return {
        name: (1 - alpha) * current_weights.get(name, 1.0) + alpha * a
        for name, a in accuracy_signals.items()
    }

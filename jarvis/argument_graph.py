from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .evidence import Evidence

if TYPE_CHECKING:
    from anthropic import Anthropic
    from jarvis.debate_config import DebateConfig
    from jarvis.consensus import ConsensusResult


@dataclass
class Claim:
    claim_id: str
    agent_name: str
    content: str
    position: str
    criterion_scores: dict[str, float] = field(default_factory=dict)  # s_{i,k}(o)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ArgumentEdge:
    source_id: str
    target_id: str
    relation: str    # "support" | "attack"
    rationale: str


@dataclass
class ArgumentGraph:
    debate_topic: str
    claims: list[Claim] = field(default_factory=list)
    edges: list[ArgumentEdge] = field(default_factory=list)

    def trust_weighted_scores(self, weights: dict[str, float]) -> dict[str, float]:
        """Heuristique legacy bon marché : +w par support, -0.5w par attack, par claim.

        Supplantée pour la décision formelle par jarvis.consensus.compute_consensus
        (S(o) trust-weighted normalisé, comparé à theta) — conservée ici comme signal
        consultatif à granularité différente (par claim plutôt que par option), déjà
        checkpointée via cp.vote_scores.
        """
        scores: dict[str, float] = {c.claim_id: 0.0 for c in self.claims}
        agent_weight = {c.claim_id: weights.get(c.agent_name, 1.0) for c in self.claims}
        for edge in self.edges:
            if edge.relation == "support" and edge.target_id in scores:
                scores[edge.target_id] += agent_weight.get(edge.source_id, 1.0)
            elif edge.relation == "attack" and edge.target_id in scores:
                scores[edge.target_id] -= agent_weight.get(edge.source_id, 1.0) * 0.5
        return scores


def detect_conflicts(
    client: "Anthropic",
    config: "DebateConfig",
    antitheses: dict[str, str],
) -> str:
    """Orchestrateur identifie le conflit central à partir des antithèses."""
    from .debate_config import resolve_model
    formatted = "\n\n".join(f"[{name}]\n{text}" for name, text in antitheses.items())
    prompt = f"""Here are the final positions from all analysts after the antithesis round:

{formatted}

In one concise sentence, identify the central conflict — the core point of semantic opposition — that divides these analysts. Return only the sentence, nothing else."""

    response = client.messages.create(
        model=resolve_model(config, "conflict_detection", None, is_orchestrator=True),
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def build_argument_graph(
    client: "Anthropic",
    config: "DebateConfig",
    antitheses: dict[str, str],
    topic: str,
) -> ArgumentGraph:
    """
    1. Chaque agent formule 1-2 claims sur le topic de conflit, avec des scores par
       critère s_{i,k}(o) et des preuves à l'appui (Evidence).
    2. L'orchestrateur mappe les relations support/attack entre claims.
    """
    import json

    from .debate_config import resolve_model

    graph = ArgumentGraph(debate_topic=topic)
    claim_counter = 0
    criteria = list(config.lambda_weights.keys()) or ["relevance", "confidence"]

    for agent_name, antithesis in antitheses.items():
        claim_counter += 1
        claim_id = f"C{claim_counter}"
        criteria_list = ", ".join(criteria)
        prompt = f"""DEBATE TOPIC: {topic}

YOUR PREVIOUS POSITION:
{antithesis}

Formulate ONE clear, specific claim (1-2 sentences) that captures your stance on this topic.
Then provide a short label (3-7 words) summarizing your position.

Then score your own claim on each of these criteria, from -1 (strongly against) to 1
(strongly in favor): {criteria_list}.

Then list 1-3 pieces of evidence backing your claim (source_type, a short reference/citation,
a short content excerpt, your own reliability estimate in [0,1], and an optional date
"YYYY-MM-DD" if known).

Reply in this exact format:
CLAIM: <your claim>
LABEL: <short label>
EVIDENCE_JSON: {{"criterion_scores": {{"<criterion>": <float>, ...}}, "evidence": [{{"source_type": "...", "reference": "...", "content": "...", "reliability": <float>, "date": "YYYY-MM-DD or null"}}, ...]}}"""

        response = client.messages.create(
            model=resolve_model(config, "argument_graph", None, is_orchestrator=False),
            max_tokens=768,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        claim_text = ""
        label_text = ""
        criterion_scores: dict[str, float] = {}
        evidence_items: list[Evidence] = []
        for line in text.splitlines():
            if line.startswith("CLAIM:"):
                claim_text = line[len("CLAIM:"):].strip()
            elif line.startswith("LABEL:"):
                label_text = line[len("LABEL:"):].strip()
            elif line.startswith("EVIDENCE_JSON:"):
                raw_json = line[len("EVIDENCE_JSON:"):].strip()
                try:
                    payload = json.loads(raw_json)
                    criterion_scores = {
                        str(k): float(v) for k, v in (payload.get("criterion_scores") or {}).items()
                    }
                    evidence_items = [
                        Evidence(
                            source_type=str(e.get("source_type", "")),
                            reference=str(e.get("reference", "")),
                            content=str(e.get("content", "")),
                            reliability=float(e.get("reliability", 0.5)),
                            date=e.get("date") or None,
                        )
                        for e in (payload.get("evidence") or [])
                    ]
                except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
                    criterion_scores = {}
                    evidence_items = []

        graph.claims.append(Claim(
            claim_id=claim_id,
            agent_name=agent_name,
            content=claim_text or text,
            position=label_text or f"Position of {agent_name}",
            criterion_scores=criterion_scores,
            evidence=evidence_items,
        ))

    if len(graph.claims) >= 2:
        claims_summary = "\n".join(
            f"{c.claim_id} [{c.agent_name}]: {c.content}" for c in graph.claims
        )
        edge_prompt = f"""These are claims from different analysts on the topic: "{topic}"

{claims_summary}

For each pair of claims that have a clear relationship, specify whether one SUPPORTS or ATTACKs the other.

Reply with a JSON array (and nothing else) in this format:
[
  {{"source_id": "C1", "target_id": "C2", "relation": "attack", "rationale": "brief reason"}},
  ...
]

Only include pairs with a genuine relationship. If no clear relationship exists between two claims, omit them."""

        edge_response = client.messages.create(
            model=resolve_model(config, "argument_graph", None, is_orchestrator=True),
            max_tokens=1024,
            messages=[{"role": "user", "content": edge_prompt}],
        )
        raw = edge_response.content[0].text.strip()
        try:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            edges_data = json.loads(raw[start:end])
            for e in edges_data:
                graph.edges.append(ArgumentEdge(
                    source_id=e["source_id"],
                    target_id=e["target_id"],
                    relation=e["relation"],
                    rationale=e.get("rationale", ""),
                ))
        except (json.JSONDecodeError, KeyError):
            pass

    return graph


def format_graph_for_synthesis(
    graph: ArgumentGraph,
    scores: dict[str, float],
    consensus: Optional["ConsensusResult"] = None,
    credibility: Optional[dict[str, float]] = None,
) -> str:
    """Formate le graph + scores (+ consensus/crédibilité si fournis) pour injecter dans
    le prompt de synthèse."""
    lines = [f"DEBATE TOPIC: {graph.debate_topic}", ""]

    if consensus is not None:
        lines.append(f"DECISION OPTIONS — CONSENSUS SCORES S(o) (theta={consensus.theta:.2f}):")
        for option in consensus.decision_options:
            s = consensus.scores.get(option, 0.0)
            accepted = "yes" if option in consensus.accepted_options else "no"
            marker = "  ← winning" if option == consensus.winning_option else ""
            lines.append(f"  {option}: S(o)={s:+.2f}  accepted={accepted}{marker}")
        lines.append("")

    lines.append("CLAIMS:")
    for c in graph.claims:
        score = scores.get(c.claim_id, 0.0)
        cred_part = ""
        if credibility is not None:
            cred_part = f", credibility: {credibility.get(c.claim_id, 0.0):.2f}"
        lines.append(f"  {c.claim_id} [{c.agent_name}] (score: {score:+.1f}{cred_part}): {c.content}")
    if graph.edges:
        lines.append("")
        lines.append("ARGUMENT GRAPH:")
        for e in graph.edges:
            lines.append(f"  {e.source_id} --{e.relation}--> {e.target_id}: {e.rationale}")
    return "\n".join(lines)

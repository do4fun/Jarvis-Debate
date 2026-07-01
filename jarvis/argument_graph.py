from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anthropic import Anthropic
    from jarvis.debate_config import DebateConfig


@dataclass
class Claim:
    claim_id: str
    agent_name: str
    content: str
    position: str


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
    from anthropic import Anthropic as _Anthropic
    formatted = "\n\n".join(f"[{name}]\n{text}" for name, text in antitheses.items())
    prompt = f"""Here are the final positions from all analysts after the antithesis round:

{formatted}

In one concise sentence, identify the central conflict — the core point of semantic opposition — that divides these analysts. Return only the sentence, nothing else."""

    response = client.messages.create(
        model=config.orchestrator_model,
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
    1. Chaque agent formule 1-2 claims sur le topic de conflit.
    2. L'orchestrateur mappe les relations support/attack entre claims.
    """
    import json

    graph = ArgumentGraph(debate_topic=topic)
    claim_counter = 0

    for agent_name, antithesis in antitheses.items():
        claim_counter += 1
        claim_id = f"C{claim_counter}"
        prompt = f"""DEBATE TOPIC: {topic}

YOUR PREVIOUS POSITION:
{antithesis}

Formulate ONE clear, specific claim (1-2 sentences) that captures your stance on this topic.
Then provide a short label (3-7 words) summarizing your position.

Reply in this exact format:
CLAIM: <your claim>
LABEL: <short label>"""

        response = client.messages.create(
            model=config.agent_model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        claim_text = ""
        label_text = ""
        for line in text.splitlines():
            if line.startswith("CLAIM:"):
                claim_text = line[len("CLAIM:"):].strip()
            elif line.startswith("LABEL:"):
                label_text = line[len("LABEL:"):].strip()

        graph.claims.append(Claim(
            claim_id=claim_id,
            agent_name=agent_name,
            content=claim_text or text,
            position=label_text or f"Position of {agent_name}",
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
            model=config.orchestrator_model,
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


def format_graph_for_synthesis(graph: ArgumentGraph, scores: dict[str, float]) -> str:
    """Formate le graph + scores pour injecter dans le prompt de synthèse."""
    lines = [f"DEBATE TOPIC: {graph.debate_topic}", ""]
    lines.append("CLAIMS:")
    for c in graph.claims:
        score = scores.get(c.claim_id, 0.0)
        lines.append(f"  {c.claim_id} [{c.agent_name}] (score: {score:+.1f}): {c.content}")
    if graph.edges:
        lines.append("")
        lines.append("ARGUMENT GRAPH:")
        for e in graph.edges:
            lines.append(f"  {e.source_id} --{e.relation}--> {e.target_id}: {e.rationale}")
    return "\n".join(lines)

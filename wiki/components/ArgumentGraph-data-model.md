---
type: component
status: active
tags: [component]
created: 2026-07-03
updated: 2026-07-03
---

# ArgumentGraph — modèle de données

Trois dataclasses ([[argument_graph]], [[evidence]]) :

```python
Claim(claim_id, agent_name, content, position,
      criterion_scores: dict[str, float],  # s_{i,k}(o)
      evidence: list[Evidence])

ArgumentEdge(source_id, target_id, relation,  # "support" | "attack"
             rationale)

ArgumentGraph(debate_topic, claims: list[Claim], edges: list[ArgumentEdge])
```

Un `Claim` = un agent, une position sur le sujet de conflit. Les `ArgumentEdge` sont
générées par un unique appel LLM groupé (pas pairwise) — complétude non garantie, dépend de
la capacité du modèle à énumérer les relations en un coup.

## Où ce modèle est consommé

- `ArgumentGraph.trust_weighted_scores()` — heuristique legacy.
- [[consensus]]`.compute_consensus()` — lit `Claim.position` + `Claim.criterion_scores`.
- [[evidence]]`.argument_credibility()` — lit `Claim.evidence`.
- `format_graph_for_synthesis()` — aplatit tout en texte pour le prompt de synthèse.

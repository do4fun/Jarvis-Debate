---
type: module
path: "jarvis/evidence.py"
status: active
language: python
purpose: "Modèle de preuve domain-agnostic et crédibilité des arguments"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["argument_graph", "debate", "research"]
tags: [module, core, formula]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/evidence.py

Implémente §3.3.5 de Yin 2025. Voir [[001-yin-2025-consensus-formulas]].

## `Evidence`

```python
source_type: str        # libre — "market_data", "filing", "web_search", ...
reference: str
content: str
reliability: float = 0.5   # r(e_j) ∈ [0,1]
date: Optional[str] = None # "YYYY-MM-DD"
```

Domain-agnostic par design : aucun type de source codé en dur dans `jarvis/`. Le domaine
finance (`jarvis/finance_config.py`) déclare `evidence_source_weights` avec ses propres
types (`market_data`, `filing`, `analyst_rating`, `public_statement`, `web_search`).

## Formules

- `freshness_decay(evidence_date, reference_date, half_life_days=180)` : `h(e_j)`,
  décroissance exponentielle par âge. Neutre (`1.0`) si date absente/invalide.
- `argument_credibility(evidence_list, source_weights)` : `C(a_i) = (1/m) · Σ_j
  w_s(e_j)·r(e_j)·h(e_j)`. `0.0` si aucune preuve (m=0).

## Lié à la recherche web

[[research]] peuple `Evidence.source_type="web_search"` implicitement via le formalisme
existant — aucun changement de schéma n'a été nécessaire pour brancher la recherche web sur
ce modèle (voir [[003-web-research-single-anchor]]).

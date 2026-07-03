---
type: module
path: "jarvis/consensus.py"
status: active
language: python
purpose: "Formules de consensus pondéré par la confiance (Yin 2025)"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["debate"]
tags: [module, core, formula]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/consensus.py

Implémente §3.3.4 de Yin 2025. Voir [[001-yin-2025-consensus-formulas]] pour le contexte
de la décision.

## Formules

- `compute_stance(criterion_scores, lambda_weights) -> int` :
  `v_i(o) = sign(Σ_k λ_k · s_{i,k}(o))`, retourne -1/0/1.
- `compute_consensus(claims, trust_weights, lambda_weights, theta) -> ConsensusResult` :
  `S(o) = Σ_i(w_i · v_i(o)) / Σ_i(w_i)`. **Décision de design** : le dénominateur porte
  sur TOUS les agents du débat (pas seulement ceux ayant un claim sur l'option `o`), sinon
  `S(o)` ne serait pas comparable entre options. Options acceptées si `S(o) >= theta`.
- `update_trust_weights(current_weights, accuracy_signals, alpha) -> dict` :
  `w_i(t+1) = (1-alpha)·w_i(t) + alpha·a_i(t)` — moyenne mobile exponentielle.

## `derive_decision_options()`

Les options de décision `o` sont dérivées des `Claim.position` distincts (dédoublonnés par
`strip().lower()`). Limite connue : "Bullish" et "Bullish on tech" ne sont PAS fusionnés —
acceptée comme limitation phase 1 (voir la note "open question 5" dans l'historique de
conception).

## `a_i(t)` — signal d'exactitude historique

Résolu par [[trust_store]]`.resolve_accuracy_signals()` : valeur de feedback différé si
enregistrée pour cette session+agent, sinon `0.5` (neutre).

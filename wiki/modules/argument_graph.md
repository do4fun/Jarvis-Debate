---
type: module
path: "jarvis/argument_graph.py"
status: active
language: python
purpose: "Détection de conflit et construction du graphe d'arguments"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: ["debate_config", "evidence"]
used_by: ["debate"]
tags: [module, core]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/argument_graph.py

Voir [[ArgumentGraph-data-model]] pour le modèle de données. Deux appels LLM :

1. `detect_conflicts()` — un appel orchestrateur qui identifie le point de désaccord
   central entre les antithèses de tous les agents (`conflict_topic`, une phrase).
2. `build_argument_graph()` — un appel par agent (produit un `Claim` avec position,
   scores par critère `s_{i,k}(o)`, et `Evidence` citées), puis un appel groupé qui mappe
   les relations `support`/`attack` entre tous les claims.

## `trust_weighted_scores()` (heuristique legacy)

Score par claim : `+trust_weight` par support, `-0.5*trust_weight` par attack. Conservée
comme signal consultatif bon marché (checkpointée via `cp.vote_scores`), mais **supplantée**
pour la décision formelle par [[consensus]]`.compute_consensus()` (S(o) normalisé + seuil
theta) — voir [[001-yin-2025-consensus-formulas]].

## `format_graph_for_synthesis()`

Aplatit `ArgumentGraph` + scores + consensus + crédibilité en texte pour le prompt de
synthèse. Seul point où le graphe structuré redevient du texte libre avant d'atteindre le
modèle de synthèse (pas de schéma structuré pour le graphe lui-même).

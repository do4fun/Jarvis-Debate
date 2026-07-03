---
type: module
path: "jarvis/debate.py"
status: active
language: python
purpose: "Orchestration du pipeline de débat complet"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: ["debate_config", "argument_graph", "consensus", "evidence", "trust_store", "research", "checkpoint", "session_log", "agent_persona", "loader"]
used_by: ["main.py"]
tags: [module, core]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/debate.py

Le cœur du protocole. Contient `run_debate()` (point d'entrée public) et
`_run_single_debate()` (exécute les 7 phases pour une question). Voir [[debate-pipeline]]
pour le déroulé complet.

## Fonctions clés

- `_call_agent` / `_call_orchestrator` — les deux seules façons d'appeler l'API Anthropic
  dans le protocole. Résolvent le modèle via `resolve_model()` ([[debate_config]]),
  acceptent un paramètre `phase` pour l'override de modèle par phase.
- `_run_agents_in_speaking_order` — exécute un groupe d'agents selon leur
  `speaking_mode` : `sequential`, `parallel`, ou `dependency` (tri topologique via
  `_topo_sort_group`, algorithme de Kahn sur `wait_for`).
- `_run_brainstorming_phase` — thread partagé, orchestrateur modérateur, interventions du
  Devil's Advocate.
- `_interactive_question_validation` / `_interactive_plan_validation` — boucles
  interactives où l'utilisateur valide ou révise avant de continuer.

## Points d'extension récents

- Phase `research` insérée avant le brainstorming (voir [[research]],
  [[003-web-research-single-anchor]]) — le `research_briefing` est injecté dans le prompt
  d'ouverture du brainstorm et dans le prompt de thèse.
- Calcul du consensus (`compute_consensus`) et de la crédibilité (`argument_credibility`)
  juste après `build_argument_graph`, avant la synthèse.
- Mise à jour du poids de confiance (`update_trust_weights`) après la synthèse, gardée
  idempotente par `cp.trust_updated` (pas de phase dédiée dans `checkpoint.PHASES`).

## Pièges connus

- `_make_cp` (dans `run_debate`) doit initialiser `phase="research"` (pas `"brainstorm"`)
  pour qu'un débat neuf ne saute pas la phase de recherche — `is_orchestrator_done`
  compare des index positionnels dans `checkpoint.PHASES`.

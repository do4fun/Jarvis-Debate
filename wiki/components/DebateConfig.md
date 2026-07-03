---
type: component
status: active
tags: [component]
created: 2026-07-03
updated: 2026-07-03
---

# DebateConfig

Structure de configuration centrale ([[debate_config]]), domain-agnostic. Un domaine
construit une instance via `build_<domaine>_config()` (ex: `jarvis/finance_config.py`).

## Groupes de champs

- **Modèles** — `agent_model`, `orchestrator_model`, `phase_models` (résolus via
  `resolve_model()`).
- **Itérations** — `iterations_brainstorming/thesis/antithesis/synthesis`.
- **Phases activées** — `enabled_phases` (défaut : `research, brainstorm, thesis,
  antithesis, conflict_detection, argument_graph, synthesis`).
- **Prompts** — `question_analyst_prompt`, `brainstorm_moderator_prompt`, `planner_prompt`,
  `synthesis_prompt`, `researcher_prompt`, `source_validator_prompt` (les deux derniers
  vides par défaut → fallback sur des prompts génériques dans `jarvis/research.py`).
- **Schéma de sortie** — `output_schema`, `output_pydantic_model`.
- **Consensus (Yin 2025)** — `theta`, `alpha`, `lambda_weights`, `evidence_source_weights`.
- **Recherche web** — `web_search_enabled`, `web_search_max_uses`, `web_fetch_max_uses`,
  `web_fetch_max_content_tokens`, `web_search_allowed_domains`/`blocked_domains`.

## Principe de séparation domaine/protocole

Tous les dicts domaine-spécifiques (`lambda_weights`, `evidence_source_weights`,
`web_search_allowed_domains`) restent vides au niveau protocole — jamais codés en dur dans
`jarvis/`. Voir [[002-agents-directory-rule]] pour la règle analogue sur les agents.

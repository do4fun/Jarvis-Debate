---
type: module
path: "jarvis/debate_config.py"
status: active
language: python
purpose: "Configuration centrale du protocole, domain-agnostic"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["debate", "argument_graph", "research", "cost_forecast", "finance_config"]
tags: [module, core, config]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/debate_config.py

`DebateConfig` (voir [[DebateConfig]]) et deux fonctions : `load_default_config()`
(peuple depuis les variables d'environnement, deux niveaux — `.env` générique puis
`.env` spécifique au domaine actif, `override=True`) et `resolve_model()`.

## `resolve_model()`

Précédence unique pour choisir un modèle LLM à travers tout le protocole :

```
persona.model  >  config.phase_models[phase]  >  orchestrator_model | agent_model
```

Utilisé par `_call_agent`, `_call_orchestrator`, et directement dans [[argument_graph]] /
[[research]] pour les appels qui court-circuitent ces deux fonctions.

## Champs ajoutés au fil des décisions

| Champ | Origine | Décision liée |
|---|---|---|
| `theta`, `alpha`, `lambda_weights`, `evidence_source_weights`, `phase_models` | Consensus Yin 2025 | [[001-yin-2025-consensus-formulas]] |
| `web_search_enabled`, `web_search_max_uses`, `web_fetch_max_uses`, `web_fetch_max_content_tokens`, `web_search_allowed_domains`/`blocked_domains`, `researcher_prompt`, `source_validator_prompt` | Recherche web | [[003-web-research-single-anchor]] |

Tous les champs domaine-spécifiques (`lambda_weights`, `evidence_source_weights`,
`web_search_allowed_domains`, ...) restent vides au niveau protocole — c'est
`jarvis/finance_config.py` (ou tout `<domaine>_config.py` futur) qui les peuple.

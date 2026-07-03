---
type: dependency
path: "requirements.txt"
status: active
language: python
purpose: "Client API Claude — seule dépendance d'exécution LLM"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["debate", "argument_graph", "research"]
tags: [dependency]
created: 2026-07-03
updated: 2026-07-03
---

# anthropic (SDK Python)

`anthropic>=0.52.0` dans `requirements.txt` (floor pin, pas de plafond). Version installée
vérifiée : **0.111.0** (suffisante pour `web_search_20260209`/`web_fetch_20260209`,
`thinking={"type": "adaptive"}`, `output_config.format` json_schema).

## Fonctionnalités utilisées

- `client.messages.create(...)` — seul point d'entrée, jamais de streaming.
- `thinking={"type": "adaptive"}` — sur tous les appels orchestrateur.
- `output_config={"format": {"type": "json_schema", ...}}` — synthèse ([[debate]]) et
  validation des sources ([[research]]).
- `tools=[...]` — `web_search_20260209` + `web_fetch_20260209` (serveur, aucune exécution
  côté client), uniquement dans [[research]].

## Piège connu

`_call_agent` lit `response.content[0].text` sans filtrage — fragile si des tools étaient
ajoutés à ce point d'appel (voir [[003-web-research-single-anchor]], raison pour laquelle
les tools ne sont jamais donnés aux agents du débat directement). `_call_orchestrator`,
lui, filtre déjà `if b.type == "text"`.

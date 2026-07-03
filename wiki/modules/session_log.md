---
type: module
path: "jarvis/session_log.py"
status: active
language: python
purpose: "Log JSON complet et chronologique d'une session de débat"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["debate"]
tags: [module, core]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/session_log.py

Un fichier par session : `rapports/sessions/{session_id}_full.json`. Deux structures dans
`self._data` :

- `phases` — un instantané par nom de phase (écrasé si la phase est loguée plusieurs fois,
  ex : itérations de synthèse).
- `timeline` — liste ordonnée `{"phase": ..., "timestamp": ISO8601}`, **un élément par
  appel** à `log_phase()`, jamais écrasée. C'est elle qui permet de reconstruire la
  séquence chronologique exacte — voir [[004-session-timeline-timestamps]].

## Méthodes

`log_brainstorm`, `log_plan`, `log_theses`, `log_antitheses`, `log_conflict`,
`log_argument_graph`, `log_vote_scores`, `log_consensus`, `log_credibility`,
`log_research`, `log_trust_update`, `log_synthesis` — toutes de simples wrappers autour de
`log_phase(phase, data)`.

## Conversation la plus littérale du système

Le `brainstorm_thread` (loggé via `log_brainstorm`) est une liste de tours
`{"role", "agent", "content", "iteration", "timestamp"}` — la structure la plus proche
d'une vraie conversation multi-agents dans le codebase. Chaque tour porte maintenant son
propre timestamp (ajouté dans `jarvis/debate.py`, pas dans ce module).

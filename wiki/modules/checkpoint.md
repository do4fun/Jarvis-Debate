---
type: module
path: "jarvis/checkpoint.py"
status: active
language: python
purpose: "Reprise sur interruption du pipeline de débat"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["debate"]
tags: [module, core]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/checkpoint.py

Voir [[checkpoint-resume-flow]] pour le mécanisme complet.

## `PHASES` (ordre positionnel)

```python
PHASES = ["research", "brainstorm", "planning", "thesis", "antithesis",
          "conflict_detection", "argument_graph", "synthesis"]
```

`phase_index()`, `is_agent_done()`, `is_orchestrator_done()` comparent des index dans cette
liste — **l'ordre est significatif**. `"research"` a été inséré en première position (voir
[[003-web-research-single-anchor]]), ce qui a nécessité de changer le `phase="brainstorm"`
initial de `_make_cp` (dans `debate.py`) en `phase="research"`, sinon un débat neuf
sauterait la recherche.

## `DebateCheckpoint`

Sauvegardé (overwrite complet) après quasiment chaque appel API réussi
(`rapports/checkpoints/checkpoint_{session_id}.json`). Supprimé après succès — seul
[[session_log]] conserve un historique permanent. Champs ajoutés récemment :
`consensus_data`, `credibility_scores`, `trust_updated` (garde d'idempotence — pas de phase
`PHASES` dédiée pour la mise à jour du trust weight), `research_briefing`,
`research_findings`.

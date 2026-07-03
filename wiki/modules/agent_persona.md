---
type: module
path: "jarvis/agent_persona.py"
status: active
language: python
purpose: "Contrat de données que tout agent de domaine doit remplir"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["debate", "loader"]
tags: [module, core]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/agent_persona.py

Voir [[AgentPersona]] pour le détail des champs. Un seul dataclass, aucune logique — le
"contrat" que chaque agent de domaine (ex: `domains/finance/agents/*.py`) doit remplir en
exposant une variable module-level `AGENT = AgentPersona(...)`.

`speaking_mode` accepte trois valeurs : `"sequential"` (défaut), `"parallel"`, et
`"dependency"` (tri topologique via `wait_for`, ajouté récemment — voir
`_topo_sort_group` dans [[debate]]).

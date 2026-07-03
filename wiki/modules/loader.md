---
type: module
path: "jarvis/loader.py"
status: active
language: python
purpose: "Chargement dynamique des agents depuis AGENTS_DIR"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: ["agent_persona"]
used_by: ["debate"]
tags: [module, core]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/loader.py

`load_agents()` scanne `AGENTS_DIR` (variable d'env, ex: `domains/finance/agents`), importe
chaque `*.py` dynamiquement (`importlib`), cherche une variable `AGENT: AgentPersona`.
Fichier invalide → skip avec warning, pas d'arrêt du chargement.

## Règle stricte liée

Voir [[002-agents-directory-rule]] : `AGENTS_DIR` doit **toujours** pointer vers
`domains/<domaine>/agents`, jamais vers un répertoire `agents/` à la racine du projet.

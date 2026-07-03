---
type: component
status: active
tags: [component]
created: 2026-07-03
updated: 2026-07-03
---

# AgentPersona

Structure de données réutilisable ([[agent_persona]]) définissant un agent participant au
débat. Champs :

| Champ | Type | Rôle |
|---|---|---|
| `name` | `str` | Identifiant affiché, clé dans les dicts de poids/scores |
| `system_prompt` | `str` | Personnalité et expertise de l'agent |
| `order` | `int` | Ordre de parole en mode `sequential`/`parallel` |
| `model` | `Optional[str]` | Override de modèle — priorité maximale sur `resolve_model()` |
| `speaking_group` | `int` | Groupe de parole (groupes exécutés séquentiellement, ascendant) |
| `speaking_mode` | `str` | `"sequential"` \| `"parallel"` \| `"dependency"` |
| `trust_weight` | `float` | Poids initial (`1.0` par défaut) — écrasé par [[trust_store]] si une valeur persistée existe |
| `wait_for` | `list[str]` | Noms d'agents à attendre (mode `dependency` : tri topologique ; autres modes : assertion bloquante) |
| `role` | `str` | `"regular"` \| `"devil_advocate"` |

## Instances connues

`domains/finance/agents/*.py` : Market Analyst, Equity Analyst, Risk Manager, Portfolio
Manager, Devil's Advocate (tous `speaking_group=0` sauf Devil's Advocate `=1`, tous
`trust_weight=1.0` cold-start, aucun override `model`).

# Log — jarvis-debate wiki

Journal chronologique de toutes les opérations sur le wiki. Append-only : les nouvelles
entrées vont en HAUT du fichier, les entrées passées ne sont jamais modifiées.

---

## 2026-07-03T20:25:00 — DOC UPDATE + PUSH

`README.md` mis à jour : fonctionnalité `timeline` chronologique de `SessionLog` ajoutée à
la liste des fonctionnalités, nouvelle section « Wiki d'architecture » pointant vers ce
vault. `_meta/hot.md` rafraîchie (état des tests, branches, tâches actives).

Contexte : ce commit fait suite à celui de 00:40 (scaffold du vault) et à l'ajout de
`SessionLog.timeline`/timestamps par tour de brainstorm, tous deux committés ensemble sur
une nouvelle branche `dev` (`28ab934`, poussée sur `origin/dev`) — `main` n'a pas bougé.

---

## 2026-07-03T00:40:00 — SCAFFOLD

Vault initialisé (Mode B — GitHub/Repository) directement dans le repo `jarvis-debate`.
Structure créée : `wiki/{modules,components,decisions,dependencies,flows}/`, `.raw/`,
`_meta/`, `_templates/`, `.obsidian/snippets/vault-colors.css`.

Pages initiales écrites à partir de la connaissance directe du codebase (pas d'ingest
depuis `.raw/` — le code source fait foi) :
- 12 pages `wiki/modules/*` (un module Python = une page)
- 3 pages `wiki/components/*` (structures de données réutilisables)
- 4 pages `wiki/decisions/*` (décisions d'architecture déjà prises dans ce projet)
- 3 pages `wiki/dependencies/*`
- 2 pages `wiki/flows/*`

Section « Wiki Knowledge Base » ajoutée à `CLAUDE.md` (existant, non écrasé) pour que les
futures sessions Claude Code sachent consulter `_meta/hot.md` en premier.

`CLAUDE.md` du vault **non créé** séparément : ce repo a déjà un `CLAUDE.md` qui sert le
code (instructions de dev) — le rôle du CLAUDE.md-vault (conventions wiki) est fusionné
dedans plutôt que dupliqué dans un second fichier concurrent.

`git init` **non exécuté** : ce répertoire est déjà un dépôt git (`jarvis-debate`,
remote `origin` déjà configuré) — le vault est versionné dans le même historique que le
code plutôt que dans un dépôt séparé.

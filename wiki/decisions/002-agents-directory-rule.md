---
type: decision
status: active
priority: 2
date: 2026-07-02
owner: ""
due_date: ""
context: "Répertoire agents_/ obsolète trouvé à la racine du projet"
tags: [decision]
created: 2026-07-03
updated: 2026-07-03
---

# ADR-002 : Aucun agent de domaine à la racine du projet

## Contexte

Un répertoire `agents_/` (copie non trackée, obsolète) et un ancien répertoire `agents/`
(tracké git, en cours de suppression) contenaient des agents finance dupliqués à la racine
du projet, alors que `domains/finance/agents/` était déjà la source de vérité active
(`AGENTS_DIR` dans `.env` pointait déjà correctement).

## Décision

Règle stricte, documentée dans `CLAUDE.md` : aucun agent propre à un domaine ne doit être
défini à la racine du projet. Un répertoire `agents/` à la racine, s'il existe, est réservé
à des agents **transverses non spécifiques à un domaine** (recherche, pré-traitement de
données) — jamais à des participants d'un débat.

## Actions

- Suppression de `agents_/` (untracked, copie obsolète).
- `.env.example` : `AGENTS_DIR` documenté avec un exemple pointant vers
  `domains/finance/agents`, plus l'avertissement explicite.
- `CLAUDE.md` : ajout de la section "Règle stricte — emplacement des agents".

## Voir aussi

[[loader]] — `AGENTS_DIR` (variable d'env) est le seul point de configuration qui détermine
d'où les agents sont chargés pour un débat.

---
type: decision
status: active
priority: 1
date: 2026-07-02
owner: ""
due_date: ""
context: "Exigence : agents débattants avec sources de confiance et à jour, économe en tokens"
tags: [decision]
created: 2026-07-03
updated: 2026-07-03
---

# ADR-003 : Recherche web — un seul point d'ancrage, pipeline en 2 appels

## Contexte

Deux contraintes non négociables : (1) fiabilité — sources de confiance, validées
indépendamment ; (2) économie de tokens — interdiction de charger des pages entières ou
d'injecter du bruit, coût borné indépendamment du nombre d'agents/itérations.

## Décision

Nouvelle phase `research`, unique, avant le brainstorming. Pipeline en **exactement 2
appels LLM** par débat (voir [[research]]) :

1. Chercheur (`web_search` + `web_fetch`, domaines de confiance) — échantillonnage forcé
   par consigne : titre/en-tête + 1er paragraphe + 1 paragraphe du milieu + 1 paragraphe
   proche de la fin (jamais le dernier, jamais la page complète) par source.
2. Validateur indépendant (aucun accès web) — filtre les sources non fiables avant
   qu'elles n'atteignent le contexte des agents.

Le briefing résultant est une chaîne de texte injectée une fois (ouverture du brainstorm +
prompt de thèse) — jamais rejouée par agent ni par itération.

## Alternatives considérées et rejetées

- **Outil `web_search` donné directement à chaque agent** — rejeté : multiplierait les
  recherches par agent × itération, romprait l'économie de tokens (les blocs de résultat
  seraient réinjectés à chaque tour via `state.messages`).
- **Point d'ancrage à la phase de planning en plus de l'enrichissement de question** —
  proposé initialement (1er brouillon du plan), remplacé par la phase `research` dédiée
  une fois l'exigence de validation indépendante précisée par l'utilisateur.
- **Extraction déterministe par code (parsing HTML)** — rejetée : nécessiterait une
  dépendance externe (BeautifulSoup ou équivalent), contraire au principe "pas de
  dépendances inutiles" (`CLAUDE.md`). L'échantillonnage ciblé est appliqué par consigne de
  prompt, pas par slicing déterministe.
- **Auto-validation en un seul appel** (chercheur juge lui-même ses sources) — rejetée au
  profit d'un validateur strictement indépendant, pour la fiabilité.

## Conséquences

- `checkpoint.PHASES` gagne `"research"` en première position → `_make_cp` doit
  initialiser `phase="research"` (pas `"brainstorm"`), sinon un débat neuf saute la phase
  (bug identifié et corrigé pendant l'implémentation).
- `Evidence.source_type="web_search"` fonctionne sans changement de schéma (voir
  [[evidence]]).
- `cost_forecast.py` étendu avec 2 lignes constantes — preuve par test que le coût ne
  scale pas avec le nombre d'agents/itérations.

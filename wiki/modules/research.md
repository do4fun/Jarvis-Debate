---
type: module
path: "jarvis/research.py"
status: active
language: python
purpose: "Recherche web économe en tokens pour données actuelles"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: ["debate_config"]
used_by: ["debate"]
tags: [module, core]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/research.py

Voir [[003-web-research-single-anchor]] pour la décision d'architecture complète et
`PLAN_recherche_web.md` (racine du repo) pour le plan détaillé d'origine.

## Pipeline — exactement 2 appels LLM, quel que soit le débat

1. **Chercheur** (`run_research`, appel 1) — outils serveur `web_search_20260209` +
   `web_fetch_20260209`, bornés par `max_uses`/`max_content_tokens`, restreints aux
   domaines de confiance. Consigne stricte : n'extraire QUE titre/en-tête + 1er paragraphe
   + 1 paragraphe du milieu + 1 paragraphe proche de la fin (jamais le dernier, jamais la
   page complète) par source.
2. **Validateur indépendant** (appel 2) — aucun accès web, juge uniquement les extraits de
   l'appel 1. Sortie structurée (`output_config.format` JSON schema). Seules les sources
   `trustworthy: true` passent dans le briefing final.

`format_research_briefing()` assemble le texte final — pur formatage, aucun appel LLM
supplémentaire.

## Pourquoi 2 appels et pas plus

- **Pas d'outil donné aux agents du débat directement** — ça multiplierait les recherches
  par agent × itération et romprait la contrainte d'économie de tokens.
- **Chercheur et validateur séparés** — un contrôle indépendant sert la fiabilité (un
  auto-jugement en un seul appel serait moins fiable qu'une seconde passe dédiée).
- Prouvé par test : `tests/test_integration_wiring.py::test_research_calls_bounded_to_two_regardless_of_agent_count`.

## Parsing

`_parse_researcher_output()` — parsing défensif par regex du format texte
`SOURCE:`/`TITLE:`/`DATE:`/`EXCERPT:`, jamais de structured output pour cet appel (car
incompatible avec `tools=` sur cette version d'API) — entrées malformées silencieusement
ignorées, cohérent avec le style de `argument_graph.py`.

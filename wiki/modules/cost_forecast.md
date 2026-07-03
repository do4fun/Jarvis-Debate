---
type: module
path: "jarvis/cost_forecast.py"
status: active
language: python
purpose: "Estimation tokens/coût/durée avant chaque débat"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["debate"]
tags: [module]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/cost_forecast.py

`compute_forecast(...)` construit un `Forecast` (liste de `ForecastLine`) affiché à
l'utilisateur avant validation du plan (`forecast.format_display()`). Estimations tokens
statiques par type d'appel (`_BASE_TOKENS`), pas de mesure réelle.

## Extension recherche web

Deux lignes ajoutées quand `web_search_enabled=True` : "Recherche web" et "Validation
sources", 1 appel chacune — reflète directement la contrainte d'économie de
[[003-web-research-single-anchor]] (coût constant, pas proportionnel au nombre d'agents).

## Limite connue

Le tarif du web search serveur Anthropic (distinct du prix par token) n'a pas été vérifié
contre la documentation tarifaire actuelle au moment de l'implémentation — les
`_BASE_TOKENS["research"]`/`["research_validate"]` sont des estimations indicatives, pas
un chiffre de facturation vérifié.

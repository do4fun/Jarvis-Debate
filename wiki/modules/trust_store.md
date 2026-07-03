---
type: module
path: "jarvis/trust_store.py"
status: active
language: python
purpose: "Persistance des poids de confiance entre débats"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["debate"]
tags: [module, core]
created: 2026-07-03
updated: 2026-07-03
---

# jarvis/trust_store.py

Deux fichiers JSON sous `rapports/` (overwrite complet à chaque sauvegarde, même
convention que [[checkpoint]]) :

- `rapports/trust_weights.json` — `{"Nom Agent": poids, ...}`. Chargé au début de chaque
  débat (`load_trust_weights()`), surcharge le `trust_weight=1.0` statique des fichiers
  `AgentPersona` s'il existe une valeur apprise.
- `rapports/trust_feedback.json` — feedback différé, clé `"{session_id}:{agent_name}"`.
  `record_feedback()` est un hook public **volontairement non relié à une CLI/UI** en phase
  1 — importable par un script externe pour enregistrer un résultat réel a posteriori.

## Pourquoi un hook externe et pas un calcul automatique

Une décision financière n'a pas de résultat vérifiable immédiat. Plutôt que d'inventer un
proxy (ex: alignement avec le consensus final), le choix a été de laisser `a_i(t)` neutre
(`0.5`) tant qu'aucun feedback réel n'est enregistré — voir
[[001-yin-2025-consensus-formulas]] pour la discussion complète.

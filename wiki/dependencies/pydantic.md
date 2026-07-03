---
type: dependency
path: "requirements.txt"
status: active
language: python
purpose: "Validation du schéma de sortie structuré"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["domains/finance/models.py"]
tags: [dependency]
created: 2026-07-03
updated: 2026-07-03
---

# pydantic

`pydantic>=2.0.0`. Utilisé uniquement pour définir le schéma de sortie de la synthèse
(`ConsensusReport` dans `domains/finance/models.py`) et valider la réponse JSON du modèle
(`model_validate_json`).

## Piège connu — `$ref`/`$defs`/`anyOf`

Le schéma JSON auto-généré par Pydantic utilise `$ref`/`$defs`/`anyOf`, que l'API Anthropic
n'accepte pas dans `output_config.format`. D'où `_inline_refs()` dans [[debate]] (résolution
manuelle des références) ET un `CONSENSUS_REPORT_SCHEMA` écrit à la main en parallèle du
modèle Pydantic dans `domains/finance/models.py` — les deux doivent rester synchronisés
manuellement.

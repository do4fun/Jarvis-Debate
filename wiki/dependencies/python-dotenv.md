---
type: dependency
path: "requirements.txt"
status: active
language: python
purpose: "Chargement .env à deux niveaux (générique + domaine)"
maintainer: ""
last_updated: 2026-07-03
linked_issues: []
depends_on: []
used_by: ["debate_config", "main.py"]
tags: [dependency]
created: 2026-07-03
updated: 2026-07-03
---

# python-dotenv

`python-dotenv>=1.0.0`. Chargé en deux passes dans [[debate_config]] :

1. `.env` générique à la racine du projet (`load_dotenv()`).
2. `.env` du domaine actif — dérivé de `AGENTS_DIR` (`Path(AGENTS_DIR).parent / ".env"`),
   chargé avec `override=True` pour lui permettre de surcharger les valeurs communes
   (ex: `DEFAULT_QUESTIONS` spécifique au domaine finance).

Piège historique : les valeurs multi-lignes non quotées (ex: un tableau JSON étalé sur
plusieurs lignes) ne sont pas parsées correctement par `python-dotenv` — corrigé en
imposant un format JSON sur une seule ligne dans `domains/finance/.env`.

---
type: meta
title: "Hot Cache"
updated: 2026-07-03T00:40:00
---

# Recent Context

## Last Updated
2026-07-03. Vault scaffoldé (Mode B — GitHub/Repository) pour documenter l'architecture de
`jarvis-debate`. Aucun ingest externe : les pages initiales viennent directement de la
connaissance du code acquise pendant les sessions de développement récentes.

## Key Recent Facts
- Le projet vient d'implémenter les formules de consensus pondéré par la confiance
  (Yin 2025 §3.3.4-3.3.5) : `v_i(o)`, `S(o)`, seuil `theta`, mise à jour dynamique `w_i`,
  crédibilité des arguments `C(a_i)`. Voir [[001-yin-2025-consensus-formulas]].
- Une phase de recherche web économe en tokens a été ajoutée (2 appels LLM constants par
  débat, quel que soit le nombre d'agents/itérations). Voir [[003-web-research-single-anchor]].
- Règle stricte : aucun agent de domaine ne doit être défini à la racine du projet — voir
  [[002-agents-directory-rule]] et `CLAUDE.md`.
- Chaque session de débat (`rapports/sessions/{id}_full.json`) a maintenant une `timeline`
  horodatée permettant de reconstruire l'ordre chronologique exact — voir
  [[004-session-timeline-timestamps]].
- 68 tests unitaires passent (`python run_tests.py`).

## Recent Changes
- Created: 12 pages `wiki/modules/*`, 4 pages `wiki/decisions/*`, 3 pages
  `wiki/dependencies/*`, 2 pages `wiki/flows/*`, 3 pages `wiki/components/*`.
- Updated: `CLAUDE.md` (ajout section « Wiki Knowledge Base »).

## Active Threads
- Le domaine finance (`domains/finance/`) n'a pas encore de pages dédiées dans le wiki —
  à faire si le projet ajoute un second domaine (le protocole `jarvis/` prime pour l'instant).
- Aucune page `wiki/components/*` pour les 5 agents finance concrets (market_analyst,
  equity_analyst, risk_manager, portfolio_manager, devil_advocate) — candidats pour un
  futur ingest ciblé si leur logique devient plus complexe.

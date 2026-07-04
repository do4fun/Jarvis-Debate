---
type: meta
title: "Hot Cache"
updated: 2026-07-03T20:25:00
---

# Recent Context

## Last Updated
2026-07-03. Le vault (créé plus tôt aujourd'hui) et le travail de la même session
(horodatage chronologique des sessions) ont été committés ensemble sur une nouvelle
branche `dev` (poussée sur `origin/dev`) — `main` reste inchangé. README.md et cette page
mises à jour en conséquence.

## Key Recent Facts
- Le projet vient d'implémenter les formules de consensus pondéré par la confiance
  (Yin 2025 §3.3.4-3.3.5) : `v_i(o)`, `S(o)`, seuil `theta`, mise à jour dynamique `w_i`,
  crédibilité des arguments `C(a_i)`. Voir [[001-yin-2025-consensus-formulas]].
- Une phase de recherche web économe en tokens a été ajoutée (2 appels LLM constants par
  débat, quel que soit le nombre d'agents/itérations). Voir [[003-web-research-single-anchor]].
- Règle stricte : aucun agent de domaine ne doit être défini à la racine du projet — voir
  [[002-agents-directory-rule]] et `CLAUDE.md`.
- `SessionLog` a maintenant une `timeline` horodatée (un timestamp par appel de phase,
  jamais écrasé) et chaque tour du `brainstorm_thread` porte son propre timestamp —
  reconstruction chronologique complète d'une session. Voir
  [[004-session-timeline-timestamps]].
- Vault Obsidian scaffoldé (Mode B) dans ce même dépôt — voir `CLAUDE.md` § Wiki Knowledge
  Base et README.md § Wiki d'architecture.
- 83 tests unitaires passent, 1 skip attendu (`python run_tests.py`) — inclut désormais
  `tests/test_session_log.py` (timeline) et `tests/test_obsidian_vault.py` (intégrité du
  vault + Obsidian réellement installé/up).
- Branches : `main` (66b29fc, stable) et `dev` (28ab934, en avance de 1 commit —
  timeline + wiki), toutes deux poussées sur origin.

## Recent Changes
- Created: 12 pages `wiki/modules/*`, 4 pages `wiki/decisions/*`, 3 pages
  `wiki/dependencies/*`, 2 pages `wiki/flows/*`, 3 pages `wiki/components/*`,
  `tests/test_obsidian_vault.py`, `tests/test_session_log.py`.
- Updated: `CLAUDE.md` (section « Wiki Knowledge Base »), `README.md` (fonctionnalité
  timeline + section « Wiki d'architecture »), `.gitignore` (exclusion
  `rapports/trust_weights.json`/`trust_feedback.json`).

## Active Threads
- Le domaine finance (`domains/finance/`) n'a pas encore de pages dédiées dans le wiki —
  à faire si le projet ajoute un second domaine (le protocole `jarvis/` prime pour l'instant).
- Aucune page `wiki/components/*` pour les 5 agents finance concrets (market_analyst,
  equity_analyst, risk_manager, portfolio_manager, devil_advocate) — candidats pour un
  futur ingest ciblé si leur logique devient plus complexe.
- `dev` n'a pas encore été mergée dans `main` — en attente de décision utilisateur (PR
  disponible : https://github.com/do4fun/Jarvis-Debate/pull/new/dev).

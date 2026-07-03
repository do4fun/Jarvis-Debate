---
type: flow
status: active
tags: [flow]
created: 2026-07-03
updated: 2026-07-03
---

# Pipeline de débat — flux complet

Orchestré par `_run_single_debate()` ([[debate]]). Chaque phase est checkpointée
([[checkpoint]]) et loguée ([[session_log]]).

```
Étape A — Validation de la question (interactive, utilisateur valide/révise)
       ↓
Phase "research"          ← [[research]] : 2 appels LLM, briefing texte compact
       ↓ (research_briefing injecté)
Phase 0 — Brainstorming    ← thread partagé, DA peut intervenir, orchestrateur modère
       ↓
Étape B — Validation du plan (interactive)
       ↓
Round 1 — Thesis           ← research_briefing injecté ici aussi (agents débattants)
       ↓ (ordre selon speaking_mode : sequential | parallel | dependency)
Round 2 — Antithesis
       ↓
Phase "conflict_detection" ← 1 appel, identifie LE conflit central (toujours supposé exister)
       ↓
Phase "argument_graph"     ← claims + edges support/attack + evidence, puis :
       ↓                     compute_consensus() (v_i, S(o), theta)
       ↓                     argument_credibility() (C(a_i))
Round 3 — Synthesis        ← sortie structurée (output_config.format json_schema)
       ↓
Mise à jour trust_weight   ← w_i(t+1), persisté dans rapports/trust_weights.json
```

## Points d'injection du briefing de recherche web

Le `research_briefing` (texte compact, sources déjà validées) est injecté à exactement
deux endroits : l'ouverture du brainstorming et le prompt de thèse initial. Jamais rejoué
ailleurs — voir [[003-web-research-single-anchor]].

## Gates de phase

Chaque phase optionnelle est gardée par `"<phase>" in config.enabled_phases` — permet à un
domaine de désactiver `conflict_detection`/`argument_graph`/`research` sans toucher au
code.

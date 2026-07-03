---
type: flow
status: active
tags: [flow]
created: 2026-07-03
updated: 2026-07-03
---

# Reprise sur interruption — flux

1. `main.py` détecte un checkpoint non terminé au démarrage
   (`checkpoint.find_latest()` — cherche le fichier le plus récent où `phase != "done"`).
2. Propose la reprise à l'utilisateur ; sinon repart de zéro (nouveau `session_id`).
3. `_run_single_debate` restaure les `AgentState` depuis `cp.agents`
   (`_restore_agents`) et affiche la position de reprise.
4. Chaque phase compare sa position (`phase`, `phase_iteration`, `agent_index`) à
   `checkpoint.PHASES` via `is_agent_done()`/`is_orchestrator_done()` — comparaison
   **positionnelle**, pas par contenu. Les appels déjà faits sont sautés silencieusement
   (affichage `"... (repris)"`).
5. À la fin réussie : `cp.phase = "done"`, sauvegardé, puis le fichier checkpoint est
   supprimé (`cp_delete`) — seul [[session_log]] garde une trace permanente.

## Piège critique déjà rencontré

L'ordre des entrées dans `checkpoint.PHASES` est significatif. Ajouter une phase en tête de
liste (ex: `"research"`, voir [[003-web-research-single-anchor]]) sans mettre à jour le
`phase=` initial fixé dans `_make_cp` (côté `run_debate`) fait sauter silencieusement la
nouvelle phase sur un débat neuf — `is_orchestrator_done` la considère "déjà passée" par
comparaison d'index.

## Ce qui N'est PAS repris automatiquement

La boucle de validation interactive de la question (`_interactive_question_validation`)
n'a pas de checkpointing fin : si interrompue avant que l'utilisateur confirme, elle
recommence entièrement (y compris une éventuelle recherche web) au prochain lancement —
limitation pré-existante, non corrigée par les décisions récentes.

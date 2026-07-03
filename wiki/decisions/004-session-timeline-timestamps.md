---
type: decision
status: active
priority: 3
date: 2026-07-03
owner: ""
due_date: ""
context: "Besoin de reconstruire les conversations dans l'ordre"
tags: [decision]
created: 2026-07-03
updated: 2026-07-03
---

# ADR-004 : Timeline horodatée dans SessionLog + timestamps par tour du brainstorm

## Contexte

`SessionLog.phases` est un dict clé=nom de phase, écrasé si une phase est loguée
plusieurs fois — aucune notion de temps ni de séquence fine pour reconstruire "les
conversations" (au sens propre : le `brainstorm_thread`, la seule vraie conversation
multi-tours du système).

## Décision

Deux ajouts additifs, sans casser la structure existante :

1. [[session_log]] gagne un champ `timeline` — liste `{"phase", "timestamp"}`, un élément
   par appel à `log_phase()` (contrairement à `phases`, jamais écrasée).
2. Chaque tour ajouté au `brainstorm_thread` ([[debate]]) reçoit un `"timestamp"` ISO 8601
   via un nouveau helper `_now()`.

## Alternatives considérées

- **Timestamp sur `DebateCheckpoint`** — rejeté : le checkpoint est un état de reprise
  supprimé après succès, pas un historique ; il ne sert pas la reconstruction
  post-hoc d'une session terminée.
- **Restructurer `phases` en liste au lieu d'un dict** — rejeté : aurait cassé la
  rétrocompatibilité de lecture des logs existants ; `timeline` est additif, `phases`
  reste inchangé en structure.

## Conséquences

`tests/test_session_log.py` (6 tests) vérifie l'ordre, le format ISO, et que les logs
répétés d'une même phase sont tous tracés dans `timeline` (pas seulement le dernier).

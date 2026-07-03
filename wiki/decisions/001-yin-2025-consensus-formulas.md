---
type: decision
status: active
priority: 1
date: 2026-07-01
owner: ""
due_date: ""
context: "Audit de conformité vs Yin 2025 (A multi-agent debate workflow for construction projects)"
tags: [decision]
created: 2026-07-03
updated: 2026-07-03
---

# ADR-001 : Implémenter les formules de consensus Yin 2025

## Contexte

Un audit (3 agents d'exploration en parallèle) a montré que le protocole n'avait qu'une
heuristique de vote ad-hoc (`trust_weighted_scores` : +w/-0.5w par claim), sans seuil de
décision, sans mise à jour du poids de confiance, sans notion de crédibilité des preuves.

## Décision

Implémenter les 5 formules du papier dans trois nouveaux modules protocole
domain-agnostic :

- [[consensus]] — `v_i(o) = sign(Σ λ_k·s_{i,k}(o))`, `S(o) = Σ(w_i·v_i(o))/Σ(w_i)`,
  acceptation `S(o) >= theta`.
- [[evidence]] — `C(a_i) = (1/m)·Σ w_s(e_j)·r(e_j)·h(e_j)`.
- [[trust_store]] — `w_i(t+1) = (1-alpha)·w_i(t) + alpha·a_i(t)`, persisté entre débats.

## Alternatives considérées

- **Portée complète en un passage** (formules + extraction de preuves depuis documents
  externes + audit complet de chaque appel LLM) — rejetée : trop large, priorisée en
  "Phase 1" (formules + config directement liée) vs "Phase 2" (extraction documentaire,
  audit trail complet), reportée.
- **Types de preuve BIM/IFC/CAD/BoQ** (littéraux du papier, contexte construction) —
  rejetés : ce projet cible la finance, pas la construction. `Evidence.source_type` reste
  une chaîne libre domain-agnostic plutôt que des types codés en dur.
- **Signal `a_i(t)` = alignement avec le consensus final** (proxy immédiat) — rejeté au
  profit d'un **hook de feedback externe différé** (`trust_store.record_feedback()`),
  neutre (`0.5`) par défaut : une décision financière n'a pas de résultat vérifiable
  immédiat, un proxy interne aurait été trompeur.

## Conséquences

- `ArgumentGraph.trust_weighted_scores()` conservée (pas supprimée) comme métrique
  consultative bon marché à granularité différente (par claim, pas par option) —
  rétrocompatible avec `cp.vote_scores`.
- Nouveau mode `speaking_mode="dependency"` ajouté en même temps (tri topologique de Kahn)
  pour satisfaire l'exigence de configurabilité "ordre de parole par dépendances strictes".

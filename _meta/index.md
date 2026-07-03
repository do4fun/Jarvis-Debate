---
type: meta
title: "Index"
updated: 2026-07-03T00:40:00
---

# Index — jarvis-debate wiki

Catalogue maître de toutes les pages du wiki. Mise à jour à chaque ingest/scaffold.

## Modules (`wiki/modules/`)

| Page | Rôle |
|---|---|
| [[debate]] | Pipeline principal — orchestration des 7 phases du débat |
| [[debate_config]] | `DebateConfig` dataclass, `resolve_model()`, chargement env |
| [[argument_graph]] | Détection de conflit, `Claim`/`ArgumentEdge`/`ArgumentGraph` |
| [[consensus]] | Formules Yin 2025 : `v_i(o)`, `S(o)`, theta, mise à jour `w_i` |
| [[evidence]] | `Evidence`, décroissance de fraîcheur, crédibilité `C(a_i)` |
| [[research]] | Recherche web économe en tokens (chercheur + validateur) |
| [[trust_store]] | Persistance JSON des poids de confiance entre débats |
| [[checkpoint]] | Reprise sur interruption, `PHASES`, `DebateCheckpoint` |
| [[session_log]] | Log JSON complet par session, timeline chronologique |
| [[cost_forecast]] | Estimation tokens/coût/durée avant chaque débat |
| [[agent_persona]] | `AgentPersona` — contrat que tout agent de domaine doit remplir |
| [[loader]] | Chargement dynamique des agents depuis `AGENTS_DIR` |

## Composants (`wiki/components/`)

| Page | Rôle |
|---|---|
| [[AgentPersona]] | Structure de données réutilisable définissant un agent |
| [[DebateConfig]] | Structure de configuration centrale, domain-agnostic |
| [[ArgumentGraph-data-model]] | Modèle claims + edges + evidence partagé par tout domaine |

## Décisions (`wiki/decisions/`)

| Page | Résumé |
|---|---|
| [[001-yin-2025-consensus-formulas]] | Implémentation des formules de consensus pondéré (v_i, S(o), theta, w_i, C(a_i)) |
| [[002-agents-directory-rule]] | Interdiction des agents de domaine à la racine du projet |
| [[003-web-research-single-anchor]] | Recherche web : un seul point d'ancrage, économe en tokens |
| [[004-session-timeline-timestamps]] | Horodatage pour reconstruire l'ordre chronologique des sessions |

## Dépendances (`wiki/dependencies/`)

| Page | Rôle |
|---|---|
| [[anthropic-sdk]] | Client API Claude — seule dépendance d'exécution LLM |
| [[pydantic]] | Validation du schéma de sortie structuré (`ConsensusReport`) |
| [[python-dotenv]] | Chargement `.env` à deux niveaux (générique + domaine) |

## Flux (`wiki/flows/`)

| Page | Rôle |
|---|---|
| [[debate-pipeline]] | Séquence complète research → brainstorm → thesis → antithesis → conflict_detection → argument_graph → synthesis |
| [[checkpoint-resume-flow]] | Comment une interruption est détectée et reprise sans recalcul |

## Domaine finance (exemple)

Voir `domains/finance/` dans le code — non dupliqué ici tant qu'aucune page ne l'exige
spécifiquement (le wiki documente le **protocole**, le code documente le **domaine**).

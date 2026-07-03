# Jarvis-Debate — CLAUDE.md

## Vision architecturale

Système de débat multi-agents domain-agnostic. Le protocole de débat (rounds, buffers, injection croisée, argument graph) est entièrement séparé du contenu métier.

**Phase actuelle** : domaine finance comme exemple dans `domains/finance/`.

**Phase cible** : n'importe quel domaine peut être branché via un `DebateConfig` personnalisé.

## Architecture

```
jarvis/            — Core domain-agnostic
  debate.py         — Pipeline principal : research → brainstorm → thesis → antithesis →
                       conflict_detection → argument_graph → synthesis
  debate_config.py  — DebateConfig dataclass + load_default_config() + resolve_model()
  research.py       — Recherche web économe en tokens (2 appels LLM : chercheur + validateur
                       indépendant), voir PLAN_recherche_web.md
  argument_graph.py — Conflict detection, ArgumentGraph (claims + evidence + relations support/attack)
  consensus.py       — Consensus pondéré par la confiance (Yin 2025 §3.3.4) : v_i(o), S(o), theta
  evidence.py         — Evidence (preuves), crédibilité des arguments C(a_i) (§3.3.5)
  trust_store.py       — Persistance des poids de confiance entre débats (rapports/trust_weights.json)
  cost_forecast.py       — Estimation tokens/coût/durée avant chaque débat
  session_log.py           — Log complet de chaque étape dans rapports/sessions/
  checkpoint.py               — Reprise sur interruption (PHASES = research, brainstorm, ...)
  agent_persona.py               — AgentPersona : name, model, speaking_group, speaking_mode
                                    ("sequential"|"parallel"|"dependency"), trust_weight, wait_for, role
  loader.py                        — Chargement dynamique des agents depuis AGENTS_DIR

domains/finance/   — Domaine finance (exemple)
  agents/          — 5 agents spécialisés
  models.py        — ConsensusReport schema
  finance_config.py — build_finance_config() → DebateConfig prêt à l'emploi (dans jarvis/)
```

**Règle stricte — emplacement des agents** : aucun agent propre à un domaine ne doit
être défini à la racine du projet. Les agents utilisés dans un débat sont toujours
chargés depuis `domains/<domaine>/agents/` (via `AGENTS_DIR` dans `.env`, cf.
`jarvis/loader.py`). Un éventuel répertoire `agents/` à la racine n'est réservé qu'à
des agents transverses, non spécifiques à un domaine (recherche, pré-traitement de
données) — jamais à des agents participant à un débat.

## Principes de développement

- **Pas d'async** — exécution séquentielle uniquement
- **Pas de dépendances inutiles** — anthropic, pydantic, python-dotenv uniquement
- **Configurable avant tout** — modèles, personas, phases, schéma de sortie = paramètres
- **Séparation domaine / protocole** — le pipeline ne contient jamais de logique métier

## Modèles par défaut

- Agents : `claude-sonnet-4-6`
- Orchestrateur / synthèse : `claude-opus-4-8` avec `thinking: {type: "adaptive"}`
- Modèle surchageable par phase via `DebateConfig.phase_models` (clés : `research`,
  `research_validate`, `brainstorm`, `thesis`, `antithesis`, `conflict_detection`,
  `argument_graph`, `synthesis`, `planning`, `question_analyst`), précédence :
  `AgentPersona.model` > `phase_models[phase]` > modèle global.

## Recherche web

Désactivée par défaut (`DebateConfig.web_search_enabled = False`). Un seul point d'ancrage
dans le pipeline (phase `research`, avant le brainstorming) — voir `jarvis/research.py` et
`PLAN_recherche_web.md` pour l'architecture complète (2 appels LLM, échantillonnage ciblé,
validation indépendante des sources, domaines de confiance configurables).

## Ajouter un nouveau domaine

1. Créer `domains/<domaine>/agents/*.py` avec des `AgentPersona`
2. Créer `domains/<domaine>/models.py` avec le schéma de sortie Pydantic + JSON schema
3. Créer `jarvis/<domaine>_config.py` avec `build_<domaine>_config() -> DebateConfig`, qui
   peuple au minimum `lambda_weights` (critères de stance) et `evidence_source_weights`
   (types de preuve reconnus par le domaine, dont `"web_search"` si la recherche web est
   activée) — `jarvis/finance_config.py` sert de référence
4. Pointer `AGENTS_DIR=domains/<domaine>/agents` dans `.env`
5. Appeler `run_debate(questions, config=build_<domaine>_config())` depuis `main.py`

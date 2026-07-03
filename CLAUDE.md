# Jarvis-Debate — CLAUDE.md

## Vision architecturale

Système de débat multi-agents domain-agnostic. Le protocole de débat (rounds, buffers, injection croisée, argument graph) est entièrement séparé du contenu métier.

**Phase actuelle** : domaine finance comme exemple dans `domains/finance/`.

**Phase cible** : n'importe quel domaine peut être branché via un `DebateConfig` personnalisé.

## Architecture

```
jarvis/            — Core domain-agnostic
  debate.py        — Pipeline principal : brainstorm → thesis → antithesis → argument_graph → synthesis
  debate_config.py — DebateConfig dataclass + load_default_config()
  argument_graph.py — Conflict detection, ArgumentGraph, trust-weighted voting
  session_log.py   — Log complet de chaque étape dans rapports/sessions/
  checkpoint.py    — Reprise sur interruption
  agent_persona.py — AgentPersona : name, model, speaking_group, speaking_mode, trust_weight, wait_for, role
  loader.py        — Chargement dynamique des agents depuis AGENTS_DIR

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

## Ajouter un nouveau domaine

1. Créer `domains/<domaine>/agents/*.py` avec des `AgentPersona`
2. Créer `domains/<domaine>/models.py` avec le schéma de sortie Pydantic + JSON schema
3. Créer `jarvis/<domaine>_config.py` avec `build_<domaine>_config() -> DebateConfig`
4. Pointer `AGENTS_DIR=domains/<domaine>/agents` dans `.env`
5. Appeler `run_debate(questions, config=build_<domaine>_config())` depuis `main.py`

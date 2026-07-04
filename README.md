# Jarvis-Debate

Système de débat multi-agents domain-agnostic avec argument graph, recherche web économe en
tokens, et consensus pondéré par la confiance des agents (Yin 2025).

## Fonctionnalités

- **Pipeline de débat structuré** : recherche web → brainstorming → thèse → antithèse → détection de conflits → argument graph → synthèse
- **Recherche web économe en tokens** : un seul point d'ancrage par débat (2 appels LLM au total, quel que soit le nombre d'agents/itérations), sources restreintes à des domaines de confiance, échantillonnage ciblé (titre/en-tête + 3 paragraphes par source, jamais la page complète), validation indépendante par un rôle spécialisé avant injection dans le débat — voir `PLAN_recherche_web.md`
- **Ordre de parole configurable** : séquentiel, parallèle, ou par dépendances strictes (tri topologique via `wait_for`)
- **Modèle par agent et par phase** : chaque agent peut utiliser un modèle différent (`AgentPersona.model`), et chaque phase du pipeline peut avoir son propre override (`DebateConfig.phase_models`)
- **Argument graph** : détection automatique des conflits, claims avec relations support/attaque et preuves (`Evidence`) citées à l'appui
- **Consensus pondéré par la confiance** (Yin 2025 §3.3.4) : stance par agent `v_i(o)`, score de consensus `S(o)`, seuil d'acceptation `theta` configurable
- **Poids de confiance dynamique et persistant** : `trust_weight` mis à jour après chaque débat (moyenne mobile exponentielle) et conservé entre les sessions dans `rapports/trust_weights.json`
- **Crédibilité des arguments** (§3.3.5) : score `C(a_i)` combinant fiabilité et fraîcheur des preuves citées par les agents
- **Reprise sur interruption** : checkpoint après chaque appel API, y compris la phase de recherche web
- **Log complet et chronologique** : toutes les étapes dans `rapports/sessions/{session_id}_full.json`, avec une `timeline` horodatée (un timestamp par appel de phase, jamais écrasé) permettant de reconstruire l'ordre exact des événements d'une session — y compris tour par tour dans le `brainstorm_thread`

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
# Éditer .env : ajouter ANTHROPIC_API_KEY
```

## Usage

```bash
python main.py "Faut-il acheter des actions Nvidia en ce moment ?"
```

Ou définir `DEFAULT_QUESTIONS` dans `.env`.

## Configurer les agents

Chaque agent est un fichier Python sous `domains/<domaine>/agents/` (jamais à la racine du
projet — voir `CLAUDE.md`, section « Règle stricte — emplacement des agents ») :

```python
from jarvis.agent_persona import AgentPersona

AGENT = AgentPersona(
    name="Mon Agent",
    order=1,
    system_prompt="Vous êtes...",
    speaking_group=0,       # groupe de parole (même groupe = même vague)
    speaking_mode="sequential",  # "sequential" | "parallel" | "dependency"
    trust_weight=1.0,       # poids initial dans le vote pondéré (mis à jour dynamiquement ensuite)
    wait_for=[],            # noms d'agents à attendre avant de parler (utilisé par "dependency")
    role="regular",         # "regular" | "devil_advocate"
    model=None,             # None = résolu via phase_models puis modèle global, ou un modèle explicite
)
```

## Recherche web

Désactivée par défaut. Pour l'activer, dans `.env` :

```bash
WEB_SEARCH_ENABLED=true
WEB_SEARCH_ALLOWED_DOMAINS=reuters.com,bloomberg.com,wsj.com,ft.com,federalreserve.gov,sec.gov,imf.org,bis.org
```

Le domaine finance (`jarvis/finance_config.py`) l'active par défaut avec ces mêmes sources.
Voir `PLAN_recherche_web.md` pour le détail de l'architecture (pipeline en 2 appels,
échantillonnage ciblé, validation indépendante des sources).

## Tests

```bash
python run_tests.py
```

## Wiki d'architecture

Un vault Obsidian (Mode B — GitHub/Repository) documente l'architecture du projet dans ce
même dépôt (`wiki/`, `_meta/`). Ouvrir `c:\dev\jarvis-debate` comme vault dans Obsidian, ou
lire directement `_meta/hot.md` (contexte récent) puis `_meta/index.md` (catalogue complet).
Voir `CLAUDE.md`, section « Wiki Knowledge Base », pour les conventions de mise à jour.

## Ajouter un nouveau domaine

Voir `CLAUDE.md`.

## Structure des rapports

- `rapports/analyses/` — rapport Markdown final
- `rapports/sessions/{id}_full.json` — log complet de toutes les étapes (y compris `research`, `consensus`, `credibility`, `trust_update`)
- `rapports/checkpoints/` — checkpoints (supprimés après succès)
- `rapports/trust_weights.json` — poids de confiance des agents, persistés entre débats
- `rapports/trust_feedback.json` — feedback différé optionnel pour la mise à jour des poids de confiance

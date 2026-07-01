# Jarvis-Debate

Système de débat multi-agents domain-agnostic avec argument graph et vote pondéré par confiance.

## Fonctionnalités

- **Pipeline de débat structuré** : brainstorming → thèse → antithèse → détection de conflits → argument graph → synthèse
- **Ordre de parole configurable** : séquentiel, parallèle, avec dépendances entre agents
- **Modèle par agent** : chaque agent peut utiliser un modèle différent
- **Argument graph** : détection automatique des conflits, claims avec relations support/attaque
- **Vote pondéré par confiance** : `trust_weight` par agent influence l'arbitrage final
- **Reprise sur interruption** : checkpoint après chaque appel API
- **Log complet** : toutes les étapes dans `rapports/sessions/{session_id}_full.json`

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

Chaque agent est un fichier Python dans `agents/` :

```python
from jarvis.agent_persona import AgentPersona

AGENT = AgentPersona(
    name="Mon Agent",
    order=1,
    system_prompt="Vous êtes...",
    speaking_group=0,       # groupe de parole (même groupe = même vague)
    speaking_mode="sequential",  # "sequential" | "parallel"
    trust_weight=1.0,       # poids dans le vote pondéré
    wait_for=[],            # noms d'agents à attendre avant de parler
    role="regular",         # "regular" | "devil_advocate"
    model=None,             # None = modèle global, ou "claude-haiku-4-5-20251001"
)
```

## Ajouter un nouveau domaine

Voir `CLAUDE.md`.

## Structure des rapports

- `rapports/analyses/` — rapport Markdown final
- `rapports/sessions/{id}_full.json` — log complet de toutes les étapes
- `rapports/checkpoints/` — checkpoints (supprimés après succès)

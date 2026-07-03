# Recherche web pour les agents du débat (sources à jour, économe en tokens)

> Statut : **implémenté**. Ce document décrit le design final tel que codé (voir « Fichiers
> livrés » en fin de document). La toute première version de ce plan proposait un point
> d'ancrage unique dans l'appel d'enrichissement de la question ; elle a été remplacée par
> la conception ci-dessous, plus fidèle aux exigences de fiabilité (validation indépendante
> des sources) et d'échantillonnage ciblé demandées explicitement par l'utilisateur.

## Contexte

Les agents du débat raisonnent uniquement à partir de leurs connaissances d'entraînement,
sans accès à des données actuelles. Deux contraintes fortes, non négociables :

1. **Fiabilité** — les agents ne doivent débattre qu'à partir de sources de confiance et à
   jour, validées indépendamment (pas seulement auto-déclarées par le processus qui les a
   trouvées).
2. **Économie de tokens** — interdiction de charger des pages entières ou d'injecter du bruit
   textuel inutile dans le contexte. Coût borné à un petit nombre d'appels LLM **constant**,
   indépendant du nombre d'agents et d'itérations du débat.

## Architecture retenue

### Un seul point d'ancrage dans le pipeline : la phase `research`

Nouvelle phase, insérée **avant le brainstorming**, juste après la validation interactive de
la question. Elle produit un court **briefing texte** (quelques puces sourcées), injecté une
seule fois dans :
- le prompt d'ouverture du brainstorming (`_build_orchestrator_brainstorm_open_prompt`),
- le prompt de la thèse initiale (`_build_round1_prompt`), là où les agents du débat le
  consomment directement.

Le briefing est une chaîne de caractères simple — jamais rejoué dans l'historique de
conversation d'un agent (contrairement à ce qui se passerait si l'outil `web_search` était
donné directement à chaque agent à chaque tour). Le coût de la recherche est donc payé
**une fois par débat**, pas une fois par agent × itération.

### Pipeline en 2 appels LLM au total (`jarvis/research.py`)

**Appel 1 — Chercheur** (`web_search` + `web_fetch`, domaines de confiance uniquement) :
le modèle cherche, puis récupère au plus `web_fetch_max_uses` pages parmi les plus
prometteuses. Pour **chaque** page récupérée, il lui est interdit de résumer ou citer autre
chose que :
- le titre et l'en-tête,
- le premier paragraphe (contexte),
- **un** paragraphe représentatif du milieu du texte (substance),
- **un** paragraphe proche de la fin — **jamais le tout dernier** (souvent un
  disclaimer/call-to-action, pas du contenu substantiel).

Cet échantillonnage (demandé explicitement par l'utilisateur) limite mécaniquement le volume
de texte reproduit par source, quelle que soit la longueur réelle de la page. `max_content_tokens`
sur l'outil `web_fetch` agit en garde-fou supplémentaire (borne dure côté serveur).

**Appel 2 — Validateur indépendant** (aucun accès web, uniquement les extraits de l'appel 1) :
un rôle spécialisé et **distinct** du chercheur juge, pour chaque source, si le domaine est
réputé/autoritaire, si la donnée est raisonnablement datée, et si le contenu est pertinent —
sans jamais voir la page complète. Sortie structurée (`output_config.format` JSON schema,
même mécanisme que la synthèse). Seules les sources jugées `trustworthy: true` sont retenues
pour le briefing final ; les autres sont journalisées mais exclues du contexte des agents.

Séparer chercheur et validateur en deux appels indépendants (plutôt qu'un auto-jugement en un
seul appel) sert directement l'exigence de fiabilité : un contrôle indépendant détecte des
biais que le chercheur, focalisé sur la découverte, pourrait laisser passer.

L'assemblage final du briefing (`format_research_briefing`) est du pur formatage de chaînes —
aucun appel LLM supplémentaire.

## Configuration (`jarvis/debate_config.py`)

```python
web_search_enabled: bool = False              # opt-in, désactivé par défaut
web_search_max_uses: int = 3                  # recherches (appel 1)
web_fetch_max_uses: int = 2                   # pages récupérées (appel 1)
web_fetch_max_content_tokens: int = 3000      # garde-fou dur côté serveur
web_search_allowed_domains: list[str] = []    # peuplé par le domaine
web_search_blocked_domains: list[str] = []
researcher_prompt: str = ""                   # vide → fallback jarvis/research.py (générique)
source_validator_prompt: str = ""             # idem
```
Variables d'environnement correspondantes dans `.env.example` (`WEB_SEARCH_ENABLED`,
`WEB_SEARCH_MAX_USES`, `WEB_FETCH_MAX_USES`, `WEB_FETCH_MAX_CONTENT_TOKENS`,
`WEB_SEARCH_ALLOWED_DOMAINS`). Modèles utilisés pour les 2 appels résolus via le mécanisme
existant `resolve_model(config, "research"/"research_validate", ...)` — surchargeable par
domaine via `phase_models` sans toucher au code.

Domaine finance (`jarvis/finance_config.py`) : activé par défaut, sources de confiance =
reuters.com, bloomberg.com, wsj.com, ft.com, federalreserve.gov, sec.gov, imf.org, bis.org ;
`evidence_source_weights["web_search"] = 0.7` (le formalisme de crédibilité C(a_i) existant
peut donc noter une preuve citée par un agent comme provenant du web).

## Traçabilité et reprise sur interruption

- `SessionLog.log_research(briefing, findings)` — journalise le briefing final **et** la
  liste complète des sources trouvées (validées ou rejetées, avec la raison du validateur).
- `DebateCheckpoint.research_briefing` / `research_findings` — la phase `research` est
  checkpointée comme les autres phases orchestrateur (`is_orchestrator_done(cp, "research")`) :
  sur reprise après interruption, aucune nouvelle recherche n'est déclenchée.
- `checkpoint.PHASES` et `DebateConfig.enabled_phases` gagnent `"research"` en toute première
  position (avant `"brainstorm"`) — les deux gate-checks existants (`"research" in
  config.enabled_phases` et `config.web_search_enabled`) permettent de désactiver la
  fonctionnalité indépendamment via la config ou via l'env.

## Estimation de coût (`jarvis/cost_forecast.py`)

Deux lignes ajoutées au forecast affiché avant chaque débat (« Recherche web », « Validation
sources »), avec des estimations tokens indicatives. Le point clé, vérifié par test
(`tests/test_integration_wiring.py::test_research_calls_bounded_to_two_regardless_of_agent_count`) :
le nombre d'appels de recherche reste **exactement 2**, que le débat ait 2 ou 8 agents, 1 ou 3
itérations par phase — la preuve chiffrée de la contrainte d'économie de tokens.

## Fichiers livrés

- `jarvis/research.py` (nouveau) — `SourceFinding`, `build_search_tools`,
  `_parse_researcher_output`, `format_research_briefing`, `run_research`.
- `jarvis/debate_config.py` — nouveaux champs + variables d'env.
- `jarvis/checkpoint.py` — phase `"research"` + champs `research_briefing`/`research_findings`.
- `jarvis/session_log.py` — `log_research`.
- `jarvis/debate.py` — câblage de la phase, injection du briefing dans brainstorm-open et
  thesis, correction du `phase` initial du checkpoint (`_make_cp`) pour que la phase
  `research` ne soit pas sautée sur un débat neuf.
- `jarvis/cost_forecast.py` — lignes de coût recherche web.
- `jarvis/finance_config.py` — activation + sources de confiance du domaine finance.
- `.env.example` — documentation des nouvelles variables.
- `tests/test_research.py`, `tests/test_integration_wiring.py` — 20 tests (parsing,
  formatage, tool specs, ordre des phases, non-scalabilité du coût avec le nombre d'agents).

## Vérification

1. `python run_tests.py` — 62 tests passent (dont les 20 nouveaux dédiés à cette fonctionnalité).
2. **Bout en bout** (nécessite une clé API valide) : `python main.py "<question test>"` avec
   `WEB_SEARCH_ENABLED=true`, vérifier que :
   - `[Recherche web]...` s'affiche avant `[Brainstorming]` dans la sortie console.
   - `rapports/sessions/{session_id}_full.json` contient une section `"research"` avec
     `briefing` (texte) et `findings` (liste de sources, certaines `trustworthy: true`,
     d'autres `false` avec une `validator_reason`).
   - Le texte de thèse des agents (Round 1) référence les faits du briefing.
   - Interrompre après la phase `research` puis reprendre ne redéclenche pas de recherche
     (`[Recherche web]... (repris)`).
3. **Non-régression** : avec `WEB_SEARCH_ENABLED=false` (défaut), comportement strictement
   identique à avant — aucun outil envoyé, `run_research` retourne `("", [])` immédiatement.

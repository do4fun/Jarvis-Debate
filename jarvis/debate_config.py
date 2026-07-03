from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os

from dotenv import load_dotenv

load_dotenv()

# Le domaine actif (AGENTS_DIR, ex: domains/finance/agents) peut fournir son
# propre .env — chargé après le générique, override=True pour lui permettre
# de surcharger les valeurs communes (DEFAULT_QUESTIONS, etc.).
_agents_dir = Path(__file__).parent.parent / os.getenv("AGENTS_DIR", "agents")
_domain_env = _agents_dir.parent / ".env"
if _domain_env.is_file():
    load_dotenv(dotenv_path=_domain_env, override=True)


@dataclass
class DebateConfig:
    agent_model: str
    orchestrator_model: str
    iterations_brainstorming: int = 1
    iterations_thesis: int = 1
    iterations_antithesis: int = 1
    iterations_synthesis: int = 1
    enabled_phases: list[str] = field(default_factory=lambda: [
        "research", "brainstorm", "thesis", "antithesis",
        "conflict_detection", "argument_graph", "synthesis",
    ])
    question_analyst_prompt: str = ""
    brainstorm_moderator_prompt: str = ""
    planner_prompt: str = ""
    conflict_detector_prompt: str = ""
    synthesis_prompt: str = ""
    output_schema: dict = field(default_factory=dict)
    output_pydantic_model: Optional[type] = None

    # Recherche web économe en tokens (jarvis/research.py) — désactivée par défaut.
    web_search_enabled: bool = False
    web_search_max_uses: int = 3
    web_fetch_max_uses: int = 2
    web_fetch_max_content_tokens: int = 3000
    web_search_allowed_domains: list[str] = field(default_factory=list)
    web_search_blocked_domains: list[str] = field(default_factory=list)
    # Prompts vides → fallback sur les valeurs par défaut domain-agnostic de jarvis/research.py
    researcher_prompt: str = ""
    source_validator_prompt: str = ""

    # Consensus pondéré par la confiance (Yin 2025, §3.3.4) — v_i(o), S(o), theta
    theta: float = 0.65
    # Mise à jour dynamique du poids de confiance (§3.3.4) — w_i(t+1) = (1-alpha)*w_i(t) + alpha*a_i(t)
    alpha: float = 0.2
    # Poids lambda_k par critère pour la stance v_i(o) — peuplé par le domaine, vide au niveau protocole
    lambda_weights: dict[str, float] = field(default_factory=dict)
    # Poids w_s(e_j) par type de source pour la crédibilité C(a_i) — peuplé par le domaine
    evidence_source_weights: dict[str, float] = field(default_factory=dict)
    # Override de modèle par phase — clés: brainstorm, thesis, antithesis, conflict_detection,
    # argument_graph, synthesis, planning, question_analyst. Précédence: persona.model > ceci > global.
    phase_models: dict[str, str] = field(default_factory=dict)


def resolve_model(
    config: "DebateConfig",
    phase: str,
    persona_model: Optional[str],
    is_orchestrator: bool,
) -> str:
    """Précédence de résolution du modèle : persona.model > config.phase_models[phase] >
    (orchestrator_model si appel orchestrateur, sinon agent_model)."""
    if persona_model:
        return persona_model
    override = config.phase_models.get(phase, "")
    if override:
        return override
    return config.orchestrator_model if is_orchestrator else config.agent_model


def _split_env_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def load_default_config() -> DebateConfig:
    _phase_names = (
        "research", "research_validate", "brainstorm", "thesis", "antithesis",
        "conflict_detection", "argument_graph", "synthesis", "planning", "question_analyst",
    )
    return DebateConfig(
        agent_model=os.getenv("AGENT_MODEL", "claude-sonnet-4-6"),
        orchestrator_model=os.getenv("ORCHESTRATOR_MODEL", "claude-opus-4-8"),
        iterations_brainstorming=max(1, int(os.getenv("ITERATIONS_BRAINSTORMING", "1"))),
        iterations_thesis=max(1, int(os.getenv("ITERATIONS_THESIS", "1"))),
        iterations_antithesis=max(1, int(os.getenv("ITERATIONS_ANTITHESIS", "1"))),
        iterations_synthesis=max(1, int(os.getenv("ITERATIONS_SYNTHESIS", "1"))),
        theta=float(os.getenv("CONSENSUS_THETA", "0.65")),
        alpha=float(os.getenv("TRUST_ALPHA", "0.2")),
        phase_models={
            phase: os.getenv(f"MODEL_{phase.upper()}", "")
            for phase in _phase_names
            if os.getenv(f"MODEL_{phase.upper()}")
        },
        web_search_enabled=os.getenv("WEB_SEARCH_ENABLED", "").strip().lower() in ("1", "true", "yes"),
        web_search_max_uses=int(os.getenv("WEB_SEARCH_MAX_USES", "3")),
        web_fetch_max_uses=int(os.getenv("WEB_FETCH_MAX_USES", "2")),
        web_fetch_max_content_tokens=int(os.getenv("WEB_FETCH_MAX_CONTENT_TOKENS", "3000")),
        web_search_allowed_domains=_split_env_list(os.getenv("WEB_SEARCH_ALLOWED_DOMAINS", "")),
        web_search_blocked_domains=_split_env_list(os.getenv("WEB_SEARCH_BLOCKED_DOMAINS", "")),
    )

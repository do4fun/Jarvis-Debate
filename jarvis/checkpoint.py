"""
Checkpoint / resume pour le pipeline de débat.

Sauvegarde l'état complet après chaque appel API réussi.
En cas de crash, le prochain lancement détecte le fichier et propose de reprendre.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

CHECKPOINTS_DIR = Path(__file__).parent.parent / "rapports" / "checkpoints"

# Ordre des phases dans le pipeline
PHASES = ["brainstorm", "planning", "thesis", "antithesis",
          "conflict_detection", "argument_graph", "synthesis"]


@dataclass
class AgentSnapshot:
    name: str
    messages: list[dict] = field(default_factory=list)
    brainstorm: str = ""
    thesis: str = ""
    antithesis: str = ""


@dataclass
class DebateCheckpoint:
    session_id: str
    questions: list[str]
    mode: str                      # "concurrent" | "sequential"
    n_debates: int
    debate_index: int              # débat courant (mode séquentiel)

    # Position courante dans le pipeline
    phase: str                     # voir PHASES + "done"
    phase_iteration: int           # itération courante au sein de la phase
    agent_index: int               # index agent courant dans la phase

    # Résultats accumulés
    plan: str = ""
    agents: list[AgentSnapshot] = field(default_factory=list)
    brainstorm_thread: list[dict] = field(default_factory=list)  # thread partagé du brainstorming
    previous_report: Optional[dict] = None   # rapport du débat précédent (mode séquentiel)
    synthesis_report: Optional[dict] = None  # rapport de synthèse du débat courant

    # Questions confirmées après validation utilisateur (Étape A)
    confirmed_questions: list[str] = field(default_factory=list)

    # Snapshot de configuration (validation à la reprise)
    agent_model: str = ""
    orchestrator_model: str = ""
    argument_graph_data: Optional[dict] = None
    vote_scores: Optional[dict] = None

    # Consensus/crédibilité (Yin 2025 §3.3.4-3.3.5) et garde d'idempotence pour la mise à
    # jour du poids de confiance (pas de phase dédiée dans PHASES pour ce dernier)
    consensus_data: Optional[dict] = None
    credibility_scores: Optional[dict] = None
    trust_updated: bool = False


# ── Persistance ───────────────────────────────────────────────────────────────

def _path(session_id: str) -> Path:
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    return CHECKPOINTS_DIR / f"checkpoint_{session_id}.json"


def save(cp: DebateCheckpoint) -> None:
    data = asdict(cp)
    _path(cp.session_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _deserialize(data: dict) -> DebateCheckpoint:
    agents = [AgentSnapshot(**a) for a in data.pop("agents", [])]
    known = {f.name for f in DebateCheckpoint.__dataclass_fields__.values()}
    data = {k: v for k, v in data.items() if k in known}
    cp = DebateCheckpoint(**data)
    cp.agents = agents
    return cp


def load(session_id: str) -> Optional[DebateCheckpoint]:
    p = _path(session_id)
    if not p.exists():
        return None
    return _deserialize(json.loads(p.read_text(encoding="utf-8")))


def delete(session_id: str) -> None:
    p = _path(session_id)
    if p.exists():
        p.unlink()


def find_latest() -> Optional[DebateCheckpoint]:
    """Retourne le checkpoint le plus récent (non terminé), ou None."""
    if not CHECKPOINTS_DIR.exists():
        return None
    files = sorted(CHECKPOINTS_DIR.glob("checkpoint_*.json"), reverse=True)
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("phase") != "done":
                return _deserialize(data)
        except Exception:
            continue
    return None


# ── Helpers positionnels ──────────────────────────────────────────────────────

def phase_index(phase: str) -> int:
    try:
        return PHASES.index(phase)
    except ValueError:
        return len(PHASES)  # "done" → après tout


def is_agent_done(cp: DebateCheckpoint, phase: str, iteration: int, agent_idx: int) -> bool:
    """Vrai si cet appel est déjà dans le checkpoint (à sauter lors de la reprise)."""
    pi = phase_index(phase)
    cp_pi = phase_index(cp.phase)
    if pi < cp_pi:
        return True
    if pi > cp_pi:
        return False
    # Même phase
    if iteration < cp.phase_iteration:
        return True
    if iteration > cp.phase_iteration:
        return False
    # Même itération
    return agent_idx <= cp.agent_index


def is_orchestrator_done(cp: DebateCheckpoint, phase: str, iteration: int = 0) -> bool:
    """Vrai si cet appel orchestrateur est déjà dans le checkpoint."""
    pi = phase_index(phase)
    cp_pi = phase_index(cp.phase)
    if pi < cp_pi:
        return True
    if pi > cp_pi:
        return False
    return iteration <= cp.phase_iteration

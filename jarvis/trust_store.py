"""
Persistance JSON du poids de confiance des agents et du feedback différé.

Même convention que checkpoint.py : fichiers sous rapports/, overwrite complet à chaque
sauvegarde (pas d'append).
"""

import json
from pathlib import Path
from typing import Optional

TRUST_WEIGHTS_PATH = Path(__file__).parent.parent / "rapports" / "trust_weights.json"
TRUST_FEEDBACK_PATH = Path(__file__).parent.parent / "rapports" / "trust_feedback.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_trust_weights() -> dict[str, float]:
    return _load_json(TRUST_WEIGHTS_PATH)


def save_trust_weights(weights: dict[str, float]) -> None:
    _save_json(TRUST_WEIGHTS_PATH, weights)


def record_feedback(session_id: str, agent_name: str, accuracy: float) -> None:
    """Hook public pour enregistrer un feedback différé (accuracy ∈ [0,1])."""
    data = _load_json(TRUST_FEEDBACK_PATH)
    data[f"{session_id}:{agent_name}"] = accuracy
    _save_json(TRUST_FEEDBACK_PATH, data)


def get_feedback(session_id: str, agent_name: str) -> Optional[float]:
    return _load_json(TRUST_FEEDBACK_PATH).get(f"{session_id}:{agent_name}")


def resolve_accuracy_signals(session_id: str, agent_names: list[str]) -> dict[str, float]:
    """a_i(t) : feedback enregistré si présent, sinon 0.5 (neutre)."""
    data = _load_json(TRUST_FEEDBACK_PATH)
    return {name: data.get(f"{session_id}:{name}", 0.5) for name in agent_names}

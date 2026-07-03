import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.argument_graph import ArgumentGraph
    from jarvis.consensus import ConsensusResult


SESSIONS_DIR = Path(__file__).parent.parent / "rapports" / "sessions"


class SessionLog:
    def __init__(self, session_id: str) -> None:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.path = SESSIONS_DIR / f"{session_id}_full.json"
        self._data: dict = {"session_id": session_id, "phases": {}}

    def log_phase(self, phase: str, data: Any) -> None:
        self._data["phases"][phase] = data
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def log_brainstorm(self, thread: list[dict]) -> None:
        self.log_phase("brainstorm", thread)

    def log_plan(self, plan: str) -> None:
        self.log_phase("plan", plan)

    def log_theses(self, agent_theses: dict[str, str]) -> None:
        self.log_phase("thesis", agent_theses)

    def log_antitheses(self, agent_antitheses: dict[str, str]) -> None:
        self.log_phase("antithesis", agent_antitheses)

    def log_conflict(self, topic: str) -> None:
        self.log_phase("conflict_detection", {"topic": topic})

    def log_argument_graph(self, graph: "ArgumentGraph") -> None:
        self.log_phase("argument_graph", asdict(graph))

    def log_vote_scores(self, scores: dict[str, float]) -> None:
        self.log_phase("vote_scores", scores)

    def log_synthesis(self, report: dict) -> None:
        self.log_phase("synthesis", report)

    def log_consensus(self, consensus: "ConsensusResult") -> None:
        self.log_phase("consensus", asdict(consensus))

    def log_credibility(self, credibility: dict[str, float]) -> None:
        self.log_phase("credibility", credibility)

    def log_trust_update(
        self,
        old_weights: dict[str, float],
        new_weights: dict[str, float],
        accuracy_signals: dict[str, float],
    ) -> None:
        self.log_phase("trust_update", {
            "before": old_weights,
            "after": new_weights,
            "accuracy_signal": accuracy_signals,
        })

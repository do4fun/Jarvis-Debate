from dataclasses import dataclass, field
from typing import Optional
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DebateConfig:
    agent_model: str
    orchestrator_model: str
    iterations_brainstorming: int = 1
    iterations_thesis: int = 1
    iterations_antithesis: int = 1
    iterations_synthesis: int = 1
    enabled_phases: list[str] = field(default_factory=lambda: [
        "brainstorm", "thesis", "antithesis", "conflict_detection", "argument_graph", "synthesis"
    ])
    question_analyst_prompt: str = ""
    brainstorm_moderator_prompt: str = ""
    planner_prompt: str = ""
    conflict_detector_prompt: str = ""
    synthesis_prompt: str = ""
    output_schema: dict = field(default_factory=dict)
    output_pydantic_model: Optional[type] = None


def load_default_config() -> DebateConfig:
    return DebateConfig(
        agent_model=os.getenv("AGENT_MODEL", "claude-sonnet-4-6"),
        orchestrator_model=os.getenv("ORCHESTRATOR_MODEL", "claude-opus-4-8"),
        iterations_brainstorming=max(1, int(os.getenv("ITERATIONS_BRAINSTORMING", "1"))),
        iterations_thesis=max(1, int(os.getenv("ITERATIONS_THESIS", "1"))),
        iterations_antithesis=max(1, int(os.getenv("ITERATIONS_ANTITHESIS", "1"))),
        iterations_synthesis=max(1, int(os.getenv("ITERATIONS_SYNTHESIS", "1"))),
    )

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentPersona:
    name: str
    system_prompt: str
    order: int = 0
    model: Optional[str] = None
    speaking_group: int = 0
    speaking_mode: str = "sequential"
    trust_weight: float = 1.0
    wait_for: list[str] = field(default_factory=list)
    role: str = "regular"

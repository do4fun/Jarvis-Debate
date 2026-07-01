from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FinalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NO_TRADE = "NO_TRADE"


class ConsensusReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conviction_score: float = Field(ge=0.0, le=1.0)
    major_agreements: list[str]
    irreconcilable_differences: list[str]
    final_action: FinalAction
    stop_loss_limit_price: Optional[float] = None


# Schéma JSON manuel — évite anyOf/oneOf/$ref/$defs générés par Pydantic,
# incompatibles avec output_config.format de l'API Anthropic.
CONSENSUS_REPORT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "conviction_score",
        "major_agreements",
        "irreconcilable_differences",
        "final_action",
        "stop_loss_limit_price",
    ],
    "properties": {
        "conviction_score": {
            "type": "number",
            "description": "Score de conviction global entre 0.0 (aucune conviction) et 1.0 (conviction maximale)",
        },
        "major_agreements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Points de consensus entre les analystes",
        },
        "irreconcilable_differences": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Désaccords fondamentaux non résolus entre les analystes",
        },
        "final_action": {
            "type": "string",
            "enum": ["BUY", "SELL", "HOLD", "NO_TRADE"],
            "description": "Recommandation directionnelle : BUY (augmenter l'exposition), SELL (réduire), HOLD (maintenir), NO_TRADE (pas de conviction suffisante)",
        },
        "stop_loss_limit_price": {
            "type": "number",
            "description": "Niveau de prix ou d'indice seuil. Retourner 0 si non applicable.",
        },
    },
}

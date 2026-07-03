"""
Analyse prévisionnelle des coûts, tokens et temps par phase de débat.
Toutes les estimations sont indicatives — les tokens réels varient selon
la longueur des questions et des réponses des agents.
"""

from dataclasses import dataclass

# ── Tarification (USD / million de tokens) ────────────────────────────────────
# Source : tarifs publics Anthropic au 2026-06-29
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.00,  5.00),
    "claude-haiku-4-5":          (1.00,  5.00),
    "claude-sonnet-4-6":         (3.00, 15.00),
    "claude-sonnet-3-5":         (3.00, 15.00),
    "claude-opus-4-8":           (5.00, 25.00),
    "claude-opus-4-6":           (5.00, 25.00),
}
_DEFAULT_PRICING = (3.00, 15.00)

# ── Estimation tokens par appel (input, output) ───────────────────────────────
# Les valeurs "input" des phases tardives grossissent avec N agents car
# chaque agent injecte le contexte des autres dans son fil.
_BASE_TOKENS: dict[str, tuple[int, int]] = {
    "brainstorm_init":   (  600, 1000),
    "brainstorm_refine": ( 1600,  800),
    "planning":          ( 5500,  700),   # agrège tous les brainstorms
    "thesis_init":       ( 2000, 1200),
    "thesis_refine":     ( 2600, 1000),
    "antithesis_init":   ( 5000, 1000),   # voit les N-1 thèses
    "antithesis_refine": ( 5200,  800),
    "synthesis_init":    (11500, 1000),   # log complet du débat
    "synthesis_refine":  ( 2000, 1000),
    "research":          ( 1200,  800),   # web_search + web_fetch — extraits ciblés seulement
    "research_validate": (  800,  400),   # validation des sources (extraits seuls, pas de web)
}

# Durée estimée par appel (secondes)
_SECONDS_AGENT        = 6
_SECONDS_ORCHESTRATOR = 18


# ── Structures de données ─────────────────────────────────────────────────────

@dataclass
class ForecastLine:
    phase: str
    agent_type: str       # "Agent" | "Orchestrateur"
    calls: int
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    seconds: int


@dataclass
class Forecast:
    lines: list[ForecastLine]
    n_agents: int
    n_questions: int
    mode: str             # "concurrent" | "sequential"
    n_debates: int

    @property
    def total_calls(self) -> int:
        return sum(l.calls for l in self.lines)

    @property
    def total_input_tokens(self) -> int:
        return sum(l.input_tokens for l in self.lines)

    @property
    def total_output_tokens(self) -> int:
        return sum(l.output_tokens for l in self.lines)

    @property
    def total_cost(self) -> float:
        return sum(l.cost_usd for l in self.lines)

    @property
    def total_seconds(self) -> int:
        return sum(l.seconds for l in self.lines)

    def format_display(self) -> str:
        mins, secs = divmod(self.total_seconds, 60)
        duration = f"{mins}m {secs:02d}s" if mins else f"{secs}s"

        mode_label = (
            f"{self.n_questions} question(s) — mode {self.mode}"
            if self.n_questions > 1
            else "1 question"
        )
        if self.mode == "sequential" and self.n_questions > 1:
            mode_label += f" → {self.n_debates} débat(s)"

        header = (
            f"\n{'─'*66}\n"
            f"  ANALYSE PRÉVISIONNELLE\n"
            f"{'─'*66}\n"
            f"  Agents : {self.n_agents}  |  {mode_label}\n"
            f"  Appels total : {self.total_calls}  |  Durée estimée : ~{duration}\n"
        )

        col_w = [22, 14, 7, 10, 10, 9]
        sep = "  " + "-" * (sum(col_w) + len(col_w) * 3 - 1)
        head_row = _row(["Phase", "Type d'agent", "Appels", "Tokens →", "Tokens ←", "Coût $"], col_w)

        rows = [header, sep, head_row, sep]
        for l in self.lines:
            rows.append(_row([
                l.phase,
                l.agent_type,
                str(l.calls),
                f"{l.input_tokens:,}",
                f"{l.output_tokens:,}",
                f"${l.cost_usd:.3f}",
            ], col_w))

        rows.append(sep)
        rows.append(_row([
            "TOTAL",
            "",
            str(self.total_calls),
            f"{self.total_input_tokens:,}",
            f"{self.total_output_tokens:,}",
            f"${self.total_cost:.3f}",
        ], col_w))
        rows.append(f"{'─'*66}")
        rows.append(f"  * Estimations indicatives — tokens réels varient selon les réponses.")

        return "\n".join(rows)


def _row(cells: list[str], widths: list[int]) -> str:
    padded = [c.ljust(w)[:w] for c, w in zip(cells, widths)]
    return "  " + "   ".join(padded)


def _pricing(model: str) -> tuple[float, float]:
    for key, val in MODEL_PRICING.items():
        if key in model:
            return val
    return _DEFAULT_PRICING


def _cost(input_tok: int, output_tok: int, model: str) -> float:
    price_in, price_out = _pricing(model)
    return (input_tok * price_in + output_tok * price_out) / 1_000_000


# ── Calcul prévisionnel ───────────────────────────────────────────────────────

def compute_forecast(
    n_agents: int,
    n_questions: int,
    mode: str,
    agent_model: str,
    orchestrator_model: str,
    iter_brainstorm: int,
    iter_thesis: int,
    iter_antithesis: int,
    iter_synthesis: int,
    web_search_enabled: bool = False,
) -> Forecast:
    n_debates = n_questions if mode == "sequential" else 1
    lines: list[ForecastLine] = []

    def add(phase: str, agent_type: str, calls: int, model: str, tok_key: str) -> None:
        inp, out = _BASE_TOKENS[tok_key]
        total_inp = inp * calls
        total_out = out * calls
        secs = calls * (_SECONDS_ORCHESTRATOR if agent_type == "Orchestrateur" else _SECONDS_AGENT)
        lines.append(ForecastLine(
            phase=phase,
            agent_type=agent_type,
            calls=calls,
            model=_short_model(model),
            input_tokens=total_inp,
            output_tokens=total_out,
            cost_usd=_cost(total_inp, total_out, model),
            seconds=secs,
        ))

    per_debate_calls: list[tuple] = []

    # Recherche web (avant brainstorming) — 2 appels au total, indépendant du nb d'agents
    if web_search_enabled:
        per_debate_calls.append(("Recherche web", "Orchestrateur", 1, orchestrator_model, "research"))
        per_debate_calls.append(("Validation sources", "Orchestrateur", 1, orchestrator_model, "research_validate"))

    # Brainstorming
    per_debate_calls.append(("Brainstorming (init)", "Agent", n_agents, agent_model, "brainstorm_init"))
    for i in range(1, iter_brainstorm):
        per_debate_calls.append((f"Brainstorming (iter {i+1})", "Agent", n_agents, agent_model, "brainstorm_refine"))

    # Planning
    per_debate_calls.append(("Planning", "Orchestrateur", 1, orchestrator_model, "planning"))

    # Thesis
    per_debate_calls.append(("Thesis (init)", "Agent", n_agents, agent_model, "thesis_init"))
    for i in range(1, iter_thesis):
        per_debate_calls.append((f"Thesis (iter {i+1})", "Agent", n_agents, agent_model, "thesis_refine"))

    # Antithesis
    per_debate_calls.append(("Antithesis (init)", "Agent", n_agents, agent_model, "antithesis_init"))
    for i in range(1, iter_antithesis):
        per_debate_calls.append((f"Antithesis (iter {i+1})", "Agent", n_agents, agent_model, "antithesis_refine"))

    # Synthesis
    per_debate_calls.append(("Synthesis (init)", "Orchestrateur", 1, orchestrator_model, "synthesis_init"))
    for i in range(1, iter_synthesis):
        per_debate_calls.append((f"Synthesis (iter {i+1})", "Orchestrateur", 1, orchestrator_model, "synthesis_refine"))

    for phase, agent_type, calls, model, tok_key in per_debate_calls:
        add(phase, agent_type, calls * n_debates, model, tok_key)

    return Forecast(
        lines=lines,
        n_agents=n_agents,
        n_questions=n_questions,
        mode=mode,
        n_debates=n_debates,
    )


def _short_model(model: str) -> str:
    mapping = {
        "haiku-4-5":  "Haiku 4.5",
        "sonnet-4-6": "Sonnet 4.6",
        "sonnet-3-5": "Sonnet 3.5",
        "opus-4-8":   "Opus 4.8",
        "opus-4-6":   "Opus 4.6",
    }
    for key, label in mapping.items():
        if key in model:
            return label
    return model[:12]

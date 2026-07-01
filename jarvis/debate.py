import copy
import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional
from anthropic import Anthropic

from .debate_config import DebateConfig
from .argument_graph import (
    ArgumentGraph, build_argument_graph, detect_conflicts, format_graph_for_synthesis,
)
from .session_log import SessionLog
from .agent_persona import AgentPersona
from .loader import load_agents
from .cost_forecast import Forecast, compute_forecast
from .checkpoint import (
    AgentSnapshot, DebateCheckpoint,
    delete as cp_delete, is_agent_done, is_orchestrator_done, save as cp_save,
)


def _inline_refs(schema: dict) -> dict:
    """Résout les $ref inline — l'API Anthropic n'accepte pas $defs/$ref."""
    schema = copy.deepcopy(schema)
    defs = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                resolved = resolve(copy.deepcopy(defs[name]))
                extra = {k: resolve(v) for k, v in node.items() if k != "$ref"}
                return {**resolved, **extra}
            return {k: resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return resolve(schema)


@dataclass
class DebateResult:
    questions: list[str]
    plan: str
    report: Any
    agent_names: list[str]
    session_log_path: Optional[str] = None


@dataclass
class AgentState:
    persona: AgentPersona
    messages: list[dict] = field(default_factory=list)
    brainstorm: str = ""
    thesis: str = ""
    antithesis: str = ""

    @property
    def latest(self) -> str:
        return self.antithesis if self.antithesis else self.thesis


# ── API calls ─────────────────────────────────────────────────────────────────

def _call_agent(client: Anthropic, state: AgentState, user_message: str, config: DebateConfig) -> str:
    model = state.persona.model or config.agent_model
    state.messages.append({"role": "user", "content": user_message})
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=state.persona.system_prompt,
        messages=state.messages,
    )
    text = response.content[0].text
    state.messages.append({"role": "assistant", "content": text})
    return text


def _call_orchestrator(client: Anthropic, system: str, user_message: str, config: DebateConfig, max_tokens: int = 2048) -> str:
    response = client.messages.create(
        model=config.orchestrator_model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return next(b.text for b in reversed(response.content) if b.type == "text")


# ── Speaking order ────────────────────────────────────────────────────────────

def _run_agents_in_speaking_order(
    client: Anthropic,
    states: list[AgentState],
    build_prompt_fn,
    phase: str,
    iteration: int,
    cp: Optional[DebateCheckpoint],
    config: DebateConfig,
) -> None:
    import copy as _copy

    completed: set[str] = set()
    groups = sorted(set(s.persona.speaking_group for s in states))

    for group_id in groups:
        group = [s for s in states if s.persona.speaking_group == group_id]
        mode = group[0].persona.speaking_mode

        if mode == "parallel":
            context_snapshot = _copy.deepcopy(states)
            for state in sorted(group, key=lambda s: s.persona.order):
                for dep in state.persona.wait_for:
                    if dep not in completed:
                        raise RuntimeError(
                            f"Agent '{state.persona.name}' attend '{dep}' qui n'a pas encore parlé."
                        )
                idx = states.index(state)
                if cp and is_agent_done(cp, phase, iteration, idx):
                    print(f"  → {state.persona.name}... (repris)")
                    completed.add(state.persona.name)
                    continue
                print(f"  → {state.persona.name} [parallel]...", end=" ", flush=True)
                _call_agent(client, state, build_prompt_fn(state.persona.name, context_snapshot), config)
                print("OK")
                completed.add(state.persona.name)
                if cp:
                    _update_cp(cp, phase, iteration, idx, states)
        else:
            for state in sorted(group, key=lambda s: s.persona.order):
                for dep in state.persona.wait_for:
                    if dep not in completed:
                        raise RuntimeError(
                            f"Agent '{state.persona.name}' attend '{dep}' qui n'a pas encore parlé."
                        )
                idx = states.index(state)
                if cp and is_agent_done(cp, phase, iteration, idx):
                    print(f"  → {state.persona.name}... (repris)")
                    completed.add(state.persona.name)
                    continue
                print(f"  → {state.persona.name}...", end=" ", flush=True)
                _call_agent(client, state, build_prompt_fn(state.persona.name, states), config)
                print("OK")
                completed.add(state.persona.name)
                if cp:
                    _update_cp(cp, phase, iteration, idx, states)


# ── Question classification ───────────────────────────────────────────────────

def _classify_questions(client: Anthropic, questions: list[str], config: DebateConfig) -> str:
    if len(questions) == 1:
        return "concurrent"
    numbered = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    response = client.messages.create(
        model=config.agent_model,
        max_tokens=16,
        messages=[{"role": "user", "content": f"""These {len(questions)} questions will be analyzed by financial experts:

{numbered}

Are they SEQUENTIAL (each question builds on the answer to the previous) or CONCURRENT (independent or complementary, can be addressed together)?

Reply with exactly one word: SEQUENTIAL or CONCURRENT."""}],
    )
    result = response.content[0].text.strip().upper()
    return "sequential" if "SEQUENTIAL" in result else "concurrent"


# ── Phase 0 — Brainstorming ───────────────────────────────────────────────────

def _format_thread(thread: list[dict]) -> str:
    if not thread:
        return "(No contributions yet.)"
    lines = []
    for e in thread:
        role = e.get("role", "")
        label = e["agent"]
        if role == "da_interject":
            label += " [intervention]"
        elif role in ("orchestrateur_open", "orchestrateur_close"):
            label += " [modérateur]"
        lines.append(f"[{label}]\n{e['content']}")
    return "\n\n".join(lines)


def _brainstorm_has_entry(thread: list[dict], iteration: int, role: str) -> bool:
    return any(e.get("iteration") == iteration and e.get("role") == role for e in thread)


def _brainstorm_iter_done(thread: list[dict], iteration: int, n_regular: int) -> bool:
    agent_count = sum(1 for e in thread if e.get("iteration") == iteration and e.get("role") == "agent")
    return _brainstorm_has_entry(thread, iteration, "orchestrateur_close") and agent_count >= n_regular


def _build_brainstorm_turn_prompt(
    questions: list[str],
    thread: list[dict],
    previous_report: Optional[Any],
    iteration: int,
) -> str:
    if len(questions) == 1:
        question_block = f"QUESTION: {questions[0]}"
    else:
        numbered = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
        question_block = f"QUESTIONS:\n{numbered}"

    context_block = ""
    if previous_report and hasattr(previous_report, "major_agreements") and hasattr(previous_report, "final_action"):
        agreements = "; ".join(previous_report.major_agreements[:2])
        context_block = f"""
PRIOR ANALYSIS CONTEXT:
- Previous decision: {previous_report.final_action} (conviction {previous_report.conviction_score:.0%})
- Key conclusions: {agreements}
"""

    thread_text = _format_thread(thread)
    return f"""{question_block}
{context_block}
SHARED BRAINSTORM THREAD:
{thread_text}

YOUR TURN — iteration {iteration + 1}.
From your area of expertise, contribute to the collective ideation:
- New dimensions, signals, or factors not yet raised
- Sub-questions that would unlock deeper analysis
- Counterintuitive angles or overlooked risks
- Direct reactions to what others have said (agree, challenge, extend)

Be generative. No commitments or conclusions yet."""


def _build_da_interject_prompt(thread: list[dict]) -> str:
    thread_text = _format_thread(thread)
    return f"""SHARED BRAINSTORM THREAD:
{thread_text}

INTERVENTION DECISION — Interject right now if you see a critical flaw, an unchallenged assumption, or a blindspot that could derail the analysis.

If you have something sharp and specific to add: write your intervention.
If not: respond with exactly one word — PASS."""


def _build_orchestrator_brainstorm_open_prompt(
    questions: list[str],
    thread: list[dict],
    iteration: int,
    previous_report: Optional[Any],
) -> str:
    if len(questions) == 1:
        question_block = f"QUESTION: {questions[0]}"
    else:
        numbered = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
        question_block = f"QUESTIONS:\n{numbered}"

    context = ""
    if previous_report and hasattr(previous_report, "final_action") and hasattr(previous_report, "conviction_score"):
        context = f"\nPRIOR ANALYSIS: {previous_report.final_action}, conviction {previous_report.conviction_score:.0%}.\n"

    if not thread:
        return f"""{question_block}
{context}
Open the brainstorming session. Frame the question(s), identify the most productive analytical angles, and invite the analysts to explore freely. Be stimulating — pose rich questions, do not give answers."""
    else:
        thread_text = _format_thread(thread)
        return f"""{question_block}
{context}
BRAINSTORM THREAD SO FAR (round {iteration} completed):
{thread_text}

Open round {iteration + 1}: synthesize what emerged, identify what is underexplored, and direct analysts toward the most productive unexplored territory."""


def _build_orchestrator_brainstorm_close_prompt(
    thread: list[dict],
    iteration: int,
    total_iterations: int,
) -> str:
    thread_text = _format_thread(thread)
    if iteration < total_iterations - 1:
        return f"""BRAINSTORM THREAD (end of round {iteration + 1}):
{thread_text}

Close this round: synthesize key themes, highlight the most interesting tensions, and formulate 2-3 sharp questions to steer the next round toward the most productive territory."""
    else:
        return f"""BRAINSTORM THREAD (final round):
{thread_text}

Close the brainstorming phase: synthesize the rich landscape of ideas, identify the major axes of disagreement that will structure the debate, and declare the brainstorm complete."""


def _call_da_brainstorm_interject(client: Anthropic, da_state: AgentState, thread: list[dict], config: DebateConfig) -> str:
    prompt = _build_da_interject_prompt(thread)
    da_state.messages.append({"role": "user", "content": prompt})
    response = client.messages.create(
        model=da_state.persona.model or config.agent_model,
        max_tokens=512,
        system=da_state.persona.system_prompt,
        messages=da_state.messages,
    )
    text = response.content[0].text
    da_state.messages.append({"role": "assistant", "content": text})
    return text


def _run_brainstorming_phase(
    client: Anthropic,
    states: list[AgentState],
    questions: list[str],
    previous_report: Optional[Any],
    cp: Optional[DebateCheckpoint],
    config: DebateConfig,
) -> list[dict]:
    """
    Brainstorming avec thread partagé.
    - Tous les agents (sauf DA) prennent leur tour en voyant les contributions des autres.
    - Le DA peut intervenir après chaque agent régulier s'il le juge nécessaire.
    - L'orchestrateur ouvre et clôture chaque itération.
    """
    regular_states = [s for s in states if s.persona.role != "devil_advocate"]
    da_state = next((s for s in states if s.persona.role == "devil_advocate"), None)

    thread: list[dict] = list(cp.brainstorm_thread) if (cp and cp.brainstorm_thread) else []

    # Thread vide mais checkpoint avancé = état incohérent (ex: ancien checkpoint
    # sans brainstorm_thread). On réinitialise la position au début du brainstorming.
    if cp and not thread and cp.phase == "brainstorm" and cp.phase_iteration > 0:
        cp.phase_iteration = 0
        cp.agent_index = -1

    for iteration in range(config.iterations_brainstorming):
        n_regular = len(regular_states)
        tag = "Brainstorming" + (f" — itération {iteration+1}/{config.iterations_brainstorming}" if config.iterations_brainstorming > 1 else "")

        if _brainstorm_iter_done(thread, iteration, n_regular):
            print(f"\n[{tag}]... (repris — itération complète)")
            continue

        print(f"\n[{tag}]")

        # 1. Orchestrateur ouvre le tour
        if _brainstorm_has_entry(thread, iteration, "orchestrateur_open"):
            print(f"  [Orchestrateur — ouverture]... (repris)")
        else:
            print(f"  [Orchestrateur — ouverture]...", end=" ", flush=True)
            text = _call_orchestrator(
                client, config.brainstorm_moderator_prompt,
                _build_orchestrator_brainstorm_open_prompt(questions, thread, iteration, previous_report),
                config,
            )
            thread.append({"role": "orchestrateur_open", "agent": "Orchestrateur", "content": text, "iteration": iteration})
            print("OK")
            if cp:
                cp.brainstorm_thread = thread
                cp_save(cp)

        # 2. Agents réguliers à tour de rôle + interventions du DA
        for idx, state in enumerate(regular_states):
            if cp and is_agent_done(cp, "brainstorm", iteration, idx):
                print(f"  → {state.persona.name}... (repris)")
                continue

            print(f"  → {state.persona.name}...", end=" ", flush=True)
            response = _call_agent(
                client, state,
                _build_brainstorm_turn_prompt(questions, thread, previous_report, iteration),
                config,
            )
            thread.append({"role": "agent", "agent": state.persona.name, "content": response, "iteration": iteration})
            print("OK")

            # DA : intervention optionnelle après chaque agent régulier
            if da_state:
                da_resp = _call_da_brainstorm_interject(client, da_state, thread, config)
                if da_resp.strip() and da_resp.strip().upper() != "PASS":
                    print(f"  → {da_state.persona.name} [intervention]... OK")
                    thread.append({
                        "role": "da_interject",
                        "agent": da_state.persona.name,
                        "content": da_resp,
                        "iteration": iteration,
                        "after_agent": state.persona.name,
                    })

            # Checkpoint après l'agent + son éventuelle intervention DA
            if cp:
                cp.brainstorm_thread = thread
                _update_cp(cp, "brainstorm", iteration, idx, states)

        # 3. Orchestrateur clôture le tour
        if _brainstorm_has_entry(thread, iteration, "orchestrateur_close"):
            print(f"  [Orchestrateur — clôture]... (repris)")
        else:
            print(f"  [Orchestrateur — clôture]...", end=" ", flush=True)
            text = _call_orchestrator(
                client, config.brainstorm_moderator_prompt,
                _build_orchestrator_brainstorm_close_prompt(thread, iteration, config.iterations_brainstorming),
                config,
            )
            thread.append({"role": "orchestrateur_close", "agent": "Orchestrateur", "content": text, "iteration": iteration})
            print("OK")
            if cp:
                cp.brainstorm_thread = thread
                _update_cp(cp, "brainstorm", iteration, -1, states)

    # Peuple state.brainstorm avec les contributions de chaque agent (compat checkpoint)
    for state in states:
        contributions = [
            e["content"] for e in thread
            if e.get("agent") == state.persona.name and e.get("role") in ("agent", "da_interject")
        ]
        state.brainstorm = "\n\n---\n\n".join(contributions)

    return thread


# ── Phase 1 — Planning ────────────────────────────────────────────────────────

def _build_planning_prompt(thread: list[dict], questions: list[str]) -> str:
    if len(questions) == 1:
        question_block = f"QUESTION: {questions[0]}"
    else:
        numbered = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
        question_block = f"QUESTIONS:\n{numbered}"

    thread_text = _format_thread(thread)
    return f"""{question_block}

Here is the complete brainstorming thread from all analysts:

{thread_text}

Produce the structured debate plan in French."""


# ── Validation interactive — question & plan ─────────────────────────────────

def _build_question_enrichment_prompt(
    questions: list[str],
    previous_report: Optional[Any],
    user_comment: str = "",
) -> str:
    if len(questions) == 1:
        question_block = f"QUESTION BRUTE : {questions[0]}"
    else:
        numbered = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
        question_block = f"QUESTIONS BRUTES :\n{numbered}"

    context_block = ""
    if previous_report and hasattr(previous_report, "final_action") and hasattr(previous_report, "conviction_score"):
        context_block = f"\nCONTEXTE ANALYSE PRÉCÉDENTE : {previous_report.final_action}, conviction {previous_report.conviction_score:.0%}\n"

    comment_block = ""
    if user_comment:
        comment_block = f"\nCOMMENTAIRE DE L'UTILISATEUR (à intégrer) :\n{user_comment}\n"

    return f"""{question_block}
{context_block}{comment_block}
Propose une reformulation enrichie avec le contexte analytique pertinent et les indicateurs de prix clés à surveiller."""


def _interactive_question_validation(
    client: Anthropic,
    questions: list[str],
    previous_report: Optional[Any],
    config: DebateConfig,
) -> list[str]:
    """Étape A — l'orchestrateur reformule la question, l'utilisateur valide ou commente."""
    user_comment = ""
    while True:
        print("\n[Orchestrateur — reformulation de la question]...", end=" ", flush=True)
        enriched = _call_orchestrator(
            client,
            config.question_analyst_prompt,
            _build_question_enrichment_prompt(questions, previous_report, user_comment),
            config,
            max_tokens=1024,
        )
        print("OK")

        print("\n" + "═" * 44)
        print("  REFORMULATION PAR L'ORCHESTRATEUR")
        print("═" * 44)
        print(enriched)
        print()
        print("  Entrée / O  → Valider et lancer le brainstorming")
        print("  Autre       → Votre commentaire (sera intégré)")
        choice = input("> ").strip()

        if choice.lower() in ("", "o", "oui", "y", "yes"):
            return [enriched]
        else:
            user_comment = choice


def _interactive_plan_validation(
    client: Anthropic,
    brainstorm_thread: list[dict],
    questions: list[str],
    states: list[AgentState],
    forecast: Optional[Forecast],
    cp: Optional[DebateCheckpoint],
    config: DebateConfig,
) -> str:
    """Étape B — génère le plan, le soumet à validation interactive, boucle sur révisions."""
    if cp and is_orchestrator_done(cp, "planning"):
        print("\n[Planning — Orchestrator]... (repris)")
        return cp.plan

    user_comment = ""
    first_display = True
    while True:
        print("\n[Planning — Orchestrator]...", end=" ", flush=True)
        prompt = _build_planning_prompt(brainstorm_thread, questions)
        if user_comment:
            prompt += f"\n\nCOMMENTAIRE UTILISATEUR (à intégrer dans la révision du plan) :\n{user_comment}"
        plan = _call_orchestrator(client, config.planner_prompt, prompt, config)
        print("OK")

        print("\n" + "═" * 44)
        print("  PLAN DE DÉBAT")
        print("═" * 44)
        print(plan)
        print("═" * 44)

        if first_display and forecast is not None:
            print(forecast.format_display())
            first_display = False

        print("\n  Entrée / O  → Valider et lancer le débat")
        print("  Autre       → Commentaire (l'orchestrateur révise)")
        choice = input("> ").strip()

        if choice.lower() in ("", "o", "oui", "y", "yes"):
            if cp:
                cp.plan = plan
                _update_cp(cp, "planning", 0, -1, states)
            return plan
        else:
            user_comment = choice


# ── Round 1 — Thesis ──────────────────────────────────────────────────────────

def _build_round1_prompt(
    questions: list[str],
    plan: str,
    previous_report: Optional[Any] = None,
) -> str:
    if len(questions) == 1:
        question_block = f"QUESTION: {questions[0]}"
    else:
        numbered = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
        question_block = f"ANALYTICAL BRIEF — address all {len(questions)} questions:\n\n{numbered}"

    context_block = ""
    if previous_report and hasattr(previous_report, "major_agreements") and hasattr(previous_report, "final_action"):
        agreements = "; ".join(previous_report.major_agreements[:2])
        context_block = f"""
CONTEXT FROM PREVIOUS ANALYSIS (build on this, do not repeat it):
- Decision: {previous_report.final_action} | Conviction: {previous_report.conviction_score:.0%}
- Key conclusions: {agreements}
"""

    return f"""{question_block}
{context_block}
DEBATE PLAN (shared with all analysts):
{plan}

THESIS PHASE — based on your brainstorm and the debate plan above, produce your complete, well-structured thesis. Be precise, quantified where possible, and defend a clear position."""


def _build_thesis_refinement_prompt(iteration: int) -> str:
    return f"""Thesis iteration {iteration + 1} — deepen your analysis.

Review your previous thesis and challenge your own assumptions:
- What key evidence or counterargument have you not yet addressed?
- Are your quantitative estimates robust?
- Strengthen your position or explicitly revise it if warranted."""


# ── Round 2 — Antithesis ──────────────────────────────────────────────────────

def _build_round2_prompt(agent_name: str, states: list[AgentState], iteration: int) -> str:
    label = "thesis" if iteration == 0 else f"latest position (iteration {iteration + 1})"
    others_section = "\n\n".join(
        f"--- {s.persona.name} ({label}) ---\n{s.latest}"
        for s in states
        if s.persona.name != agent_name
    )
    if iteration == 0:
        instruction = """Based on these positions, refine or defend your thesis. Explicitly identify:
- Points where you converge with other analysts
- Fundamental disagreements you firmly maintain
- Opposing arguments you find unacceptable and why"""
    else:
        instruction = f"""Iteration {iteration + 1} — the debate has evolved. Based on the updated positions above:
- Have any of your disagreements shifted?
- Which arguments from others have strengthened or weakened?
- Sharpen your final stance before synthesis."""

    return f"""Here are the {label}s from the other analysts:

{others_section}

{instruction}"""


# ── Round 3 — Synthesis ───────────────────────────────────────────────────────

def _build_synthesis_prompt(states: list[AgentState], graph_summary: str = "") -> str:
    debate_log = ""
    for state in states:
        debate_log += f"\n{'='*60}\n{state.persona.name.upper()}\n{'='*60}\n"
        debate_log += f"[THESIS]\n{state.thesis}\n\n"
        debate_log += f"[FINAL ANTITHESIS]\n{state.antithesis}\n"

    graph_section = f"\nARGUMENT GRAPH SUMMARY:\n{graph_summary}\n" if graph_summary else ""
    n = len(states)
    return f"""Here is the full debate between {n} analyst{'s' if n > 1 else ''}:
{graph_section}
{debate_log}

Produce the structured consensus report."""


def _build_synthesis_refinement_prompt(previous_json: str, iteration: int) -> str:
    return f"""Iteration {iteration + 1} — critically review your previous consensus report:

{previous_json}

Identify any:
- Oversimplifications that could mislead a beginner
- Agreements or disagreements missed in the debate
- Conviction score or stop-loss level that deserves revision

Produce an improved version of the full consensus report."""


# ── Checkpoint helpers ────────────────────────────────────────────────────────

def _snapshot_agents(states: list[AgentState]) -> list[AgentSnapshot]:
    return [
        AgentSnapshot(
            name=s.persona.name,
            messages=list(s.messages),
            brainstorm=s.brainstorm,
            thesis=s.thesis,
            antithesis=s.antithesis,
        )
        for s in states
    ]


def _restore_agents(
    personas: list[AgentPersona], snapshots: list[AgentSnapshot]
) -> list[AgentState]:
    snap_by_name = {s.name: s for s in snapshots}
    states = []
    for p in personas:
        state = AgentState(persona=p)
        snap = snap_by_name.get(p.name)
        if snap:
            state.messages = list(snap.messages)
            state.brainstorm = snap.brainstorm
            state.thesis = snap.thesis
            state.antithesis = snap.antithesis
        states.append(state)
    return states


def _update_cp(cp: DebateCheckpoint, phase: str, iteration: int, agent_idx: int,
               states: list[AgentState]) -> None:
    cp.phase = phase
    cp.phase_iteration = iteration
    cp.agent_index = agent_idx
    cp.agents = _snapshot_agents(states)
    cp_save(cp)


# ── Core debate loop ──────────────────────────────────────────────────────────

def _run_single_debate(
    client: Anthropic,
    personas: list[AgentPersona],
    questions: list[str],
    config: DebateConfig,
    session_id: str = "",
    previous_report: Optional[Any] = None,
    forecast: Optional[Forecast] = None,
    cp: Optional[DebateCheckpoint] = None,
) -> DebateResult:

    session_log = SessionLog(session_id if session_id else "unknown")

    # Restaure les états agents depuis le checkpoint si on reprend
    if cp and cp.agents:
        states = _restore_agents(personas, cp.agents)
        _orch_phases = {"planning", "synthesis"}
        if cp.phase in _orch_phases or cp.agent_index == -1:
            print(f"  Reprise depuis la phase '{cp.phase}' (itération {cp.phase_iteration + 1}, orchestrateur)")
        else:
            print(f"  Reprise depuis la phase '{cp.phase}' "
                  f"(itération {cp.phase_iteration + 1}, agent {cp.agent_index + 1}/{len(personas)})")
    else:
        states = [AgentState(persona=p) for p in personas]

    plan: str = cp.plan if cp else ""

    # Étape A — Validation de la question (avant brainstorming)
    if cp and cp.confirmed_questions:
        questions = cp.confirmed_questions
    else:
        questions = _interactive_question_validation(client, questions, previous_report, config)
        if cp:
            cp.confirmed_questions = questions
            cp_save(cp)

    # Phase 0 — Brainstorming (thread partagé, DA, orchestrateur modérateur)
    brainstorm_thread = _run_brainstorming_phase(client, states, questions, previous_report, cp, config)
    session_log.log_brainstorm(brainstorm_thread)

    # Étape B — Validation du plan (après brainstorming, interactive)
    plan = _interactive_plan_validation(client, brainstorm_thread, questions, states, forecast, cp, config)
    session_log.log_plan(plan)

    # Round 1 — Thesis
    for iteration in range(config.iterations_thesis):
        tag = "Round 1 / Thesis" + (f" — itération {iteration + 1}/{config.iterations_thesis}" if config.iterations_thesis > 1 else "")
        print(f"\n[{tag}]")

        def _make_thesis_prompt(agent_name: str, current_states: list, _iter=iteration) -> str:
            if _iter == 0:
                return _build_round1_prompt(questions, plan, previous_report)
            return _build_thesis_refinement_prompt(_iter)

        _run_agents_in_speaking_order(client, states, _make_thesis_prompt, "thesis", iteration, cp, config)

        for state in states:
            if state.messages:
                state.thesis = state.messages[-1]["content"]

    session_log.log_theses({s.persona.name: s.thesis for s in states})

    # Round 2 — Antithesis
    for iteration in range(config.iterations_antithesis):
        tag = "Round 2 / Antithesis" + (f" — itération {iteration + 1}/{config.iterations_antithesis}" if config.iterations_antithesis > 1 else "")
        print(f"\n[{tag}]")

        def _make_antithesis_prompt(agent_name: str, current_states: list, _iter=iteration) -> str:
            return _build_round2_prompt(agent_name, current_states, _iter)

        _run_agents_in_speaking_order(client, states, _make_antithesis_prompt, "antithesis", iteration, cp, config)

        for state in states:
            if state.messages:
                state.antithesis = state.messages[-1]["content"]

    # Log antithèses
    session_log.log_antitheses({s.persona.name: s.antithesis for s in states})

    # Phase conflict_detection
    conflict_topic = ""
    if "conflict_detection" in config.enabled_phases:
        if cp and is_orchestrator_done(cp, "conflict_detection"):
            conflict_topic = (cp.argument_graph_data or {}).get("debate_topic", "")
            print("\n[Conflict Detection]... (repris)")
        else:
            print("\n[Conflict Detection]...", end=" ", flush=True)
            antitheses_map = {s.persona.name: s.antithesis for s in states}
            conflict_topic = detect_conflicts(client, config, antitheses_map)
            print("OK")
            session_log.log_conflict(conflict_topic)
            if cp:
                _update_cp(cp, "conflict_detection", 0, -1, states)

    # Phase argument_graph
    graph = None
    vote_scores: dict = {}
    if "argument_graph" in config.enabled_phases and conflict_topic:
        if cp and cp.argument_graph_data:
            from .argument_graph import Claim, ArgumentEdge
            claims = [Claim(**c) for c in cp.argument_graph_data.get("claims", [])]
            edges = [ArgumentEdge(**e) for e in cp.argument_graph_data.get("edges", [])]
            graph = ArgumentGraph(
                debate_topic=cp.argument_graph_data.get("debate_topic", ""),
                claims=claims,
                edges=edges,
            )
            vote_scores = cp.vote_scores or {}
            print("\n[Argument Graph]... (repris)")
        else:
            print("\n[Argument Graph]...", end=" ", flush=True)
            antitheses_map = {s.persona.name: s.antithesis for s in states}
            graph = build_argument_graph(client, config, antitheses_map, conflict_topic)
            trust_weights = {s.persona.name: s.persona.trust_weight for s in states}
            vote_scores = graph.trust_weighted_scores(trust_weights)
            print("OK")
            session_log.log_argument_graph(graph)
            session_log.log_vote_scores(vote_scores)
            if cp:
                from dataclasses import asdict
                cp.argument_graph_data = asdict(graph)
                cp.vote_scores = vote_scores
                _update_cp(cp, "argument_graph", 0, -1, states)

    # Round 3 — Synthesis
    previous_json: Optional[str] = None
    report: Optional[Any] = None

    for iteration in range(config.iterations_synthesis):
        tag = "Round 3 / Synthesis" + (f" — itération {iteration + 1}/{config.iterations_synthesis}" if config.iterations_synthesis > 1 else "")
        if cp and is_orchestrator_done(cp, "synthesis", iteration):
            print(f"\n[{tag} — Orchestrator]... (repris)")
            if cp.synthesis_report is not None and previous_json is None:
                previous_json = json.dumps(cp.synthesis_report, ensure_ascii=False)
            continue
        print(f"\n[{tag} — Orchestrator]...", end=" ", flush=True)

        if iteration == 0:
            graph_summary = format_graph_for_synthesis(graph, vote_scores) if graph else ""
            user_content = _build_synthesis_prompt(states, graph_summary)
        else:
            user_content = _build_synthesis_refinement_prompt(previous_json, iteration)

        response = client.messages.create(
            model=config.orchestrator_model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=config.synthesis_prompt,
            messages=[{"role": "user", "content": user_content}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": config.output_schema,
                }
            },
        )
        print("OK")
        previous_json = next(
            block.text for block in reversed(response.content) if block.type == "text"
        )
        report = config.output_pydantic_model.model_validate_json(previous_json)
        if cp:
            cp.synthesis_report = report.model_dump()
            _update_cp(cp, "synthesis", iteration, -1, states)

    # Restaure le rapport depuis le checkpoint si toutes les itérations ont été sautées
    if report is None and cp and cp.synthesis_report:
        report = config.output_pydantic_model.model_validate(cp.synthesis_report)

    if report is not None:
        session_log.log_synthesis(report.model_dump() if hasattr(report, "model_dump") else report)

    # Debate terminé — marque "done" avant suppression pour résister aux erreurs de suppression
    if cp:
        cp.phase = "done"
        cp_save(cp)
        cp_delete(cp.session_id)

    return DebateResult(
        questions=questions,
        plan=plan,
        report=report,
        agent_names=[s.persona.name for s in states],
        session_log_path=str(session_log.path),
    )


# ── Public entry point ────────────────────────────────────────────────────────

def run_debate(
    questions: list[str],
    config: Optional[DebateConfig] = None,
    session_id: str = "",
    resume_cp: Optional[DebateCheckpoint] = None,
) -> list[DebateResult]:
    if config is None:
        from jarvis.finance_config import build_finance_config
        config = build_finance_config()

    client = Anthropic()
    print("\nChargement des agents depuis agents/...")
    personas = load_agents()
    print(f"  {len(personas)} agent(s) prêt(s) : {', '.join(p.name for p in personas)}")
    print(f"  Itérations — Brainstorming: {config.iterations_brainstorming} | Thesis: {config.iterations_thesis} | Antithesis: {config.iterations_antithesis} | Synthesis: {config.iterations_synthesis}")

    if len(questions) == 1:
        mode = "concurrent"
        n_debates = 1
    else:
        print(f"\nClassification de {len(questions)} questions...", end=" ", flush=True)
        mode = _classify_questions(client, questions, config)
        print(mode.upper())
        n_debates = len(questions) if mode == "sequential" else 1

    forecast = compute_forecast(
        n_agents=len(personas),
        n_questions=len(questions),
        mode=mode,
        agent_model=config.agent_model,
        orchestrator_model=config.orchestrator_model,
        iter_brainstorm=config.iterations_brainstorming,
        iter_thesis=config.iterations_thesis,
        iter_antithesis=config.iterations_antithesis,
        iter_synthesis=config.iterations_synthesis,
    )

    def _make_cp(debate_index: int, previous_report: Optional[Any]) -> DebateCheckpoint:
        cp = DebateCheckpoint(
            session_id=session_id,
            questions=questions,
            mode=mode,
            n_debates=n_debates,
            debate_index=debate_index,
            phase="brainstorm",
            phase_iteration=0,
            agent_index=-1,
            previous_report=previous_report.model_dump() if previous_report and hasattr(previous_report, "model_dump") else None,
            agent_model=config.agent_model,
            orchestrator_model=config.orchestrator_model,
        )
        cp_save(cp)
        return cp

    if mode == "concurrent" or len(questions) == 1:
        if len(questions) > 1:
            print("\n→ Traitement concurrent : toutes les questions en un seul débat")
        cp = resume_cp if (resume_cp and resume_cp.debate_index == 0) else _make_cp(0, None)
        return [_run_single_debate(client, personas, questions, config, session_id=session_id, forecast=forecast, cp=cp)]

    print(f"\n→ Traitement séquentiel : {len(questions)} débat(s) enchaînés")
    results: list[DebateResult] = []
    previous: Optional[Any] = None

    start_index = resume_cp.debate_index if resume_cp else 0
    # Restaure le contexte du débat précédent si on reprend en milieu de chaîne
    if resume_cp and resume_cp.previous_report:
        previous = config.output_pydantic_model.model_validate(resume_cp.previous_report)

    for i, question in enumerate(questions):
        if i < start_index:
            print(f"\n  Débat {i+1}/{len(questions)} ignoré (déjà complété dans le checkpoint)")
            continue
        print(f"\n{'='*60}")
        print(f"Question {i+1}/{len(questions)} : {question}")
        print("=" * 60)
        debate_forecast = forecast if i == start_index else None
        if resume_cp and i == start_index:
            cp = resume_cp
        else:
            cp = _make_cp(i, previous)
        result = _run_single_debate(
            client, personas, [question], config,
            session_id=session_id,
            previous_report=previous,
            forecast=debate_forecast,
            cp=cp,
        )
        results.append(result)
        previous = result.report

    return results

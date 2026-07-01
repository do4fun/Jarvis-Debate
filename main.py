import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from jarvis.checkpoint import DebateCheckpoint, find_latest
from jarvis.debate import DebateResult, run_debate
from jarvis.finance_config import build_finance_config

load_dotenv()

REPORTS_DIR = Path(__file__).parent / "rapports" / "analyses"


def _resolve_questions() -> list[str]:
    # 1. Argument CLI (question unique)
    if len(sys.argv) > 1:
        return [sys.argv[1].strip()]

    # 2. DEFAULT_QUESTIONS dans .env (format JSON : ["q1", "q2", ...])
    env_val = os.getenv("DEFAULT_QUESTIONS", "").strip()
    if env_val:
        try:
            parsed = json.loads(env_val)
            if isinstance(parsed, list):
                questions = [q.strip() for q in parsed if isinstance(q, str) and q.strip()]
                if questions:
                    return questions
        except json.JSONDecodeError:
            pass
        return [env_val]

    # 3. Prompt interactif
    print("\nAucune question définie (ni argument CLI, ni DEFAULT_QUESTIONS dans .env).")
    print("Entrez vos questions une par une. Ligne vide pour terminer.")
    questions: list[str] = []
    while True:
        q = input(f"  Question {len(questions) + 1} : ").strip()
        if not q:
            if questions:
                break
            print("  Au moins une question est requise.")
        else:
            questions.append(q)
    return questions


def _check_resume() -> tuple[list[str], str, DebateCheckpoint | None]:
    """Détecte un checkpoint non terminé et propose de reprendre."""
    cp = find_latest()
    if cp is None:
        return [], "", None

    print("\n" + "=" * 60)
    print("  SESSION INTERROMPUE DÉTECTÉE")
    print("=" * 60)
    print(f"  Session   : {cp.session_id}")
    print(f"  Questions : {len(cp.questions)}")
    for i, q in enumerate(cp.questions, 1):
        print(f"    {i}. {q[:80]}{'…' if len(q) > 80 else ''}")
    _ORCHESTRATOR_PHASES = {"planning", "synthesis"}
    if cp.phase in _ORCHESTRATOR_PHASES:
        position = f"phase '{cp.phase}', itération {cp.phase_iteration + 1} (orchestrateur)"
    else:
        position = f"phase '{cp.phase}', itération {cp.phase_iteration + 1}, agent {cp.agent_index + 1}"
    print(f"  Arrêtée à : {position}")
    print()

    answer = input("  Reprendre cette session ? [O/n] : ").strip().lower()
    if answer in ("", "o", "oui", "y", "yes"):
        return cp.questions, cp.session_id, cp
    return [], "", None


def _slug(text: str, max_len: int = 50) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = re.sub(r"[̀-ͯ]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text[:max_len].rstrip("-")


def _format_report_md(result: DebateResult, index: int, total: int, ts: str) -> str:
    r = result.report
    date_label = datetime.strptime(ts, "%Y%m%d_%H%M%S").strftime("%d %B %Y à %Hh%M")

    lines: list[str] = []

    lines.append("# Rapport Jarvis Finance")
    lines.append("")
    lines.append(f"**Date :** {date_label}")
    lines.append(f"**Agents :** {', '.join(result.agent_names)}")
    if total > 1:
        lines.append(f"**Débat :** {index + 1} / {total}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Question(s)")
    lines.append("")
    if len(result.questions) == 1:
        lines.append(result.questions[0])
    else:
        for i, q in enumerate(result.questions, 1):
            lines.append(f"{i}. {q}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Plan de Débat")
    lines.append("")
    lines.append(result.plan)
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Résultat du Débat")
    lines.append("")
    action_label = {
        "BUY": "ACHETER (BUY)",
        "SELL": "VENDRE (SELL)",
        "HOLD": "CONSERVER (HOLD)",
        "NO_TRADE": "NE PAS TRADER (NO_TRADE)",
    }.get(r.final_action.value, r.final_action.value)

    lines.append(f"| | |")
    lines.append(f"| --- | --- |")
    lines.append(f"| **Action recommandée** | **{action_label}** |")
    lines.append(f"| **Score de conviction** | {r.conviction_score:.0%} |")
    seuil = f"{r.stop_loss_limit_price:,.2f}" if r.stop_loss_limit_price is not None else "—"
    lines.append(f"| **Stop-loss / Seuil** | {seuil} |")
    lines.append("")

    lines.append("### Points d'accord majeurs")
    lines.append("")
    for item in r.major_agreements:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("### Désaccords irréductibles")
    lines.append("")
    if r.irreconcilable_differences:
        for item in r.irreconcilable_differences:
            lines.append(f"- {item}")
    else:
        lines.append("*Aucun désaccord irréductible identifié.*")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("*Généré par Jarvis Finance — système multi-agents de débat financier*")
    lines.append("")

    return "\n".join(lines)


def _save_result(result: DebateResult, index: int, total: int, ts: str) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    suffix = f"_{index + 1}" if total > 1 else ""
    filename = f"{ts}{suffix}_{_slug(result.questions[0])}.md"
    path = REPORTS_DIR / filename
    path.write_text(_format_report_md(result, index, total, ts), encoding="utf-8")
    return path


def main() -> None:
    # Vérification de reprise avant de résoudre les questions
    resume_questions, resume_session_id, resume_cp = _check_resume()

    if resume_cp:
        questions = resume_questions
        session_id = resume_session_id
        print(f"\nReprise de la session {session_id}")
    else:
        questions = _resolve_questions()
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\nJARVIS FINANCE — Analyse multi-agents")
    if len(questions) == 1:
        print(f"Question : {questions[0]}")
    else:
        print(f"{len(questions)} questions :")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q}")
    print("=" * 60)

    config = build_finance_config()
    results = run_debate(questions, config=config, session_id=session_id, resume_cp=resume_cp)
    ts = session_id  # même timestamp pour le nom du fichier rapport

    # En mode séquentiel avec reprise, les résultats ne couvrent que les débats
    # depuis start_index — les indices doivent être décalés en conséquence.
    start_index = resume_cp.debate_index if resume_cp else 0
    total_debates = resume_cp.n_debates if resume_cp else len(results)

    for i, result in enumerate(results):
        actual_index = start_index + i
        r = result.report
        print("\n" + "=" * 60)
        if total_debates > 1:
            print(f"CONSENSUS REPORT — Débat {actual_index + 1}/{total_debates}")
            print(f"  {result.questions[0]}")
        else:
            print("CONSENSUS REPORT")
        print("=" * 60)
        print(json.dumps(r.model_dump(), indent=2, ensure_ascii=False))

        path = _save_result(result, actual_index, total_debates, ts)
        print(f"\n  Rapport sauvegardé : {path}")

        if result.session_log_path:
            print(f"  Session log : {result.session_log_path}")


if __name__ == "__main__":
    main()

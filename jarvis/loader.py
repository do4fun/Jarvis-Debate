import importlib.util
import os
from pathlib import Path

from .agent_persona import AgentPersona

AGENTS_DIR = Path(__file__).parent.parent / os.getenv("AGENTS_DIR", "agents")


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_persona(module) -> AgentPersona | None:
    if hasattr(module, "AGENT") and isinstance(module.AGENT, AgentPersona):
        return module.AGENT
    for attr in vars(module).values():
        if isinstance(attr, AgentPersona):
            return attr
    return None


def _missing_fields(agent: AgentPersona) -> list[str]:
    missing = []
    if not agent.name or not str(agent.name).strip():
        missing.append("name")
    if not agent.system_prompt or not str(agent.system_prompt).strip():
        missing.append("system_prompt")
    return missing


def _prompt_completions(filename: str, agent: AgentPersona, missing: list[str]) -> None:
    for field in missing:
        while True:
            value = input(f"  [{filename}] Valeur manquante pour '{field}' : ").strip()
            if not value:
                print("    La valeur ne peut pas être vide. Réessayez.")
                continue
            if field == "name":
                agent.name = value
            elif field == "system_prompt":
                agent.system_prompt = value
            break


def load_agents() -> list[AgentPersona]:
    if not AGENTS_DIR.exists():
        raise FileNotFoundError(
            f"Répertoire agents/ introuvable : {AGENTS_DIR}\n"
            "Créez le répertoire et ajoutez vos fichiers agent (*.py)."
        )

    valid: list[AgentPersona] = []
    incomplete: list[tuple[str, AgentPersona, list[str]]] = []

    for py_file in sorted(AGENTS_DIR.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            module = _load_module(py_file)
            agent = _find_persona(module)
            if agent is None:
                print(f"  [WARN] {py_file.name} : aucune instance AgentPersona trouvée — ignoré")
                continue
            missing = _missing_fields(agent)
            if missing:
                incomplete.append((py_file.name, agent, missing))
            else:
                valid.append(agent)
        except Exception as exc:
            print(f"  [WARN] {py_file.name} : erreur au chargement ({exc}) — ignoré")

    if incomplete:
        print(f"\n  {len(incomplete)} agent(s) incomplet(s) — veuillez compléter les valeurs manquantes :")
        for filename, agent, missing in incomplete:
            _prompt_completions(filename, agent, missing)
            valid.append(agent)

    valid.sort(key=lambda a: a.order)
    return valid

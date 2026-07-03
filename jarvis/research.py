"""
Recherche web économe en tokens pour alimenter le débat en données actuelles.

Pipeline en 2 appels LLM au total (indépendant du nombre de sources trouvées) :

1. Un "chercheur" (web_search + web_fetch, domaines de confiance uniquement) trouve des
   sources et, pour chacune, n'extrait QUE : titre/en-tête, le premier paragraphe, UN
   paragraphe représentatif du milieu du texte, et UN paragraphe proche de la fin (jamais
   le tout dernier — souvent un disclaimer/CTA — ni la page complète).
2. Un "validateur" indépendant (aucun accès web, seulement les extraits ci-dessus) filtre
   les sources non fiables, non pertinentes ou non datées.

Le résultat est un court briefing texte, injecté UNE SEULE FOIS dans le pipeline de débat
(ouverture du brainstorming + round 1/thesis) — jamais rejoué par agent ni par itération,
ce qui borne le coût en tokens indépendamment du nombre d'agents/itérations du débat.
"""

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

if TYPE_CHECKING:
    from anthropic import Anthropic
    from jarvis.debate_config import DebateConfig


DEFAULT_RESEARCHER_SYSTEM = """You are a research assistant gathering current, factual context for an upcoming analytical debate. You have web_search and web_fetch tools available, restricted to a curated list of trusted domains.

Process:
1. Search for the most relevant, recent, authoritative sources on the topic.
2. Fetch at most a few of the most promising results.
3. For EACH fetched page, extract ONLY these elements — never summarize or quote anything else from the page, and keep each element to 1-2 sentences maximum:
   - The title and header/subheading
   - The opening paragraph (sets context)
   - ONE representative paragraph from the middle of the article (core substance)
   - ONE paragraph from near the end, but NOT the final paragraph (final paragraphs are usually disclaimers or calls-to-action, not substantive)
4. Discard everything else from the page. Do not reproduce full paragraphs beyond these four elements per source.

Output one entry per source, in this exact format, and nothing else:
SOURCE: <url>
TITLE: <title>
DATE: <publication date if known, else "unknown">
EXCERPT: <title/header, 1 sentence> | <opening paragraph excerpt, 1-2 sentences> | <middle paragraph excerpt, 1-2 sentences> | <near-end paragraph excerpt, 1-2 sentences>
---

If no sources are found, output nothing."""

DEFAULT_SOURCE_VALIDATOR_SYSTEM = """You are a source-credibility validator. You will be given a list of web sources (URL, domain, date, and a short excerpt) gathered for an analytical debate. You have no web access — assess ONLY from what is provided.

For each source, judge whether it is:
- From a domain consistent with reputable, authoritative reporting or an official/primary source (not a low-quality aggregator, forum, or unverified blog)
- Reasonably current (not clearly stale, and not undated when recency plainly matters for the claim)
- Substantively relevant to the topic (not a mismatch, paywall stub, or spam/placeholder page)

Reply with a JSON object listing a verdict for every source given, no more and no fewer."""

VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "trustworthy": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["url", "trustworthy", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


@dataclass
class SourceFinding:
    url: str
    title: str
    domain: str
    date: Optional[str]
    excerpt: str
    trustworthy: bool = False
    validator_reason: str = ""


def build_search_tools(config: "DebateConfig") -> list[dict]:
    """Construit les tool specs web_search + web_fetch, bornés en volume (max_uses,
    max_content_tokens) et restreints aux domaines de confiance configurés."""
    search_tool: dict = {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": config.web_search_max_uses,
    }
    fetch_tool: dict = {
        "type": "web_fetch_20260209",
        "name": "web_fetch",
        "max_uses": config.web_fetch_max_uses,
        "max_content_tokens": config.web_fetch_max_content_tokens,
    }
    if config.web_search_allowed_domains:
        search_tool["allowed_domains"] = config.web_search_allowed_domains
        fetch_tool["allowed_domains"] = config.web_search_allowed_domains
    elif config.web_search_blocked_domains:
        search_tool["blocked_domains"] = config.web_search_blocked_domains
        fetch_tool["blocked_domains"] = config.web_search_blocked_domains
    return [search_tool, fetch_tool]


_ENTRY_RE = re.compile(
    r"SOURCE:\s*(?P<url>\S+)\s*\n"
    r"TITLE:\s*(?P<title>.*?)\s*\n"
    r"DATE:\s*(?P<date>.*?)\s*\n"
    r"EXCERPT:\s*(?P<excerpt>.*?)(?=\n-{2,}|\Z)",
    re.DOTALL,
)


def _parse_researcher_output(text: str) -> list[SourceFinding]:
    """Parsing défensif du bloc SOURCE/TITLE/DATE/EXCERPT — une entrée malformée est
    simplement ignorée, cohérent avec le style de parsing déjà utilisé dans argument_graph.py."""
    findings: list[SourceFinding] = []
    for m in _ENTRY_RE.finditer(text):
        url = m.group("url").strip()
        if not url:
            continue
        try:
            domain = urlparse(url).netloc.replace("www.", "")
        except ValueError:
            domain = ""
        date = m.group("date").strip()
        findings.append(SourceFinding(
            url=url,
            title=m.group("title").strip(),
            domain=domain,
            date=None if date.lower() in ("", "unknown") else date,
            excerpt=" ".join(m.group("excerpt").split()),  # aplatit les retours à la ligne
        ))
    return findings


def _build_researcher_prompt(question_text: str) -> str:
    return f"""TOPIC FOR THE UPCOMING DEBATE:
{question_text}

Find current, trustworthy context for this topic following your instructions exactly."""


def _build_validation_prompt(findings: list[SourceFinding]) -> str:
    listing = "\n\n".join(
        f"URL: {f.url}\nDOMAIN: {f.domain}\nDATE: {f.date or 'unknown'}\nEXCERPT: {f.excerpt}"
        for f in findings
    )
    return f"Assess these {len(findings)} source(s):\n\n{listing}"


def format_research_briefing(findings: list[SourceFinding]) -> str:
    """Assemble le briefing final à partir des seules sources validées — pure formatting,
    aucun appel LLM (économie : l'assemblage ne coûte aucun token supplémentaire)."""
    validated = [f for f in findings if f.trustworthy]
    if not validated:
        return ""
    lines = ["CURRENT CONTEXT (sources web vérifiées) :"]
    for f in validated:
        lines.append(f"- [{f.domain}, {f.date or 'date inconnue'}] {f.excerpt}")
    return "\n".join(lines)


def run_research(
    client: "Anthropic",
    config: "DebateConfig",
    question_text: str,
) -> tuple[str, list[SourceFinding]]:
    """Exécute le pipeline recherche + validation (2 appels LLM au total).

    Retourne (briefing, findings). briefing == "" si web_search_enabled=False, si aucune
    source n'a été trouvée, ou si aucune source n'a passé la validation.
    """
    from .debate_config import resolve_model

    if not config.web_search_enabled:
        return "", []

    tools = build_search_tools(config)
    response = client.messages.create(
        model=resolve_model(config, "research", None, is_orchestrator=True),
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=config.researcher_prompt or DEFAULT_RESEARCHER_SYSTEM,
        messages=[{"role": "user", "content": _build_researcher_prompt(question_text)}],
        tools=tools,
    )
    text = next((b.text for b in reversed(response.content) if b.type == "text"), "")
    findings = _parse_researcher_output(text)
    if not findings:
        return "", []

    validation_response = client.messages.create(
        model=resolve_model(config, "research_validate", None, is_orchestrator=True),
        max_tokens=1024,
        system=config.source_validator_prompt or DEFAULT_SOURCE_VALIDATOR_SYSTEM,
        messages=[{"role": "user", "content": _build_validation_prompt(findings)}],
        output_config={"format": {"type": "json_schema", "schema": VALIDATION_SCHEMA}},
    )
    v_text = next(b.text for b in reversed(validation_response.content) if b.type == "text")
    try:
        verdicts = {v["url"]: v for v in json.loads(v_text).get("verdicts", [])}
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        verdicts = {}

    for f in findings:
        v = verdicts.get(f.url)
        if v:
            f.trustworthy = bool(v.get("trustworthy", False))
            f.validator_reason = str(v.get("reason", ""))

    return format_research_briefing(findings), findings

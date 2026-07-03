import unittest

from jarvis.debate_config import DebateConfig
from jarvis.research import (
    SourceFinding,
    _parse_researcher_output,
    build_search_tools,
    format_research_briefing,
)


def _config(**overrides) -> DebateConfig:
    base = dict(
        agent_model="claude-sonnet-4-6",
        orchestrator_model="claude-opus-4-8",
        web_search_enabled=True,
        web_search_max_uses=3,
        web_fetch_max_uses=2,
        web_fetch_max_content_tokens=3000,
    )
    base.update(overrides)
    return DebateConfig(**base)


class TestBuildSearchTools(unittest.TestCase):
    def test_bounds_are_applied(self):
        tools = build_search_tools(_config())
        search, fetch = tools
        self.assertEqual(search["type"], "web_search_20260209")
        self.assertEqual(search["max_uses"], 3)
        self.assertEqual(fetch["type"], "web_fetch_20260209")
        self.assertEqual(fetch["max_uses"], 2)
        self.assertEqual(fetch["max_content_tokens"], 3000)

    def test_allowed_domains_applied_to_both_tools(self):
        tools = build_search_tools(_config(web_search_allowed_domains=["reuters.com", "bloomberg.com"]))
        search, fetch = tools
        self.assertEqual(search["allowed_domains"], ["reuters.com", "bloomberg.com"])
        self.assertEqual(fetch["allowed_domains"], ["reuters.com", "bloomberg.com"])
        self.assertNotIn("blocked_domains", search)

    def test_allowed_domains_takes_priority_over_blocked(self):
        tools = build_search_tools(_config(
            web_search_allowed_domains=["reuters.com"],
            web_search_blocked_domains=["spamsite.com"],
        ))
        search, _ = tools
        self.assertIn("allowed_domains", search)
        self.assertNotIn("blocked_domains", search)

    def test_blocked_domains_used_when_no_allowed_list(self):
        tools = build_search_tools(_config(web_search_blocked_domains=["spamsite.com"]))
        search, fetch = tools
        self.assertEqual(search["blocked_domains"], ["spamsite.com"])
        self.assertEqual(fetch["blocked_domains"], ["spamsite.com"])

    def test_no_domain_restriction_when_neither_set(self):
        tools = build_search_tools(_config())
        search, fetch = tools
        self.assertNotIn("allowed_domains", search)
        self.assertNotIn("blocked_domains", search)
        self.assertNotIn("allowed_domains", fetch)


class TestParseResearcherOutput(unittest.TestCase):
    def test_parses_single_entry(self):
        text = (
            "SOURCE: https://www.reuters.com/markets/fed-rate-decision\n"
            "TITLE: Fed holds rates steady\n"
            "DATE: 2026-06-28\n"
            "EXCERPT: Fed holds rates | The Federal Reserve kept rates unchanged today. "
            "| Officials cited persistent inflation concerns. | Markets reacted modestly to the announcement.\n"
            "---"
        )
        findings = _parse_researcher_output(text)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.url, "https://www.reuters.com/markets/fed-rate-decision")
        self.assertEqual(f.domain, "reuters.com")
        self.assertEqual(f.title, "Fed holds rates steady")
        self.assertEqual(f.date, "2026-06-28")
        self.assertIn("Federal Reserve kept rates", f.excerpt)
        self.assertFalse(f.trustworthy)  # non validé par défaut

    def test_parses_multiple_entries(self):
        text = (
            "SOURCE: https://www.bloomberg.com/a\n"
            "TITLE: Title A\n"
            "DATE: 2026-06-01\n"
            "EXCERPT: header | first | middle | near-end\n"
            "---\n"
            "SOURCE: https://www.ft.com/b\n"
            "TITLE: Title B\n"
            "DATE: unknown\n"
            "EXCERPT: header2 | first2 | middle2 | near-end2\n"
            "---"
        )
        findings = _parse_researcher_output(text)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].domain, "bloomberg.com")
        self.assertEqual(findings[1].domain, "ft.com")
        self.assertIsNone(findings[1].date)  # "unknown" -> None

    def test_empty_text_returns_no_findings(self):
        self.assertEqual(_parse_researcher_output(""), [])

    def test_malformed_text_ignored_not_raised(self):
        findings = _parse_researcher_output("this is not the expected format at all")
        self.assertEqual(findings, [])

    def test_collapses_internal_newlines_in_excerpt(self):
        text = (
            "SOURCE: https://www.wsj.com/x\n"
            "TITLE: T\n"
            "DATE: 2026-01-01\n"
            "EXCERPT: line one\nline two   with   spaces\n"
            "---"
        )
        findings = _parse_researcher_output(text)
        self.assertEqual(len(findings), 1)
        self.assertNotIn("\n", findings[0].excerpt)
        self.assertNotIn("  ", findings[0].excerpt)


class TestFormatResearchBriefing(unittest.TestCase):
    def test_empty_findings_returns_empty_string(self):
        self.assertEqual(format_research_briefing([]), "")

    def test_only_trustworthy_sources_included(self):
        findings = [
            SourceFinding(url="u1", title="t1", domain="reuters.com", date="2026-06-01",
                          excerpt="fact one", trustworthy=True),
            SourceFinding(url="u2", title="t2", domain="spamsite.com", date=None,
                          excerpt="fact two", trustworthy=False),
        ]
        briefing = format_research_briefing(findings)
        self.assertIn("fact one", briefing)
        self.assertIn("reuters.com", briefing)
        self.assertNotIn("fact two", briefing)
        self.assertNotIn("spamsite.com", briefing)

    def test_all_untrustworthy_returns_empty_string(self):
        findings = [
            SourceFinding(url="u1", title="t1", domain="spamsite.com", date=None,
                          excerpt="fact", trustworthy=False),
        ]
        self.assertEqual(format_research_briefing(findings), "")

    def test_missing_date_shows_placeholder(self):
        findings = [
            SourceFinding(url="u1", title="t1", domain="reuters.com", date=None,
                          excerpt="fact", trustworthy=True),
        ]
        briefing = format_research_briefing(findings)
        self.assertIn("date inconnue", briefing)


if __name__ == "__main__":
    unittest.main()

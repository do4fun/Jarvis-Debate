"""
Vérifie que le câblage de la fonctionnalité "recherche web" (jarvis/research.py) est
cohérent à travers les modules : import propre, config du domaine finance, ordre des
phases dans le pipeline et dans le checkpoint.
"""
import unittest

from jarvis import checkpoint, cost_forecast, debate, debate_config, research, session_log
from jarvis.finance_config import build_finance_config


class TestModulesImportCleanly(unittest.TestCase):
    def test_research_module_has_expected_public_api(self):
        for name in ("run_research", "build_search_tools", "format_research_briefing", "SourceFinding"):
            self.assertTrue(hasattr(research, name), f"jarvis.research.{name} manquant")

    def test_debate_module_imports_research(self):
        self.assertTrue(hasattr(debate, "run_research"))

    def test_session_log_has_log_research(self):
        self.assertTrue(hasattr(session_log.SessionLog, "log_research"))


class TestFinanceConfigWebSearch(unittest.TestCase):
    def setUp(self):
        self.cfg = build_finance_config()

    def test_web_search_enabled_by_default_for_finance(self):
        self.assertTrue(self.cfg.web_search_enabled)

    def test_trusted_domains_configured(self):
        for domain in ("reuters.com", "bloomberg.com", "federalreserve.gov", "sec.gov"):
            self.assertIn(domain, self.cfg.web_search_allowed_domains)

    def test_web_search_source_type_has_credibility_weight(self):
        self.assertIn("web_search", self.cfg.evidence_source_weights)

    def test_max_uses_are_bounded_small(self):
        # Contrainte d'économie de tokens : bornes volontairement basses.
        self.assertLessEqual(self.cfg.web_search_max_uses, 5)
        self.assertLessEqual(self.cfg.web_fetch_max_uses, 3)


class TestPhaseOrdering(unittest.TestCase):
    def test_research_is_default_enabled_phase(self):
        cfg = debate_config.load_default_config()
        self.assertIn("research", cfg.enabled_phases)

    def test_research_runs_before_brainstorm_in_enabled_phases(self):
        cfg = debate_config.load_default_config()
        self.assertLess(
            cfg.enabled_phases.index("research"),
            cfg.enabled_phases.index("brainstorm"),
        )

    def test_research_is_first_checkpoint_phase(self):
        self.assertEqual(checkpoint.PHASES[0], "research")

    def test_research_precedes_brainstorm_in_checkpoint_phases(self):
        self.assertLess(
            checkpoint.PHASES.index("research"),
            checkpoint.PHASES.index("brainstorm"),
        )

    def test_new_debate_checkpoint_starts_at_research_phase(self):
        # run_debate._make_cp doit initialiser phase="research" pour que la phase ne soit
        # pas sautée par is_orchestrator_done sur un débat neuf (bug potentiel si laissé à
        # "brainstorm", qui a un index positionnel supérieur).
        import inspect
        source = inspect.getsource(debate.run_debate)
        self.assertIn('phase="research"', source)


class TestCostForecastAccountsForResearch(unittest.TestCase):
    def test_forecast_includes_research_lines_when_enabled(self):
        forecast = cost_forecast.compute_forecast(
            n_agents=5, n_questions=1, mode="concurrent",
            agent_model="claude-sonnet-4-6", orchestrator_model="claude-opus-4-8",
            iter_brainstorm=1, iter_thesis=1, iter_antithesis=1, iter_synthesis=1,
            web_search_enabled=True,
        )
        phases = [l.phase for l in forecast.lines]
        self.assertIn("Recherche web", phases)
        self.assertIn("Validation sources", phases)

    def test_forecast_omits_research_lines_when_disabled(self):
        forecast = cost_forecast.compute_forecast(
            n_agents=5, n_questions=1, mode="concurrent",
            agent_model="claude-sonnet-4-6", orchestrator_model="claude-opus-4-8",
            iter_brainstorm=1, iter_thesis=1, iter_antithesis=1, iter_synthesis=1,
            web_search_enabled=False,
        )
        phases = [l.phase for l in forecast.lines]
        self.assertNotIn("Recherche web", phases)

    def test_research_calls_bounded_to_two_regardless_of_agent_count(self):
        # Coeur de la contrainte d'économie : le coût de la recherche est constant, pas
        # proportionnel au nombre d'agents ni d'itérations.
        forecast_small = cost_forecast.compute_forecast(
            n_agents=2, n_questions=1, mode="concurrent",
            agent_model="claude-sonnet-4-6", orchestrator_model="claude-opus-4-8",
            iter_brainstorm=1, iter_thesis=1, iter_antithesis=1, iter_synthesis=1,
            web_search_enabled=True,
        )
        forecast_large = cost_forecast.compute_forecast(
            n_agents=8, n_questions=1, mode="concurrent",
            agent_model="claude-sonnet-4-6", orchestrator_model="claude-opus-4-8",
            iter_brainstorm=3, iter_thesis=3, iter_antithesis=3, iter_synthesis=3,
            web_search_enabled=True,
        )
        research_calls_small = sum(
            l.calls for l in forecast_small.lines if l.phase in ("Recherche web", "Validation sources")
        )
        research_calls_large = sum(
            l.calls for l in forecast_large.lines if l.phase in ("Recherche web", "Validation sources")
        )
        self.assertEqual(research_calls_small, 2)
        self.assertEqual(research_calls_large, 2)


if __name__ == "__main__":
    unittest.main()

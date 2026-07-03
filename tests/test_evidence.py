import unittest

from jarvis.evidence import Evidence, argument_credibility, freshness_decay


class TestFreshnessDecay(unittest.TestCase):
    """h(e_j): exponential decay based on evidence age."""

    def test_missing_date_returns_neutral_1(self):
        self.assertEqual(freshness_decay(None), 1.0)

    def test_invalid_date_returns_neutral_1(self):
        self.assertEqual(freshness_decay("not-a-date"), 1.0)

    def test_recent_date_close_to_1(self):
        recent = freshness_decay("2026-06-25", reference_date="2026-07-02")  # 7 days old
        self.assertGreater(recent, 0.9)
        self.assertLess(recent, 1.0)

    def test_old_date_close_to_0(self):
        old = freshness_decay("2023-01-01", reference_date="2026-07-02")  # ~3.5 years old
        self.assertLess(old, 0.02)

    def test_same_day_returns_exactly_1(self):
        same_day = freshness_decay("2026-07-02", reference_date="2026-07-02")
        self.assertAlmostEqual(same_day, 1.0)

    def test_half_life_point(self):
        # At exactly one half-life, decay should be 0.5
        half_life = freshness_decay("2026-01-03", reference_date="2026-07-02", half_life_days=180.0)
        self.assertAlmostEqual(half_life, 0.5, places=2)


class TestArgumentCredibility(unittest.TestCase):
    """C(a_i) = (1/m) * sum_j( w_s(e_j) * r(e_j) * h(e_j) )"""

    def test_no_evidence_returns_0(self):
        self.assertEqual(argument_credibility([], {"market_data": 1.0}), 0.0)

    def test_matches_manual_calculation(self):
        evidence_list = [
            Evidence(source_type="market_data", reference="r1", content="c1", reliability=1.0, date="2026-07-01"),
            Evidence(source_type="filing", reference="r2", content="c2", reliability=0.5, date=None),
        ]
        source_weights = {"market_data": 1.0, "filing": 0.9}
        cred = argument_credibility(evidence_list, source_weights, reference_date="2026-07-02")

        h1 = freshness_decay("2026-07-01", "2026-07-02")
        expected = (1.0 * 1.0 * h1 + 0.9 * 0.5 * 1.0) / 2
        self.assertAlmostEqual(cred, expected)

    def test_unknown_source_type_defaults_weight_to_1(self):
        evidence_list = [Evidence(source_type="unknown_type", reference="r", content="c", reliability=1.0)]
        cred = argument_credibility(evidence_list, {"market_data": 1.0})
        self.assertAlmostEqual(cred, 1.0)

    def test_low_reliability_lowers_credibility(self):
        evidence_list = [Evidence(source_type="market_data", reference="r", content="c", reliability=0.1)]
        cred = argument_credibility(evidence_list, {"market_data": 1.0})
        self.assertAlmostEqual(cred, 0.1)


if __name__ == "__main__":
    unittest.main()

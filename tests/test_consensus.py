import unittest

from jarvis.argument_graph import Claim
from jarvis.consensus import (
    compute_consensus,
    compute_stance,
    derive_decision_options,
    update_trust_weights,
)


class TestComputeStance(unittest.TestCase):
    """v_i(o) = sign(sum_k lambda_k * s_{i,k}(o))"""

    def test_positive_sum_returns_1(self):
        self.assertEqual(compute_stance({"a": 1.0, "b": 1.0}, {"a": 1.0, "b": 1.0}), 1)

    def test_negative_sum_returns_minus_1(self):
        self.assertEqual(compute_stance({"a": -1.0, "b": -1.0}, {"a": 1.0, "b": 1.0}), -1)

    def test_empty_scores_returns_0(self):
        self.assertEqual(compute_stance({}, {"a": 1.0}), 0)

    def test_zero_sum_returns_0(self):
        self.assertEqual(compute_stance({"a": 0.0}, {"a": 1.0}), 0)

    def test_missing_lambda_defaults_to_1(self):
        # criterion not present in lambda_weights falls back to weight 1.0
        self.assertEqual(compute_stance({"unknown": 1.0}, {}), 1)


class TestDeriveDecisionOptions(unittest.TestCase):
    def test_dedups_by_lower_strip(self):
        claims = [
            Claim("C1", "Agent A", "content1", "Bullish"),
            Claim("C2", "Agent B", "content2", "bullish "),
            Claim("C3", "Agent C", "content3", "Bearish"),
        ]
        self.assertEqual(derive_decision_options(claims), ["Bullish", "Bearish"])

    def test_empty_claims_returns_empty(self):
        self.assertEqual(derive_decision_options([]), [])


class TestComputeConsensus(unittest.TestCase):
    """S(o) = sum_i(w_i * v_i(o)) / sum_i(w_i) ; acceptance: S(o) >= theta"""

    def setUp(self):
        self.claims = [
            Claim("C1", "A", "c1", "BUY", criterion_scores={"relevance": 1.0}),
            Claim("C2", "B", "c2", "BUY", criterion_scores={"relevance": 1.0}),
            Claim("C3", "C", "c3", "SELL", criterion_scores={"relevance": 1.0}),
        ]
        self.trust_weights = {"A": 1.0, "B": 1.0, "C": 1.0}
        self.lambda_weights = {"relevance": 1.0}

    def test_scores_match_manual_calculation(self):
        # v_A(BUY)=1, v_B(BUY)=1, v_C(BUY)=0 (no claim on BUY) -> S(BUY) = 2/3
        # v_A(SELL)=0, v_B(SELL)=0, v_C(SELL)=1 -> S(SELL) = 1/3
        result = compute_consensus(self.claims, self.trust_weights, self.lambda_weights, theta=0.5)
        self.assertAlmostEqual(result.scores["BUY"], 2 / 3)
        self.assertAlmostEqual(result.scores["SELL"], 1 / 3)

    def test_acceptance_gate_theta(self):
        result = compute_consensus(self.claims, self.trust_weights, self.lambda_weights, theta=0.5)
        self.assertEqual(result.accepted_options, ["BUY"])
        self.assertEqual(result.winning_option, "BUY")

    def test_theta_boundary_is_inclusive(self):
        # S(BUY) == 2/3 exactly; theta == 2/3 must still accept (>=, not >)
        result = compute_consensus(self.claims, self.trust_weights, self.lambda_weights, theta=2 / 3)
        self.assertIn("BUY", result.accepted_options)

    def test_no_option_accepted_when_theta_too_high(self):
        result = compute_consensus(self.claims, self.trust_weights, self.lambda_weights, theta=0.99)
        self.assertEqual(result.accepted_options, [])
        self.assertIsNone(result.winning_option)

    def test_denominator_uses_all_participants(self):
        # An agent with no claim at all still counts in sum_i(w_i), diluting S(o).
        trust_weights = {"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0}  # D has no claims
        result = compute_consensus(self.claims, trust_weights, self.lambda_weights, theta=0.5)
        self.assertAlmostEqual(result.scores["BUY"], 2 / 4)

    def test_multiple_claims_same_agent_same_option_averaged(self):
        claims = [
            Claim("C1", "A", "c1", "BUY", criterion_scores={"relevance": 1.0}),
            Claim("C2", "A", "c2", "BUY", criterion_scores={"relevance": -1.0}),
        ]
        result = compute_consensus(claims, {"A": 1.0}, self.lambda_weights, theta=0.5)
        # average criterion_scores = 0.0 -> sign(0) = 0 -> S(BUY) = 0/1 = 0
        self.assertEqual(result.stances["A"]["BUY"], 0)
        self.assertAlmostEqual(result.scores["BUY"], 0.0)


class TestUpdateTrustWeights(unittest.TestCase):
    """w_i(t+1) = (1-alpha)*w_i(t) + alpha*a_i(t)"""

    def test_ema_formula(self):
        old = {"A": 1.0, "B": 0.5}
        accuracy = {"A": 0.8, "B": 0.2}
        new = update_trust_weights(old, accuracy, alpha=0.2)
        self.assertAlmostEqual(new["A"], 0.8 * 1.0 + 0.2 * 0.8)
        self.assertAlmostEqual(new["B"], 0.8 * 0.5 + 0.2 * 0.2)

    def test_unknown_agent_defaults_current_weight_to_1(self):
        new = update_trust_weights({}, {"NewAgent": 0.5}, alpha=0.2)
        self.assertAlmostEqual(new["NewAgent"], 0.8 * 1.0 + 0.2 * 0.5)

    def test_alpha_zero_keeps_weight_unchanged(self):
        old = {"A": 0.7}
        new = update_trust_weights(old, {"A": 0.1}, alpha=0.0)
        self.assertAlmostEqual(new["A"], 0.7)

    def test_alpha_one_uses_accuracy_directly(self):
        old = {"A": 0.7}
        new = update_trust_weights(old, {"A": 0.9}, alpha=1.0)
        self.assertAlmostEqual(new["A"], 0.9)


if __name__ == "__main__":
    unittest.main()

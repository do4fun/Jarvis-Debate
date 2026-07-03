import unittest

from jarvis.agent_persona import AgentPersona
from jarvis.debate import AgentState, _topo_sort_group


def _state(name: str, wait_for=None) -> AgentState:
    return AgentState(persona=AgentPersona(
        name=name,
        system_prompt="",
        wait_for=wait_for or [],
    ))


class TestTopoSortGroup(unittest.TestCase):
    """Ordonnanceur par dépendances strictes (speaking_mode='dependency')."""

    def test_linear_chain_order(self):
        a = _state("A")
        b = _state("B", wait_for=["A"])
        c = _state("C", wait_for=["B"])
        group = [c, a, b]  # deliberately out of order
        ordered = _topo_sort_group(group, {"A", "B", "C"})
        self.assertEqual([s.persona.name for s in ordered], ["A", "B", "C"])

    def test_no_dependencies_deterministic_alphabetical(self):
        group = [_state("C"), _state("A"), _state("B")]
        ordered = _topo_sort_group(group, {"A", "B", "C"})
        self.assertEqual([s.persona.name for s in ordered], ["A", "B", "C"])

    def test_diamond_dependency(self):
        a = _state("A")
        b = _state("B", wait_for=["A"])
        c = _state("C", wait_for=["A"])
        d = _state("D", wait_for=["B", "C"])
        group = [d, c, b, a]
        ordered = [s.persona.name for s in _topo_sort_group(group, {"A", "B", "C", "D"})]
        self.assertEqual(ordered.index("A"), 0)
        self.assertLess(ordered.index("B"), ordered.index("D"))
        self.assertLess(ordered.index("C"), ordered.index("D"))

    def test_cycle_raises_value_error(self):
        a = _state("A", wait_for=["B"])
        b = _state("B", wait_for=["A"])
        with self.assertRaises(ValueError):
            _topo_sort_group([a, b], {"A", "B"})

    def test_unknown_dependency_raises_value_error(self):
        a = _state("A", wait_for=["Ghost"])
        with self.assertRaises(ValueError):
            _topo_sort_group([a], {"A"})

    def test_cross_group_dependency_ignored_by_topo_sort(self):
        # "Other" is not in the group (cross-group dep) — must not affect in-group ordering
        # or raise here (cross-group deps are checked separately via `completed`).
        a = _state("A", wait_for=["OutsideAgent"])
        ordered = _topo_sort_group([a], {"A", "OutsideAgent"})
        self.assertEqual([s.persona.name for s in ordered], ["A"])


if __name__ == "__main__":
    unittest.main()

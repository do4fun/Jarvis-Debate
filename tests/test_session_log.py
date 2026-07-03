"""Vérifie que SessionLog horodate chaque phase loguée, pour permettre de reconstruire
la séquence chronologique exacte d'une session (jarvis/session_log.py)."""
import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jarvis import session_log as session_log_module
from jarvis.session_log import SessionLog

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


class TestSessionLogTimeline(unittest.TestCase):
    def setUp(self):
        self._tmpdir = TemporaryDirectory()
        self._original_dir = session_log_module.SESSIONS_DIR
        session_log_module.SESSIONS_DIR = Path(self._tmpdir.name)

    def tearDown(self):
        session_log_module.SESSIONS_DIR = self._original_dir
        self._tmpdir.cleanup()

    def test_timeline_starts_empty(self):
        log = SessionLog("s1")
        self.assertEqual(log._data["timeline"], [])

    def test_each_log_phase_call_appends_one_timeline_entry(self):
        log = SessionLog("s2")
        log.log_plan("un plan")
        log.log_theses({"A": "these A"})
        self.assertEqual(len(log._data["timeline"]), 2)

    def test_timeline_entries_have_iso_timestamp(self):
        log = SessionLog("s3")
        log.log_plan("un plan")
        entry = log._data["timeline"][0]
        self.assertIn("timestamp", entry)
        self.assertTrue(_ISO_RE.match(entry["timestamp"]), entry["timestamp"])

    def test_timeline_preserves_call_order(self):
        log = SessionLog("s4")
        log.log_plan("plan")
        log.log_theses({"A": "t"})
        log.log_antitheses({"A": "a"})
        phases_in_order = [e["phase"] for e in log._data["timeline"]]
        self.assertEqual(phases_in_order, ["plan", "thesis", "antithesis"])

    def test_repeated_phase_logs_all_recorded_not_overwritten_in_timeline(self):
        # `phases` (snapshot dict) overwrites on repeat, mais `timeline` doit garder
        # une trace de chaque appel — c'est ce qui permet la reconstruction chronologique
        # même quand une phase est loguée plusieurs fois (ex: itérations de synthèse).
        log = SessionLog("s5")
        log.log_synthesis({"v": 1})
        log.log_synthesis({"v": 2})
        self.assertEqual(len(log._data["timeline"]), 2)
        self.assertEqual(log._data["phases"]["synthesis"], {"v": 2})  # dernier gagne

    def test_written_file_contains_timeline(self):
        log = SessionLog("s6")
        log.log_plan("plan")
        on_disk = json.loads(log.path.read_text(encoding="utf-8"))
        self.assertIn("timeline", on_disk)
        self.assertEqual(len(on_disk["timeline"]), 1)
        self.assertEqual(on_disk["timeline"][0]["phase"], "plan")


if __name__ == "__main__":
    unittest.main()

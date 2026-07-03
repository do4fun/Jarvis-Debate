#!/usr/bin/env python
"""
Lance la suite de tests unitaires du projet (tests/).

Usage :
    python run_tests.py
"""

import sys
import unittest
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).parent
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(project_root / "tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

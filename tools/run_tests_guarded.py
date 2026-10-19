"""Run the whole ZZLUXORA test suite with every modal dialog neutralised.

Usage:
    cd <repo> && PYTHONPATH=<repo>/tools python3 tools/run_tests_guarded.py

Two runners are used because the suite is mixed:
  * unittest discovery covers tests/test_*.py written with unittest.TestCase
  * pytest covers the newer pytest-style modules (function-based tests)

The dialog guard is installed before anything imports the UI, so no QMessageBox,
QFileDialog or QInputDialog can appear on screen or block the run.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import _autodialog_guard  # noqa: F401  (installs the dialog stubs)

if not _autodialog_guard.GUARDED:
    print("warning: dialog guard could not be installed", file=sys.stderr)


def _is_pytest_module(path) -> bool:
    """True for a test module written for pytest rather than unittest.

    The marker is a module-level ``import pytest``, which every pytest-style
    module in this repository carries.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    return "import pytest" in text


def collect_unittest_modules(tests_dir) -> list[str]:
    """Test module names the unittest phase should run.

    Excludes the pytest-style modules so no file is executed twice. Kept as its
    own function so the rule can be tested directly instead of being inferred
    from a full suite run.
    """
    from pathlib import Path

    return [
        f"{Path(tests_dir).name}.{path.stem}"
        for path in sorted(Path(tests_dir).glob("test_*.py"))
        if not _is_pytest_module(path)
    ]


def run_unittest_suite() -> bool:
    """Run the unittest-style modules, leaving pytest-style ones to pytest.

    Discovery used to sweep every test_*.py file, so the classes inside the
    pytest-style modules ran here as well as under pytest. test_suite_hygiene.py
    holds a TestCase class, so its tests executed twice and its module was
    imported twice, adding wall-clock time for no extra coverage. Filter them out
    so each test runs exactly once, matching what the pytest step's docstring
    already claimed.
    """
    from pathlib import Path

    suite = unittest.TestLoader().loadTestsFromNames(collect_unittest_modules(Path("tests")))
    return unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful()


def run_pytest_suite() -> bool:
    """Run pytest-style modules, if pytest is available.

    Only the modules written for pytest are listed, so the unittest-style
    modules are not executed twice.
    """
    pytest_modules = []
    from pathlib import Path

    for path in sorted(Path("tests").glob("test_*.py")):
        if _is_pytest_module(path):
            pytest_modules.append(str(path))

    if not pytest_modules:
        return True

    try:
        import pytest
    except ImportError:
        print("note: pytest not installed, skipping", pytest_modules, file=sys.stderr)
        return True

    return pytest.main(["-q", *pytest_modules]) == 0


def main() -> int:
    unittest_ok = run_unittest_suite()
    pytest_ok = run_pytest_suite()
    return 0 if (unittest_ok and pytest_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())

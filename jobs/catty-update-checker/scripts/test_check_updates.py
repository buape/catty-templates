import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_updates as checker
import update_state


class UpdateCheckerTests(unittest.TestCase):
    def run_check(self, state, version="0.7.0", installed=True):
        info = {"formulae": [{"full_name": checker.FORMULA, "installed": [{"version": "0.6.0"}] if installed else []}]}
        outdated = {"formulae": [{"name": "catty", "current_version": version, "pinned": True}] if version else []}
        output = io.StringIO()
        with patch.object(checker, "STATE", state), patch.object(checker, "brew_command", return_value="brew"), patch.object(checker, "run_brew", side_effect=["", json.dumps(info), json.dumps(outdated)]) as brew, contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = checker.main()
        self.assertEqual(brew.call_args_list[0].args, ("brew", "update"))
        return code, json.loads(output.getvalue()) if output.getvalue() else None

    def test_new_pinned_update_and_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            for _ in range(2):
                code, result = self.run_check(state)
                self.assertEqual(code, 0)
                self.assertTrue(result["run"])

    def test_acknowledged_update_suppressed_but_next_version_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            self.run_check(state)
            with patch.object(update_state, "STATE", state), patch("sys.argv", ["update_state.py", "mark-notified"]), contextlib.redirect_stdout(io.StringIO()):
                update_state.main()
            self.assertFalse(self.run_check(state)[1]["run"])
            self.assertTrue(self.run_check(state, "0.8.0")[1]["run"])

    def test_up_to_date(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(self.run_check(Path(folder), None)[1]["run"])

    def test_not_installed_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.run_check(Path(folder), installed=False)[0], 1)

    def test_outdated_exit_one_with_json_is_accepted(self):
        import subprocess
        result = subprocess.CompletedProcess([], 1, '{"formulae": []}', "")
        with patch.object(checker.subprocess, "run", return_value=result):
            self.assertEqual(json.loads(checker.run_brew("brew", "outdated", "--json=v2")), {"formulae": []})
            with self.assertRaises(RuntimeError):
                checker.run_brew("brew", "update")

    def test_brew_failure_fails_check(self):
        with patch.object(checker, "brew_command", return_value="brew"), patch.object(checker, "run_brew", side_effect=RuntimeError("brew failed")), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(checker.main(), 1)


if __name__ == "__main__":
    unittest.main()

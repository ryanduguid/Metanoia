"""Exercise the topics script with a local GitHub CLI stub."""

import shutil
import subprocess
import unittest
from pathlib import Path


class TopicScriptTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pwsh') or shutil.which('powershell'), 'PowerShell required')
    def test_failed_edit_stops_before_success_message(self):
        script = Path(__file__).with_name('apply-topics.ps1')
        command = (
            'function gh { $global:LASTEXITCODE = 1 }; '
            "& '" + str(script).replace("'", "''") + "'"
        )
        result = subprocess.run(
            [shutil.which('pwsh') or shutil.which('powershell'), '-NoProfile', '-Command', command],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('successfully updated', result.stdout)
        self.assertIn('Failed to update topics', result.stderr)

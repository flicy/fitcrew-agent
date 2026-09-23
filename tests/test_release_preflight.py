"""Privacy and failure gates for the read-only server diagnostic."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "release_preflight", Path(__file__).resolve().parents[1] / "infra/tencent/release-preflight.py"
)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class ReleasePreflightTests(unittest.TestCase):
    def test_failures_do_not_forward_command_output(self):
        failed = subprocess.CompletedProcess([], 1, "PRIVATE_TOKEN", "PRIVATE_DATABASE_URL")
        with patch.object(preflight.subprocess, "run", return_value=failed):
            self.assertIsNone(preflight.query(["docker", "inspect"]))
        with patch.object(preflight.subprocess, "run", side_effect=subprocess.TimeoutExpired([], 20)):
            self.assertIsNone(preflight.query(["docker", "inspect"]))

    def test_missing_repository_does_not_invoke_commands(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(preflight, "query") as query:
            result = preflight.collect(Path(folder) / "missing")
            self.assertEqual(result["blockers"], ["repository_directory_unavailable"])
            query.assert_not_called()

    def test_healthy_metadata_does_not_claim_restore_or_submission(self):
        commands = []

        def query(argv):
            commands.append(argv)
            if argv[0] == "git":
                return "a" * 40 if argv[-1] == "HEAD" else ""
            if argv[1] == "inspect":
                return "|".join(("b" * 64, "sha256:" + "c" * 64,
                                 "running", "healthy", "2026-09-16T02:10:00Z"))
            self.assertEqual(argv[:5], ["docker", "exec", "--env",
                                      "PGOPTIONS=-c default_transaction_read_only=on",
                                      "fitcrew-bodyos-db-1"])
            self.assertEqual(argv[-1], "SELECT version_num FROM alembic_version;")
            return "0004_product_records"

        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            runtime = repo / "infra/tencent/runtime"
            (runtime / "backups").mkdir(parents=True)
            for filename in (".env.runtime", "backup.key", "backups/bodyos-example.sql.enc"):
                (runtime / filename).write_text("PRIVATE_CONTENT_MUST_NOT_BE_READ")
            usage = preflight.shutil._ntuple_diskusage(100 * 1024**3, 80 * 1024**3, 20 * 1024**3)
            with patch.object(preflight, "query", side_effect=query), \
                 patch.object(preflight.shutil, "disk_usage", return_value=usage), \
                 patch.object(Path, "read_text", side_effect=AssertionError("No private file reads")):
                result = preflight.collect(repo)
        self.assertEqual(result["blockers"], [])
        self.assertFalse(result["restore_verified"])
        self.assertFalse(result["deployment_performed"])
        self.assertFalse(result["platform_submission_verified"])
        self.assertNotIn("PRIVATE_CONTENT", json.dumps(result))
        self.assertEqual(len(commands), 8)

    def test_low_disk_and_unexpected_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(preflight, "query", return_value="PRIVATE_UNEXPECTED_OUTPUT"), \
             patch.object(preflight.shutil, "disk_usage", return_value=
                          preflight.shutil._ntuple_diskusage(60 * 1024**3, 59 * 1024**3, 1024**3)):
            result = preflight.collect(Path(folder))
        self.assertIn("less_than_10_GiB_build_headroom", result["blockers"])
        self.assertIn("database_revision_unavailable", result["blockers"])
        self.assertIsNone(result["checkout_revision"])
        self.assertEqual(result["containers"], {})
        self.assertNotIn("PRIVATE_UNEXPECTED_OUTPUT", json.dumps(result))


if __name__ == "__main__":
    unittest.main()

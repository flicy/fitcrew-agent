import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def operations(tmp_path):
    scripts = tmp_path / "infra" / "tencent"
    runtime = scripts / "runtime"
    runtime.mkdir(parents=True)
    (runtime / ".env.runtime").write_text("# synthetic test only\n")
    (runtime / "backup.key").write_text("synthetic-backup-key")
    for name in ("backup.sh", "restore-test.sh"):
        shutil.copy(ROOT / "infra" / "tencent" / name, scripts / name)
    commands = tmp_path / "commands"
    commands.mkdir()
    docker = commands / "docker"
    docker.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        "from pathlib import Path\n"
        "a=sys.argv[1:]\n"
        "with open(os.environ['TEST_TRACE'], 'a') as f: f.write(' '.join(a)+'\\n')\n"
        "if 'pg_dump' in a:\n"
        " print('CREATE TABLE synthetic_test (id integer);')\n"
        " sys.exit(int(os.environ.get('TEST_DUMP_EXIT', '0')))\n"
        "if 'psql' in a:\n"
        " if '-c' in a: print(os.environ.get('TEST_TABLE_COUNT', '20'))\n"
        " else: sys.stdin.read()\n"
        " sys.exit(int(os.environ.get('TEST_RESTORE_EXIT', '0')))\n"
    )
    docker.chmod(0o755)
    env = {**os.environ, "PATH": f"{commands}:{os.environ['PATH']}",
           "TEST_TRACE": str(tmp_path / "trace")}
    return scripts, runtime, env


def run(scripts, env, name, *args):
    return subprocess.run(
        ["bash", str(scripts / name), *map(str, args)],
        env=env, text=True, capture_output=True, timeout=15,
    )


def test_failed_database_dump_cannot_publish_a_successful_backup(operations):
    scripts, runtime, env = operations
    result = run(scripts, {**env, "TEST_DUMP_EXIT": "23"}, "backup.sh")
    assert result.returncode != 0
    assert "backup created" not in result.stdout
    assert not list((runtime / "backups").glob("bodyos-*.sql.enc"))
    assert not list((runtime / "backups").glob("*.partial"))


@pytest.mark.parametrize("failure", ["corrupt", "psql", "schema"])
def test_restore_failure_propagates_and_cleans_test_database(operations, failure):
    scripts, runtime, env = operations
    assert run(scripts, env, "backup.sh").returncode == 0
    backup = next((runtime / "backups").glob("bodyos-*.sql.enc"))
    if failure == "corrupt":
        backup.write_bytes(b"invalid encrypted backup")
    elif failure == "psql":
        env = {**env, "TEST_RESTORE_EXIT": "24"}
    else:
        env = {**env, "TEST_TABLE_COUNT": "2"}
    result = run(scripts, env, "restore-test.sh", backup)
    assert result.returncode != 0
    assert "Restore test passed" not in result.stdout
    last_command = Path(env["TEST_TRACE"]).read_text().splitlines()[-1]
    assert "dropdb --if-exists -U bodyos bodyos_restore_test" in last_command


def test_encrypted_backup_restore_success(operations):
    scripts, runtime, env = operations
    assert run(scripts, env, "backup.sh").returncode == 0
    backup = next((runtime / "backups").glob("bodyos-*.sql.enc"))
    assert b"CREATE TABLE" not in backup.read_bytes()
    result = run(scripts, env, "restore-test.sh", backup)
    assert result.returncode == 0, result.stderr
    assert "Restore test passed" in result.stdout

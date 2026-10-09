"""Stage only committed API sources for a CloudBase source deployment."""

import argparse
import json
import subprocess
from pathlib import Path

SOURCE_PATHS = (
    "Dockerfile",
    "pyproject.toml",
    "uv.lock",
    "alembic.ini",
    "apps/api/bodyos_api",
    "apps/api/migrations",
    "infra/tencent/api-entrypoint.sh",
    "infra/tencent/cloudbase-api-entrypoint.sh",
)
REQUIRED_FILES = frozenset(SOURCE_PATHS[:4] + SOURCE_PATHS[-2:])


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root)


def stage(output: Path) -> dict[str, object]:
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip()).resolve()
    output = output.resolve()
    if output.is_relative_to(root):
        raise ValueError("deployment stage must be outside the source worktree")
    if output.exists():
        raise ValueError("deployment stage already exists")
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("commit all tracked release changes before staging")

    head = git(root, "rev-parse", "HEAD").decode().strip()
    files = git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", *SOURCE_PATHS)
    names = files.decode().splitlines()
    if not REQUIRED_FILES.issubset(names) or not names:
        raise ValueError("release commit lacks required API build files")

    output.mkdir(parents=True)
    for name in names:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git(root, "show", f"HEAD:{name}"))
    return {"source_commit": head, "staging_directory": str(output), "file_count": len(names)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.output), sort_keys=True))


if __name__ == "__main__":
    main()

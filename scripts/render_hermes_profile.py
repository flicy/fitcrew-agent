#!/usr/bin/env python3
"""Render the dedicated BodyOS Hermes profile without logging secrets."""

import argparse
import os
import shutil
from pathlib import Path

import yaml


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"required environment variable is missing: {name}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", type=Path, default=Path("/app"))
    parser.add_argument("--profile-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.app_root
    profile = args.profile_dir
    profile.mkdir(parents=True, exist_ok=True, mode=0o700)

    for name in ("AGENTS.md", "SOUL.md", "HERMES.md"):
        shutil.copy2(root / "agent" / name, profile / name)
    for relative in (
        "memories/groups",
        "memories/private",
        "memories/daily",
        "scripts",
        "plugins/bodyos_guard",
        "hooks/bodyos-envelope",
        ".bodyos-sanitized",
    ):
        (profile / relative).mkdir(parents=True, exist_ok=True, mode=0o700)
    for source in (root / "memories").rglob("*.md"):
        destination = profile / source.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(source, destination)
    for name in ("feishu_group_watcher.py", "add_group_rule.py", "add-group.sh"):
        shutil.copy2(root / "scripts" / name, profile / "scripts" / name)
    integrations = root / "integrations/hermes"
    for source, destination in (
        (integrations / "bodyos_guard/plugin.yaml", profile / "plugins/bodyos_guard/plugin.yaml"),
        (integrations / "bodyos_guard/__init__.py", profile / "plugins/bodyos_guard/__init__.py"),
        (integrations / "gateway_hook/HOOK.yaml", profile / "hooks/bodyos-envelope/HOOK.yaml"),
        (integrations / "gateway_hook/handler.py", profile / "hooks/bodyos-envelope/handler.py"),
    ):
        shutil.copy2(source, destination)

    config = yaml.safe_load((root / "config/config.template.yaml").read_text())
    config["model"]["base_url"] = required("BODYOS_MODEL_BASE_URL")
    config["hooks_auto_accept"] = True
    group_id = os.environ.get("FEISHU_ALLOWED_GROUP_ID", "").strip()
    if group_id:
        config["platforms"]["feishu"]["extra"]["group_rules"] = {
            group_id: {"policy": "open", "require_mention": True}
        }
    (profile / "config.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    os.chmod(profile / "config.yaml", 0o600)
    os.chmod(profile / ".bodyos-sanitized", 0o700)
    (profile / ".bodyos-synchronous-dispatch").write_text("enabled\n", encoding="utf-8")
    os.chmod(profile / ".bodyos-synchronous-dispatch", 0o600)
    print("BodyOS Hermes profile rendered (secrets omitted)")


if __name__ == "__main__":
    main()

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[3]


def test_renderer_builds_a_complete_fail_closed_bodyos_profile(tmp_path: Path) -> None:
    profile = tmp_path / "bodyos-profile"
    environment = {
        **os.environ,
        "BODYOS_MODEL_BASE_URL": "https://bodyos.example.test/v1",
        "FEISHU_ALLOWED_GROUP_ID": "oc_bodyos_group",
    }

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/render_hermes_profile.py"),
            "--app-root",
            str(ROOT),
            "--profile-dir",
            str(profile),
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert (profile / "AGENTS.md").read_text() == (ROOT / "agent/AGENTS.md").read_text()
    assert (profile / "hooks/bodyos-envelope/handler.py").is_file()
    assert (profile / "plugins/bodyos_guard/__init__.py").is_file()

    config = yaml.safe_load((profile / "config.yaml").read_text())
    assert config["model"]["base_url"] == "https://bodyos.example.test/v1"
    assert config["plugins"]["enabled"] == ["bodyos_guard"]
    assert config["hooks_auto_accept"] is True
    assert config["group_sessions_per_user"] is True
    assert config["platforms"]["feishu"]["extra"]["group_rules"] == {
        "oc_bodyos_group": {"policy": "open", "require_mention": True}
    }
    assert (profile / ".bodyos-synchronous-dispatch").is_file()

    seed = json.loads((ROOT / "cron/jobs.seed.json").read_text(encoding="utf-8"))
    assert seed["jobs"] == []


def test_rendered_rules_allow_only_bound_controlled_identities_in_private_coaching(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "bodyos-profile"
    environment = {
        **os.environ,
        "BODYOS_MODEL_BASE_URL": "https://bodyos.example.test/v1",
    }

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/render_hermes_profile.py"),
            "--app-root",
            str(ROOT),
            "--profile-dir",
            str(profile),
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    hermes_rules = (profile / "HERMES.md").read_text(encoding="utf-8")
    soul = (profile / "SOUL.md").read_text(encoding="utf-8")
    assert "explicitly bound, controlled-allowlisted BodyOS identities" in hermes_rules
    assert "Unknown and uninvited users remain denied" in hermes_rules
    assert "FEISHU_ALLOW_ALL_USERS=false" in hermes_rules
    assert "fail closed" in hermes_rules
    assert "only the owner in `FEISHU_ALLOWED_USERS` may use DMs" not in hermes_rules
    assert "only in DMs from explicitly bound, controlled-allowlisted BodyOS identities" in soul
    assert "fixed low-sensitivity behavior tokens" in hermes_rules
    assert "no group model is invoked" in hermes_rules
    assert "no identity, personal feature, private excerpt" in hermes_rules


def test_rendered_rules_allow_only_published_shared_knowledge_in_group_coaching(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "bodyos-profile"
    environment = {
        **os.environ,
        "BODYOS_MODEL_BASE_URL": "https://bodyos.example.test/v1",
    }

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/render_hermes_profile.py"),
            "--app-root",
            str(ROOT),
            "--profile-dir",
            str(profile),
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    agents = (profile / "AGENTS.md").read_text(encoding="utf-8")
    hermes = (profile / "HERMES.md").read_text(encoding="utf-8")
    soul = (profile / "SOUL.md").read_text(encoding="utf-8")
    rendered_rules = "\n".join((agents, hermes, soul))

    assert "published shared expert knowledge" in rendered_rules
    assert "private excerpts" in rendered_rules
    assert "proactive group coaching" in rendered_rules.lower()
    assert "locally reviewed title/page-cited template" in rendered_rules
    assert "no group model is invoked" in rendered_rules
    assert "bodyos-public.v1" not in rendered_rules
    assert "bodyos-public.v2" not in rendered_rules

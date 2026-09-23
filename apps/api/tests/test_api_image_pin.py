import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def test_api_pin_preserves_existing_service_tag_and_credentials(tmp_path):
    runtime = tmp_path / ".env.runtime"
    runtime.write_text("FITCREW_IMAGE_TAG=old-image\nBODYOS_INTERNAL_TOKEN=synthetic\n")
    tag = "a" * 40
    result = subprocess.run(
        [sys.executable, str(ROOT / "infra/tencent/set-runtime-image.py"),
         "--file", str(runtime), "--service", "api", tag],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert runtime.read_text().splitlines() == [
        "FITCREW_IMAGE_TAG=old-image", "BODYOS_INTERNAL_TOKEN=synthetic",
        f"FITCREW_API_IMAGE_TAG={tag}",
    ]
    assert runtime.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("script", ["deploy.sh", "rollback.sh"])
def test_legacy_full_deploy_refuses_independently_pinned_api(tmp_path, script):
    root = tmp_path / "infra" / "tencent"
    runtime = root / "runtime"
    runtime.mkdir(parents=True)
    (runtime / ".env.runtime").write_text("FITCREW_API_IMAGE_TAG=" + "a" * 40 + "\n")
    (root / script).write_text((ROOT / "infra/tencent" / script).read_text())
    result = subprocess.run(
        ["bash", str(root / script), "b" * 40],
        env={**os.environ, "ROLLBACK_SHA": "b" * 40}, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "independently pinned API" in result.stderr


def test_bad_api_pin_cannot_modify_runtime(tmp_path):
    runtime = tmp_path / ".env.runtime"
    original = "FITCREW_IMAGE_TAG=old-image\n"
    runtime.write_text(original)
    result = subprocess.run(
        [sys.executable, str(ROOT / "infra/tencent/set-runtime-image.py"),
         "--file", str(runtime), "--service", "api", "latest"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert runtime.read_text() == original

#!/usr/bin/env python3
"""Fail CI when XcodeGen strips FitCrew's HealthKit configuration."""

from __future__ import annotations

import plistlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "apps" / "ios-bridge" / "FitCrewHealthBridge"


def load_plist(path: Path) -> dict:
    with path.open("rb") as handle:
        return plistlib.load(handle)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    info = load_plist(BRIDGE / "Info.plist")
    entitlements = load_plist(BRIDGE / "FitCrewHealthBridge.entitlements")
    project = (ROOT / "apps" / "ios-bridge" / "project.yml").read_text()

    require(
        info.get("CFBundleShortVersionString") == "3.0.0",
        "generated Info.plist has the wrong release version",
    )
    build_version = info.get("CFBundleVersion")
    require(
        isinstance(build_version, str)
        and build_version.isdigit()
        and int(build_version) > 0,
        "generated Info.plist needs a positive numeric build version",
    )
    require(
        info.get("ITSAppUsesNonExemptEncryption") is False,
        "generated Info.plist is missing the export-compliance declaration",
    )

    require(
        bool(info.get("NSHealthShareUsageDescription")),
        "generated Info.plist is missing NSHealthShareUsageDescription",
    )
    require(
        "processing" in info.get("UIBackgroundModes", []),
        "generated Info.plist is missing background processing mode",
    )
    require(
        "com.fitcrew.healthbridge.daily-sync"
        in info.get("BGTaskSchedulerPermittedIdentifiers", []),
        "generated Info.plist is missing the daily sync task identifier",
    )
    url_schemes = {
        scheme
        for item in info.get("CFBundleURLTypes", [])
        for scheme in item.get("CFBundleURLSchemes", [])
    }
    require(
        "fitcrew-health" in url_schemes,
        "generated Info.plist is missing the private pairing URL scheme",
    )
    require(
        entitlements.get("com.apple.developer.healthkit") is True,
        "generated entitlements are missing HealthKit",
    )
    require(
        entitlements.get("com.apple.developer.applesignin") == ["Default"],
        "generated entitlements are missing Sign in with Apple",
    )
    require(
        "com.apple.developer.healthkit.access" not in entitlements,
        "generated entitlements unexpectedly request Verifiable Health Records",
    )
    require(
        "ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon" in project,
        "XcodeGen project is missing the AppIcon build setting",
    )
    icon = BRIDGE / "Assets.xcassets" / "AppIcon.appiconset" / "AppIcon-1024.png"
    require(icon.is_file(), "AppIcon asset is missing its 1024px source image")
    with icon.open("rb") as handle:
        header = handle.read(26)
    require(
        header[:8] == b"\x89PNG\r\n\x1a\n" and len(header) == 26,
        "AppIcon source is not a PNG",
    )
    width, height = struct.unpack(">II", header[16:24])
    require((width, height) == (1024, 1024), "AppIcon source must be 1024x1024")
    require(header[25] not in {4, 6}, "AppIcon source must not contain an alpha channel")

    print(
        "Generated iOS version, entitlements and icon checks passed; "
        "signing and review remain separate."
    )


if __name__ == "__main__":
    main()

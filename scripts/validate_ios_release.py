#!/usr/bin/env python3
"""Validate the resolved Info.plist in a built iOS app, not its source template."""

from __future__ import annotations

import argparse
import ipaddress
import plistlib
import re
from pathlib import Path
from urllib.parse import urlsplit


def public_https(value: object, *, api: bool = False) -> bool:
    if not isinstance(value, str) or re.search(r"[\s$\\]", value):
        return False
    try:
        url = urlsplit(value)
        host = url.hostname or ""
        if (url.scheme != "https" or url.username is not None or url.password is not None
                or url.fragment or url.port not in (None, 443) or (api and url.query)):
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        labels = host.split(".")
        if len(labels) < 2 or labels[-1] in {"test", "invalid", "example", "localhost", "local"}:
            return False
        if host in {"example.com", "example.org", "example.net"} or any(
            host.endswith("." + reserved) for reserved in
            ("example.com", "example.org", "example.net")
        ):
            return False
        return all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", p) for p in labels)
    except ValueError:
        return False


def validate(info: dict) -> list[str]:
    failures = []
    for key in ("FitCrewAPIBaseURL", "PrivacyPolicyURL"):
        if not public_https(info.get(key), api=key == "FitCrewAPIBaseURL"):
            failures.append(f"{key}: requires a resolved public HTTPS domain")
    if info.get("CFBundleIdentifier") != "com.fitcrew.healthbridge":
        failures.append("Unexpected or unresolved bundle identifier")
    if info.get("CFBundleShortVersionString") != "3.0.0":
        failures.append("Unexpected release version")
    if not re.fullmatch(r"[1-9][0-9]*", str(info.get("CFBundleVersion", ""))):
        failures.append("Build version must be a positive integer")
    if info.get("NSAppTransportSecurity", {}).get("NSAllowsArbitraryLoads"):
        failures.append("Transport security must not allow arbitrary loads")
    if not info.get("NSHealthShareUsageDescription"):
        failures.append("Missing HealthKit read disclosure")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plist", type=Path, help="Built .app/Info.plist")
    args = parser.parse_args()
    with args.plist.open("rb") as handle:
        failures = validate(plistlib.load(handle))
    if failures:
        raise SystemExit("\n".join(failures))
    print("Resolved iOS configuration passed. Signing, URL reachability, operator details, "
          "device acceptance and platform submission still require separate evidence.")


if __name__ == "__main__":
    main()

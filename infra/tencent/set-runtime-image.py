#!/usr/bin/env python3
import argparse
import os
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("value")
    parser.add_argument("--file", type=Path, default=Path("runtime/.env.runtime"))
    parser.add_argument("--service", choices=("all", "api"), default="all")
    args = parser.parse_args()
    if not args.value or any(character.isspace() for character in args.value):
        raise SystemExit("invalid image tag")
    if args.service == "api" and not re.fullmatch(r"[0-9a-f]{40}", args.value):
        raise SystemExit("API image requires a full immutable commit SHA")
    key = "FITCREW_API_IMAGE_TAG" if args.service == "api" else "FITCREW_IMAGE_TAG"
    lines = args.file.read_text().splitlines()
    rendered = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            rendered.append(f"{key}={args.value}")
            found = True
        else:
            rendered.append(line)
    if not found:
        rendered.append(f"{key}={args.value}")
    temporary = args.file.with_suffix(".next")
    temporary.write_text("\n".join(rendered) + "\n")
    os.chmod(temporary, 0o600)
    temporary.replace(args.file)


if __name__ == "__main__":
    main()

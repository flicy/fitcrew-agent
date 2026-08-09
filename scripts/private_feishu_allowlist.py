"""Closed, private Feishu gateway allowlist helpers."""

import os
import secrets
from pathlib import Path

ALLOWLIST_FILE_NAME = "feishu-allowed-users"


def atomic_write_text(path: Path, value: str) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(value)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_allowed_subject(value: str) -> str:
    """Validate one Feishu subject for the private newline-delimited allowlist."""
    if not value:
        raise ValueError("Feishu subject must not be empty")
    if "\n" in value or "\r" in value:
        raise ValueError("Feishu subject must not contain a newline")
    if "," in value:
        raise ValueError("Feishu subject must not contain a comma")
    if any(character.isspace() for character in value):
        raise ValueError("Feishu subject must not contain whitespace")
    if not 3 <= len(value) <= 200:
        raise ValueError("Feishu subject must contain 3 to 200 characters")
    return value


def parse_allowed_users(value: str) -> tuple[str, ...]:
    """Read the comma-delimited closed runtime allowlist."""
    users: list[str] = []
    for raw_user in value.split(","):
        subject = validate_allowed_subject(raw_user)
        if subject not in users:
            users.append(subject)
    if not users:
        raise ValueError("FEISHU_ALLOWED_USERS must contain an owner subject")
    return tuple(users)


def read_private_allowed_users(path: Path) -> tuple[str, ...]:
    """Read a previous private allowlist without widening it."""
    if path.is_symlink():
        raise ValueError("private Feishu allowlist must be a regular file")
    if not path.exists():
        return ()
    if not path.is_file():
        raise ValueError("private Feishu allowlist must be a regular file")
    if path.stat().st_mode & 0o777 != 0o600:
        raise ValueError("private Feishu allowlist must have mode 0600")
    users: list[str] = []
    for raw_user in path.read_text(encoding="utf-8").splitlines():
        subject = validate_allowed_subject(raw_user)
        if subject in users:
            raise ValueError("private Feishu allowlist must not contain duplicates")
        users.append(subject)
    if not users:
        raise ValueError("private Feishu allowlist must not be empty")
    return tuple(users)


def prepare_allowed_users(
    path: Path, *, initial_allowed_users: str, invited_subject: str
) -> tuple[str, ...]:
    """Validate and merge a controlled invitation without changing runtime state."""
    users = list(parse_allowed_users(initial_allowed_users))
    for existing_subject in read_private_allowed_users(path):
        if existing_subject not in users:
            users.append(existing_subject)
    invited = validate_allowed_subject(invited_subject)
    if invited not in users:
        users.append(invited)
    return tuple(users)


def write_allowed_users(path: Path, users: tuple[str, ...]) -> None:
    """Atomically persist an already validated closed allowlist outside Git."""
    if not users:
        raise ValueError("private Feishu allowlist must not be empty")
    for subject in users:
        validate_allowed_subject(subject)

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    atomic_write_text(path, "\n".join(users) + "\n")


def store_allowed_users(
    path: Path, *, initial_allowed_users: str, invited_subject: str
) -> tuple[str, ...]:
    """Validate, merge, and atomically persist the closed allowlist for one invite."""
    users = prepare_allowed_users(
        path,
        initial_allowed_users=initial_allowed_users,
        invited_subject=invited_subject,
    )
    write_allowed_users(path, users)
    return users

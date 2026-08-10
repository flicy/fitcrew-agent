#!/usr/bin/env python3
"""Publish the three reviewed BodyOS books without printing their contents or identities."""

import argparse
import json
import os
import stat
import uuid
from pathlib import Path

from bodyos_api.config import get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import make_engine
from bodyos_api.knowledge import (
    CONFIRMABLE_PRIVATE_RIGHTS,
    INTERNAL_EXPERT_RIGHTS,
    PUBLISHABLE_PRIVATE_RIGHTS,
    SHARED_EXPERT_TITLES,
    KnowledgeService,
)
from bodyos_api.models import KnowledgeSource
from sqlalchemy import select
from sqlalchemy.orm import Session

BOOK_TITLES = (
    "控糖革命",
    "百岁人生行动手册",
    "睡眠优化完全指南：科学与实践",
)
assert frozenset(BOOK_TITLES) == SHARED_EXPERT_TITLES


def load_owner_id(path: Path) -> str:
    if not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise SystemExit("owner identity record is unavailable")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        owner_id = payload["fitcrew_user_id"]
        parsed = uuid.UUID(owner_id)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit("owner identity record is invalid") from error
    if parsed.version != 4 or str(parsed) != owner_id:
        raise SystemExit("owner identity record is invalid")
    return owner_id


def select_title_candidate(
    session: Session, owner_id: str, title: str
) -> tuple[str, KnowledgeSource | None]:
    private = session.scalar(
        select(KnowledgeSource)
        .where(
            KnowledgeSource.title == title,
            KnowledgeSource.visibility == "private",
            KnowledgeSource.review_status == "approved_private",
            KnowledgeSource.fitcrew_user_id == owner_id,
            KnowledgeSource.rights_status.in_(
                PUBLISHABLE_PRIVATE_RIGHTS | CONFIRMABLE_PRIVATE_RIGHTS
            ),
        )
        .order_by(KnowledgeSource.updated_at.desc(), KnowledgeSource.version.desc())
        .limit(1)
    )
    if private is not None:
        return "publish", private
    published = session.scalar(
        select(KnowledgeSource)
        .where(
            KnowledgeSource.title == title,
            KnowledgeSource.visibility == "public",
            KnowledgeSource.review_status == "published",
            KnowledgeSource.rights_status == INTERNAL_EXPERT_RIGHTS,
        )
        .order_by(KnowledgeSource.version.desc())
        .limit(1)
    )
    if published is not None:
        return "already_published", None
    raise SystemExit("a required reviewed book is unavailable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-record", type=Path, required=True)
    args = parser.parse_args()
    owner_id = load_owner_id(args.owner_record)
    encoded_key = os.environ.get("BODYOS_ENCRYPTION_KEY", "")
    if not encoded_key:
        raise SystemExit("BODYOS_ENCRYPTION_KEY is required")
    settings = get_settings()
    published_count = 0
    already_published_count = 0
    with Session(make_engine(settings.database_url), expire_on_commit=False) as session:
        selected: list[KnowledgeSource] = []
        for title in BOOK_TITLES:
            action, candidate = select_title_candidate(session, owner_id, title)
            if action == "already_published":
                already_published_count += 1
                continue
            assert candidate is not None
            selected.append(candidate)

        service = KnowledgeService(session, FieldCipher.from_base64(encoded_key))
        for source in selected:
            service.publish_private_source(
                source.id,
                expected_owner_id=owner_id,
                reviewer_role="owner_editor",
                rationale="approved for internal BodyOS expert summaries",
                applicability="general food, training, sleep, and glucose education",
                rights_confirmation=(
                    "Owner/operator explicitly confirmed authorization for closed BodyOS "
                    "shared expert-knowledge use"
                ),
            )
            published_count += 1

    print(
        json.dumps(
            {
                "published": published_count,
                "already_published": already_published_count,
            },
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()

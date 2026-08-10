#!/usr/bin/env python3
"""Publish the three reviewed BodyOS books without printing their contents or identities."""

import json
import os

from bodyos_api.config import get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import make_engine
from bodyos_api.knowledge import KnowledgeService
from bodyos_api.models import KnowledgeSource
from sqlalchemy import select
from sqlalchemy.orm import Session

BOOK_TITLES = (
    "控糖革命",
    "百岁人生行动手册",
    "睡眠优化完全指南：科学与实践",
)


def main() -> None:
    encoded_key = os.environ.get("BODYOS_ENCRYPTION_KEY", "")
    if not encoded_key:
        raise SystemExit("BODYOS_ENCRYPTION_KEY is required")
    settings = get_settings()
    published_count = 0
    already_published_count = 0
    with Session(make_engine(settings.database_url), expire_on_commit=False) as session:
        selected: list[KnowledgeSource] = []
        for title in BOOK_TITLES:
            published = session.scalar(
                select(KnowledgeSource)
                .where(
                    KnowledgeSource.title == title,
                    KnowledgeSource.visibility == "public",
                    KnowledgeSource.review_status == "published",
                )
                .order_by(KnowledgeSource.version.desc())
                .limit(1)
            )
            if published is not None:
                already_published_count += 1
                continue
            private = session.scalar(
                select(KnowledgeSource)
                .where(
                    KnowledgeSource.title == title,
                    KnowledgeSource.visibility == "private",
                    KnowledgeSource.review_status == "approved_private",
                )
                .order_by(KnowledgeSource.version.desc())
                .limit(1)
            )
            if private is None:
                raise SystemExit("a required reviewed book is unavailable")
            selected.append(private)

        service = KnowledgeService(session, FieldCipher.from_base64(encoded_key))
        for source in selected:
            service.publish_private_source(
                source.id,
                reviewer_role="owner_editor",
                rationale="approved for internal BodyOS expert summaries",
                applicability="general food, training, sleep, and glucose education",
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

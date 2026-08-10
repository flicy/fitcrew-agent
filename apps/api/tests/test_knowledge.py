import importlib.util
from pathlib import Path

import pytest
from bodyos_api.crypto import FieldCipher
from bodyos_api.knowledge import KnowledgeAccessDenied, KnowledgeService
from bodyos_api.models import KnowledgeChunk, KnowledgeReview, KnowledgeSource, User
from sqlalchemy import select
from sqlalchemy.orm import Session

OWNER = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
ROOT = Path(__file__).parents[3]


def _publication_script():
    path = ROOT / "scripts/publish_shared_books.py"
    spec = importlib.util.spec_from_file_location("publish_shared_books_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_users(session: Session) -> None:
    session.add_all([User(fitcrew_user_id=OWNER), User(fitcrew_user_id=OTHER)])
    session.commit()


def test_private_book_chunks_are_encrypted_and_page_cited(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    source = service.import_pages(
        fitcrew_user_id=OWNER,
        title="控糖革命",
        author="Jessie Inchauspé",
        content_hash="a" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={12: "进餐顺序可能影响餐后葡萄糖曲线。先吃蔬菜，再吃蛋白质。"},
    )

    stored = session.scalar(select(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id))
    assert stored is not None
    assert "葡萄糖".encode() not in stored.content_ciphertext

    hits = service.search_private(OWNER, "餐后葡萄糖", limit=3)

    assert hits[0].title == "控糖革命"
    assert hits[0].page_number == 12
    assert "葡萄糖" in hits[0].excerpt


def test_other_user_cannot_search_owner_private_book(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    service.import_pages(
        fitcrew_user_id=OWNER,
        title="睡眠优化完全指南",
        author=None,
        content_hash="b" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={1: "稳定的起床时间有助于保持昼夜节律。"},
    )

    assert service.search_private(OTHER, "昼夜节律") == []
    try:
        service.get_private_source(OTHER, title="睡眠优化完全指南")
    except KnowledgeAccessDenied:
        pass
    else:
        raise AssertionError("another user accessed an owner-only source")


def test_group_public_search_rejects_published_sources_outside_the_three_book_boundary(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    draft = service.import_pages(
        fitcrew_user_id=None,
        title="公共候选",
        author=None,
        content_hash="c" * 64,
        rights_status="licensed_summary",
        pages={1: "步行是低门槛活动。"},
        visibility="public",
    )

    assert service.search_public("步行") == []

    service.review_source(
        draft.id,
        reviewer_role="editor",
        decision="approved",
        rationale="来源和适用边界已核验",
        applicability="一般成人的低强度活动建议",
    )

    assert service.search_public("步行") == []


def test_withdrawn_source_is_removed_from_retrieval(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    source = service.import_pages(
        fitcrew_user_id=OWNER,
        title="百岁人生行动手册",
        author=None,
        content_hash="d" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={8: "长期健康需要可持续的日常行动。"},
    )
    assert service.search_private(OWNER, "可持续")[0].title == "百岁人生行动手册"

    service.withdraw_source(OWNER, source.id)

    assert service.search_private(OWNER, "可持续") == []


def test_private_import_is_idempotent_and_versions_changed_content(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    first = service.import_pages(
        fitcrew_user_id=OWNER,
        title="私人资料",
        author=None,
        content_hash="e" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={1: "第一版健康行动"},
    )

    replay = service.import_pages(
        fitcrew_user_id=OWNER,
        title="私人资料",
        author=None,
        content_hash="e" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={1: "第一版健康行动"},
    )
    changed = service.import_pages(
        fitcrew_user_id=OWNER,
        title="私人资料",
        author=None,
        content_hash="f" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={1: "第二版可持续健康行动"},
    )

    assert replay.id == first.id
    assert changed.id != first.id
    assert changed.version == 2
    assert first.review_status == "superseded"
    assert len(session.scalars(select(KnowledgeSource)).all()) == 2
    hits = service.search_private(OWNER, "可持续")
    assert {hit.source_id for hit in hits} == {changed.id}


def test_private_source_can_be_published_for_shared_retrieval(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    source = service.import_pages(
        fitcrew_user_id=OWNER,
        title="控糖革命",
        author="Jessie Inchauspé",
        content_hash="1" * 64,
        rights_status="user_provided_internal_expert_use",
        pages={12: "进餐顺序可能影响餐后葡萄糖曲线。"},
    )

    published = service.publish_private_source(
        source.id,
        expected_owner_id=OWNER,
        reviewer_role="owner_editor",
        rationale="approved for internal expert summaries",
        applicability="general lifestyle education",
        rights_confirmation="owner confirmed closed BodyOS shared expert use",
    )

    assert published.visibility == "public"
    assert published.fitcrew_user_id is None
    assert published.review_status == "published"
    assert service.search_private(OWNER, "餐后葡萄糖") == []
    hit = service.search_public("餐后葡萄糖")[0]
    assert hit.source_id == source.id
    review = session.scalar(
        select(KnowledgeReview).where(KnowledgeReview.source_id == source.id)
    )
    assert review is not None
    assert review.decision == "approved"


def test_user_search_combines_published_and_owned_private_sources(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    shared = service.import_pages(
        fitcrew_user_id=OWNER,
        title="睡眠优化完全指南：科学与实践",
        author=None,
        content_hash="2" * 64,
        rights_status="user_provided_internal_expert_use",
        pages={21: "稳定节律有助于睡眠恢复。"},
    )
    service.publish_private_source(
        shared.id,
        expected_owner_id=OWNER,
        reviewer_role="owner_editor",
        rationale="approved for internal expert summaries",
        applicability="general lifestyle education",
        rights_confirmation="owner confirmed closed BodyOS shared expert use",
    )
    service.import_pages(
        fitcrew_user_id=OWNER,
        title="Owner 私人笔记",
        author=None,
        content_hash="3" * 64,
        rights_status="private_note",
        pages={1: "睡眠恢复需要减少晚间干扰。"},
    )

    owner_hits = service.search_for_user(OWNER, "睡眠恢复", limit=3)
    other_hits = service.search_for_user(OTHER, "睡眠恢复", limit=3)

    assert {hit.title for hit in owner_hits} == {
        "睡眠优化完全指南：科学与实践",
        "Owner 私人笔记",
    }
    assert {hit.title for hit in other_hits} == {"睡眠优化完全指南：科学与实践"}


def test_publishing_requires_an_approved_private_source(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    public_draft = service.import_pages(
        fitcrew_user_id=None,
        title="候选知识",
        author=None,
        content_hash="4" * 64,
        rights_status="licensed_summary",
        pages={1: "一般健康知识。"},
        visibility="public",
    )

    try:
        service.publish_private_source(
            public_draft.id,
            expected_owner_id=OWNER,
            reviewer_role="owner_editor",
            rationale="invalid source",
            applicability="general",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("a public draft was republished through the private-source path")


def test_publication_rejects_another_users_matching_private_book(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    other_source = service.import_pages(
        fitcrew_user_id=OTHER,
        title="控糖革命",
        author=None,
        content_hash="5" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={1: "其他用户的私人内容。"},
    )

    try:
        service.publish_private_source(
            other_source.id,
            expected_owner_id=OWNER,
            reviewer_role="owner_editor",
            rationale="must remain private",
            applicability="general",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("another user's private book was published")
    assert service.search_public("私人内容") == []


def test_publishing_a_new_reviewed_edition_supersedes_the_old_shared_version(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    first = service.import_pages(
        fitcrew_user_id=OWNER,
        title="控糖革命",
        author=None,
        content_hash="6" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={12: "第一版进餐顺序。"},
    )
    service.publish_private_source(
        first.id,
        expected_owner_id=OWNER,
        reviewer_role="owner_editor",
        rationale="approved internal expert use",
        applicability="general lifestyle education",
        rights_confirmation="owner confirmed closed BodyOS shared expert use",
    )
    second = service.import_pages(
        fitcrew_user_id=OWNER,
        title="控糖革命",
        author=None,
        content_hash="7" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={14: "第二版蔬菜进食顺序。"},
    )

    published = service.publish_private_source(
        second.id,
        expected_owner_id=OWNER,
        reviewer_role="owner_editor",
        rationale="approved updated internal expert use",
        applicability="general lifestyle education",
        rights_confirmation="owner confirmed closed BodyOS shared expert use",
    )

    assert first.review_status == "superseded"
    assert published.version == 2
    assert published.rights_status == "user_provided_internal_expert_use"
    hits = service.search_public("蔬菜进食顺序")
    assert {hit.source_id for hit in hits} == {second.id}


def test_publication_script_prefers_the_owners_new_private_edition_over_existing_public(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    first = service.import_pages(
        fitcrew_user_id=OWNER,
        title="控糖革命",
        author=None,
        content_hash="8" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={1: "第一版。"},
    )
    service.publish_private_source(
        first.id,
        expected_owner_id=OWNER,
        reviewer_role="owner_editor",
        rationale="approved internal expert use",
        applicability="general lifestyle education",
        rights_confirmation="owner confirmed closed BodyOS shared expert use",
    )
    owner_update = service.import_pages(
        fitcrew_user_id=OWNER,
        title="控糖革命",
        author=None,
        content_hash="9" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={2: "Owner 更新版。"},
    )
    service.import_pages(
        fitcrew_user_id=OTHER,
        title="控糖革命",
        author=None,
        content_hash="a" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={3: "其他用户版本。"},
    )

    action, candidate = _publication_script().select_title_candidate(
        session, OWNER, "控糖革命"
    )

    assert action == "publish"
    assert candidate is not None
    assert candidate.id == owner_update.id


def test_unverified_private_book_requires_an_audited_rights_confirmation(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    source = service.import_pages(
        fitcrew_user_id=OWNER,
        title="控糖革命",
        author=None,
        content_hash="b" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={1: "进餐顺序。"},
    )

    with pytest.raises(ValueError, match="rights confirmation"):
        service.publish_private_source(
            source.id,
            expected_owner_id=OWNER,
            reviewer_role="owner_editor",
            rationale="approved internal expert use",
            applicability="general lifestyle education",
        )

    published = service.publish_private_source(
        source.id,
        expected_owner_id=OWNER,
        reviewer_role="owner_editor",
        rationale="approved internal expert use",
        applicability="general lifestyle education",
        rights_confirmation="owner confirmed closed BodyOS shared expert use",
    )
    decisions = session.scalars(
        select(KnowledgeReview.decision).where(KnowledgeReview.source_id == source.id)
    ).all()

    assert published.rights_status == "user_provided_internal_expert_use"
    assert decisions == ["rights_confirmed", "approved"]


def test_reimporting_the_same_hash_after_publication_is_idempotent(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_users(session)
    service = KnowledgeService(session, field_cipher)
    source = service.import_pages(
        fitcrew_user_id=OWNER,
        title="控糖革命",
        author=None,
        content_hash="c" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={1: "进餐顺序。"},
    )
    published = service.publish_private_source(
        source.id,
        expected_owner_id=OWNER,
        reviewer_role="owner_editor",
        rationale="approved internal expert use",
        applicability="general lifestyle education",
        rights_confirmation="owner confirmed closed BodyOS shared expert use",
    )

    repeated = service.import_pages(
        fitcrew_user_id=OWNER,
        title="控糖革命",
        author=None,
        content_hash="c" * 64,
        rights_status="user_provided_private_use_unverified",
        pages={1: "进餐顺序。"},
    )
    rows = session.scalars(
        select(KnowledgeSource).where(KnowledgeSource.title == "控糖革命")
    ).all()

    assert repeated.id == published.id
    assert len(rows) == 1
    assert rows[0].version == 1
    assert rows[0].review_status == "published"

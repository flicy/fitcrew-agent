import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bodyos_api.crypto import EncryptedValue, FieldCipher
from bodyos_api.models import KnowledgeChunk, KnowledgeReview, KnowledgeSource


class KnowledgeAccessDenied(PermissionError):
    pass


SHARED_EXPERT_TITLES = frozenset(
    {
        "控糖革命",
        "百岁人生行动手册",
        "睡眠优化完全指南：科学与实践",
    }
)
INTERNAL_EXPERT_RIGHTS = "user_provided_internal_expert_use"
PUBLISHABLE_PRIVATE_RIGHTS = frozenset({INTERNAL_EXPERT_RIGHTS})
CONFIRMABLE_PRIVATE_RIGHTS = frozenset({"user_provided_private_use_unverified"})


@dataclass(frozen=True, slots=True)
class SearchHit:
    source_id: str
    title: str
    page_number: int
    excerpt: str
    score: float


def chunk_text(text: str, *, size: int = 800, overlap: int = 100) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks = []
    cursor = 0
    while cursor < len(normalized):
        chunks.append(normalized[cursor : cursor + size])
        if cursor + size >= len(normalized):
            break
        cursor += size - overlap
    return chunks


def _tokens(text: str) -> set[str]:
    lowered = text.casefold()
    latin = set(re.findall(r"[a-z0-9_]{2,}", lowered))
    chinese_runs = re.findall(r"[\u3400-\u9fff]+", lowered)
    chinese = {
        run[index : index + 2] for run in chinese_runs for index in range(max(0, len(run) - 1))
    }
    return latin | chinese


class KnowledgeService:
    def __init__(self, session: Session, cipher: FieldCipher):
        self._session = session
        self._cipher = cipher

    def import_pages(
        self,
        *,
        fitcrew_user_id: str | None,
        title: str,
        author: str | None,
        content_hash: str,
        rights_status: str,
        pages: dict[int, str],
        visibility: str = "private",
    ) -> KnowledgeSource:
        if visibility == "private" and fitcrew_user_id is None:
            raise ValueError("private knowledge requires an owner")
        if visibility == "public" and fitcrew_user_id is not None:
            raise ValueError("public knowledge must not retain a private owner")
        if visibility == "private" and title in SHARED_EXPERT_TITLES:
            existing_public = self._session.scalar(
                select(KnowledgeSource)
                .where(
                    KnowledgeSource.title == title,
                    KnowledgeSource.content_hash == content_hash,
                    KnowledgeSource.visibility == "public",
                    KnowledgeSource.review_status == "published",
                    KnowledgeSource.rights_status == INTERNAL_EXPERT_RIGHTS,
                )
                .order_by(KnowledgeSource.version.desc())
                .limit(1)
            )
            if existing_public is not None:
                return existing_public
        owner_filter = (
            KnowledgeSource.fitcrew_user_id == fitcrew_user_id
            if fitcrew_user_id is not None
            else KnowledgeSource.fitcrew_user_id.is_(None)
        )
        latest = self._session.scalar(
            select(KnowledgeSource)
            .where(
                KnowledgeSource.visibility == visibility,
                KnowledgeSource.title == title,
                owner_filter,
            )
            .order_by(KnowledgeSource.version.desc())
            .limit(1)
        )
        if (
            latest is not None
            and latest.content_hash == content_hash
            and latest.review_status != "withdrawn"
        ):
            return latest
        version = (latest.version + 1) if latest is not None else 1
        if visibility == "private" and latest is not None:
            latest.review_status = "superseded"
        source = KnowledgeSource(
            fitcrew_user_id=fitcrew_user_id,
            visibility=visibility,
            source_type="book",
            title=title,
            author=author,
            content_hash=content_hash,
            rights_status=rights_status,
            review_status="approved_private" if visibility == "private" else "captured",
            version=version,
        )
        self._session.add(source)
        self._session.flush()
        for page_number, page_text in sorted(pages.items()):
            for chunk_index, content in enumerate(chunk_text(page_text)):
                aad = f"knowledge:{source.id}:{page_number}:{chunk_index}"
                encrypted = self._cipher.encrypt_json({"content": content}, aad=aad)
                self._session.add(
                    KnowledgeChunk(
                        source_id=source.id,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        content_nonce=encrypted.nonce,
                        content_ciphertext=encrypted.ciphertext,
                    )
                )
        self._session.commit()
        return source

    def get_private_source(self, fitcrew_user_id: str, *, title: str) -> KnowledgeSource:
        source = self._session.scalar(
            select(KnowledgeSource)
            .where(
                KnowledgeSource.title == title,
                KnowledgeSource.visibility == "private",
                KnowledgeSource.review_status == "approved_private",
            )
            .order_by(KnowledgeSource.version.desc())
            .limit(1)
        )
        if source is None or source.fitcrew_user_id != fitcrew_user_id:
            raise KnowledgeAccessDenied("private source is unavailable for this user")
        return source

    def search_private(
        self, fitcrew_user_id: str, query: str, *, limit: int = 5
    ) -> list[SearchHit]:
        return self._search(
            query,
            limit=limit,
            source_filters=(
                KnowledgeSource.visibility == "private",
                KnowledgeSource.fitcrew_user_id == fitcrew_user_id,
                KnowledgeSource.review_status == "approved_private",
            ),
        )

    def search_public(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        return self._search(
            query,
            limit=limit,
            source_filters=(
                KnowledgeSource.visibility == "public",
                KnowledgeSource.review_status == "published",
                KnowledgeSource.title.in_(SHARED_EXPERT_TITLES),
                KnowledgeSource.rights_status == INTERNAL_EXPERT_RIGHTS,
            ),
        )

    def search_for_user(
        self, fitcrew_user_id: str, query: str, *, limit: int = 5
    ) -> list[SearchHit]:
        hits = self.search_private(fitcrew_user_id, query, limit=limit) + self.search_public(
            query, limit=limit
        )
        return sorted(
            hits,
            key=lambda hit: (-hit.score, hit.title, hit.page_number, hit.source_id),
        )[:limit]

    def publish_private_source(
        self,
        source_id: str,
        *,
        expected_owner_id: str,
        reviewer_role: str,
        rationale: str,
        applicability: str,
        rights_confirmation: str | None = None,
    ) -> KnowledgeSource:
        source = self._session.get(KnowledgeSource, source_id)
        if (
            source is None
            or source.visibility != "private"
            or source.review_status != "approved_private"
            or source.fitcrew_user_id != expected_owner_id
            or source.title not in SHARED_EXPERT_TITLES
            or source.rights_status
            not in (PUBLISHABLE_PRIVATE_RIGHTS | CONFIRMABLE_PRIVATE_RIGHTS)
        ):
            raise ValueError("approved private knowledge source not found")
        if (
            not expected_owner_id.strip()
            or not reviewer_role.strip()
            or not rationale.strip()
            or not applicability.strip()
        ):
            raise ValueError("publication review fields are required")
        if source.rights_status in CONFIRMABLE_PRIVATE_RIGHTS:
            if rights_confirmation is None or not rights_confirmation.strip():
                raise ValueError("explicit internal-use rights confirmation is required")
            self._session.add(
                KnowledgeReview(
                    source_id=source.id,
                    reviewer_role=reviewer_role,
                    decision="rights_confirmed",
                    rationale=rights_confirmation.strip(),
                    applicability="closed BodyOS shared expert knowledge",
                )
            )
            source.rights_status = INTERNAL_EXPERT_RIGHTS
        published_sources = self._session.scalars(
            select(KnowledgeSource).where(
                KnowledgeSource.id != source.id,
                KnowledgeSource.title == source.title,
                KnowledgeSource.visibility == "public",
                KnowledgeSource.review_status == "published",
            )
        ).all()
        for published in published_sources:
            published.review_status = "superseded"
        prior_version = self._session.scalar(
            select(func.max(KnowledgeSource.version)).where(
                KnowledgeSource.id != source.id,
                KnowledgeSource.title == source.title,
            )
        )
        if prior_version is not None and source.version <= prior_version:
            source.version = prior_version + 1
        source.fitcrew_user_id = None
        source.visibility = "public"
        source.rights_status = INTERNAL_EXPERT_RIGHTS
        source.review_status = "published"
        self._session.add(
            KnowledgeReview(
                source_id=source.id,
                reviewer_role=reviewer_role,
                decision="approved",
                rationale=rationale,
                applicability=applicability,
            )
        )
        self._session.commit()
        return source

    def _search(self, query: str, *, limit: int, source_filters: tuple) -> list[SearchHit]:
        rows = self._session.execute(
            select(KnowledgeSource, KnowledgeChunk)
            .join(KnowledgeChunk, KnowledgeChunk.source_id == KnowledgeSource.id)
            .where(*source_filters)
        ).all()
        query_tokens = _tokens(query)
        hits: list[SearchHit] = []
        for source, chunk in rows:
            aad = f"knowledge:{source.id}:{chunk.page_number}:{chunk.chunk_index}"
            content = self._cipher.decrypt_json(
                EncryptedValue(chunk.content_nonce, chunk.content_ciphertext), aad=aad
            )["content"]
            content_tokens = _tokens(content)
            overlap = len(query_tokens.intersection(content_tokens))
            phrase_bonus = 3 if query.casefold() in content.casefold() else 0
            score = float(overlap + phrase_bonus)
            if score <= 0:
                continue
            hits.append(
                SearchHit(
                    source_id=source.id,
                    title=source.title,
                    page_number=chunk.page_number,
                    excerpt=content[:400],
                    score=score,
                )
            )
        return sorted(hits, key=lambda hit: (-hit.score, hit.title, hit.page_number))[:limit]

    def review_source(
        self,
        source_id: str,
        *,
        reviewer_role: str,
        decision: str,
        rationale: str,
        applicability: str,
    ) -> KnowledgeSource:
        source = self._session.get(KnowledgeSource, source_id)
        if source is None or source.visibility != "public":
            raise ValueError("public knowledge source not found")
        if decision not in {"approved", "rejected"}:
            raise ValueError("review decision must be approved or rejected")
        self._session.add(
            KnowledgeReview(
                source_id=source_id,
                reviewer_role=reviewer_role,
                decision=decision,
                rationale=rationale,
                applicability=applicability,
            )
        )
        source.review_status = "published" if decision == "approved" else "rejected"
        self._session.commit()
        return source

    def withdraw_source(self, fitcrew_user_id: str, source_id: str) -> None:
        source = self._session.get(KnowledgeSource, source_id)
        if source is None or source.fitcrew_user_id != fitcrew_user_id:
            raise KnowledgeAccessDenied("source does not belong to user")
        source.review_status = "withdrawn"
        self._session.commit()

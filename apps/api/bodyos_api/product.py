"""User-private decision loop; no external model receives these documents."""

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from bodyos_api.crypto import EncryptedValue, FieldCipher
from bodyos_api.models import (
    AuditEvent,
    Consent,
    DailyFeature,
    DemandItem,
    DeviceBinding,
    HealthSample,
    IdentityBinding,
    Insight,
    KnowledgeChunk,
    KnowledgeReview,
    KnowledgeSource,
    Memory,
    OutboxEvent,
    PairingExchangeSession,
    ProductRecord,
    SyncBatch,
    User,
)

GOALS = {
    "sleep": "建立稳定睡眠节律",
    "energy": "了解自己的精力变化",
    "activity": "建立轻松活动习惯",
}
PRIVACY_VERSION = "2026-09-07"


class ProductService:
    def __init__(
        self, session: Session, cipher: FieldCipher, user_id: str, generation=None, device_id=None
    ):
        self.session, self.cipher, self.user_id = session, cipher, user_id
        self.generation = (
            generation if generation is not None else session.get(User, user_id).data_generation
        )
        self.device_id = device_id

    def lock(self):
        user = self.session.scalar(
            select(User)
            .where(User.fitcrew_user_id == self.user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not user or user.status != "active":
            raise HTTPException(401, "account unavailable")
        if user.data_generation != self.generation:
            raise HTTPException(409, "data was erased; refresh before making a new request")
        if self.device_id:
            device = self.session.get(DeviceBinding, self.device_id, populate_existing=True)
            if not device or device.revoked_at:
                raise HTTPException(401, "device session revoked")
        return user

    def now(self):
        return datetime.now(UTC)

    def today(self):
        user = self.session.get(User, self.user_id)
        return self.now().astimezone(ZoneInfo(user.timezone)).date().isoformat()

    def rows(self, kind):
        return self.session.scalars(
            select(ProductRecord)
            .where(
                ProductRecord.fitcrew_user_id == self.user_id,
                ProductRecord.kind == kind,
            )
            .order_by(ProductRecord.created_at, ProductRecord.id)
        ).all()

    def row(self, kind, key):
        return self.session.scalar(
            select(ProductRecord).where(
                ProductRecord.fitcrew_user_id == self.user_id,
                ProductRecord.kind == kind,
                ProductRecord.resource_key == key,
            )
        )

    def read(self, row):
        if row is None:
            return None
        return self.cipher.decrypt_json(
            EncryptedValue(row.payload_nonce, row.payload_ciphertext),
            aad=f"product:{self.user_id}:{row.id}",
        )

    def write(self, kind, key, payload):
        row = self.row(kind, key)
        if row is None:
            row = ProductRecord(
                id=str(uuid4()),
                fitcrew_user_id=self.user_id,
                kind=kind,
                resource_key=key,
                revision=0,
            )
            self.session.add(row)
        row.revision += 1
        payload = {**payload, "id": key, "revision": row.revision}
        encrypted = self.cipher.encrypt_json(payload, aad=f"product:{self.user_id}:{row.id}")
        row.payload_nonce, row.payload_ciphertext = encrypted.nonce, encrypted.ciphertext
        self.session.flush()
        return payload

    def mutate(self, operation: str, body: dict, action: Callable):
        # PostgreSQL serializes each user's mutations, including concurrent retries.
        self.lock()
        key = str(body["request_id"])
        digest = hashlib.sha256(
            json.dumps({"operation": operation, "body": body}, sort_keys=True, default=str).encode()
        ).hexdigest()
        previous = self.read(self.row("request", key))
        if previous:
            if previous.get("erased"):
                raise HTTPException(410, "this request was erased and cannot be replayed")
            if previous["digest"] != digest:
                raise HTTPException(409, "request_id already used with different content")
            return previous["response"]
        result = action()
        self.write("request", key, {"digest": digest, "response": result})
        self.session.commit()
        return result

    def trends(self, logs, experiments=()):
        end = datetime.fromisoformat(self.today()).date()
        grouped = {}
        for item in logs:
            grouped.setdefault(item["date"], []).append(item)
        events = {}
        for experiment in experiments:
            if experiment.get("accepted_at"):
                day = (
                    datetime.fromisoformat(experiment["accepted_at"])
                    .astimezone(ZoneInfo(self.session.get(User, self.user_id).timezone))
                    .date()
                    .isoformat()
                )
                events.setdefault(day, []).append("开始实验：" + experiment["title"])
        points = []
        for offset in range(89, -1, -1):
            day = (end - timedelta(days=offset)).isoformat()
            records = grouped.get(day, [])
            points.append(
                {
                    "date": day,
                    "count": len(records),
                    "events": events.get(day, []),
                    "energy": round(sum(r["energy"] for r in records) / len(records), 2)
                    if records
                    else None,
                    "stress": round(sum(r["stress"] for r in records) / len(records), 2)
                    if records
                    else None,
                }
            )
        return {"source": "manual_logs", "window_end": end.isoformat(), "points": points}

    def next_check(self, journey, experiments, logs):
        active = next(
            (e for e in experiments if e["status"] in {"running", "paused", "proposed"}), None
        )
        if not journey:
            return {
                "title": "先选择旅程方向",
                "detail": "选定方向后，才能确认观察什么。",
                "action": "journey",
            }
        if not active:
            return {
                "title": "准备下一次观察",
                "detail": "先记录此刻感受，再在实验页查看提案与结果。",
                "action": "experiments",
            }
        if active["status"] == "proposed":
            return {
                "title": "等待你确认实验",
                "detail": "阅读用途、时间窗与停止条件后再开始；尚未开始观察。",
                "action": "experiments",
            }
        if active["status"] == "paused":
            return {
                "title": "实验已暂停",
                "detail": "暂停期间的记录不计入观察；继续后会延长观察期限。",
                "action": "experiments",
            }
        observed = {
            r["date"]
            for r in logs
            if active["accepted_at"] <= r["created_at"] <= active["ends_at"]
            and not any(a <= r["created_at"] < b for a, b in active.get("pause_intervals", []))
        }
        ended = self.now() >= datetime.fromisoformat(active["ends_at"])
        detail = (
            f"观察期已有 {len(observed)} 个有效记录日，比较至少需要四天；基线也需四天才能比较两窗。"
        )
        if ended:
            detail += "观察期已结束，可以查看评估；记录不足时会显示无法比较。"
        else:
            detail += "观察期结束后才能评估；现在可按自己的节奏记录。"
        return {
            "title": "可以查看评估" if ended else "等待观察条件",
            "detail": detail,
            "action": "experiments" if ended else "log",
        }

    def onboarding(self):
        return self.read(self.row("onboarding", "current")) or {
            "step": 1,
            "revision": 0,
            "route": None,
        }

    def advance_onboarding(self, step, route=None):
        progress = self.onboarding()
        if progress["step"] != step:
            raise HTTPException(409, "onboarding changed; refresh before continuing")
        if step == 2 and not self.row("journey", "current"):
            raise HTTPException(409, "save a journey direction first")
        if step == 4:
            if route not in {"manual", "health"}:
                raise HTTPException(422, "choose a data route")
            progress["route"] = route
        if step == 5:
            if route == "manual":
                progress["route"] = "manual"
            if progress.get("route") == "health":
                synced = self.session.scalar(
                    select(SyncBatch.id)
                    .join(Consent, Consent.id == SyncBatch.consent_id)
                    .join(DeviceBinding, DeviceBinding.id == SyncBatch.device_binding_id)
                    .where(
                        SyncBatch.fitcrew_user_id == self.user_id,
                        SyncBatch.status == "accepted",
                        Consent.fitcrew_user_id == self.user_id,
                        Consent.granted.is_(True),
                        Consent.withdrawn_at.is_(None),
                        Consent.purpose == "private_coaching",
                        Consent.granted_at.is_not(None),
                        SyncBatch.created_at >= Consent.granted_at,
                        DeviceBinding.fitcrew_user_id == self.user_id,
                        DeviceBinding.revoked_at.is_(None),
                    )
                    .limit(1)
                )
                if not synced:
                    raise HTTPException(
                        409, "no confirmed sync; retry sync or choose manual records"
                    )
        if step == 6 and not self.rows("log"):
            raise HTTPException(409, "save a body check first")
        progress["step"] = step + 1
        progress["updated_at"] = self.now().isoformat()
        if step in {1, 3}:
            progress[f"disclosure_{step}"] = PRIVACY_VERSION
        return self.write("onboarding", "current", progress)

    def active_health_categories(self):
        return sorted(
            set(
                self.session.scalars(
                    select(Consent.category).where(
                        Consent.fitcrew_user_id == self.user_id,
                        Consent.granted.is_(True),
                        Consent.withdrawn_at.is_(None),
                        Consent.purpose == "private_coaching",
                    )
                ).all()
            )
        )

    def today_context(self, logs, categories):
        end = self.today()
        start = (datetime.fromisoformat(end) - timedelta(days=6)).date().isoformat()
        observed = len({r["date"] for r in logs if start <= r["date"] <= end})
        status = (
            "restricted" if not categories else "baseline_building" if observed < 4 else "ready"
        )
        titles = {
            "restricted": "手动记录模式",
            "baseline_building": "正在积累记录",
            "ready": "可以查看记录变化",
        }
        detail = f"近七天有 {observed} 个手动记录日，缺少 {7 - observed} 天。"
        detail += "四个记录日是当前实验比较的最低要求，不是健康评分。"
        if not categories:
            detail += "尚无有效健康上传授权，可以继续手动记录。"
        else:
            detail += "已选择健康上传范围；这不代表设备已允许全部读取，也不代表样本完整。"
        return {
            "status": status,
            "title": titles[status],
            "detail": detail,
            "window_start": start,
            "window_end": end,
            "observed_days": observed,
            "source": "手动身体记录",
            "health_categories": categories,
        }

    def state(self):
        journey = self.read(self.row("journey", "current"))
        categories = self.active_health_categories()
        last = self.session.scalar(
            select(func.max(DeviceBinding.last_sync_at)).where(
                DeviceBinding.fitcrew_user_id == self.user_id, DeviceBinding.revoked_at.is_(None)
            )
        )
        count = self.session.scalar(
            select(func.count(HealthSample.id)).where(
                HealthSample.fitcrew_user_id == self.user_id, HealthSample.kind.in_(categories)
            )
        )
        logs = [self.read(row) for row in self.rows("log")]
        experiments = [self.read(row) for row in self.rows("experiment")]
        return {
            "journey": journey,
            "experiments": experiments,
            "logs": logs,
            "trends": self.trends(logs, experiments),
            "next_check": self.next_check(journey, experiments, logs),
            "onboarding": self.onboarding(),
            "today_context": self.today_context(logs, categories),
            "mission": self.mission(journey) if journey else None,
            "health": {
                "sample_count": count or 0,
                "last_sync_at": last.isoformat() if last and categories else None,
            },
            "privacy_version": PRIVACY_VERSION,
        }

    def set_journey(self, goal):
        old = self.read(self.row("journey", "current"))
        if (
            old
            and old["goal"] != goal
            and any(
                self.read(r)["status"] in {"running", "paused"} for r in self.rows("experiment")
            )
        ):
            raise HTTPException(409, "stop the current experiment before changing direction")
        if old and old["goal"] != goal:
            for row in self.rows("experiment"):
                item = self.read(row)
                if item["status"] == "proposed":
                    self.write("experiment", row.resource_key, {**item, "status": "stopped"})
        return self.write(
            "journey",
            "current",
            {
                "goal": goal,
                "title": GOALS[goal],
                "start_date": old["start_date"] if old else self.today(),
                "days": 90,
            },
        )

    def propose(self, selection=None):
        journey = self.read(self.row("journey", "current"))
        if not journey:
            raise HTTPException(409, "choose a journey first")
        for row in self.rows("experiment"):
            item = self.read(row)
            if item["status"] in {"proposed", "running", "paused"}:
                return item
        goal = journey["goal"]
        selection = selection or {
            "source": "rule_based",
            "ai_status": "not_authorized",
            "choice": "standard",
        }
        intervention = {
            "sleep": "睡前留出 10 分钟安静收尾，按自己的作息休息",
            "energy": "每天在相近时间记录精力和压力",
            "activity": "身体允许时，尝试 5 分钟轻松活动",
        }[goal]
        if selection["choice"] == "gentle":
            intervention = "暂不增加活动要求，在相近时间记录精力与压力，先观察自己的节律"
        return self.write(
            "experiment",
            str(uuid4()),
            {
                "title": GOALS[goal] + " · 7 天观察",
                "hypothesis": "观察这个小行动是否伴随主观精力变化；不预设结果。",
                "intervention": intervention,
                "metrics": ["每天主观精力（1–5）", "压力（1–3）"],
                "success_criteria": [
                    "至少四个不同日期的记录",
                    "比较观察期前后记录；不解释为因果或疗效",
                ],
                "stop_conditions": ["出现不适立即停止", "你可以随时暂停、停止或删除数据"],
                "data_categories": ["手动精力与压力记录"],
                "duration_days": 7,
                "baseline_days": 7,
                "purpose": (
                    "用于你本人的生活方式观察；基线为开始前七天，观察期为开始后七天。"
                    "两窗各至少四个记录日才比较均值，不判断疗效。"
                ),
                "status": "proposed",
                "source": selection["source"],
                "ai_status": selection["ai_status"],
                "result": None,
                "created_at": self.now().isoformat(),
            },
        )

    def transition(self, key, action, revision):
        item = self.read(self.row("experiment", key))
        if not item:
            raise HTTPException(404, "experiment not found")
        if item["revision"] != revision:
            raise HTTPException(409, "experiment changed; refresh before retrying")
        allowed = {
            "accept": ({"proposed"}, "running"),
            "pause": ({"running"}, "paused"),
            "resume": ({"paused"}, "running"),
            "stop": ({"proposed", "running", "paused"}, "stopped"),
            "evaluate": ({"running"}, "completed"),
        }
        valid, target = allowed[action]
        if item["status"] not in valid:
            raise HTTPException(409, "invalid experiment transition")
        if action == "accept":
            item["accepted_at"] = self.now().isoformat()
            item["baseline_start"] = (self.now() - timedelta(days=7)).isoformat()
            item["consent_version"] = PRIVACY_VERSION
            item["ends_at"] = (self.now() + timedelta(days=item["duration_days"])).isoformat()
        if action == "pause":
            item["paused_at"] = self.now().isoformat()
        if action == "resume":
            pause_start = item.pop("paused_at")
            item.setdefault("pause_intervals", []).append([pause_start, self.now().isoformat()])
            pause_length = self.now() - datetime.fromisoformat(pause_start)
            item["ends_at"] = (datetime.fromisoformat(item["ends_at"]) + pause_length).isoformat()
        if action == "evaluate":
            if self.now() < datetime.fromisoformat(item["ends_at"]):
                raise HTTPException(409, "observation window is not complete")
            records = [self.read(row) for row in self.rows("log")]
            baseline_start = item.get(
                "baseline_start",
                (datetime.fromisoformat(item["accepted_at"]) - timedelta(days=7)).isoformat(),
            )
            baseline = [
                r for r in records if baseline_start <= r["created_at"] < item["accepted_at"]
            ]
            baseline_dates = sorted({r["date"] for r in baseline})
            baseline_means = [
                sum(r["energy"] for r in baseline if r["date"] == day)
                / sum(r["date"] == day for r in baseline)
                for day in baseline_dates
            ]
            records = [
                r
                for r in records
                if item["accepted_at"] <= r["created_at"] <= item["ends_at"]
                and not any(
                    start <= r["created_at"] < end for start, end in item.get("pause_intervals", [])
                )
            ]
            days = sorted({r["date"] for r in records})
            day_means = [
                sum(r["energy"] for r in records if r["date"] == day)
                / sum(r["date"] == day for r in records)
                for day in days
            ]
            change = (
                round((sum(day_means[-2:]) - sum(day_means[:2])) / 2, 2) if len(days) >= 4 else None
            )
            summary = "记录仅描述这段时间的主观感受，无法证明行动导致变化。"
            if change is not None:
                summary = (
                    f"最后两个记录日相对最初两个记录日，精力均值变化 {change:+g} 档。" + summary
                )
            else:
                summary = "有效记录不足四天，不能比较前后变化。" + summary
            between_change = (
                round(
                    sum(day_means) / len(day_means) - sum(baseline_means) / len(baseline_means), 2
                )
                if len(days) >= 4 and len(baseline_dates) >= 4
                else None
            )
            if between_change is None:
                summary += "基线或观察期不足四个记录日，无法比较两窗均值。"
            else:
                summary += f"观察期相对基线的每日精力均值变化 {between_change:+g} 档，仅为描述。"
            item["result"] = {
                "baseline_window_start": baseline_start,
                "baseline_window_end": item["accepted_at"],
                "baseline_observed_days": len(baseline_dates),
                "between_window_energy_change": between_change,
                "status": "descriptive_only" if len(days) >= 4 else "insufficient_data",
                "observed_days": len(days),
                "window_start": item["accepted_at"],
                "window_end": item["ends_at"],
                "summary": summary,
                "energy_change": change,
            }
        item["status"] = target
        return self.write("experiment", key, item)

    def add_log(self, values):
        return self.write(
            "log",
            str(uuid4()),
            {**values, "created_at": self.now().isoformat(), "date": self.today()},
        )

    def mission(self, journey):
        key = self.today()
        stored = self.read(self.row("mission", key))
        if stored:
            return stored
        title = {
            "sleep": "睡前留 10 分钟安静收尾",
            "energy": "记录此刻的精力与压力",
            "activity": "身体允许时，轻松活动 5 分钟",
        }[journey["goal"]]
        return {
            "id": key,
            "title": title,
            "status": "proposed",
            "date": key,
            "why": "根据你选择的方向给出基础行动；不是对健康数据的判断。",
            "revision": 0,
        }

    def act(self, action, alternative="brief_check", mission_id=None, revision=None):
        journey = self.read(self.row("journey", "current"))
        if not journey:
            raise HTTPException(409, "choose a journey first")
        mission = self.mission(journey)
        if (mission_id is not None and mission_id != mission["id"]) or (
            revision is not None and revision != mission["revision"]
        ):
            raise HTTPException(409, "mission changed; refresh and choose again")
        if mission["status"] in {"done", "skipped"}:
            raise HTTPException(409, "today's action is already recorded")
        if action == "lighten":
            mission["title"] = {
                "brief_check": "只记录此刻的感受，今天先照顾自己",
                "quiet_minute": "留一分钟安静休息，不要求完成其他行动",
            }[alternative]
            mission["alternative"] = alternative
            mission["adjusted_at"] = self.now().isoformat()
        else:
            mission["status"] = "done" if action == "done" else "skipped"
            mission["recorded_at"] = self.now().isoformat()
        return self.write("mission", self.today(), mission)

    def receipt(self, event):
        receipt = str(uuid4())
        self.session.add(
            AuditEvent(
                id=receipt,
                fitcrew_user_id=self.user_id,
                event_type=event,
                resource_type="private_data",
                policy_result="allowed",
                trace_id=str(uuid4()),
            )
        )
        return {"deleted": True, "receipt_id": receipt}

    def delete_log(self, key):
        self.lock()
        row = self.row("log", key)
        if not row:
            raise HTTPException(404, "record not found")
        removed = self.read(row)
        self.session.delete(row)
        invalidated = {key}
        for experiment in self.rows("experiment"):
            item = self.read(experiment)
            if item.get("result") and item.get("result", {}).get(
                "baseline_window_start", item.get("accepted_at", "")
            ) <= removed["created_at"] <= item.get("ends_at", ""):
                item["result"] = {
                    "status": "invalidated",
                    "observed_days": 0,
                    "window_start": item["accepted_at"],
                    "window_end": item["ends_at"],
                    "summary": "观察记录已撤回，原结果已失效。",
                    "energy_change": None,
                }
                self.write("experiment", experiment.resource_key, item)
                invalidated.add(experiment.resource_key)
        # Remove cached request responses containing the withdrawn private record.
        for cached in self.rows("request"):
            if self.read(cached).get("response", {}).get("id") in invalidated:
                self.write(
                    "request",
                    cached.resource_key,
                    {"digest": self.read(cached)["digest"], "erased": True},
                )
        result = self.receipt("product.log.deleted")
        self.session.commit()
        return result

    def erase(self, account=False):
        user = self.lock()
        user.data_generation += 1
        sources = select(KnowledgeSource.id).where(KnowledgeSource.fitcrew_user_id == self.user_id)
        for model in (KnowledgeChunk, KnowledgeReview):
            self.session.execute(delete(model).where(model.source_id.in_(sources)))
        for record in self.rows("request"):
            self.write(
                "request",
                record.resource_key,
                {"digest": self.read(record)["digest"], "erased": True},
            )
        self.session.execute(
            delete(ProductRecord).where(
                ProductRecord.fitcrew_user_id == self.user_id, ProductRecord.kind != "request"
            )
        )
        for model in (
            HealthSample,
            DailyFeature,
            Insight,
            Memory,
            DemandItem,
            OutboxEvent,
            KnowledgeSource,
            SyncBatch,
            PairingExchangeSession,
        ):
            self.session.execute(delete(model).where(model.fitcrew_user_id == self.user_id))
        now = self.now()
        self.session.execute(
            update(Consent)
            .where(Consent.fitcrew_user_id == self.user_id)
            .values(granted=False, withdrawn_at=now)
        )
        self.session.execute(
            update(DeviceBinding)
            .where(DeviceBinding.fitcrew_user_id == self.user_id)
            .values(last_cursor=None, last_sync_at=None)
        )
        if account:
            self.session.execute(
                delete(IdentityBinding).where(IdentityBinding.fitcrew_user_id == self.user_id)
            )
            self.session.execute(
                update(DeviceBinding)
                .where(DeviceBinding.fitcrew_user_id == self.user_id)
                .values(revoked_at=now)
            )
            self.session.get(User, self.user_id).status = "deleted"
        result = self.receipt("account.deleted" if account else "product.data.deleted")
        self.session.commit()
        return result

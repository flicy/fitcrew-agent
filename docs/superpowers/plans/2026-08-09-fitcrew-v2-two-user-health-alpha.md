# FitCrew V2 Two-User Health Alpha Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an invite-only two-user BodyOS with isolated Feishu identities and HealthKit device pairing, prepare the iOS app for private TestFlight distribution, merge PR #1 after green CI, and deploy the merged SHA to Tencent.

**Architecture:** Add a focused enrollment service behind the existing owner-authenticated API, keeping identity, device, consent, and health queries scoped by `fitcrew_user_id`. Reuse one HealthKit iPhone app with a unique pairing payload per user. Treat Apple membership and external beta review as external gates while allowing the server release and upload-ready archive configuration to complete independently.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, PostgreSQL, pytest, Swift 6, SwiftUI, HealthKit, XcodeGen, Docker Compose, Hermes Feishu gateway, GitHub Actions, TestFlight.

---

## 中文实施任务

### Task 1：用户邀请服务与 Owner API

**Files:**
- Create: `apps/api/bodyos_api/enrollment.py`
- Modify: `apps/api/bodyos_api/owner_routes.py`
- Test: `apps/api/tests/test_user_enrollment.py`

- [ ] **Step 1：先写邀请接口失败测试**

```python
def test_invite_feishu_user_is_idempotent(client):
    first = client.post("/v1/owner/users/invite", headers=OWNER, json={"feishu_subject": "ou_invited", "locale": "zh-CN", "timezone": "Asia/Shanghai"})
    second = client.post("/v1/owner/users/invite", headers=OWNER, json={"feishu_subject": "ou_invited", "locale": "zh-CN", "timezone": "Asia/Shanghai"})
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json() == {"created": True, "status": "invited"}
    assert second.json() == {"created": False, "status": "invited"}
```

- [ ] **Step 2：运行并确认红灯**

Run: `uv run pytest apps/api/tests/test_user_enrollment.py::test_invite_feishu_user_is_idempotent -q`

Expected: `404` because `/v1/owner/users/invite` does not exist.

- [ ] **Step 3：实现最小邀请服务和接口**

```python
@dataclass(frozen=True)
class InvitationResult:
    fitcrew_user_id: str
    created: bool

def hash_subject(subject: str, pepper: str) -> str:
    if not pepper:
        raise RuntimeError("BODYOS_IDENTITY_PEPPER is required")
    return hmac.new(pepper.encode(), subject.encode(), hashlib.sha256).hexdigest()

def invite_feishu_user(session: Session, cipher: FieldCipher, *, subject: str, pepper: str, locale: str, timezone: str) -> InvitationResult:
    subject_hash = hash_subject(subject, pepper)
    identity = session.scalar(select(IdentityBinding).where(IdentityBinding.provider == "feishu", IdentityBinding.subject_hash == subject_hash, IdentityBinding.revoked_at.is_(None)))
    if identity is not None:
        return InvitationResult(identity.fitcrew_user_id, False)
    user = User(locale=locale, timezone=timezone)
    session.add(user)
    session.flush()
    binding = IdentityBinding(fitcrew_user_id=user.fitcrew_user_id, provider="feishu", subject_hash=subject_hash, encrypted_subject=b"", verified_at=datetime.now(UTC))
    session.add(binding)
    session.flush()
    encrypted = cipher.encrypt_json({"subject": subject}, aad=f"identity:{binding.id}")
    binding.encrypted_subject = encrypted.nonce + encrypted.ciphertext
    session.commit()
    return InvitationResult(user.fitcrew_user_id, True)
```

The route returns only `{created, status}` and never exposes subject or internal user ID.

- [ ] **Step 4：运行邀请与身份冲突测试**

Run: `uv run pytest apps/api/tests/test_user_enrollment.py -q`

Expected: invitation tests pass, including owner-token rejection and unchanged existing binding.

- [ ] **Step 5：提交**

```bash
git add apps/api/bodyos_api/enrollment.py apps/api/bodyos_api/owner_routes.py apps/api/tests/test_user_enrollment.py
git commit -m "feat: add controlled BodyOS user invitations"
```

### Task 2：每用户独立设备配对与同意

**Files:**
- Modify: `apps/api/bodyos_api/enrollment.py`
- Modify: `apps/api/bodyos_api/owner_routes.py`
- Test: `apps/api/tests/test_user_enrollment.py`
- Test: `apps/api/tests/test_health_routes.py`

- [ ] **Step 1：写两用户配对与跨令牌拒绝测试**

```python
def test_pairing_is_scoped_to_invited_user(client, session):
    invite(client, "ou_second")
    response = client.post("/v1/owner/users/pair", headers=OWNER, json={"feishu_subject": "ou_second", "device_public_id": "xuecheng-iphone", "categories": ["sleep_asleep", "heart_rate_variability", "resting_heart_rate", "workout", "active_energy", "step_count", "stand_hours", "activity_summary"]})
    assert response.status_code == 201
    assert set(response.json()) == {"device_binding_id", "consent_ids", "device_token", "pairing_url"}
    assert session.query(DeviceBinding).filter_by(device_public_id="xuecheng-iphone").one().fitcrew_user_id != OWNER_USER_ID
```

Add a health-ingest test that sends the invited user's batch with the owner's bearer token and expects `401`.

- [ ] **Step 2：运行并确认红灯**

Run: `uv run pytest apps/api/tests/test_user_enrollment.py apps/api/tests/test_health_routes.py -q`

Expected: pairing endpoint test fails with `404`.

- [ ] **Step 3：实现配对服务**

```python
class EnrollmentConflict(ValueError):
    pass

@dataclass(frozen=True)
class PairingResult:
    device_binding_id: str
    consent_ids: dict[str, str]
    device_token: str
    pairing_url: str

def pair_invited_user(session: Session, *, fitcrew_user_id: str, device_public_id: str, categories: set[HealthKind], public_base_url: str) -> PairingResult:
    existing = session.scalar(select(DeviceBinding).where(DeviceBinding.device_public_id == device_public_id))
    if existing is not None and existing.fitcrew_user_id != fitcrew_user_id:
        raise EnrollmentConflict("device is bound to another user")
    token = secrets.token_urlsafe(32)
    binding = existing or DeviceBinding(fitcrew_user_id=fitcrew_user_id, device_public_id=device_public_id, token_hash="")
    binding.token_hash = hash_device_token(token)
    binding.revoked_at = None
    session.add(binding)
    session.flush()
```

Create fresh granted consents only for requested categories and return the existing versioned private pairing URL payload. The endpoint requires `X-Owner-Token` and maps `EnrollmentConflict` to HTTP `409`.

- [ ] **Step 4：运行配对、摄取和 Owner 回归测试**

Run: `uv run pytest apps/api/tests/test_user_enrollment.py apps/api/tests/test_health_routes.py apps/api/tests/test_bodyos_routes.py -q`

Expected: all selected tests pass and the original owner status remains connected.

- [ ] **Step 5：提交**

```bash
git add apps/api/bodyos_api/enrollment.py apps/api/bodyos_api/owner_routes.py apps/api/tests/test_user_enrollment.py apps/api/tests/test_health_routes.py
git commit -m "feat: isolate HealthKit pairing per BodyOS user"
```

### Task 3：安全运维脚本与飞书白名单

**Files:**
- Create: `scripts/bootstrap_invited_user.py`
- Modify: `infra/tencent/compose.yaml`
- Modify: `docs/operations/deployment-and-rollback.md`
- Test: `apps/api/tests/test_operations.py`

- [ ] **Step 1：写运行产物隐私测试**

```python
def test_invited_user_bootstrap_never_prints_pairing_secrets():
    source = (ROOT / "scripts/bootstrap_invited_user.py").read_text()
    assert "print(payload)" not in source
    assert 'mode=0o700' in source
    assert 'os.chmod(record, 0o600)' in source
    assert 'os.chmod(qr_path, 0o600)' in source
```

- [ ] **Step 2：运行并确认红灯**

Run: `uv run pytest apps/api/tests/test_operations.py -q`

Expected: missing script causes failure.

- [ ] **Step 3：实现脚本**

The script reads `BODYOS_INVITEE_FEISHU_SUBJECT`, `BODYOS_INVITEE_DEVICE_PUBLIC_ID`, and `BODYOS_INVITEE_SLUG`, calls invite then pair through loopback, and writes `invitees/<slug>/pairing.json` plus `pairing.png` under `/owner-runtime` with directory `0700` and files `0600`. Its only stdout is `Invited user pairing stored outside Git.`

- [ ] **Step 4：记录白名单更新和重启顺序**

Document an exact operation that appends the invited subject to `FEISHU_ALLOWED_USERS` without echo, rerenders the Hermes profile, recreates only `gateway`, and verifies both users while retaining `FEISHU_ALLOW_ALL_USERS=false`.

- [ ] **Step 5：测试并提交**

Run: `uv run pytest apps/api/tests/test_operations.py apps/api/tests/test_v1_hardening.py -q`

```bash
git add scripts/bootstrap_invited_user.py infra/tencent/compose.yaml docs/operations/deployment-and-rollback.md apps/api/tests/test_operations.py
git commit -m "feat: add private invited-user bootstrap operations"
```

### Task 4：iOS TestFlight 与 HealthKit 发布准备

**Files:**
- Modify: `apps/ios-bridge/project.yml`
- Modify: `apps/ios-bridge/FitCrewHealthBridge/Info.plist`
- Modify: `apps/ios-bridge/FitCrewHealthBridge/ContentView.swift`
- Create: `apps/ios-bridge/FitCrewHealthBridge/Assets.xcassets/Contents.json`
- Create: `apps/ios-bridge/FitCrewHealthBridge/Assets.xcassets/AppIcon.appiconset/Contents.json`
- Create: `apps/ios-bridge/FitCrewHealthBridge/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png`
- Create: `docs/release/testflight-metadata.md`
- Modify: `scripts/check_ios_generated_config.py`
- Test: `apps/ios-bridge/FitCrewHealthBridgeTests/ConsentStoreTests.swift`

- [ ] **Step 1：写发布配置失败检查**

Extend `check_ios_generated_config.py` to require `CFBundleShortVersionString == "2.0.0"`, integer build text, `ITSAppUsesNonExemptEncryption == false`, an App Icon source, HealthKit entitlement, pairing URL scheme, and no Verifiable Health Records entitlement.

- [ ] **Step 2：运行并确认红灯**

Run: `(cd apps/ios-bridge && xcodegen generate && python3 ../../scripts/check_ios_generated_config.py)`

Expected: fail because export-compliance and App Icon configuration are absent.

- [ ] **Step 3：实现最小发布配置**

Set `ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon`, preserve the unique bundle ID, add `ITSAppUsesNonExemptEncryption: false` only after verifying the app uses platform HTTPS/Keychain APIs without custom export-controlled cryptography, and add a visible in-app privacy-policy link to the merged public repository URL.

Generate a text-free 1024×1024 FitCrew icon and reference it from the asset catalog. Do not include health values, Apple marks, or medical claims.

- [ ] **Step 4：添加 TestFlight 双语元数据**

Include exact beta description, testing focus, feedback/support/privacy URLs, review notes explaining HealthKit read-only use, external email-only group policy, and Account Holder fields that must be supplied manually.

- [ ] **Step 5：验证并提交**

Run: `(cd apps/ios-bridge && xcodegen generate && python3 ../../scripts/check_ios_generated_config.py && xcodebuild build -project FitCrewHealthBridge.xcodeproj -scheme FitCrewHealthBridge -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO -quiet)`

Expected: generated config and unsigned Simulator build pass.

```bash
git add apps/ios-bridge docs/release scripts/check_ios_generated_config.py
git commit -m "feat: prepare FitCrew Health Bridge for TestFlight"
```

### Task 5：完整验证、PR 与代码审查

**Files:**
- Modify: `docs/evidence/2026-08-09-two-user-alpha-verification.md`

- [ ] **Step 1：运行完整验证**

```bash
uv sync --frozen --extra dev
uv run pytest -q
uv run ruff check apps/api scripts infra/tencent
python3 scripts/check_bilingual_docs.py
(cd apps/ios-bridge/Core && swift test)
(cd apps/ios-bridge && xcodegen generate && python3 ../../scripts/check_ios_generated_config.py)
git diff --check
```

Expected: all tests and checks pass; generated `.xcodeproj` remains untracked.

- [ ] **Step 2：写双语脱敏证据并检查秘密**

Evidence records test counts, Boolean isolation results, build status, and remaining Apple membership gate only. Run `git grep -nE 'BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|sk-[A-Za-z0-9_-]{16,}' -- ':!uv.lock'` and expect no matches.

- [ ] **Step 3：提交并推送现有 PR 分支**

```bash
git add docs/evidence/2026-08-09-two-user-alpha-verification.md
git commit -m "docs: record two-user alpha verification"
git push origin codex/v2-owner-alpha
gh pr checks 1 --repo flicy/fitcrew-agent --watch
```

Expected: `python-and-policy`, `swift-core`, and `ios-build` pass.

- [ ] **Step 4：执行代码审查并修复高优先级问题**

Review only the PR diff against its GitHub base, rerun relevant tests for every fix, and push no unrelated changes.

### Task 6：合并、腾讯云部署与双用户验收

**Files:**
- Runtime-only: `/opt/fitcrew-bodyos/infra/tencent/runtime/*` on Tencent

- [ ] **Step 1：确认合并门禁**

Run: `gh pr view 1 --repo flicy/fitcrew-agent --json state,mergeable,statusCheckRollup,headRefOid`

Expected: PR is open, mergeable, and all required checks pass.

- [ ] **Step 2：按用户授权合并 PR**

Run: `gh pr merge 1 --repo flicy/fitcrew-agent --merge --delete-branch=false`

Expected: PR state becomes `MERGED`; no Release is created.

- [ ] **Step 3：从合并后的 main 部署腾讯云**

On Tencent, fetch the exact merged `main` SHA into `/opt/fitcrew-bodyos`, run `infra/tencent/deploy.sh`, and require database, API, worker, gateway, and Caddy health before accepting traffic. Never print `.env.runtime` or pairing payloads.

- [ ] **Step 4：创建第二用户身份与配对私密产物**

Resolve the invited Feishu subject without printing it, update the DM allowlist, run `bootstrap_invited_user.py`, and retain the QR only in the `0700` owner runtime directory. Do not send the QR until the user explicitly authorizes transmission to the intended recipient.

- [ ] **Step 5：执行真实验收**

Verify Chris remains connected with existing category labels, Xue Cheng has isolated group/DM behavior, service restart recovery succeeds, and no raw health values appear. HealthKit sync for Xue Cheng remains pending until paid membership, TestFlight upload, Apple review, remote install, authorization, and private pairing complete.

## English execution mapping

The six tasks above are the complete executable plan. English operators should follow the same code blocks and commands in order:

1. Add the idempotent owner-authenticated Feishu invitation service and prove repeated invitations return the same binding without exposing identifiers.
2. Add per-user pairing and consent issuance, then prove subject/device conflicts and cross-token health ingestion fail closed.
3. Add a private runtime bootstrap script, preserve the closed Hermes DM allowlist, and document a no-echo gateway restart procedure.
4. Prepare the iOS target for TestFlight with a production icon, stable bundle/version metadata, HealthKit privacy disclosure, export-compliance declaration, bilingual beta metadata, and an unsigned Simulator build.
5. Run the complete Python, Swift, iOS configuration, security, bilingual, and CI suite; write redacted bilingual evidence; update PR #1 and review the actual PR diff.
6. Merge only after green gates, deploy the merged `main` SHA to Tencent, create the second user's private pairing artifact, and verify live two-user isolation. TestFlight installation remains gated on the Account Holder's paid membership and Apple's external beta approval.

All implementation commits must preserve Chris's existing device token and data, keep raw health values and Feishu identifiers out of logs/Git/PRs, leave the generated Xcode project untracked, avoid a public TestFlight link, and perform no purchase or agreement acceptance on the user's behalf.

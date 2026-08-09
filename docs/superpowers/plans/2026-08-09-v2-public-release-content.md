# FitCrew V2 Public Release Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a factually precise FitCrew / BodyOS V2.0 product narrative for Xiaohongshu, WeChat Official Account, GitHub README, and a `v2.0.0` GitHub Release.

**Architecture:** Keep the repository as the source of truth: a bilingual release note records capabilities, evidence, and explicit non-completion boundaries; a bilingual launch kit holds platform-specific ready-to-post copy; README becomes the concise technical entry point. The public GitHub Release is created only from the merged documentation commit and links to the product page, privacy policy, and operational evidence without exposing personal health data or credentials.

**Tech Stack:** Markdown, repository bilingual-doc checker, Git, GitHub CLI.

---

## 中文计划摘要

目标：为FitCrew / BodyOS V2.0准备小红书、公众号、GitHub README和公开Release。所有对外内容只采用已验证事实：PR#2已合并、生产服务已部署、三项CI已通过。内容必须明确Apple健康是可选授权、原始数据加密、群聊不展示健康原始值、不提供医疗诊断；TestFlight外部测试和薛程真机验收尚未完成。

执行顺序：先提交双语发布说明和发布文案，再更新README并通过文档检查；文档PR合并后才创建`v2.0.0`GitHub Release。Release需要标注已部署后端仍报告`v2.0.0-alpha.1`，避免将TestFlight或16天实验误写为已经完成。

---

### Task 1: Write bilingual V2.0 release notes and launch kit

**Files:**
- Create: `docs/release/v2.0-release-notes.md`
- Create: `docs/release/v2.0-launch-kit.md`
- Test: `scripts/check_bilingual_docs.py`

- [ ] **Step 1: Define release facts before writing copy**

Use only verified claims: PR #2 merge commit `3438e02770a04478913dfeeead029d23a55167f5`; deployed health endpoint `https://124.156.218.104/healthz`; version `v2.0.0-alpha.1`; GitHub CI passed Python/policy, Swift Core, and iOS simulator. State that TestFlight external distribution and the invited user's physical-device acceptance remain future milestones.

- [ ] **Step 2: Write `v2.0-release-notes.md` in Chinese and English sections**

Include: release summary; FitCrew/BodyOS/Moticlaw naming; encrypted HealthKit/Apple Watch/CGM path; Feishu group/DM privacy boundary; one-time pairing and two-user isolation; deployment/rollback/TLS evidence; exact boundaries that prevent a false claim about TestFlight, medical diagnosis, or 16 days of completed data.

- [ ] **Step 3: Write `v2.0-launch-kit.md` in Chinese and English sections**

Include a Xiaohongshu post built around the user-approved story “from a glucose meter, Apple Watch, and a Feishu group to a private health coach”: title candidates, cover copy, ready-to-post body, hashtags, and a pinned comment. Include a WeChat Official Account article with title, lead, sectioned article body, and ending CTA. Do not claim medical diagnosis, public sharing of health data, or TestFlight availability.

- [ ] **Step 4: Run the bilingual documentation check**

Run: `uv run python scripts/check_bilingual_docs.py`

Expected: `All Markdown documents have Chinese and English coverage.`

- [ ] **Step 5: Commit the release documents**

```bash
git add docs/release/v2.0-release-notes.md docs/release/v2.0-launch-kit.md
git commit -m "docs: add FitCrew V2 public launch kit"
```

### Task 2: Make README the public technical entry point

**Files:**
- Modify: `README.md`
- Test: `scripts/check_bilingual_docs.py`

- [ ] **Step 1: Add a V2.0 now-live section in both language sections**

Add the verified public deployment URL, V2 two-user isolation/pairing summary, green-leaf Health Bridge/TestFlight preparation, security and deployment evidence, and links to the release notes and launch kit. Preserve existing privacy claims and replace the obsolete owner-only wording with a factual invitation-ready description.

- [ ] **Step 2: Preserve declared boundaries**

Keep these explicit: Apple Health is optional; HealthKit data is encrypted; groups never expose raw health data; BodyOS is not medical diagnosis; TestFlight external distribution is not yet available; all real health data and private pairing artifacts stay outside Git.

- [ ] **Step 3: Validate README and repository docs**

Run: `uv run python scripts/check_bilingual_docs.py && git diff --check`

Expected: bilingual checker passes and `git diff --check` prints nothing.

- [ ] **Step 4: Commit README update**

```bash
git add README.md
git commit -m "docs: present FitCrew V2 public release"
```

### Task 3: Submit, validate, and publish the GitHub V2.0 release

**Files:**
- No repository file changes beyond Tasks 1–2.

- [ ] **Step 1: Push the release-content branch and open a PR to `main`**

Use a bilingual PR body that states documentation-only scope and carries the verified release boundaries. Do not modify the already deployed runtime code.

- [ ] **Step 2: Require the existing CI gates before merge**

Wait for `python-and-policy`, `swift-core`, and `ios-build` to pass. If a check fails, investigate and repair only a failure caused by this branch.

- [ ] **Step 3: Merge the documentation PR**

Merge only after all required checks are green. Fetch the exact resulting `main` commit SHA.

- [ ] **Step 4: Create the public GitHub Release**

Create tag `v2.0.0` at the merged documentation commit. Set the title to `FitCrew / BodyOS V2.0` and use the Chinese/English release-note summary. Clearly label the deployed backend version as `v2.0.0-alpha.1` and list TestFlight/invited-device acceptance as next milestones.

- [ ] **Step 5: Verify public release and final repository state**

Run: `gh release view v2.0.0 --repo flicy/fitcrew-agent` and `git ls-remote --tags origin refs/tags/v2.0.0`.

Expected: both identify the same tag and the release notes contain no health values, identifiers, secrets, or one-time pairing artifacts.

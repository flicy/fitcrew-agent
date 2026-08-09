# FitCrew V2 Public Content Implementation Plan / FitCrew V2 公开内容实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the FitCrew Agent README, V2 release notes, and social launch copy around the stable FitCrew/BodyOS product definition and the four confirmed V2 user capabilities, then update the existing GitHub `v2.0.0` Release without moving its tag. / 围绕稳定的 FitCrew/BodyOS 产品定义和四项已确认的 V2 用户能力，重写 FitCrew Agent README、V2 版本说明和社交发布文案，并原位更新 GitHub `v2.0.0` Release，不移动标签。

**Architecture:** The repository remains the source of truth for the bilingual product story. `README.md` explains the product to a new user, `docs/release/v2.0-release-notes.md` records the version, and `docs/release/v2.0-launch-kit.md` contains channel-ready Xiaohongshu and WeChat copy. The GitHub Release body is rendered from the same facts after the documentation PR is merged. / 仓库继续作为双语产品叙事的唯一事实来源：`README.md` 面向第一次了解产品的用户，版本说明记录版本内容，发布素材提供可直接使用的小红书和公众号文案；文档 PR 合并后，再用同一事实原位更新 GitHub Release。

**Tech Stack:** Markdown, Git, GitHub CLI, repository bilingual-document checker. / Markdown、Git、GitHub CLI、仓库双语文档检查器。

---

## 中文实施步骤

### Task 1：建立发布事实门禁

**Files:**
- Read: `README.md`
- Read: `docs/release/v2.0-release-notes.md`
- Read: `docs/release/v2.0-launch-kit.md`
- Read: `docs/superpowers/specs/2026-08-09-v2-user-facing-release-design.md`

- [ ] **Step 1：确认当前分支与基线**

Run:

```bash
git status --short --branch
git rev-parse HEAD
git merge-base HEAD origin/main
```

Expected: branch is `codex/v2-user-story`, the tree contains no unrelated edits, and the merge base is the current accepted `main` lineage.

- [ ] **Step 2：保存现有 Release 的不可变属性**

Run:

```bash
gh release view v2.0.0 --repo flicy/fitcrew-agent \
  --json tagName,targetCommitish,isDraft,isPrerelease,url
```

Expected: `tagName` is `v2.0.0`, `isDraft` and `isPrerelease` are false. Record `targetCommitish` only for the final equality check; do not retag or recreate the Release.

- [ ] **Step 3：运行预修改内容审计，确认旧叙事确实存在**

Run:

```bash
rg -n '两用户健康 Alpha|two-user health Alpha|一次性配对|one-time pairing|v2\.0\.0-alpha\.1' \
  README.md docs/release/v2.0-release-notes.md docs/release/v2.0-launch-kit.md
```

Expected: the command finds engineering-first copy in the current public files. This is the red-state evidence that the rewrite is needed.

### Task 2：用用户视角重写 README

**Files:**
- Modify: `README.md`

- [ ] **Step 1：替换首屏与产品定位**

Use `apply_patch` so the first visible Chinese section starts with this exact meaning:

```markdown
# FitCrew · AI 健身管理专家

**BodyOS 是你在飞书中接触到的私人生活方式教练。**

FitCrew 把持续汇集的身体数据、你的主观感受和科学知识放进同一段长期对话里，帮助你更容易看懂生活方式与身体状态之间的关系，并把建议落实成今天能做的小行动。
```

The English opening must be semantically aligned:

```markdown
# FitCrew · AI Fitness Management Expert

**BodyOS is the private lifestyle coach you meet in Feishu.**

FitCrew brings continuously collected body data, subjective perception, and scientific knowledge into one long-running conversation so you can better understand lifestyle patterns and turn guidance into a small action you can take today.
```

- [ ] **Step 2：加入四项 V2 用户能力，顺序固定**

Write a Chinese “V2 现在能做什么” section and an aligned English “What V2 can do now” section with these four cards/bullets in this order:

```markdown
1. **汇集 Apple Watch 与鱼跃血糖数据**：经用户授权，iPhone HealthKit Bridge 读取已经进入 Apple Health 的 Apple Watch 与鱼跃 Anytime 5 Pro 数据。
2. **理解食物 × 血糖 × 身体感知**：在 BodyOS 私聊中，结合授权数据和你的主观感受，讨论今天的食物、血糖变化与生活方式之间可能的关系。
3. **在群聊里一起行动和学习**：回答通用的饮食、训练、睡眠与控糖知识问题，也可以参与打卡和日常健康互动。
4. **用三本科学书籍辅助判断**：知识库收录《控糖革命》《百岁人生行动手册》《睡眠优化完全指南：科学与实践》。
```

The English bullets must preserve the same scope and order, including the authorized Apple Health route and the general-knowledge-only group boundary.

- [ ] **Step 3：明确群聊与私聊的使用方式**

Add a comparison that says:

```markdown
- **群聊**：通用饮食、训练、睡眠、控糖知识；共同打卡与健康互动。群聊不读取任何成员的个人健康数据、私聊内容或私人知识库。
- **BodyOS 私聊**：基于该用户主动授权的数据，讨论个人的食物、血糖、睡眠、训练和身体感知；不向其他用户泄露。
```

Do not describe group answers as using personal context. Do not make Apple devices or HealthKit authorization a prerequisite for basic group participation.

- [ ] **Step 4：重写科学依据、隐私和医疗边界**

The scientific-basis section must list the three exact Chinese titles. The privacy section must state that Apple Health authorization is optional, personal data never enters group answers, raw sensitive fields are encrypted at rest, and BodyOS does not diagnose disease, prescribe treatment, or advise on medication.

- [ ] **Step 5：把开发者事实移到末尾**

Keep the verified architecture, CI, deployment, one-time pairing, two-user controlled test, TestFlight status, and incomplete 16-day study only in a final “开发者与验证 / Developer and verification” section. Preserve the truthful boundary that external TestFlight distribution, invited-device acceptance, and the 16-day outcome are not complete.

### Task 3：重写 V2 Release Notes 和社交发布素材

**Files:**
- Modify: `docs/release/v2.0-release-notes.md`
- Modify: `docs/release/v2.0-launch-kit.md`

- [ ] **Step 1：重写版本说明的信息顺序**

Use this exact section order in both Chinese and English:

```markdown
1. FitCrew 与 BodyOS 是什么
2. V2 新增的四项能力
3. 群聊与私聊怎么分工
4. 三本科学书籍
5. 数据、隐私与医疗边界
6. 已验证的工程状态
7. 尚未完成的外部分发、受邀真机验收和 16 天实验
```

The title should communicate the product value, for example “FitCrew V2：把 Apple Watch、血糖仪和科学知识接进 BodyOS”，not lead with “two-user Alpha.”

- [ ] **Step 2：重写小红书发布稿**

The Chinese Xiaohongshu section must use the confirmed personal-experiment narrative and include:

```markdown
标题：我把 Apple Watch、血糖仪和 3 本书，接进了飞书里的私人教练

开头：以前我的运动、睡眠、血糖和身体感受分散在不同 App 里。数据很多，但它们不会主动告诉我：今天吃的东西、血糖变化和身体感受之间，可能有什么关系。

现在：FitCrew V2 让 BodyOS 在飞书里持续陪我——授权后汇集 Apple Watch 和鱼跃 Anytime 5 Pro 数据；私聊讨论食物、血糖和身体感知；群聊回答通用饮食、训练、睡眠与控糖问题；并使用三本确认过的科学书籍作为知识来源。

边界：这不是医疗产品，也不替代医生；16 天真实实验仍在进行，TestFlight 外部分发尚未完成。
```

Keep the text conversational and user-centered. Do not claim measured outcomes that have not been observed.

- [ ] **Step 3：重写公众号长文**

Use this narrative arc in the Chinese WeChat section, with an aligned English reference version:

```markdown
1. 问题：健康数据、身体感知和知识彼此分散。
2. 产品：FitCrew 是 AI 健身管理专家，BodyOS 是飞书里的私人生活方式教练。
3. 数据：Apple Watch 与鱼跃 Anytime 5 Pro 经 Apple Health / HealthKit 授权汇集。
4. 对话：私聊理解食物 × 血糖 × 身体感知；群聊回答通用知识并陪伴打卡。
5. 知识：三本书为什么分别覆盖控糖、长期健康行动与睡眠。
6. 边界：隐私隔离、授权可选、不诊断、不治疗、不做用药建议。
7. 现状：工程验证已通过；外部 TestFlight、受邀设备和 16 天结论仍未完成。
```

- [ ] **Step 4：清除错误或过时用词**

Run after editing:

```bash
if rg -n 'FitClew|鱼悦|《抗糖革命》|群聊.*个人健康数据|group.*personal health data' \
  README.md docs/release/v2.0-release-notes.md docs/release/v2.0-launch-kit.md; then
  exit 1
fi
```

Expected: no matches.

### Task 4：验证、提交并创建文档 PR

**Files:**
- Verify: `README.md`
- Verify: `docs/release/v2.0-release-notes.md`
- Verify: `docs/release/v2.0-launch-kit.md`

- [ ] **Step 1：运行术语与能力一致性门禁**

Run:

```bash
for file in README.md docs/release/v2.0-release-notes.md docs/release/v2.0-launch-kit.md; do
  rg -q 'FitCrew' "$file"
  rg -q 'BodyOS' "$file"
  rg -q 'Apple Watch' "$file"
  rg -q 'Anytime 5 Pro' "$file"
  rg -q '控糖革命' "$file"
  rg -q '百岁人生行动手册' "$file"
  rg -q '睡眠优化完全指南：科学与实践' "$file"
done
```

Expected: exit code 0 for all files.

- [ ] **Step 2：运行仓库文档与差异检查**

Run:

```bash
uv run python scripts/check_bilingual_docs.py
git diff --check
git diff --stat origin/main...HEAD
```

Expected: bilingual checker passes, whitespace check is clean, and the diff only includes the approved spec plus public-content files and implementation plans.

- [ ] **Step 3：提交公开内容修改**

Run:

```bash
git add README.md docs/release/v2.0-release-notes.md docs/release/v2.0-launch-kit.md
git commit -m "docs: tell the FitCrew V2 product story"
```

Expected: one focused content commit.

- [ ] **Step 4：推送并创建 PR**

Run:

```bash
git push -u origin codex/v2-user-story
gh pr create --repo flicy/fitcrew-agent --base main --head codex/v2-user-story \
  --title "docs: align FitCrew V2 public product story" \
  --body-file docs/release/v2.0-release-notes.md
```

Expected: a new PR URL targeting `main`.

- [ ] **Step 5：等待 CI 并合并**

Run:

```bash
gh pr checks --repo flicy/fitcrew-agent --watch
gh pr merge --repo flicy/fitcrew-agent --squash --delete-branch
```

Expected: every required check is successful before the squash merge.

### Task 5：原位更新 GitHub Release 并验证标签未移动

**Files:**
- Read source: `docs/release/v2.0-release-notes.md`
- Temporary file: a private `mktemp` path used only to assemble the bilingual Release body

- [ ] **Step 1：从版本说明组装精简双语 Release 正文**

Create a temporary file with `mktemp`, then use `apply_patch` against that exact temporary path. The body must contain, in both languages: stable product definition, four V2 abilities, group/DM privacy boundary, three books, medical boundary, verified engineering state, and incomplete TestFlight/device/16-day items.

- [ ] **Step 2：编辑现有 Release**

Run:

```bash
gh release edit v2.0.0 --repo flicy/fitcrew-agent \
  --title "FitCrew V2 · BodyOS 私人生活方式教练" \
  --notes-file "$RELEASE_BODY_FILE"
```

Expected: the existing Release URL remains `https://github.com/flicy/fitcrew-agent/releases/tag/v2.0.0`; no new tag or Release is created.

- [ ] **Step 3：验证 Release 和标签不可变属性**

Run:

```bash
gh release view v2.0.0 --repo flicy/fitcrew-agent \
  --json tagName,targetCommitish,isDraft,isPrerelease,url,body
git ls-remote --tags origin refs/tags/v2.0.0
```

Expected: tag name and tag object match the pre-edit values, draft/prerelease remain false, and the body now leads with the product definition and four capabilities.

---

## English execution summary

1. Capture the current immutable `v2.0.0` Release properties and demonstrate that the existing public copy is engineering-first.
2. Rewrite `README.md` around FitCrew as the AI fitness-management expert and BodyOS as the Feishu private lifestyle coach.
3. Present the four capabilities in the confirmed order: Apple Watch/Yuwell data via authorized Apple Health, food-glucose-perception discussion in DM, general health knowledge and check-ins in groups, and guidance from the three exact books.
4. Rewrite bilingual release notes, Xiaohongshu copy, and WeChat copy without claiming completed TestFlight distribution, invited-device acceptance, a finished 16-day study, or medical outcomes.
5. Run terminology, bilingual-document, and whitespace gates; create a focused PR; merge only after required CI passes.
6. Edit the existing GitHub Release in place and verify that `v2.0.0` was not recreated or moved.

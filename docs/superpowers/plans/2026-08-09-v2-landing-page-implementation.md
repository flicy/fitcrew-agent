# FitCrew V2 Landing Page Implementation Plan / FitCrew V2 落地页实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `https://flicy.github.io/cola-pages/fitcrew/` so the existing green-leaf FitCrew landing page visibly presents V2 as live, explains the four confirmed user capabilities, and states the correct group/DM privacy boundary. / 更新现有绿色叶子 FitCrew 落地页，使其明确展示 V2 已上线、四项用户能力以及正确的群聊/私聊隐私边界。

**Architecture:** Keep the existing single-file static page and its responsive visual system. Make a focused content-and-layout enhancement in `fitcrew/index.html` on a feature branch based on `gh-pages`, then merge through a PR to `gh-pages` and verify the deployed GitHub Pages output. / 保持现有单文件静态页面与响应式视觉系统，只对 `gh-pages` 上的 `fitcrew/index.html` 做聚焦的内容与布局增强，通过独立 PR 合并后验证 GitHub Pages 公网页面。

**Tech Stack:** Semantic HTML, existing CSS design tokens, vanilla JavaScript, GitHub Pages, GitHub CLI. / 语义化 HTML、现有 CSS 设计变量、原生 JavaScript、GitHub Pages、GitHub CLI。

---

## 中文实施步骤

### Task 1：建立独立的 Cola Pages 工作区

**Files:**
- Repository: `flicy/cola-pages`
- Base branch: `gh-pages`
- Working directory: `/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story`

- [ ] **Step 1：确认目标目录不存在，避免覆盖用户文件**

Run:

```bash
test ! -e "/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story"
```

Expected: exit code 0. If the directory already exists, inspect it and reuse only if it is the expected clean repository; never delete it blindly.

- [ ] **Step 2：克隆 `gh-pages` 并创建功能分支**

Run:

```bash
gh repo clone flicy/cola-pages "/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story" -- --branch gh-pages
git -C "/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story" switch -c codex/fitcrew-v2-update
git -C "/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story" status --short --branch
```

Expected: clean branch `codex/fitcrew-v2-update` based on `origin/gh-pages`.

- [ ] **Step 3：运行预修改页面审计**

Run:

```bash
rg -n 'v2 · 开发中|《抗糖革命》|问任何健康问题|结合你的情况' \
  "/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story/fitcrew/index.html"
```

Expected: all four outdated phrases are found. This is the red-state evidence for the landing-page correction.

### Task 2：加入 V2 导航与“V2 已上线”模块

**Files:**
- Modify: `/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story/fitcrew/index.html`

- [ ] **Step 1：在导航增加 V2 锚点**

Use `apply_patch` to add this link inside the existing `.nav-links` list without removing existing navigation:

```html
<a href="#v2-update">V2 更新</a>
```

- [ ] **Step 2：复用现有设计变量增加 V2 卡片样式**

Add focused CSS near the existing section/card rules:

```css
.v2-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.v2-card{background:var(--card);border:1.5px solid #E3EBDD;border-radius:var(--r);padding:26px;box-shadow:var(--sh)}
.v2-card .v2-icon{font-size:30px;margin-bottom:14px}
.v2-card h3{font-size:20px;line-height:1.35;margin-bottom:9px}
.v2-card p{color:var(--ink-soft)}
.v2-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:26px}
@media(max-width:720px){.v2-grid{grid-template-columns:1fr}.v2-card{padding:22px}}
```

Do not introduce a new color system or replace the green-leaf logo.

- [ ] **Step 3：在核心能力之后加入完整 V2 模块**

Insert this semantic structure between the existing core-capability section and roadmap flow:

```html
<section id="v2-update">
  <div class="wrap">
    <div class="sec-head reveal">
      <span class="sec-tag">V2 · 已上线</span>
      <h2>身体数据、主观感受和科学知识，终于能在同一段对话里工作</h2>
      <p>FitCrew V2 让 BodyOS 成为你在飞书中持续对话的私人生活方式教练。</p>
    </div>
    <div class="v2-grid">
      <article class="v2-card reveal">
        <div class="v2-icon">⌚️</div>
        <h3>Apple Watch + 鱼跃血糖数据</h3>
        <p>经你授权，由 iPhone HealthKit Bridge 读取已进入 Apple Health 的 Apple Watch 与鱼跃 Anytime 5 Pro 数据。</p>
      </article>
      <article class="v2-card reveal">
        <div class="v2-icon">🥗</div>
        <h3>食物 × 血糖 × 身体感知</h3>
        <p>在 BodyOS 私聊中，把今天吃了什么、血糖如何变化和自己的感受放在一起讨论。</p>
      </article>
      <article class="v2-card reveal">
        <div class="v2-icon">💬</div>
        <h3>群聊里的通用健康问答</h3>
        <p>回答通用饮食、训练、睡眠与控糖知识，也参与打卡互动；不会在群里读取或展示个人健康数据。</p>
      </article>
      <article class="v2-card reveal">
        <div class="v2-icon">📚</div>
        <h3>三本科学书籍持续指导</h3>
        <p>知识库收录《控糖革命》《百岁人生行动手册》《睡眠优化完全指南：科学与实践》。</p>
      </article>
    </div>
    <div class="v2-actions reveal">
      <a class="btn btn-fill" href="https://github.com/flicy/fitcrew-agent/releases/tag/v2.0.0" target="_blank" rel="noopener">查看 V2 版本说明</a>
    </div>
  </div>
</section>
```

### Task 3：统一现有页面的产品事实与隐私边界

**Files:**
- Modify: `/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story/fitcrew/index.html`

- [ ] **Step 1：修正专家系统与知识共建书名**

Replace vague book references with this exact list wherever books are described:

```html
《控糖革命》《百岁人生行动手册》《睡眠优化完全指南：科学与实践》
```

Do not leave `《抗糖革命》` or the vague standalone phrase “精力管理” as a book title.

- [ ] **Step 2：修正群聊能力和演示**

Replace the “问任何健康问题、结合你的情况” copy with:

```html
<p class="p-desc">群里 @ FitCrew，可以询问通用饮食、训练、睡眠与控糖知识，也可以一起打卡；个人健康数据只在本人授权后的 BodyOS 私聊中使用。</p>
<div class="demo">「@FitCrew 晚饭后散步为什么有助于控糖？」——它会提供<b>通用科学知识与可执行建议</b>，不会读取群成员的个人健康数据。</div>
```

Review the “真实案例” section and remove any copy that presents a diagnosis or claims personalization from private health data in a group. General knowledge and conservative lifestyle guidance may remain.

- [ ] **Step 3：更新隐私区域**

Ensure the trust section communicates all of these points in visible text:

```html
群聊只回答通用饮食、训练、睡眠与控糖知识，并参与打卡互动。
个人健康数据和身体感知分析只在对应用户主动授权后的 BodyOS 私聊中发生。
BodyOS 提供生活方式指导，不提供疾病诊断、治疗或用药建议。
```

- [ ] **Step 4：更新路线图**

Replace the V2 card with this delivered-state meaning:

```html
<div class="rm-tag">v2 · 已上线</div>
<h3>「读懂身体」</h3>
<div class="rm-solve">解决“数据很多，却不知道它们说明什么”</div>
<p>汇集 Apple Watch 与鱼跃血糖数据，在私聊中理解食物、血糖和身体感知，在群聊中回答通用健康问题，并用三本科学书籍持续指导。</p>
```

Keep later versions as a short future direction without claiming delivery.

### Task 4：静态、响应式与链接验证

**Files:**
- Verify: `/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story/fitcrew/index.html`

- [ ] **Step 1：运行内容回归门禁**

Run:

```bash
PAGE="/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story/fitcrew/index.html"
rg -q 'id="v2-update"' "$PAGE"
rg -q 'v2 · 已上线' "$PAGE"
rg -q 'Apple Watch \+ 鱼跃血糖数据' "$PAGE"
rg -q '食物 × 血糖 × 身体感知' "$PAGE"
rg -q '群聊里的通用健康问答' "$PAGE"
rg -q '控糖革命' "$PAGE"
rg -q '百岁人生行动手册' "$PAGE"
rg -q '睡眠优化完全指南：科学与实践' "$PAGE"
rg -q 'releases/tag/v2.0.0' "$PAGE"
if rg -n 'v2 · 开发中|《抗糖革命》|问任何健康问题|结合你的情况' "$PAGE"; then exit 1; fi
```

Expected: exit code 0 with no outdated phrase output.

- [ ] **Step 2：检查 HTML 基本结构和差异**

Run:

```bash
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path

class Parser(HTMLParser):
    pass

page = Path('/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story/fitcrew/index.html')
parser = Parser()
parser.feed(page.read_text(encoding='utf-8'))
print('HTML parse: PASS')
PY
git -C "/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story" diff --check
```

Expected: `HTML parse: PASS` and clean whitespace check.

- [ ] **Step 3：本地查看桌面和移动布局**

Run a local server without modifying files:

```bash
python3 -m http.server 4173 --directory "/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story"
```

Open `http://127.0.0.1:4173/fitcrew/`. Verify at approximately 1440 px and 390 px widths that the V2 module is visible, cards collapse from two columns to one, navigation does not overlap, the green-leaf logo remains, and existing buttons/anchors still work. Stop only the local server after verification.

### Task 5：提交、PR、合并并验证 GitHub Pages

**Files:**
- Commit: `fitcrew/index.html`

- [ ] **Step 1：提交落地页修改**

Run:

```bash
git -C "/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story" add fitcrew/index.html
git -C "/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story" commit -m "feat: present the FitCrew V2 update"
```

Expected: one focused landing-page commit.

- [ ] **Step 2：推送并创建独立 PR**

Run:

```bash
git -C "/Users/chrisc/Documents/Fit Crew/cola-pages-v2-user-story" push -u origin codex/fitcrew-v2-update
gh pr create --repo flicy/cola-pages --base gh-pages --head codex/fitcrew-v2-update \
  --title "feat: add the FitCrew V2 release story" \
  --body "## 中文\n更新 FitCrew 落地页：V2 已上线、四项用户能力、三本科学书籍，以及群聊与私聊的隐私边界。\n\n## English\nUpdates the FitCrew landing page with the live V2 story, four user capabilities, three scientific books, and the group/DM privacy boundary."
```

Expected: a new PR URL targeting `gh-pages`.

- [ ] **Step 3：检查并合并 PR**

Run:

```bash
gh pr checks --repo flicy/cola-pages --watch
gh pr merge --repo flicy/cola-pages --squash --delete-branch
```

Expected: all configured checks pass before merge. If the repository has no required checks, inspect the PR diff and base branch once more before merging.

- [ ] **Step 4：等待 Pages 发布并严格验证公网内容**

Run:

```bash
gh api repos/flicy/cola-pages/pages/builds/latest --jq '{status,error:.error.message,commit}'
curl --fail --silent --show-error --location \
  https://flicy.github.io/cola-pages/fitcrew/ > /tmp/fitcrew-v2-public.html
rg -q 'v2 · 已上线' /tmp/fitcrew-v2-public.html
rg -q 'Apple Watch + 鱼跃血糖数据' /tmp/fitcrew-v2-public.html
rg -q '群聊里的通用健康问答' /tmp/fitcrew-v2-public.html
rg -q 'releases/tag/v2.0.0' /tmp/fitcrew-v2-public.html
```

Expected: Pages build status is `built`, HTTPS succeeds without certificate bypass, and every public-content assertion exits 0.

---

## English execution summary

1. Create a clean feature branch from the `gh-pages` source without overwriting local user files.
2. Preserve the current green-leaf brand and single-page layout while adding a responsive “V2 is live” four-card module and Release link.
3. Correct every existing group interaction claim so groups answer general food, training, sleep, and glucose-management questions without reading personal health data.
4. Replace vague or incorrect book references with the three confirmed titles and update the roadmap from “in development” to “live.”
5. Run exact content assertions, parse the HTML, inspect desktop/mobile layouts, create a separate PR to `gh-pages`, and verify the deployed GitHub Pages page over strict HTTPS.

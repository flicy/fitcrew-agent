# FitCrew 微信设计更新 / WeChat design refresh

## 中文

**方向：暖白底、深紫主行动、清晰的选择与反馈。** 延续 v4 iOS 原型与当前发布分支的紫色方向，系统字体、稳定的实色内容层、克制的 180ms 面板动效；尊重减少动态效果偏好。适配只涉及小程序呈现，不改变后端健康、身份或授权合同。

### 真正查看的参考

| 原始来源 | 本次访问证据 | 采用的原则 |
| --- | --- | --- |
| [strangehelix · Log Weight Flow](https://dribbble.com/shots/26883287-asklepios-v3-AI-Health-Wellness-App-Log-Weight-Flow-UI) | 已打开详情并查看三屏设计图 | 输入旁显示当前选择；FitCrew 采用直接点选离散档位，无体重目标或评分移植 |
| [strangehelix · Feedback UI Pattern](https://dribbble.com/shots/26882748-asklepios-v3-AI-Health-Wellness-App-Feedback-UI-Pattern) | 已查看进度与 1–5 反馈控件原图 | 选择有明确边界、文字与选中状态；不使用奖励、连续打卡压力或健康评分 |
| [Halo Lab · Instagram](https://www.instagram.com/halolabteam/)；[尝试打开的帖子](https://www.instagram.com/halolabteam/p/DcdzWucDWYF/) | 主页部分缩略图可见；单篇提示注册或登录，**未读到单篇内容** | 不把搜索摘要或缩略图当成完整案例；未绕过登录限制 |
| [Halo Lab · Routine Hero](https://www.halo-lab.com/project/routine-hero) | 已读作者案例与[公开登录界面图](https://www.halo-lab.com/images/projects/69ba614d7b851242aff33b87_routine-proj-img-02.avif) | 清楚的入口与一个主要动作；作者关于情绪舒适的描述是自述，未验证留存或健康效果 |

公开浏览日期：2026-09-08。图像仅用于观察，未复制进小程序。还实际读取了产品[评审页](https://flicy.github.io/cola-pages/fitcrew/v4/review/)、[iOS 原型](https://flicy.github.io/cola-pages/fitcrew/v4/ios/)和 [Dashboard](https://flicy.github.io/cola-pages/fitcrew/v4/dashboard/)；其中模拟数据和未来能力没有进入正式源码。

### 实际改动

- 今日：来源、窗口与限制保持可见；唯一主行动放在最近记录之前；完成/调轻/跳过、六步恢复引导、下一次检查及真实进行中实验均保留。调轻面板可滚动，有取消与就近失败反馈。
- 旅程：方向与日历阶段先于趋势；30/60/90 天选中态明确，默认滚到最近日期，每天均可点开；空缺不连线、不填零；里程碑和撤回回执保留。
- 记录：精力五档、压力三档、身体感受直接点选；睡醒、运动、压力来源和备注保留；失败保留草稿，提交时锁定输入。选中态用文字/边框/颜色共同表达。
- 实验：假设与行动先展示，新提案完整披露默认展开；运行/历史详情可收起，暂停、停止、评估入口保留。结果反馈与确认记忆仍是不同决定，失效结果不显示反馈入口。
- 我的：账户、数据源、独立 AI 同意、确认记忆与数据管理分区；导出/删除范围、主动分享、确认影响和服务回执全部保留。
- 共享：原生五 Tab 增加原创本地图标；控件最小 44px、一般按钮 48px；读取宿主字号设置；新增明确保存反馈，并要求 DELETE 同时返回 deleted 与 receipt_id 后才宣称成功。

`lib/page.js` 的增量只涉及字号、状态反馈、面板触摸拦截和删除回执确认；幂等、重试、账号代次和既有端点继续沿用。新增内容可以复用 `.experiment-feedback`、`.list-item`、`.notice`，避免每轮功能添加不同样式。

### 验证与边界

| 已实际执行 | 结果 |
| --- | --- |
| `node --test apps/wechat-mini/tests/*.test.js` | 23 项通过：原有 18 项 + 5 项分档、输入锁定、保存反馈、字号和回执保护测试 |
| `python3 scripts/verify_wechat_compilation.py` | 本机官方 wcc 编译 7 个 WXML/WXS，wcsc 编译 6 个 WXSS 成功；这是离线模板编译 |
| 浏览器源码近似渲染 | 五页 320px、100%/130%/160% 字号共 15 组无整页横向溢出；所有测量的按钮/选择控件/文本框至少 44×44px，见 [测量数据](previews/layout-checks.json) |
| 实际点击 | 分档变化、保存失败保留精力 5、调轻取消、60/90 天趋势、空缺详情、失效结果隐藏反馈已检查 |
| 配色对比度计算 | 正文 14.23:1；辅助文字 5.37:1；主按钮 7.22:1；深紫卡说明 8.66:1；错误 7.16:1；成功 6.14:1 |

截图使用同一套**合成测试数据**，直接读取 WXML/WXSS 和页面 JS，属于浏览器近似渲染。原生 picker、ActionSheet、Modal、TabBar、键盘、屏幕阅读器及系统字号最终表现仍需微信设备验证。未完成真机、登录、正式后台联调、提审或部署；未访问受禁止的后台控制台。离线编译和浏览器检查不能代替这些验收。

[今日更新前](previews/today-before.png) · [今日更新后](previews/today-after.png) · [调轻面板](previews/today-sheet.png) · [旅程](previews/journey-after.png) · [日期详情](previews/journey-detail.png) · [记录更新前](previews/log-before.png) · [记录更新后](previews/log-after.png) · [320px / 130% 字号](previews/log-narrow-large.png) · [实验](previews/experiments-after.png) · [我的](previews/profile-after.png)

### 整合

独立分支 `codex/wechat-design-20260908`；最终功能基线 `a1ef7e9`，包含主任务本轮反馈、记忆、里程碑、导出与删除范围。设计提交可 cherry-pick 到同一基线或其后代；如主任务继续修改同一页面，应保留新功能绑定并套用当前结构，不恢复旧的整行 WXML。主发布工作树文件没有由本任务直接编辑。

预览工具位于 `tools/wechat-design-preview/`，运行说明见该目录 README；不在小程序打包根目录，合成数据与模拟写入不参与产品运行。前后对照的“更新前”固定为 `f8da3c2`，对应加入里程碑后的旧视觉版本。

## English

**Direction: warm white, a deep-purple primary action, and explicit selection/feedback.** This mini-program adaptation follows the current release branch and v4 iOS lavender direction, using system typography, solid content surfaces and a restrained 180ms sheet transition with reduced-motion support. Backend health, identity and consent contracts remain unchanged.

The two linked Dribbble detail pages and their images were actually viewed: Log Weight Flow informed adjacent input feedback; Feedback UI Pattern informed explicit discrete selection. The Halo Lab Instagram profile exposed limited thumbnails, but the linked post required sign-in and was not read. No restriction was bypassed. The same author's public Routine Hero case and launch-screen image supplied a verifiable fallback. Its emotional-comfort claims are author statements, not independently verified outcomes. No reference images were copied into the app. Product review, iOS and dashboard pages were read; mock measurements and future capabilities were not imported.

Today prioritizes the real mission while retaining evidence windows, limits, onboarding and next checks. Journey keeps direction/calendar stage before selectable 30/60/90-day evidence, opens at recent dates, preserves gaps and supports milestone withdrawal. Log replaces sliders with discrete energy/stress choices and preserves every existing optional signal, draft and retry. Experiments show proposal disclosures in full, keep lifecycle actions available and separate feedback from memory confirmation; invalidated results cannot be rated. Profile retains independent consent, memory withdrawal, export/deletion scopes, confirmation and receipts. Original local icons enhance the native five-tab bar.

Shared changes are limited to host text scaling, save feedback, sheet touch handling and requiring both deletion acknowledgment and receipt. Existing idempotency, retries and account-generation guards remain intact. Extension classes include `.experiment-feedback`, `.list-item` and `.notice`.

Validation: 23 Node tests passed; installed official wcc compiled seven WXML/WXS files and wcsc compiled six stylesheets. Fifteen browser layout combinations (five pages at 320px and 100%/130%/160% text) had no page-level horizontal overflow and no measured control below 44×44px. Click checks covered discrete input, failed-save retention, sheet cancellation, 60/90-day windows, missing-day detail and invalidated-feedback hiding. Calculated text contrast ratios are 14.23:1 (body), 5.37:1 (secondary), 7.22:1 (primary button), 8.66:1 (dark-card explanation), 7.16:1 (error) and 6.14:1 (success).

The linked screenshots are browser approximations generated from source with **synthetic fixtures**, not native-device evidence. Native controls, keyboard/safe-area behavior, screen readers, host font scaling, authentication and production integration still need device verification. No review submission, deployment or prohibited console access occurred.

The isolated design branch is based on `a1ef7e9`, including the concurrent feedback, memories, milestones and scoped export/deletion work. Apply the design commit on that base or a descendant; preserve newer feature bindings when resolving later conflicts. The release worktree was not directly edited. The developer-only preview harness lives outside the mini-program package and fixes the old visual baseline at `f8da3c2`. See its bilingual README to reproduce the comparison.

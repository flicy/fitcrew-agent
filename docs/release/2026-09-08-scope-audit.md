# 全范围完成审计 / Full-scope Completion Audit

## 中文

证据时间：2026-09-08。依据用户提供的在线 [评审页](https://flicy.github.io/cola-pages/fitcrew/v4/review/) S1–S10、用户确认免费与真实 Apple Health、后续明确保留 AI 和主动帮助方向，以及当前开发分支源码。结论：目标未完成；PR #12 的基础实现与通过的测试不能替代完整产品及正式提审。

| 要求 | 当前证据与状态 | 完成所需证据 |
| --- | --- | --- |
| 五 Tab 与四层时间结构 | 两端已有五页；`product.py` 有旅程/实验/每日行动。Right Now 和 Next Check 尚未形成完整策略 | 同一真实账号贯穿四层，重启后保持一致；下次评估条件由真实数据驱动 |
| 登录及安全会话 | 服务端 Apple/微信验证及过期、换号隔离测试通过；测试号配置仅在本地独立副本 | 真实平台登录、取消、过期重登、账号隔离；测试号不能作为正式账号资格证据 |
| O1–O6 可恢复引导 | 当前没有完整可中断恢复的六步引导状态机 | 每一步杀进程/重启恢复到最近未完成步骤；拒绝健康授权仍可手动记录 |
| HealthKit 分类授权和首同步 | 复用 Bridge；身份变化时拒绝旧授权/同步结果；仅模拟器验证 | 真机真实样本、部分可用/无样本/系统限制/撤回、首同步重试及游标证据 |
| Today 四态、来源、质量与 Why | 有未登录/无数据/网络错误和规则行动；未完整实现基线建设、质量说明与来源联动 | 四态场景验收，时间窗和缺口可追溯，不虚构评分 |
| 调轻行动与审计 | 当前点击直接提交 lighten；没有评审要求的替代方案 Sheet | 展示 2–3 个允许方案，取消不写入，选定后幂等保存并显示时间/回执 |
| 旅程阶段、30/60/90趋势与里程碑 | 当前只有方向和记录列表；不能等同于趋势/里程碑 | 三个窗口、断点不连线、文字摘要、相关实验、里程碑撤回/删除 |
| 实验授权、观察与评估 | 有提案、接受、暂停/恢复/停止、每周手动记录描述性对比和数据不足状态 | 授权完整展示 purpose、基线/实验窗与质量门槛；停止影响确认；真实授权健康聚合参与观察 |
| 结果反馈及确认记忆 | 尚无完整 user_feedback → confirmed memory → next experiment 链路 | 用户可拒绝/纠正结论，确认后才形成可追溯记忆，源记录删除使依赖失效 |
| 五类主观记录 | 有精力、压力、整体感受与笔记；睡眠感受、训练感受、不适停止引导不完整 | 各类结构化输入、保存时间、撤回、失败保留、幂等；不适明确提供停止入口 |
| 数据主权 | 已有单条删除、全部删除/注销和导出；范围选择、授权派生影响说明尚不足 | 范围/影响/确认/进度/回执全链路，线上备份留存与删除说明对应实际配置 |
| AI 与主动帮助 | 当前 AI 仅基于最小手动聚合选择受限动作；未实现用户最新描述的上下文记忆与主动帮助全链路 | 明确事实/偏好/推测，用户控制记忆；授权触达、静默期、失败与无权限状态可验证 |
| 微信 AI 入口 | 官方 AI 开发模式指南仍声明内测代码暂不开放正式提审；用户缺开发者侧入口，已有小微聊天入口 | 真实 AppID 获权及官方可提审状态；内测代码与正式版本隔离，不绕过灰度 |
| 微信正式发布 | 尚无正式 AppID/备案域名/资格、后端联调、官方编译与提交回执 | 真实版本号、官方构建/真机验收、隐私/类目/备案核验和正式审核回执 |
| iOS 正式发布 | 3.0.0 (1) 无签名构建通过；会员、主体适用性、签名、真机、正式提审未完成 | 真实 Team/Bundle ID、签名产物、真机 HealthKit、政策核验和 App Store 审核提交回执 |
| 不破坏已有材料 | 独立克隆与分支；旧工作区、飞书入口和 Demo 未改动 | 发布前后生产组件与数据核验；不得运行会启动历史 gateway 的旧全服务部署脚本 |

明确排除：原评审首发排除餐食照片识别、医疗诊断、模型直读原始健康数据；用户已确认免费，付费墙不需要实现。用户后续提出更丰富的吃睡动上下文与主动帮助，须细化为可审核设计，不能用旧“无提醒”决定永久排除，也不能默认为可无限微信推送。S8 微信优先/邮箱兜底及 S10 待决策建议不是全部已确认需求；跨端账号关联仍需明确并落实。

### 本轮测试准备

独立测试副本位于 `.sandbox/wechat-test/`，由 Git 排除。已验证用户提供的测试 AppID、JSON 配置及保持域名校验。后端 URL 仍为空，没有真实登录或持久化验收证据。测试号后台被浏览器安全策略明确禁止访问，不能改用其他浏览器、cookie 或接口绕过。

已通过 Homebrew 官方 cask 元数据定位腾讯官方下载：Apple Silicon 稳定版 2.02.2608070，安装包 HEAD 返回 254414826 字节（约 243 MiB）。当前根卷可用空间约 150 MiB，连安装包都无法完整容纳，尚未下载安装。应先由用户释放空间或提供可用存储，不清理用户文件或缓存来勉强继续。

### 下一步顺序

1. 补齐已确认的原评审功能：五类记录与不适停止提示、可恢复引导、Today 证据/四态及调轻选择、趋势与里程碑、反馈确认记忆。
2. 对用户新增的上下文记忆与主动帮助设计作明确确认；保留 AI 目标，独立核实个人主体资格及官方入口可用性。
3. 获得可用磁盘后安装官方开发者工具，导入隔离测试副本；以独立测试后端完成真实登录和记录验证，凭据留在本地安全配置而非聊天或 Git。
4. 完成真机、生产配置和材料后再申请用户确认具体提审版本；两端分别以正式提交回执作为最终证明。

## English

As of 2026-09-08, the full goal is incomplete. The user-supplied live review specification S1–S10, subsequent free/HealthKit/AI decisions and current source are the evidence. PR #12's foundation and passing tests do not establish complete product or submission readiness.

Implemented foundations include five native pages/tabs, private journey/experiment/mission/log APIs, encrypted identity and records, category consent, retry/revision/ownership controls, descriptive experiment comparisons, deletion and export. Missing or incomplete requirements include resumable six-step onboarding; evidence/quality-aware Today states and next-check conditions; a choice sheet before lightening a mission; 30/60/90-day trends and retractable milestones; full experiment purpose/windows/quality disclosures; health-aggregate observations; user feedback and explicitly confirmed memories; five structured subjective record types including discomfort-stop guidance; and scoped export/erasure impact flows.

The user's newer AI direction requires user-controlled context memory and proactive assistance, not only a constrained action selector. Facts, preferences and hypotheses must remain distinct; sending requires real authorized channels and quiet-hour/failure handling. Developer AI access is separate from the user's existing Xiaowei chat access. Current official beta guidance does not allow production submission of AI development-mode code. Do not bypass access controls or hide beta features in production.

Meal-photo recognition, medical diagnosis and raw-health model access were explicitly excluded from the original first release. Payment is excluded by the user's free-release decision. The review's open questions and suggested login alternatives are not all approved requirements. Cross-platform identity linking remains unresolved and must not be advertised as implemented.

The isolated `.sandbox/wechat-test/` copy contains the user-supplied test AppID, valid JSON and enabled domain validation. It is excluded from Git; its backend URL is empty. Real authentication/persistence is not verified. Browser policy blocks the sandbox console; alternate browser/cookie/API workarounds are prohibited.

Official Homebrew cask metadata points to Tencent's Apple Silicon stable DevTools 2.02.2608070 installer. Its HEAD response is 254414826 bytes, exceeding the currently available approximately 150 MiB before installation even begins. No download or installation occurred. Owner-provided storage or cleanup is needed; do not remove unrelated user files or caches.

Continue by completing confirmed specification gaps, confirming the newer proactive-context design, installing DevTools when storage permits, running isolated real-account integration, and obtaining actual Apple/WeChat membership/configuration/filing/privacy and device evidence. Preserve the existing Feishu ingress, original workspace and demos. Only each platform's formal submission receipt proves the requested final state.

## 代码进展补记 / Implementation update

2026-09-08：两端补齐可选睡醒/训练感受与压力来源，不适时提供前往停止实验的入口。Today 增加两个调轻方案的选择面板，取消不写入；确认后保存所选方案、调整时间与记录版本。小程序测试覆盖离线保留、取消零写入与同一请求重试。后端覆盖字段保存/导出/删除、方案校验与幂等。此补记更新上述两行的代码状态，不代表真机验收或提审完成。iOS 当前修改只做语法检查，尚待完整构建及设备验证。

2026-09-08: Both clients now include optional sleep/training feelings and stress source, with a discomfort link to experiment stop controls. Today offers two lighter alternatives in a choice panel; cancellation performs no write. Confirmation persists the selected alternative, adjustment timestamp and record revision. Mini-program tests cover offline preservation, zero-write cancellation and idempotent retries; backend tests cover persistence/export/deletion and alternative validation. This updates the corresponding implementation statuses above, but does not establish device acceptance or formal submission. Current iOS edits have syntax validation only; full build and device verification remain outstanding.

### 趋势与构建进展 / Trends and build progress

提交 `1cfbc9e` 的 CI 34159001171 已全部通过，包含 iOS 模拟器构建与测试、Swift 核心、后端/小程序及容器检查。之后补充任务日期/版本冲突保护，以及两端 30/60/90 天手动精力记录趋势。趋势以同日均值展示，空缺不补零、不连线；删除记录后重新计算。当前后端 368 项、小程序 17 项测试通过，新 iOS 页面仅语法检查通过，待下一次云端构建。HealthKit 趋势、里程碑及完整旅程阶段仍未完成，不将手动趋势当作整个旅程要求完成。

CI 34159001171 passed for commit `1cfbc9e`, including iOS simulator build/tests, Swift core, backend/mini-program checks and the container smoke test. Subsequent changes add mission date/revision conflict protection and 30/60/90-day manual energy trends in both clients. Daily means preserve gaps without zero filling or connecting lines; source deletion recomputes aggregates. The backend has 368 passing tests and the mini-program has 17. New iOS views passed syntax checking only and await the next cloud build. HealthKit trends, milestones and full journey stages remain incomplete.

### 实验窗口补记 / Experiment windows update

已加入开始前七天基线、开始后七天观察期及用途说明；暂停时段仍从观察记录排除。两窗各至少四个不同日期才计算按日均值差，缺失基线不推断；既有观察期内部比较与基线比较分别标明。删除基线来源记录会使结果和缓存失效。新增基线比较/撤回测试通过，仍只验证合成手动记录，不代表真实 HealthKit 聚合已接入实验。两端显示窗口与开始前用途说明，新代码仍待完整 iOS 构建验证。

Added a seven-day pre-start baseline, seven-day observation window and purpose disclosure; paused periods remain excluded. Both windows require four distinct recorded dates before comparing day-weighted means. Missing baseline data yields no between-window estimate. Within-window and baseline comparisons remain separately labeled. Deleting baseline source records invalidates results and cached responses. Synthetic manual-record tests cover comparison and withdrawal; real HealthKit aggregates are not yet integrated into experiment evaluation. Both clients disclose the windows before acceptance; current changes still await full iOS build validation.

### 条件提示与构建 / Conditions and build verification

`afeac8b` 的 CI 34159297298 三项已全部通过，包含 iOS 模拟器构建与测试。后续本地补充趋势详情、实验基线和 Today 下一次检查条件，尚需新一轮完整构建。Next Check 根据目标、提案、暂停、期限及有效记录日数显示后续动作；时间到不等于样本充足。iOS 停止实验增加确认，保留历史与记录。目标仍未完成，不能将此进展当作完整 Today 四态、真实 HealthKit 评价或正式提审的证明。

All three jobs in CI 34159297298 passed for `afeac8b`, including iOS simulator build/tests. Later local changes add trend details, experiment baselines and conditional Next Check guidance and need a new full build. Guidance distinguishes missing goals, proposals, pauses, elapsed windows and valid recorded days; elapsed time does not establish sufficient evidence. iOS now confirms stopping while retaining history and records. The full goal remains incomplete, including full Today states, real HealthKit evaluation and formal submission.

### 安装与汇总修正 / Installation and aggregate correction

微信开发者工具 2.02.2608070 已安装至 `/Applications/wechatwebdevtools.app`，官方安装包 SHA-256 已核对；CLI 已启动，但 `islogin` 返回 false，测试项目导入返回 code 10，需要用户扫码登录。二维码是临时登录凭据，仅在 Git 排除的本地 sandbox 中。用户尚未完成登录，不能声称已编译或真机预览。CI 34159571316 对 `a269eb8` 已全部通过。

健康日汇总算法更新为 `features.v2`：无样本的睡眠、活动指标返回 null，有明确零值样本才返回 0。后台全量 373 项测试通过。仅改变新计算或重新物化的汇总，旧 `features.v1` 缓存尚未批量重算；正式接入时须处理旧缓存并验证来源去重与授权过滤，不可把此改动当作 HealthKit 完整分析已完成。

WeChat DevTools 2.02.2608070 is installed at `/Applications/wechatwebdevtools.app`, with the official installer SHA-256 verified. The CLI started, but `islogin` returned false and project import returned code 10 requiring user QR login. Temporary QR credentials stay in the Git-excluded local sandbox. No official mini-program compile or device preview is verified. CI 34159571316 passed for `a269eb8`.

Daily health aggregation now uses `features.v2`: absent sleep/activity samples yield null, while an explicitly measured zero remains zero. All 373 backend tests pass. This affects newly computed/rematerialized aggregates; old `features.v1` caches have not been batch-recomputed. Production integration must address legacy caches, source deduplication and consent filtering. Full HealthKit analysis remains incomplete.

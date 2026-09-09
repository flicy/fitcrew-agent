# 全范围完成审计 / Full-scope Completion Audit

## 2026-09-09 最新补记 / Latest update

加密备份与恢复已在真实 PostgreSQL CI 容器中验证通过（运行 34295290029）。API 独立镜像配置和非 API 服务保持不变的检查也已通过（运行 34298675448 的后端任务，iOS 仍在运行）；未部署生产。服务器 SSH 拒绝现有凭据，开发者工具仍等待持有人扫码登录。

小程序已修复请求乱序导致旧数据覆盖新状态的问题；Today 增加可展开的近七天健康样本情况，区分未选择上传、缺少样本、部分样本、冲突/异常。32 项 Node 测试及官方离线编译通过；新 UI 的视觉和真机验收仍未完成。预览服务器已恢复，当前浏览器错误页的导航被策略拦截。正式配置检查会拒绝已知测试号、IP 地址及保留测试域名。正式 AppID、业务域名、真实登录、部署和提审回执仍缺失。

Encrypted backup and restore passed against real PostgreSQL in CI run 34295290029. Independent API image configuration and unchanged non-API service checks passed in run 34298675448's backend job; iOS is still running. Production was not deployed. SSH rejects the existing credentials; DevTools awaits the account holder's login scan.

The Mini Program now rejects out-of-order refresh results that could overwrite newer state. Today adds collapsible seven-day health-sample coverage, separating unselected uploads, missing samples, partial samples, and conflicts/invalid data. All 32 Node tests and official offline compilation pass; new UI visual and device acceptance remain unverified. The preview server is restored, but navigation from its browser error page is policy-blocked. Formal configuration validation rejects the known sandbox AppID, IP addresses, and reserved test domains. Production AppID, business domain, real login, deployment, and submission receipts remain outstanding.

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

### 旧汇总读取兼容 / Legacy aggregate read compatibility

私人上下文读取旧缓存时，现按 sample_counts 将没有样本依据的睡眠、活动与恢复值置为 null，保留有明确样本的零值。此修正不写回历史密文、不冒充重算，保留原 algorithm_version 并标记 read_policy_version。已通过加密数据库读取测试与缺失/零值单测。CI 34159896202 已验证 `4478a9b` 的 iOS 删除/刷新修复，三项均通过；本次汇总修正另待新一轮 CI。

Private-context reads now mask unsupported legacy sleep, activity and recovery values using sample_counts while preserving measured zeros. The compatibility path does not rewrite encrypted history or claim recomputation; it preserves algorithm_version and marks read_policy_version. Encrypted database read tests and missing-versus-zero tests pass. CI 34159896202 passed all three jobs for the iOS deletion/refresh fixes at `4478a9b`; aggregate changes await a separate CI run.

### 六步引导进展 / Six-step onboarding progress

两端加入 O1–O6 引导，账号内加密保存步骤、阅读确认版本和数据路径，写入使用原有幂等机制。服务端拒绝跳步、未设方向、未记录 Body Check 的完成请求。健康路径第五步要求有效用途授权及已确认同步；用户可明确切到手动路径，不伪造健康授权或样本。删除全部数据重置引导。后端流程测试通过；真机杀进程恢复、部分授权及首次同步 UI 验收仍待执行，不能仅凭持久化代码声称完成整条 onboarding 验收。

Both clients now expose O1–O6 onboarding. Encrypted account records retain the current step, disclosure versions and selected data route, using existing idempotent mutations. The server rejects skipped steps and completion without a direction or Body Check. The health route requires active purpose consent and a confirmed sync at step five; users can explicitly choose manual records without fabricated health authorization or samples. Full erasure resets onboarding. Backend flow tests pass; real-device process-restart recovery, partial consent and initial-sync UI acceptance remain outstanding.

### Today 来源与缺口 / Today provenance and gaps

Today 增加近七天手动记录来源、窗口、有效记录天数和缺口。restricted 表示当前无健康上传授权，仍可手动记录；baseline_building/ready 仅对应已说明的手动记录比较门槛，不代表健康评分、完整 HealthKit 覆盖或因果结论。服务器样本计数仅覆盖当前有效授权类别，撤回后隐藏同步时间。测试覆盖授权撤回与过期手动数据不计入窗口。完整设备侧权限分支和 HealthKit 指标质量仍待验收。

Today now shows the seven-day manual-record source, window, observed days and gaps. Restricted means no current health upload consent while manual records remain available. Baseline-building/ready refer only to the disclosed manual-record comparison threshold, not a health score, complete HealthKit coverage or causality. Server sample counts include only currently consented categories and hide sync timestamps after withdrawal. Tests cover consent withdrawal and stale records outside the window. Device permission branches and HealthKit metric-quality acceptance remain outstanding.

### 反馈、记忆与旅程时间 / Feedback, memory and journey time

`9949f50` 的 CI 34161190320 已全部通过。`68ea503` 加入实验主观反馈、独立确认记忆及撤回入口；379 项后端、18 项小程序测试通过，新完整 CI 34161612971 尚待结果。删除来源记录会使相关结果和确认记忆失效，旧幂等请求不能恢复删除内容。确认记忆尚未自动送入 AI，不能当作完整上下文能力。

旅程页补充方向之后、趋势之前的日历阶段：1–30、31–60、61–90 天及窗口结束状态。仅统计该旅程窗口内的手动记录日期，同日多条不重复计天，删除后重新计算；不表示改善、行动完成或实验有效。里程碑、HealthKit 趋势及真机验收仍未完成。

CI 34161190320 passed for `9949f50`. Commit `68ea503` adds subjective experiment feedback, separately confirmed memories and withdrawal, with 379 backend and 18 mini-program tests passing; full CI 34161612971 remains pending. Source erasure invalidates dependent results and memories, and old idempotent requests cannot restore deleted content. Confirmed memories are not automatically supplied to AI and do not establish full contextual assistance.

The journey now presents calendar stages after its direction and before trends: days 1–30, 31–60, 61–90 and an ended-window state. It counts distinct manually recorded dates within that journey window, recalculates after deletion, and makes no claim of improvement, completed actions or experimental validity. Milestones, HealthKit trends and real-device acceptance remain incomplete.

### 撤回来源修复 / Source withdrawal correction

删除暂停期内未参与评估的记录，不再错误作废实验结果和确认记忆；删除真正参与基线或观察的记录仍会作废。两端失效结果关闭反馈与确认记忆入口。相关后端回归通过。本地 Swift 完整测试因磁盘写满中断，已清理本任务构建缓存及已安装的下载包，后续使用云端完整构建，不将此次中断当作测试通过。

Deleting excluded pause-period records no longer invalidates unrelated experiment results or confirmed memories. Removing actual baseline or observation sources still invalidates them. Both clients hide feedback and memory confirmation for invalidated results. Targeted backend regression tests pass. Local Swift testing stopped because the disk filled; task build caches and the already-installed download were removed. Full verification continues in cloud CI; the interrupted run is not a pass.

### 里程碑实现 / Milestone implementation

CI 34161612971 已验证 `68ea503`，全部通过，含 iOS 模拟器构建测试。新里程碑由已评估实验派生，显示观察窗口日期、行动和证据；不足数据仍如实显示，不命名为改善。撤回保留状态但移除该卡的行动与证据展示，原实验与记录保留；来源删除自动失效。后端测试覆盖来源删除、重复撤回回执、跨账号拒绝及全部删除。两端新页面仍待新完整构建及真机验证。

CI 34161612971 passed for `68ea503`, including iOS simulator build/tests. New milestones derive from evaluated experiments and show observation dates, actions and evidence without claiming improvement when evidence is insufficient. Explicit withdrawal retains a status marker but removes the card's action/evidence; original experiments and records remain. Source deletion invalidates derived milestones. Backend tests cover source erasure, repeat withdrawal receipts, cross-account rejection and full deletion. New client changes still need full build and real-device validation.

### 导出范围 / Export scopes

两端新增全部、手动记录与实验、Apple 健康数据三种导出范围。服务器验证范围并附生成时间、范围和审计回执；只证明生成，不证明保存或分享。手动范围不含健康样本与健康状态元数据；健康范围不含手动记录。重新生成前清理旧文件，避免失败后分享上次不同范围的文件。383 项后端测试与18项小程序测试通过，Swift 新请求使用独立查询参数，页面语法通过，尚待完整构建。删除范围选择仍待实现。

Both clients now offer all, manual/product and Apple Health export scopes. Server validation and metadata record scope, generation time and an audit receipt, proving generation only. Product-only export excludes health samples and health-status metadata; health-only excludes manual records. Old exports are removed before regeneration to prevent sharing a previous scope after failure. The backend has 383 passing tests and the mini-program 18. Swift uses separate URL query items and passed syntax parsing; full build validation remains pending. Scoped deletion is still incomplete.

### 删除范围 / Deletion scopes

新增全部私有数据与仅全部手动身体记录两种删除范围。后者使用同一事务删除记录、作废依赖结果/确认记忆/里程碑并生成回执，保留健康授权、同步位置、账号及实验历史。两端在确认前说明影响，删除成功后清除页面草稿与导出，重新读取状态。385 项后端、18 项小程序测试通过，新 iOS 代码仅语法检查；完整构建及设备验证仍待完成。此范围不提供按日期或单独健康类别批量删除，不将其描述为任意范围删除。

Deletion now supports all private data or all manual body records. The latter removes records and invalidates dependent results/memories/milestones in one transaction, issues a receipt, and preserves health consent, sync cursors, identity and experiment history. Both clients explain impact before confirmation, clear drafts/exports after success and refresh state. Backend tests: 385 passing; mini-program tests: 18 passing. New iOS changes have syntax validation only and await full build/device checks. Date-range and individual health-category bulk deletion are not offered.

### 官方离线编译 / Official offline compilation

主发布分支用已安装微信开发者工具的 wcc 复现了表达式转义错误（unexpected `;`），已仅修复 Today、Experiments、Profile 的绑定表达式。运行 `python3 scripts/verify_wechat_compilation.py` 已成功编译 6 个 WXML 模板与 3 个 WXSS 样式文件，输出在临时目录验证后清除；18 项 Node 测试通过。脚本找不到官方编译器时会失败，不假装通过。此证据不包含真实登录、设备渲染、后台联调或正式提审。

The release branch reproduced an official wcc expression-escaping failure (unexpected `;`) and corrected bindings in Today, Experiments and Profile only. `python3 scripts/verify_wechat_compilation.py` successfully compiled six WXML templates and three WXSS files, verified nonempty output and removed temporary artifacts. All 18 Node tests passed. The script fails if official compilers are unavailable. This does not prove authentication, device rendering, backend integration or formal review submission.

### iOS 本机导出清理 / iOS local export cleanup

iOS 不再静默忽略旧导出删除失败：关闭分享入口、阻止新生成，并保留独立错误及重试入口。服务器删除成功与本机清理失败分别展示。新增注入失败的测试覆盖不发起生成、跨账号清理失败提示、重试成功及 health 查询参数。当前只通过 Swift 语法检查，测试尚未执行；本机空间不足时不反复启动完整构建，等待云端网络恢复验证。

iOS now surfaces old-export cleanup failures, disables sharing, blocks regeneration and provides a persistent retry action. Server erasure and local cleanup failures remain distinct. Added failure-injection tests cover blocked generation, identity changes, successful retry and the health query parameter. These changes have syntax validation only; the new tests have not run. Full builds await cloud connectivity instead of repeatedly exhausting local disk.

### 睡眠重复时长 / Overlapping sleep duration

日汇总升级 `features.v3`：总睡眠按时间区间并集合并，重复来源、通用睡眠与分期重叠不再重复计时；各分期也在自身类别内合并。真实区间缺口保留，反向区间返回未知并记录质量计数。原测试中 1 小时深睡与同起点 1.5 小时 REM 实际覆盖 1.5 小时，已纠正原先相加为 2.5 小时的错误预期；新增重复来源/缺口测试。386 项后端测试通过。旧缓存尚未重算；分期冲突、跨午夜归属及活动多来源去重仍需处理，不能据此宣称完整健康趋势或真机准确性。

Daily aggregation now uses `features.v3`: total sleep is the union of sleep intervals, preventing duplicate sources and generic/staged overlap from double counting. Each stage is also merged within its category. Real gaps remain; reversed intervals produce unknown values and a quality count. The earlier fixture's one-hour deep sleep and same-start 1.5-hour REM cover 1.5 hours, not the previously asserted 2.5. Added duplicate-source/gap regression coverage; all 386 backend tests pass. Legacy caches are not recomputed. Stage conflicts, cross-midnight attribution and activity-source deduplication remain outstanding; this is not full health-trend or device-accuracy proof.

### 跨日睡眠与时区 / Sleep calendar boundaries and timezones

睡眠日汇总按批次声明的时区切分实际时间区间：22 点至次日 7 点分别计入 2 小时和 7 小时，恰好午夜结束不会在下一天生成零值睡眠；夏令时按真实经过秒数计算。样本入库前规范为 UTC，样本缺失时区被拒绝，避免 SQLite 丢失偏移后错误解释。新汇总记录 day_timezone 和 sleep_day_policy。390 项后端测试通过。这里是日历日分配，不是“按醒来日归属整夜”；旧缓存未重算，健康趋势仍未接入产品页。健康授权撤回现有逻辑清除汇总，不等同于已完成所有健康样本删除/重算路径验证。

Sleep aggregation clips actual intervals to calendar days in the batch's declared timezone: 22:00–07:00 contributes two and seven hours, an exact-midnight end creates no next-day zero, and DST uses elapsed seconds. Samples normalize to UTC before storage and timezone-free samples are rejected, avoiding SQLite offset loss. New aggregates include day_timezone and sleep_day_policy. All 390 backend tests pass. This is calendar-day allocation, not whole-night attribution to waking date. Old caches remain unrecomputed, and health trends are not yet integrated into product pages. Existing consent withdrawal clears aggregates, which does not establish every sample-erasure/recomputation path.

### 设计整合 / Design integration

独立设计提交 `c13ca4c` 已作为 `77d42ed` 合入发布分支。主分支复验官方 wcc（7 WXML/WXS）、wcsc（6 WXSS）及23项Node测试通过，测试号副本已同步，保留原 AppID 与后端配置。前后对照服务 http://127.0.0.1:8768/ 返回200，已请求在应用内打开。预览与截图使用合成数据和浏览器近似渲染，不是原生真机验收。设计参考与窄屏测量见 `docs/design/2026-09-08-wechat-refresh.md`。后端390项测试在此次纯小程序设计合入前通过；无后端冲突。远端推送仍未成功，完整最新 iOS 云端验证仍待进行。

Independent design commit `c13ca4c` was integrated as `77d42ed`. The release branch passed official wcc compilation of seven WXML/WXS sources, wcsc compilation of six WXSS files and all 23 Node tests. The test-ID copy was synchronized while retaining its AppID/backend configuration. The comparison server at http://127.0.0.1:8768/ returned 200 and was requested in the app. Its fixtures/screenshots are synthetic browser approximations, not native device acceptance. References and narrow-layout measurements are recorded in `docs/design/2026-09-08-wechat-refresh.md`. The 390 backend tests passed before this mini-program-only integration, with no backend conflicts. Remote push and full latest iOS CI remain unverified.

### 健康趋势接口 / Health trend API

账号状态新增 health_trends，窗口90天，按账号时区读取当前获准类别的加密样本，不复用旧汇总缓存，也不发送模型。每日期包含睡眠小时、步数、HRV均值及样本数、来源、状态。睡眠合并实际区间；步数/HRV多来源先显示冲突，步数同来源重叠也不相加；无样本不填零，明确测量零保留。所有有值记录仍标 partial，不代表全天覆盖。手动范围导出明确排除此字段。391项后端测试通过；两端 UI 尚未接入此字段，健康趋势体验仍未完成。

Account state now includes a 90-day health_trends field, computed in the account timezone from currently authorized encrypted sample categories, without legacy cached aggregates or model calls. Each date carries sleep hours, steps, mean HRV, sample count, sources and status. Sleep uses interval union; multi-source steps/HRV and overlapping step intervals are reported as conflicts rather than summed. Missing values remain null and measured zero is preserved. Values remain partial, never proof of full-day coverage. Product-only export explicitly excludes this field. All 391 backend tests pass; client UI integration is pending, so the health-trend experience is not complete.

### 两端健康趋势显示 / Health trend clients

两端旅程页接入 sleep/steps/hrv 指标与30/60/90日窗口，区分缺失和明确零值，点按显示样本数、来源及状态。柱高按窗口最大值缩放，附单位和非评分说明。详情在刷新失败或账号边界后清除；来源冲突即使误带数值也不展示。小程序官方编译及24项Node测试通过；iOS模型、页面与新增指标状态测试仅语法检查，完整构建和真实设备尚未验证。已有设计预览服务仍指向独立设计工作树，不包含此次健康趋势新卡片，不能拿旧预览证明新卡片渲染。

Both Journey clients now display sleep, steps and HRV over 30/60/90 days, preserve missing-versus-zero distinctions, and open source/count/status details. Bars scale to the current window maximum with units and a non-score notice. Details clear on failed refresh or account changes; conflicted values remain hidden even if a numeric payload is present. Official mini-program compilation and all 24 Node tests pass. New iOS models, UI and metric-state tests have syntax validation only, pending full build and device tests. The existing preview server still uses the separate design worktree and does not prove rendering of this new health card.

### 16:08 验证恢复 / Verification resumed at 16:08

GitHub连接恢复，`13061a6` 已推送，最新CI 34202880672正在运行。旧CI 34161964649（f8da3c2）已核实全部通过。最新Swift Core实际编译和测试通过，双语文档检查通过。`devicectl list devices` 显示用户iPhone 16 Pro为 unavailable，不能安装或执行真机健康验证；微信DevTools实测login=false。不能将配对历史或Apple Watch可见性当作iPhone可用、微信登录或提审证据。

GitHub connectivity recovered and `13061a6` was pushed. CI 34202880672 is running. Earlier CI 34161964649 for f8da3c2 was verified successful. Current Swift Core compiled and passed its tests; bilingual documentation validation passed. `devicectl list devices` reports the owner's iPhone 16 Pro unavailable, preventing installation and real-device health validation. WeChat DevTools reports login=false. Pairing history or Apple Watch visibility establishes neither iPhone availability nor WeChat login or submission.

### 最新完整 CI / Latest full CI

已通过 GitHub 查询核实提交 `13061a61fbca3084986051f0a821721c10197bac` 的 [CI 34202880672](https://github.com/flicy/fitcrew-agent/actions/runs/34202880672) 全部成功：Python 测试与策略检查、小程序边界测试、Compose 冒烟、Swift Core、iOS 模拟器项目生成及测试。此结果更新上文有关最新 iOS 构建尚未验证的历史状态；不证明签名归档、真实 HealthKit 数据链路或平台提审。主发布工作树另有端口 8769 的合成健康趋势预览，可选择零值、缺口和来源冲突场景；HTTP 返回 200，仅证明服务可访问，完整视觉验收仍待进行。

GitHub confirms all jobs succeeded for commit `13061a61fbca3084986051f0a821721c10197bac` in [CI 34202880672](https://github.com/flicy/fitcrew-agent/actions/runs/34202880672): Python tests/policy, mini-program boundaries, Compose smoke tests, Swift Core, and iOS simulator project generation and testing. This supersedes earlier pending-build entries, but does not prove a signed archive, real HealthKit ingestion or platform submission. The release worktree also serves synthetic health-trend previews on port 8769 with measured zeros, gaps and source conflicts. HTTP 200 proves accessibility only; full visual acceptance remains pending.

进一步读取同一运行日志：iOS 应用层 Swift Testing 的 12 项测试通过，包括 `failedExportCleanupBlocksGenerationUntilRetry`；Swift Core 的 XCTest 6 项及 Swift Testing 11 项通过。日志中 XCTest 的“0 tests”不代表应用测试未执行，后续 Swift Testing 有明确执行结果。CI 使用 `CODE_SIGNING_ALLOWED=NO`，因此不提供签名能力证据。

Reading the same run's logs confirms 12 application Swift Testing tests passed, including `failedExportCleanupBlocksGenerationUntilRetry`; Core passed six XCTest and 11 Swift Testing tests. The application's XCTest “0 tests” line is followed by explicit Swift Testing execution results. CI sets `CODE_SIGNING_ALLOWED=NO`, so this provides no signing evidence.

### 健康详情窄屏检查 / Narrow health detail inspection

通过 CUA 操作发布工作树的 8769 预览，设置旅程、合成健康场景、320px 宽度及 160% 字号。选择步数后点按 2026-08-31，详情显示“0 步”、部分样本、2 条样本及合成来源；关闭后点按 2026-09-03，显示来源冲突且无数值。截图中关闭按钮可见、来源可换行、说明可读；冲突详情日期换成两行。这仅证明两个合成场景的浏览器交互和可读性，不覆盖微信原生弹层、真实数据、全部窗口或 iOS 界面。

CUA inspected the release worktree preview on port 8769 with Journey, synthetic health data, 320px width and 160% text. Selecting steps and 2026-08-31 showed measured zero, partial status, two samples and a synthetic source. Closing it and selecting 2026-09-03 showed source conflict without a value. Screenshots showed an accessible close button, wrapping provenance and readable notices; the conflict date wrapped to two lines. This proves only those two synthetic browser interactions and readability, not native WeChat sheets, real data, all windows or iOS UI.

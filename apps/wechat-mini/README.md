# FitCrew 微信原生小程序 / Native WeChat Mini Program

## 中文

五个原生页面：今日、旅程、实验、记录、我的。沿用 V2 私有 API、内部身份与 consent；无模拟健康数据、支付或订阅提醒。紫色与薰衣草色沿用已确认的 iOS Demo 方向。

将已核实的 AppID 写入 project.config.json，将已备案并配置微信 request 合法域名的 HTTPS API 写入 config.js。两者默认留空，缺失时登录被阻止，发布校验失败。AppSecret 仅配置在后端；客户端只在小程序私有存储保存设备 token，不记录 code、openid 或凭据到日志。登录返回不同服务地址时拒绝，防止凭据被重定向。

运行 `node --test apps/wechat-mini/tests/*.test.js`；发布前运行 `node apps/wechat-mini/scripts/validate-release.js`。请在微信开发者工具导入本目录，保持域名校验开启，验证真实登录、隐私指引、五页闭环、断网重试、冲突提示、独立 AI 授权、导出与删除回执。Node 测试只验证客户端边界，不能替代微信编译与真机测试。

默认没有演示记录。首次登录后选择旅程，获取提案，阅读完整指标、停止条件与数据使用后确认实验，再记录感受。网络失败保留草稿及同一 request_id，修改内容生成新请求 ID。409 可重新读取状态再操作。评估只显示后端真实结果，窗口未完成由服务拒绝。

AI 能力按服务端状态展示，服务商、披露版本及单独同意均可见，可撤回。规则与 AI 选择分别标注。个人主体生成式 AI 类目资格尚未核实；不得隐藏功能规避审核。AppID、类目、备案、隐私平台配置、正式 HTTPS 后端和真实登录均为发布前门槛。

小程序不能读取 HealthKit，只显示同一账户经 iOS 同步的条数与时间。微信身份默认不自动合并现有 iOS/飞书身份，账户关联需要受验证的后端配对流程。导出仅在主动确认后写入微信私有文件沙箱；用户可主动选接收位置或清除文件。删除/注销展示服务回执，只有服务器确认注销后清除 token。

## English

会话边界会同步清空所有缓存页面的私有状态与草稿；401 或本机 30 天有效期到期恢复登录入口。每次请求及弹窗后均检查会话代次，旧账户响应不能回填新账户。导出文件在启动、登录、数据删除及注销时清理；「清除本机导出」始终可用。清理失败不会宣称成功，登录会停止以避免跨账户遗留。

Session boundaries reset private state and drafts in all cached tabs. A 401 or local 30-day expiry restores login. Request and modal continuations check a session generation so old-account responses cannot populate a new account. Exports are cleaned on launch, login, data deletion and account deletion; the cleanup button remains available after restart. Cleanup failures are explicit and prevent account installation.

Five native tabs implement Today, Journey, Experiments, Log and Profile on the existing private V2 identity/consent API. No mock health records, payments or subscription reminders. Lavender styling follows the approved iOS demo.

Set the verified AppID in project.config.json and the registered production HTTPS API in config.js. Both are empty by default and block login/release validation. Keep AppSecret on the server. Only the device token is persisted in app-private storage; never log login codes or credentials. A different server-selected base URL is rejected to prevent bearer redirection.

Run `node --test apps/wechat-mini/tests/*.test.js` and `node apps/wechat-mini/scripts/validate-release.js`. Import this directory into official WeChat Developer Tools with domain validation enabled. Verify real login/privacy consent, all five pages, offline retries, conflicts, separate AI consent, export and deletion receipts on device. Node tests are not native compilation or real login evidence.

Empty accounts stay empty. Start a journey, request an experiment and accept its full disclosure before participation. Network failures retain drafts and request IDs; changed input starts a new intent. Refresh after revision conflicts. Results only display actual server evaluation.

AI provider disclosure and independent revocable consent remain visible. Rule proposals and AI-selected actions have distinct labels. Personal-subject generative AI category eligibility remains unresolved; never hide functionality to bypass review. AppID, category, filing, privacy configuration, production API and real login are release gates.

WeChat cannot read HealthKit. It displays only health sync count/time from the same account. WeChat identities do not automatically merge with iOS/Feishu accounts; validated server-side pairing is required. Explicit export writes only to the app sandbox, with optional user-initiated file sharing and cleanup. Deletion shows the server receipt; account tokens clear only after confirmed server deletion.

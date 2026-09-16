# 当前小程序源码验收 / Current Mini Program source acceptance

## 中文

本次把本机 8768 预览从旧设计工作树切换到当前发布源码。页面顶部显示提交号，前后对照仍保留旧视觉基线 f8da3c2。新增设备连接、独立 AI 同意、健康实验观察的合成场景；同一场景的记录、反馈、记忆及授权在切换页面后保留，刷新整页重置。WXS 格式化代码直接从产品读取，避免维护副本遗漏修复。

实际检查了生成连接前说明、取消不生成、生成后有效期、撤销未使用连接、AI 单独同意，以及实验反馈经第二次确认后在“我的”显示记忆。切页后 AI 同意保留，连接链接隐藏。模拟复制不写系统剪贴板，合成连接不能兑换真实账号；所有模拟操作不访问生产 API。未支持的模拟接口明确报错。

在产品基线 1386968 上，五页 × 320px × 100%/130%/160% 字号的 15 组测量无整页横向溢出，所测控件均至少 44×44px。页面名、实际字号和控件数量见 [测量数据](previews-20260910/layout-checks.json)。查看并保存了 [健康观察大字号截图](previews-20260910/health-observation-large.png) 和 [连接确认截图](previews-20260910/pairing-confirmation.png)。这些是浏览器近似渲染，截图捕获于时间格式修复之前。

检查发现一次性连接的 ISO 有效期被截断后丢失时区。主发布任务已在 c79dd9d 保留 UTC/UTC±HH:MM 或标明时区未知；当前预览也读取这一修复。实际生成的合成连接显示 UTC；修复后的 Profile 在 320px、160% 字号下重新测量通过，见 [时区排版复核](previews-20260910/timezone-layout.json)。本次最后复验：小程序 42 项 Node 测试全部通过，官方 wcc 编译 7 个 WXML/WXS、wcsc 编译 6 个 WXSS 通过。

本机预览由 launchd 会话作业 com.fitcrew.source-preview.8768 启动，仅监听 127.0.0.1；没有安装登录自启动文件。启动/停止说明见 [预览 README](../../tools/wechat-design-preview/README.md)。这是合成源码验收，不代表原生弹窗、系统剪贴板、真实 AI、HealthKit 或生产数据验收。

外部条件仍未完成：本轮官方微信 CLI 实测 login=false；尝试刷新二维码因 TLS 连接建立前断开失败（code 10），没有生成新码。旧二维码修改时间为 2026-09-10 02:11+08:00，未当作有效码展示。正式配置校验仍缺生产 AppID 和 HTTPS 域名。主发布任务另完成 iOS 地址构建配置与无签名设备架构构建，但实际签名缺 Apple 账号/描述文件，现有服务器 SSH 凭据仍被拒绝。未部署、上传或正式提审。

## English

Port 8768 now serves the current release worktree rather than the older design checkout. The banner identifies the source revision; the old visual baseline remains f8da3c2. Synthetic scenarios cover device connection, independent AI consent and health experiment observations. Scenario state survives page changes and resets on full reload. Formatting loads the product WXS directly rather than maintaining a stale copy.

Actual browser checks covered the connection disclosure, cancellation without generation, generated expiry, unused-link revocation, separate AI consent and confirmed feedback appearing as memory in Profile. Consent survives navigation while the connection link is hidden. Simulated copy does not modify the system clipboard; synthetic links cannot access real accounts. No simulation calls production APIs, and unsupported endpoints fail explicitly.

On product baseline 1386968, all 15 combinations of five pages at 320px and 100%/130%/160% text had no page-level overflow or measured control below 44×44px. The linked JSON records page identity, actual scale and control counts. The linked health-observation and connection-confirmation screenshots were inspected and captured before the timezone fix; they are browser approximations.

Inspection found that truncating ISO connection expiries removed their timezone. Release commit c79dd9d preserves UTC/UTC offsets or explicitly labels missing zones. The preview consumes that exact formatter. A generated synthetic connection displayed UTC, and Profile passed another 320px/160% layout check after the fix. Final verification passed all 42 Mini Program Node tests, seven official wcc WXML/WXS compilations and six wcsc stylesheets.

A session launchd job named com.fitcrew.source-preview.8768 now runs the local-only preview. No login-startup file was installed. See the preview README for operation. Synthetic source acceptance does not establish native controls, clipboard behavior, real model calls, HealthKit or production data acceptance.

External gates remain: official WeChat CLI reports login=false. Refreshing its QR code failed before TLS establishment (code 10), producing no new code; the older code dated 2026-09-10 02:11+08:00 was not presented as current. Production AppID and HTTPS domain checks still fail. The release task separately completed iOS endpoint build configuration and an unsigned device-architecture build, but signing lacks an Apple account/profile and the existing server rejects SSH credentials. No deployment, upload or formal submission occurred.

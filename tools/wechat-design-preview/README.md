# 小程序源码设计预览 / Mini-program source design preview

## 中文

在仓库根目录运行 `python3 tools/wechat-design-preview/serve.py`，打开 [本地对照页](http://127.0.0.1:8768)。仅绑定 127.0.0.1，无额外依赖、无远程请求。`Ctrl-C` 停止。默认比较固定 Git 基线 `f8da3c2` 和当前源码；可切换五页、空态、失败态、引导、屏幕宽度和字号。状态只在当前浏览器内存中模拟，不连接真实 API。

工具读取 WXML/WXSS，转换常见标签和控制流，并运行原有页面 JavaScript；不能替代微信运行时。原生选择器、弹窗、导航和生命周期在这里仅近似展示。所有数据均为明确标注的合成测试数据，本目录不在小程序包内。

截图使用 `?capture=1&page=today&width=402` 等查询参数；加 `version=before` 显示旧版。浏览器视口使用同一宽度和 874px 高度。对应证据在 `docs/design/previews/`，不含 AppID、凭据、二维码或真实健康数据。

运行 `python3 scripts/verify_wechat_compilation.py` 进行本机官方离线编译；运行 `node --test apps/wechat-mini/tests/*.test.js` 验证客户端逻辑。图标可通过 `python3 tools/wechat-design-preview/make-icons.py` 重建（需要 Pillow，运行小程序不需要此依赖）。

## English

From the repository root, run `python3 tools/wechat-design-preview/serve.py` and open the local comparison URL above. The server binds only to 127.0.0.1, needs no extra dependencies and makes no remote requests. Stop with Ctrl-C. It compares fixed Git baseline `f8da3c2` with working source; controls select the page, synthetic state, onboarding step, width and text scale. Simulated mutations stay in browser memory and never reach the real API.

The harness reads WXML/WXSS, translates common tags/control flow and runs the original page JavaScript. Native pickers, dialogs, navigation and lifecycle are approximations. It is not a WeChat runtime or production replacement. All fixtures are explicitly synthetic and this directory is outside the mini-program package.

Use `?capture=1&page=today&width=402`, optionally with `version=before`, for screenshot capture at a matching viewport width and 874px height. Evidence is under `docs/design/previews/`; it contains no real health records, credentials, AppIDs or login QR codes. Run the official offline compilation script and Node tests shown above. Original icons can be regenerated with `make-icons.py` and Pillow; Pillow is not a product runtime dependency.

可用 `--port 8769` 在另一个端口查看不同工作树；“健康趋势（合成）”场景只在预览工具内生成数据，用来检查缺口、来源冲突、零值和详情，不进入小程序包。

Use `--port 8769` to preview another worktree separately. The synthetic health scenario generates preview-only gaps, source conflicts, measured zeros and details; it is excluded from the mini-program package.

## 2026-09-10 更新 / Update

预览新增「设备与 AI（合成）」状态，包含设备连接、独立 AI 同意与健康实验观察。切换页面时，同一场景的模拟记录、反馈、记忆和授权保留；刷新整个页面重置。连接链接不可兑换，复制只模拟在预览内，不写系统剪贴板；导出不生成实际健康文件。未支持的模拟接口会明确报错。预览不是后台模型或原生能力的端到端测试。

The new “Devices and AI (synthetic)” scenario covers device connections, separate AI consent and health experiment observations. Scene state survives tab changes and resets on a full reload. Pairing links cannot be redeemed; copy does not touch the system clipboard, and exports do not create real health files. Unsupported simulated endpoints fail explicitly. This is not end-to-end backend or native-runtime validation.

顶部 `/meta` 信息标明当前源码提交。格式化函数直接读取 `templates/format.wxs`，避免预览副本遗漏产品修复。服务必须在当前发布工作树启动，而不是旧设计工作树。当前 Mac 会话由 launchd 的 `com.fitcrew.source-preview.8768` 作业运行；停止方式：`launchctl remove com.fitcrew.source-preview.8768`。未安装登录自启动文件。

The `/meta` banner identifies the source commit. The formatter reads `templates/format.wxs` directly so preview copies cannot omit product fixes. Run the server from the current release worktree. The current Mac session uses the launchd job `com.fitcrew.source-preview.8768`; stop it with the command above. No login-startup file was installed.

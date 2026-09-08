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

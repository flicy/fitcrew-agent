# 微信原生运行时排错 / Native WeChat runtime diagnosis

## 中文

微信开发者工具已登录。2026-09-10 在 Stable 2.02.2608070 上检查隔离测试副本，发现两个独立问题：

1. 基础库下载不完整：FitCrew 和只有静态文字的最小探针均报模拟器启动失败。日志出现 vendor 包校验失败，本机只有部分下载文件。依据工具缓存配置，从微信官方 `https://res.servicewechat.com/weapp/public/commlib/1641.wxapkg` 下载 3.17.2 完整包，共 40,474,333 字节；验证每段 Content-Range 和长度，并使用工具自带 `checkBufferSignature` 与配置中的签名验证成功后写入基础库缓存。没有修改 TLS、代理、签名校验或登录信息。测试副本固定使用已验证的 3.17.2；重新编译后最小探针实际显示 `Runtime probe ready`。
2. Profile 模块遗漏：基础库恢复后首页显示正文，但进入“我的”报 `module 'lib/device-pairing.js' is not defined`，文件实际存在。将对象展开中的 `require` 改为显式顶层引用，再展开变量。相同官方模拟器重编译后，“我的身体，我做主”、登录说明、健康来源、导出与删除入口均显示，调试器为 0 errors。保留设备连接、确认、撤销与身份边界逻辑。

源代码修改仅涉及 Profile 的模块引入；基础库缓存、探针和测试 AppID 配置在 Git 外。修复后 42 项 Node 测试及官方 wcc 7 文件、wcsc 6 文件编译通过。旧的离线编译和 Node 测试未覆盖此次官方打包依赖问题，不能代替原生运行检查。

首轮官方 CLI 预览已返回成功，测试包 129,997 字节，但生成于 Profile 修复前，不应交付该码。修复后的官方 CLI 预览也成功，包体 135,823 字节，二维码生成于本机 `.sandbox/native-preview/preview-fixed-20260910.png`，不进入 Git。测试副本 baseURL 仍为空，页面如实显示服务未配置；没有真实登录服务、健康数据、模型调用或生产验收。官方预览包不是正式上传版本或审核回执。后续继续补正式 AppID、部署域名和服务器访问，进行真实联调后再按具体版本确认提审。

## English

WeChat Developer Tools is signed in. Two independent issues were observed in the isolated test copy using Stable 2.02.2608070:

1. Incomplete runtime downloads: both FitCrew and a static-text probe failed to start. Logs showed vendor package verification failures and only partial downloads existed. Version 3.17.2 was downloaded from the official URL above, totaling 40,474,333 bytes. Every Content-Range and segment length was checked, followed by the bundled `checkBufferSignature` against the configured signature before installing the package in the vendor cache. TLS, proxy, signature verification and login information were unchanged. The isolated copies use verified 3.17.2; the recompiled probe visibly rendered `Runtime probe ready`.
2. Missing Profile dependency: after restoring the runtime, Today rendered but Profile reported the missing device-pairing module despite its file being present. Replacing the inline object-spread require with an explicit top-level require and spreading its variable restored Profile in the same official simulator, with its account/privacy/data controls visible and zero debugger errors. Pairing and identity-boundary behavior was preserved.

Only the Profile import changed in product source. Runtime caches, probe and test AppID configuration remain outside Git. All 42 Node tests and official compilation of seven WXML/WXS and six WXSS files passed. Earlier offline checks did not cover this native packaging dependency failure and cannot replace runtime acceptance.

The first CLI preview succeeded with a 129,997-byte package, but preceded the Profile fix and its QR must not be delivered. The corrected CLI preview also succeeded, producing a 135,823-byte package and local `.sandbox/native-preview/preview-fixed-20260910.png`; the QR stays outside Git. The test copy still has an empty baseURL and truthfully displays missing service configuration. No real service login, health-data/model integration or production acceptance occurred. Preview generation is neither a formal upload nor review receipt. Production AppID/domain/server access and real acceptance remain necessary before confirmation of the concrete review version.

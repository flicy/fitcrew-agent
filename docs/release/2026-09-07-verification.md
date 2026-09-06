# 验证记录 / Verification Record

## 中文

本记录针对独立开发分支，不是正式提审回执。

| 检查 | 结果与证明范围 |
| --- | --- |
| `uv run pytest -q` | 364 通过；包含原有回归、V3 用户隔离/加密/幂等/删除、真实签名验证及模拟平台响应、SQLite 迁移 |
| `uv run ruff check apps/api scripts infra/tencent` | 通过 |
| `swift test`（iOS Core 目录） | 15 通过：4 XCTest 与 11 Swift Testing |
| iOS `xcodebuild test ... CODE_SIGNING_ALLOWED=NO` | 9 通过，包含旧账号异步响应拒绝、重登、导出清理、隐私 URL 门槛及身份快照失效；最终日志 `/tmp/fitcrew-ios-identity-test.log` 为 TEST SUCCEEDED |
| `node --test apps/wechat-mini/tests/*.test.js` | 14 通过：API、失败/重试、身份代次、401/过期、缓存页面/导出清理、保存时草稿保护 |
| `uv run python scripts/check_ios_generated_config.py` | 版本、HealthKit / Apple 登录 entitlement、叶片图标格式通过；不能证明签名或平台注册 |
| `uv run python scripts/check_bilingual_docs.py` | 通过；补齐原有 6 份缺中文文档，保留英文原文 |
| `git diff --check` | 通过 |
| 小程序发布校验 | 正确失败：缺少真实 AppID 与 HTTPS API；不得绕过此检查声称可发布 |
| 视觉 | CUA 直接观察 iOS 紫色 Today、未连接与无数据空态；完整导航自动化遇到 AX 错误，未宣称全页视觉验收 |
| 独立复核 | 后端、iOS 及微信本轮 SPEC / QUALITY 通过；该结论只覆盖本次基础实现 |

未验证：Apple/微信真实登录、真机 HealthKit 权限与样本、正式 HTTPS V3 联调、微信官方编译、签名分发、PostgreSQL 多连接竞态、真实模型供应商响应、线上备份删除策略、完整 Demo 功能等价及平台审核资格。测试使用合成数据及模拟外部响应，不能替代这些步骤。

旧服务健康检查返回 200，而 V3 路由尚未部署。没有生产更改、没有正式审核提交。后续须先解决发布门槛，再按提审材料中的验收路径留存真实证据。

## English

This record concerns the isolated development branch, not production review submission.

Backend: 364 pytest tests pass, including existing regressions, private V3 records, isolation/encryption/retries/erasure, actual JWT signature verification with mocked providers and SQLite migration. Ruff passes. Swift Core passes 15 tests (4 XCTest plus 11 Swift Testing). The final unsigned iOS simulator test run passes nine tests covering account isolation, reauthentication, exports, the privacy URL gate and identity snapshot invalidation. The final log is /tmp/fitcrew-ios-identity-test.log (TEST SUCCEEDED). WeChat passes 14 Node tests, including session epochs, expiry/401, cached page/export cleanup and save-time draft protection.

Generated iOS version/entitlement/icon checks, bilingual documentation checks and diff whitespace checks pass. The mini-program release validator intentionally fails for missing verified AppID and HTTPS API. CUA directly showed the purple iOS home and disconnected/empty states; AX failures leave complete visual navigation unverified. Independent backend, iOS and WeChat specification/quality reviews passed for this foundation scope.

Not verified: real Apple/WeChat login, physical-device HealthKit permissions and samples, production HTTPS V3 integration, official WeChat compilation, signing/distribution, PostgreSQL multi-connection races, real model responses, production backup-erasure policy, complete demo parity or platform eligibility. Synthetic fixtures and mocked providers do not replace these checks. The old health endpoint returned 200; V3 is not deployed. No production change or formal submission occurred. Resolve the release gates and capture actual device/platform evidence next.

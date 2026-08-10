# 群聊专家知识与主动教练验证 / Group expert knowledge and proactive coaching verification

## 中文

### 验证范围

本记录只验证代码、策略、调度与构建，不包含消息正文、群或用户标识、健康数据、书籍摘录、密钥或配对信息。生产发布、共享书籍发布数量和飞书真实投递需由发布后的严格门禁单独确认。

### 本地门禁（2026-08-10）

- `uv run pytest -q`：289 项通过；唯一警告来自既有 Starlette/httpx 测试兼容性弃用提示。
- `uv run ruff check .`：通过。
- `uv run python scripts/check_bilingual_docs.py`：通过。
- `sh -n infra/tencent/*.sh scripts/*.sh` 与 `git diff --check`：通过。
- `swift test --package-path apps/ios-bridge/Core`：11 项通过。
- XcodeGen 生成与 `scripts/check_ios_generated_config.py`：通过；生成的 `.xcodeproj` 不提交。
- iPhone 17 / iOS 26.3.1 无签名 Simulator 构建完成。该 Mac 的 CoreSimulator lockdown 服务在启动测试进程时失效，因此本记录不把本地 Simulator 测试标为通过；固定 GitHub iOS CI 是发布前的最终 Simulator 门禁。

### 策略证据

自动化测试覆盖：仅 Owner 的三个已审核标题可进入共享知识；未经确认的私人权利状态必须先留下独立审核记录，相同哈希重复导入幂等，只有内容变化才替换旧版本。群聊用实际安全问题检索 `published` 范围，最多返回三段书名/页码摘录，并拒绝缺失或虚构引用；个人问题、身份、健康数值、诊断、治疗、用药和供应商错误不进入群聊；模型、检索或投递失败使用固定安全回退；主动任务具有总开关复核、静默期、从配置时刻计算的五分钟有效窗口、唯一事件键、飞书 `uuid`、三次有限重试与无正文 Outbox。

## English

### Verification scope

This record verifies code, policy, scheduling, and builds only. It contains no message text, group or user identifier, health data, book excerpt, credential, or pairing artifact. Production deployment, shared-book publication counts, and real Feishu delivery require separate strict post-release gates.

### Local gates (2026-08-10)

- `uv run pytest -q`: 289 passed; the only warning is the existing Starlette/httpx test-compatibility deprecation.
- `uv run ruff check .`: passed.
- `uv run python scripts/check_bilingual_docs.py`: passed.
- `sh -n infra/tencent/*.sh scripts/*.sh` and `git diff --check`: passed.
- `swift test --package-path apps/ios-bridge/Core`: 11 passed.
- XcodeGen generation and `scripts/check_ios_generated_config.py`: passed; the generated `.xcodeproj` is not committed.
- The unsigned iPhone 17 / iOS 26.3.1 Simulator build completed. This Mac's CoreSimulator lockdown service failed while starting the test process, so this record does not mark the local Simulator test as passed; the fixed GitHub iOS CI remains the final pre-release Simulator gate.

### Policy evidence

Automated tests cover: only the Owner's three reviewed titles may enter shared knowledge; an unconfirmed private-rights state must first receive a separate audit record, a repeated identical hash is idempotent, and only changed content supersedes an old edition. A group searches the `published` scope using the actual safe question, returns at most three title/page-cited excerpts, and rejects missing or fabricated citations; personal questions, identity, health values, diagnosis, treatment, medication, and provider errors never enter a group reply; model, retrieval, or delivery failure uses a fixed safe fallback; proactive jobs recheck the master switch, quiet hours, a five-minute validity window measured from the configured schedule, a unique event key, Feishu `uuid`, three bounded retries, and a content-free Outbox.

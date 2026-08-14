# AGENTS.md

# FitCrew Coding Agent Learning Hub

> 所有 Coding Agent 在修改本仓库前，必须先阅读本文件。

## 1. 项目是什么

FitCrew 是一个运行在飞书生态中的私人生活方式教练与健康 Agent。

产品演进：

```text
V1 = Behavior & Buddy Layer
V2 = Health Data & Privacy Layer
V3 = Decision & Learning Layer
```

### V1

解决：

“有人陪我执行。”

能力：

- 群打卡
- 每日行为
- 同伴互动
- 私聊建议

### V2

解决：

“系统开始理解我的身体数据。”

现有关键基础：

- Apple Health
- Apple Watch
- HealthKit Bridge
- 鱼跃 CGM 数据
- 睡眠
- 活动
- 恢复
- 加密摄取
- consent
- 身份隔离
- 群聊 / 私聊隐私边界
- Hermes 模型路由
- 腾讯云部署

### V3

解决：

“系统知道我下一步该做什么，并从结果中继续学习。”

新增核心：

- Today
- Journey
- Experiments
- Log
- Profile
- 90 Day Journey
- Today Mission
- Right Now Action
- Personal Body Model
- InBody
- Body Check
- Meal Event
- AI Experiment

---

## 2. 重要：V3 必须从哪里开发

V3 必须基于当前 V2 主干增量开发。

禁止：

- 新建第二套 HealthKit
- 新建第二套身份系统
- 新建第二套 consent
- 绕过现有 privacy policy
- 建一个和现有 FitCrew 无关的独立 demo app
- 把真实个人健康数据硬编码到 Git

必须复用：

### `apps/api/`

继续负责：

- consent
- encrypted ingestion
- daily features
- knowledge
- BodyOS data boundary
- API auth

### `apps/ios-bridge/`

继续负责：

- HealthKit
- Apple Watch
- Apple Health
- CGM 写入 Apple Health 后的读取
- incremental sync

### `integrations/hermes/`

继续负责：

- Feishu
- identity isolation
- group privacy
- model routing

### `infra/tencent/`

继续负责：

- deployment
- HTTPS
- backup
- rollback

---

## 3. Coding Agent 阅读顺序

开始任何 V3 开发任务前，按顺序读取：

1. `README.md`
2. `CHANGELOG.md`
3. `AGENTS.md`
4. `docs/agent-context/CURRENT_STATE.md`
5. `docs/agent-context/ARCHITECTURE_BASELINE.md`
6. `docs/agent-context/PRIVACY_BOUNDARIES.md`
7. `docs/v3/README.md`
8. `docs/v3/DESIGN.md`

如果开发 UI：

额外读：

- `docs/v3/DESIGN.md`
- `docs/v3/USER_TIPS.md`

如果开发健康数据：

额外读：

- V2 HealthKit / ingestion / aggregation 代码
- `docs/agent-context/PRIVACY_BOUNDARIES.md`

如果开发 Experiments：

额外读：

- `docs/v3/README.md`
- `docs/agent-context/V3_DATA_MODEL.md`

---

## 4. V3 产品结构

一级导航：

```text
Today
Journey
Experiments
Log
Profile
```

### Today

回答：

“我现在最应该做什么？”

必须优先展示：

- Current State
- One Next Move
- Why
- Active Experiment
- Next Check
- Body Check

### Journey

回答：

“长期上我有没有变好？”

包含：

- 90 Day Journey
- InBody
- body fat
- skeletal muscle
- VO₂ Max
- sleep
- activity
- workout events
- experiment events

### Experiments

回答：

“下一步最值得验证什么？”

包含：

- Hypothesis
- Intervention
- Metrics
- Progress
- Result
- Next Step

### Log

作为主动输入：

- meal photo
- Body Check
- weight
- circumference
- menstrual context
- workout feeling
- manual correction

### Profile

包含：

- data source
- Apple Health permission
- CGM
- InBody
- goal
- privacy
- memory
- export

---

## 5. V3 AI Native 循环

```text
Observe
→ Hypothesize
→ Recommend
→ User Action
→ Measure
→ Evaluate
→ Learn
→ Next Action
```

只做数据摘要，不算 V3。

每次建议应尽可能有：

- Action
- Why
- Evidence
- Confidence
- What I will learn

一个时刻只允许一个主 Action。

---

## 6. V3 开发优先级

优先顺序：

1. V3 data model
2. V3 API contract
3. Personal Body Model
4. Experiment engine
5. Today
6. Journey
7. Experiments
8. Log
9. Profile
10. Onboarding
11. Feishu personal integration
12. authorized group sharing

UI 不应该先于数据模型成为主工程。

---

## 7. 隐私红线

默认不能进入群聊：

- raw glucose
- HRV
- sleep duration
- body fat
- menstrual information
- private meal interpretation
- private chat
- private documents

群里可以出现：

- public health knowledge
- public challenge
- check-in
- user explicitly shared behavior result

个人层才可以使用完整授权健康上下文。

---

## 8. 设计红线

V3 设计遵守：

**FitCrew Brand × Apple Interaction**

Liquid Glass 只用于交互层。

内容层保持温暖、稳定、可读。

禁止：

- KPI wall
- BI dashboard
- 霓虹 AI
- 全屏蓝紫渐变
- 每张卡都是玻璃
- 小于规范字号塞数据

iPhone 16 Pro 基准：

```text
402 × 874 pt
```

最小 Touch Target：

```text
44 × 44 pt
```

---

## 9. 交付前自检

Coding Agent 提交代码前必须回答：

### Architecture

- 是否基于 V2 增量开发
- 是否复用了现有 auth / identity / consent
- 是否避免平行健康数据链路

### Privacy

- 是否可能把私人健康数据带入群聊
- 是否保存了不必要 raw data
- 模型是否只收到完成任务必要的信息

### Product

- 用户是否知道下一步做什么
- AI 是否在学习用户结果
- 是否产生可验证闭环

### UI

- 是否遵守 DESIGN.md
- iPhone 16 Pro 是否可用
- Touch target 是否达标
- 是否避免 KPI wall

---

## 10. Agent 完成任务后的更新义务

如果修改了产品事实、架构或 V3 规则，应同步更新：

- `docs/agent-context/CURRENT_STATE.md`
- 对应 V3 文档
- CHANGELOG

不要让代码和 Agent Learning Hub 产生明显漂移。

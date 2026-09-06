# V3 Data Model Draft

## 中文

本文是产品领域模型草案。以下中文说明与后文英文区的 TypeScript 类型定义对应，字段名、类型和枚举值以保留的代码定义为准；`?` 表示可选字段。

### TodayMission：今日任务

包含字符串字段 `id`（任务 ID）、`user_id`（用户 ID）、`date`（日期）、`action`（行动）；字符串数组 `why`（原因）、`evidence_refs`（证据引用）；`confidence`（置信度）取 `low`、`medium` 或 `high`；可选字符串 `learn_goal`（学习目标）；`status`（状态）取 `proposed`（已提出）、`accepted`（已接受）、`done`（已完成）或 `skipped`（已跳过）。

### Experiment：实验

包含字符串字段 `id`、`user_id`、`title`（标题）、`question`（问题）、`hypothesis`（假设）、`start_date`（开始日期）、`end_date`（结束日期）、`intervention`（干预行动）；字符串数组 `metrics`（指标）和 `success_criteria`（成功标准）；`status` 取 `proposed`（已提出）、`accepted`（已接受）、`running`（进行中）、`completed`（已完成）或 `cancelled`（已取消）；可选的 `confidence` 取 `low`、`medium` 或 `high`。

### BodyCheck：身体感受记录

必填字符串字段为 `id`、`user_id` 和 `timestamp`（时间戳）。可选字段包括数值 `energy`（精力）、`stress`（压力）、`hunger`（饥饿程度），字符串数组 `symptoms`（症状）及字符串 `note`（备注）。

### MealEvent：餐食事件

必填字符串字段为 `id`、`user_id` 和 `timestamp`。可选字符串字段为 `image_ref`（图片引用）、`description`（描述）。三个可选嵌套对象如下，其中所有子字段也均可选：

- `context`（场景）：布尔值 `pre_workout`（训练前）、`post_workout`（训练后）、`caffeine`（咖啡因）。
- `glucose_response`（血糖反应）：数值 `pre_meal`（餐前血糖）、`peak`（峰值）、`two_hour`（两小时血糖），以及字符串 `peak_time`（峰值时间）。
- `subjective`（主观感受）：数值 `fullness`（饱腹感）、`energy`（精力）、`hunger_2h`（两小时后的饥饿程度）。

### PersonalBodyHypothesis：个人身体假设

包含字符串字段 `id`、`user_id`、`domain`（领域）、`statement`（假设陈述）、`last_updated`（最后更新时间）；数值 `confidence`（置信度）；字符串数组 `supporting_evidence`（支持证据）和 `contradicting_evidence`（反对证据）。

### JourneyMilestone：旅程里程碑

包含字符串字段 `id`、`user_id`、`date`、`title`（标题）、`summary`（摘要）；字符串数组 `evidence_refs`（证据引用）；`type`（类型）取 `inbody`（身体成分）、`experiment`（实验）、`fitness`（体能）、`behavior`（行为）或 `custom`（自定义）。

## English

This file is a product-domain draft.

## TodayMission

```ts
type TodayMission = {
  id: string
  user_id: string
  date: string
  action: string
  why: string[]
  evidence_refs: string[]
  confidence: "low" | "medium" | "high"
  learn_goal?: string
  status: "proposed" | "accepted" | "done" | "skipped"
}
```

## Experiment

```ts
type Experiment = {
  id: string
  user_id: string
  title: string
  question: string
  hypothesis: string
  start_date: string
  end_date: string
  intervention: string
  metrics: string[]
  success_criteria: string[]
  status: "proposed" | "accepted" | "running" | "completed" | "cancelled"
  confidence?: "low" | "medium" | "high"
}
```

## BodyCheck

```ts
type BodyCheck = {
  id: string
  user_id: string
  timestamp: string
  energy?: number
  stress?: number
  hunger?: number
  symptoms?: string[]
  note?: string
}
```

## MealEvent

```ts
type MealEvent = {
  id: string
  user_id: string
  timestamp: string
  image_ref?: string
  description?: string
  context?: {
    pre_workout?: boolean
    post_workout?: boolean
    caffeine?: boolean
  }
  glucose_response?: {
    pre_meal?: number
    peak?: number
    peak_time?: string
    two_hour?: number
  }
  subjective?: {
    fullness?: number
    energy?: number
    hunger_2h?: number
  }
}
```

## PersonalBodyHypothesis

```ts
type PersonalBodyHypothesis = {
  id: string
  user_id: string
  domain: string
  statement: string
  confidence: number
  supporting_evidence: string[]
  contradicting_evidence: string[]
  last_updated: string
}
```

## JourneyMilestone

```ts
type JourneyMilestone = {
  id: string
  user_id: string
  date: string
  type: "inbody" | "experiment" | "fitness" | "behavior" | "custom"
  title: string
  summary: string
  evidence_refs: string[]
}
```

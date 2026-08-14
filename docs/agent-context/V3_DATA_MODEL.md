# V3 Data Model Draft

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

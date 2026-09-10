# FitCrew V3 Design System

## 中文

所有编写 UI 的编码 Agent 必须在实现前阅读本文。

### 核心

**FitCrew 品牌 × Apple 交互。**

### iPhone 基线

画布为 402 × 874 pt；触控目标至少为 44 × 44 pt。

### Liquid Glass

用于交互层：标签栏、导航栏、工具栏、分段控件、弹出面板和悬浮控件。不要为所有健康内容卡片都覆盖玻璃效果。

### 品牌

品牌颜色变量保留在后文的 CSS 代码块中：背景 `#F7F8F0`、主文字 `#1F3A2D`、柔和文字 `#48624F`、弱化文字 `#71856F`、绿色 `#2FB673`、深绿 `#1B9459`、叶绿 `#86D94F`、珊瑚色 `#FF8A5C`、阳光黄 `#FFC94A`、鼠尾草色 `#DDEAD2`、薄荷色 `#E9F2E2`、卡片白色 `#FFFFFF`。

### 字体

使用系统字体栈。大标题 34，一级标题 28，二级标题 22，强调标题 17 半粗体，正文 17 常规，副标题 15，脚注 13，说明文字 12。

### 内容规则

每张卡片只呈现一个主要数字。图表用于呈现证据。行动的视觉优先级高于证据。

### 今天页层级

1. 问候
2. 当前状态
3. 下一步行动
4. 原因
5. 进行中的实验
6. 下一次检查

### 应避免的视觉模式

避免 KPI 指标墙、霓虹 AI 风格、整页渐变、过度模糊、过小文字、过多强调色以及通用的发光球体。

## English

All UI coding agents must read this before implementation.

## Core

**FitCrew Brand × Apple Interaction**

## iPhone baseline

402 × 874 pt

Touch target ≥ 44 × 44 pt.

## Liquid Glass

Use for interaction layer:

- Tab Bar
- Navigation Bar
- Toolbar
- Segmented controls
- Sheets
- Floating controls

Do not cover all health-content cards with glass.

## Brand

```css
--fit-bg: #F7F8F0;
--fit-ink: #1F3A2D;
--fit-ink-soft: #48624F;
--fit-muted: #71856F;
--fit-green: #2FB673;
--fit-green-deep: #1B9459;
--fit-leaf: #86D94F;
--fit-coral: #FF8A5C;
--fit-sun: #FFC94A;
--fit-sage: #DDEAD2;
--fit-mint: #E9F2E2;
--fit-card: #FFFFFF;
```

## Typography

- Large Title 34
- Title 1 28
- Title 2 22
- Headline 17 semibold
- Body 17 regular
- Subheadline 15
- Footnote 13
- Caption 12

Use system font stack.

## Content rule

One card, one primary number.

Charts are evidence.

Action has higher visual priority than evidence.

## Today hierarchy

1. Greeting
2. Current State
3. One Next Move
4. Why
5. Active Experiment
6. Next Check

## Visual anti-patterns

Avoid:

- KPI wall
- neon AI
- full-page gradient
- excessive blur
- tiny text
- too many accent colors
- generic glowing orb

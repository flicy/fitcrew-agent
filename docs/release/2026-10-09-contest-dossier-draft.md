# 2026 微信小程序开发大赛作品说明草稿 / 2026 WeChat Mini Program Contest Dossier Draft

## 中文

**状态：内部草稿，尚不可提交。** 截至 2026 年 10 月 9 日，FitCrew 小程序尚未部署、正式上线或完成真机验收，AI 服务也未在真实云账号验证。下文描述已实现的产品方向与待验证能力，正式 PDF 必须按已上线版本重新核对，不得把计划功能写成现有功能。

### 作品定位与真实问题

FitCrew 面向希望把个人健康数据转化为日常行动的人。睡眠、活动、体重与主观感受常分散在不同入口，用户难以判断今天先做什么，也难以知道一次调整是否有效。产品将「今天的下一步」与长期旅程、可暂停的个人实验和主动记录放在同一流程中，尽量让每次建议有依据、置信度和下一次检查点。

### 当前工程与计划体验

原生微信小程序已有 Today、Journey、Experiments、Log、Profile 五页代码，支持记录、授权、导出和删除的本地验证。服务端沿用现有 V2 用户身份、设备令牌、同意记录、加密健康数据摄取与跨用户隔离；小程序可通过私有云托管传输调用现有 `/v3` API。iOS HealthKit 桥接用于经用户授权后同步 Apple Health 数据，但尚未完成真机验收。所有服务端部署、持久数据库、微信真实登录—保存—重登—删除以及平台隐私配置仍待完成。

### AI 用途与边界

拟在用户单独同意后，以完成任务所需的最小脱敏摘要生成可解释的下一步建议，再记录用户是否执行及后续观察。已有服务端可选云开发 AI 接口和同意边界代码，但实际模型、服务商、费用、合规资格、响应质量及真实调用尚未验证。正式提交前，应填写真实模型与数据接收方，并只描述上线版本中已启用、可在微信内体验的 AI 功能；若 AI 尚未可用，本稿不能作为符合赛事 AI 主题的完成作品说明。

### 提报前必填与证明

- 与微信平台已上线版本一致的正式作品名称、AppID `wxae59705a7cce30f9`、可扫码打开的正式二维码，以及上线时间和状态回执。
- 实际运行的核心流程、AI 功能和隐私说明；从真实设备验证登录、保存、重登、删除及失败状态。
- 参赛团队真实姓名与成员信息、每位成员的所需身份证件；仅由本人在官方页面提交，不写入本仓库。
- 将与已上线功能一致的中文作品说明导出为 PDF；引用团队外成果时如实注明。
- 下载官方参赛授权书，由有权参赛者阅读并自行签署，再按平台要求提交。

依据：[微信赛事平台](https://contest.weixin.qq.com/eventDetails?id=4598379302114656257)及其官方《2026 微信小程序开发大赛赛事规程》。官方规程要求作品在 2026 年 7 月 17 日至 10 月 17 日提报期内正式上线并能在微信内正常运行；提报截止为北京时间 10 月 17 日 23:59。提审或体验版均不等于正式上线。

## English

**Status: internal draft, not ready for submission.** As of October 9, 2026, the FitCrew Mini Program has not been deployed, published, or accepted on a real device, and its AI service has not been verified in a real cloud account. Reconcile every statement with the live version before exporting the required PDF; planned functions must not be described as available.

### Product and user need

FitCrew helps people turn personal health information into a practical next action. Sleep, activity, weight, and subjective observations are often scattered, making it hard to decide what to do today or whether a change helped. The product connects one next move with a longer journey, pausable personal experiments, and active logging, aiming to show evidence, confidence, and the next check for each recommendation.

### Current engineering and intended experience

The native Mini Program has code for Today, Journey, Experiments, Log, and Profile, with locally verified recording, consent, export, and deletion paths. The backend retains the V2 user identity, device tokens, consent records, encrypted health ingestion, and user isolation; a private Cloud Hosting transport can call the existing `/v3` API. The iOS HealthKit bridge is intended to sync Apple Health data with user permission, but has not passed real-device acceptance. Backend deployment, durable storage, real WeChat sign-in/save/relaunch/erasure, and platform privacy setup remain unfinished.

### AI use and limits

After separate consent, the intended AI flow uses the minimum de-identified task summary to suggest an explainable next step and observe the user's action and result. Optional CloudBase AI transport and consent boundaries exist in code, but the actual model, provider, cost, eligibility, quality, and live call are unverified. The final dossier must name the real provider and describe only AI that is enabled and usable in the published Mini Program. Without a working AI feature, this draft does not establish a completed entry under the contest's AI theme.

### Required evidence before entry

- The exact published product name, AppID `wxae59705a7cce30f9`, live QR code, publication time, and platform status.
- Real-device proof of the released core flow, AI feature, privacy notice, sign-in, save, relaunch, erasure, and failure states.
- Real participant identities and required identity documents, submitted by the people concerned only through the official site, never stored in this repository.
- A Chinese PDF describing only the published functionality, with external contributors' work attributed when used.
- The official authorization letter reviewed and signed by the authorized participant before submission.

Source: the [WeChat contest platform](https://contest.weixin.qq.com/eventDetails?id=4598379302114656257) and its official 2026 regulations. The entry must be formally published and work in WeChat during the July 17–October 17, 2026 submission period. Entries close at 23:59 China time on October 17. A review submission or trial build does not count as publication.

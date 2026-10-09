# AI 使用确认反馈 / AI use of confirmed feedback

## 中文

此前确认记忆只保存在账号中，未参与 AI 实验选择。本次沿用原有模型网关，在用户单独同意后，将同一目标下最近最多十条确认反馈加入实验选择请求。每条仅含目标类别、已知行动类型及「适合／不适合」的主观评价，按最近确认优先排列。不发送备注、身份、实验标题、记录标识或原始健康数据，也不把反馈当作疗效证据。

- 仅使用仍存在的确认记忆；其来源实验必须已完成、结果未失效，反馈仍明确确认且评价一致。不同目标、未确认、无法识别的行动与失效来源排除。保留既有两种低风险行动选择和输出校验，不输出模型任意医疗建议。
- AI 告知版本由服务商、运营者告知版本和具体告知内容共同计算。旧的聚合数据同意不会覆盖新增反馈用途；服务商或告知内容变化后必须重新同意。两端展示实际说明与版本，确认记忆不等同于同意外发。
- 依赖关系只存于账号内的加密产品记录，不发送模型。撤回或修改记忆、删除来源记录时，相关待确认提案停止，旧幂等响应失效，需重新生成。已开始或完成的行动历史不重写；未来请求不再使用撤回或失效的反馈。
- 提案展示本次 AI 请求涉及的反馈数量；规则回退不宣称 AI 成功。此实现仍需真实提供方配置、资格核实和端到端验收，合成模型测试不能证明生产 AI 已可用。

微信官方 [Handoff 示例](https://github.com/wechat-miniprogram/ai-mode-demo)要求 AppID 获得相应内测权限；目前未核实本项目具备权限。上述产品内部网关改动不表示已经接通微信小微，也不表示可以读取用户其他微信对话。官方 guide 本次读取失败，不能据此断言正式提审开放状态。

验证包含：请求只含必要字段，旧授权和服务商变化要求重新同意，撤回记忆及删除来源使待确认提案与重放失效，不同目标与未确认反馈排除，以及最近十条限制。最终完整构建结果见对应提交 CI；真机与生产验收仍待完成。

## English

Confirmed memories previously remained stored without participating in AI selection. The existing model gateway now includes up to ten recent confirmed feedback entries for the same goal after separate consent. Each contains only a goal category, recognized action type and subjective fits/not-fit assessment, newest first. Notes, identities, experiment titles, record identifiers and raw health data are excluded; feedback is not evidence of efficacy.

- Use only existing confirmed memories with completed, non-invalidated source experiments and matching, still-confirmed feedback. Exclude other goals, unconfirmed feedback, unknown actions and invalid sources. Retain the two low-risk action choices and output validation; never surface arbitrary medical advice.
- Derive the effective disclosure version from provider, operator notice version and actual notice content. Prior aggregate-only consent cannot authorize feedback use. Provider or disclosure changes require renewed consent. Both clients show the notice/version; confirming a memory is separate from authorizing transmission.
- Keep provenance only in the account's encrypted product records, not in model requests. Withdrawal, changed feedback or source deletion stops dependent unaccepted proposals and invalidates cached retries. Regeneration is required. Do not rewrite started/completed action history; subsequent requests exclude withdrawn/invalid feedback.
- Disclose the feedback count involved in a proposal's AI request. Rule fallback does not claim model success. Real provider configuration, eligibility and end-to-end acceptance remain required; synthetic tests cannot establish production availability.

The official [WeChat handoff example](https://github.com/wechat-miniprogram/ai-mode-demo) requires AppID beta access, which has not been verified for this project. These internal gateway changes do not establish Xiaowei integration or access to other WeChat conversations. The official guide failed to load, so current formal-submission availability is not established.

Validation covers minimal request fields, renewed consent for old grants/provider changes, invalidation of pending proposals and retries after withdrawal/source deletion, exclusion of other goals/unconfirmed feedback, and the ten-entry limit. Consult matching commit CI for complete builds; device and production acceptance remain outstanding.

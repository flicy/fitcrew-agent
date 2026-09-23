# iOS 配对请求边界 / iOS pairing request boundaries

## 中文

配对兑换请求现在记录发起时的账号身份和请求编号。若之后登录其他账号或再次发起配对，旧请求的成功或错误响应都不会覆盖当前账号、凭据和状态提示。手动连接界面仅在本次配对成功后清空输入并刷新。

兑换响应的服务地址必须与邀请中的服务地址相同，不能在响应里更换健康数据的接收地址。本变更仍复用原有邀请兑换与设备凭据，不实现微信和 Apple 登录身份的自动合并。

新增四个模拟传输测试覆盖：旧配对晚于新登录返回；最后一次配对成功后旧请求失败；旧请求先返回但已被新请求替代；兑换响应更换服务器地址。测试使用隔离的本地设置和合成凭据，不访问真实账号或健康数据。完整测试结果以本次构建日志及对应提交的 CI 为准；仍需真机联调。

## English

Pairing exchanges now capture the starting account identity and request identifier. A subsequent login or pairing request supersedes earlier exchanges; stale success or failure responses cannot overwrite the current account, token or status. Manual connection clears its input and refreshes only when that particular attempt succeeds.

The provisioned server URL must match the invitation URL, preventing the exchange response from redirecting subsequent health uploads. This retains the existing invitation and device-token system and does not automatically merge WeChat and Apple login identities.

Four simulated-transport tests cover a pairing response arriving after a new login, stale failure after the newest pairing succeeds, a superseded request finishing first, and a response changing the server address. Tests use isolated preferences and synthetic credentials, without real accounts or health data. Consult the build log and matching commit CI for execution results; real-device integration remains required.

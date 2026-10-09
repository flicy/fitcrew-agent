# 微信云托管传输准备 / WeChat Cloud Hosting Transport Preparation

## 中文

小程序客户端现可在原有 HTTPS `wx.request` 与 `wx.cloud.callContainer` 之间选择，均调用现有 FastAPI `/v3` 接口，沿用服务器验证的微信登录、设备令牌、授权、加密存储、导出与删除。没有新增身份或健康数据链路。云托管私有链路无需在小程序后台配置请求域名，但并不自动完成后端部署、数据库、隐私审核或 iOS 访问。

云模式需要在公开配置中填写 CloudBase 环境 ID、云托管服务名，以及该服务的 HTTPS 公网地址 `baseURL`。小程序请求通过环境和服务名走私有链路；`baseURL` 供服务端登录响应校验及 iOS 配对使用，不会代替云托管私有请求。正式环境还需服务器端安全配置微信 AppSecret、身份哈希密钥、数据加密密钥与持久数据库，绝不可写进小程序包。配置为空或不完整时客户端拒绝请求，发布校验也失败。

现有 `infra/tencent/Dockerfile.api` 包含 Feishu/Hermes/Codex 等生产组件，`compose.yaml` 将 API、worker、gateway 和 PostgreSQL 分开运行。腾讯云文档说明云托管支持 Dockerfile 和容器服务，但不能据此推断现有 Compose 可原样部署，或免费环境能够承载数据库和持续生产流量。要先取得账号下真实环境与计费信息，隔离部署 API 与持久数据库，验证迁移、备份恢复、登录/保存/重登/删除和真机体验，再上传提审。不得把已有东京 V2 服务当成新小程序已部署。

截至 2026-10-09：尚无环境 ID、服务名、实际公网地址、生产数据库、真机闭环或平台提审回执。微信开发者工具 CLI 的 `islogin` 曾返回 `true`，但 `cloud env list` 返回“需要重新登录”；需重新扫码并读取环境列表。腾讯云免费体验环境在小程序发布后第 15 天到期，不能作为长期免费正式服务；后续成本应在账号内按实际套餐核对。云托管私有调用和计费规则见[小程序访问云托管](https://docs.cloudbase.net/run/develop/access/mini)、[云托管服务设置](https://docs.cloudbase.net/run/deploy/service-setting)和[腾讯云价格文档](https://cloud.tencent.com/document/product/876/75213)。

## English

The Mini Program client can now select either its existing HTTPS `wx.request` transport or `wx.cloud.callContainer`. Both call the existing FastAPI `/v3` contract and preserve server-verified WeChat sign-in, device tokens, consent, encrypted storage, export, and deletion. No parallel identity or health-data stack is introduced. The private Cloud Hosting link does not require a Mini Program request-domain entry, but it does not deploy the backend, provision a database, complete privacy review, or provide iOS access by itself.

Cloud mode needs a CloudBase environment ID, Cloud Hosting service name, and the service's public HTTPS `baseURL` in public configuration. Mini Program requests use the private environment/service route. The URL is used to verify the server's sign-in response and for iOS pairing; it is not used for private Mini Program requests. The production server also needs a protected WeChat AppSecret, identity pepper, encryption key, and persistent database. None belongs in the Mini Program bundle. Missing or incomplete configuration fails closed in the client and release validator.

The existing `infra/tencent/Dockerfile.api` includes Feishu/Hermes/Codex production components, while `compose.yaml` runs API, worker, gateway, and PostgreSQL separately. Tencent documents Dockerfile-based container services, but that does not prove the existing Compose stack is directly deployable or that the free tier can host the database and sustained production traffic. First obtain the account's actual environment and billing details, deploy an isolated API and durable database, verify migration and backup recovery, complete sign-in/save/relaunch/deletion and device acceptance, then upload for review. The Tokyo V2 service is not evidence that the new Mini Program backend is deployed.

As of October 9, 2026, no environment ID, service name, actual public URL, production database, device acceptance, or platform review receipt is available. The WeChat DevTools CLI once reported `islogin: true`, but `cloud env list` required a fresh login; the owner must scan again before the environment can be inspected. Tencent's free experience environment expires on day 15 after Mini Program publication, so it is not a sustained free production plan; verify the account's actual paid price. See Tencent's [Mini Program Cloud Hosting access](https://docs.cloudbase.net/run/develop/access/mini), [service settings](https://docs.cloudbase.net/run/deploy/service-setting), and [pricing](https://cloud.tencent.com/document/product/876/75213).

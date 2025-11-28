waBNB Greenfield 声誉存储改造 TODO

Phase 1：接口抽象与 IPFS 适配（最小改动）✅
- [x] 引入 `ReputationStorage` 抽象类（put/get）。
- [x] 将现有 IPFS 客户端包装为 `IpfsReputationStorage`，逻辑不变，仅实现接口。
- [x] 增加工厂 `create_reputation_storage`，默认返回 IPFS 实例。
- [x] 单元测试：
  - [x] 使用 fake/stub IPFS client，验证 put/get 调用的参数透传与返回值。
  - [x] 工厂在无配置时返回 IPFS，实现默认行为。

Phase 2：Greenfield 实现（HTTP PutObject/GetObject）✅
- [x] 新增 `greenfield_storage.py`，注入 `sp_host/bucket/private_key/txn_hash`，构造 Authorization 头并执行 PUT/GET。
- [x] 补全 `_build_authorization` 签名逻辑，符合官方 README（canonical request + Txn Hash）。
- [x] 配置加载：支持 `GREENFIELD_SP_HOST`、`GREENFIELD_BUCKET`、`GREENFIELD_PRIVATE_KEY`、`GREENFIELD_TXN_HASH`、可选 content-type。
- [x] 单元测试：
  - [x] 使用 requests-mock/monkeypatch，验证 URL 形态为 `https://{bucket}.{sp_host}/{object}`，Header 带 `X-Gnfd-Txn-Hash`、Authorization 被调用。
  - [x] `_gen_key` 为空 key 时生成非空键。

Phase 3：后端切换与文档/配置验证 ✅
- [x] 工厂按 `REPUTATION_BACKEND` 返回 IPFS 或 Greenfield，默认 IPFS。
- [x] 更新环境变量示例与 README/配置文档（Plan 已含，必要时同步 SDK README）。
- [x] 预留降级策略：Greenfield 异常时清晰日志，不影响 IPFS 路径。
- [x] 单元测试：
  - [x] 参数化 `REPUTATION_BACKEND` 为 ipfs/greenfield，验证工厂实例类型。
  - [x] 缺失必要 Greenfield 配置时抛出明确异常或日志警告。

Phase 4（可选）：集成验证
- [ ] 测试网创建 bucket/object，获取 Txn Hash，跑一次 Put/Get 验证；上线前在主网重复。
- [ ] 若要对外公开读，验证无需 Authorization 也能 GET；否则验证签名 URL/鉴权策略。
- [ ] 单元/集成测试：
  - [ ] 使用测试网 SP 的 mock 或沙盒 endpoint，跑实际 PUT/GET（可标记为 integration）。

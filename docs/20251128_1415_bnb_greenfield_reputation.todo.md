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

Phase 4：集成验证 ✅
- [x] 创建集成测试文件 `tests/test_greenfield_integration.py`，包含：
  - [x] 真实 Greenfield 测试网连接测试（PUT/GET roundtrip）
  - [x] 自动生成 key 测试
  - [x] Per-object txn_hash 测试
  - [x] 大文件上传测试（1MB）
  - [x] 二进制数据完整性测试
  - [x] 错误处理测试（不存在的对象）
- [x] 公开读功能验证：
  - [x] 测试无需 Authorization 的公开读访问
  - [x] 验证公开 URL 格式
- [x] 工厂集成测试：
  - [x] 从环境变量创建 Greenfield 存储
  - [x] 后端切换测试
- [x] 创建完整的设置指南 `docs/greenfield_integration_guide.md`，包含：
  - [x] 前置条件（依赖、测试网 BNB、私钥获取）
  - [x] 测试网配置信息
  - [x] Bucket 创建步骤（DCellar 和 CLI 两种方式）
  - [x] Transaction Hash 获取方法
  - [x] 环境变量配置
  - [x] 运行测试命令
  - [x] 公开读设置
  - [x] 故障排查指南
  - [x] 主网迁移清单
- [x] 创建使用示例文档 `docs/greenfield_usage_examples.md`，包含：
  - [x] 基础用法（工厂模式和直接使用）
  - [x] 配置方法（环境变量和代码配置）
  - [x] 存储操作示例（上传、下载、批量操作）
  - [x] 错误处理（重试、降级）
  - [x] 高级用法（版本控制、元数据、内容寻址）
  - [x] 生产考虑（监控、缓存、健康检查）
  - [x] 完整的生产级服务示例

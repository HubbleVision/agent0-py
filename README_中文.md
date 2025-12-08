# Agent0 SDK - BNB 链支持与 Greenfield 声誉存储

> 🎉 完整的中文版文档和端到端测试系统

## 📋 概述

本项目为 agent0 SDK 添加了完整的 BNB 生态支持:
- ✅ **BNB 链支持**: 支持 BNB 测试网 (Chain ID 97) 和 BNB 主网 (Chain ID 56) 的 ERC-8004 智能合约
- ✅ **Greenfield 存储**: 完整的 BNB Greenfield 分布式存储支持
- ✅ **统一接口**: 从基础的 IPFS 存储到自动化的端到端测试

## 🌐 支持的区块链网络

| 区块链 | Chain ID | 状态 | 默认合约 |
|-------|----------|------|---------|
| Ethereum Sepolia | 11155111 | ✅ 已激活 | 是 |
| Base Sepolia | 84532 | ✅ 已激活 | 是 |
| Polygon Amoy | 80002 | ✅ 已激活 | 是 |
| Linea Sepolia | 59141 | ✅ 已激活 | 是 |
| **BNB 测试网** | **97** | **✅ 已激活** | **是** |
| **BNB 主网** | **56** | **🚧 即将上线** | **待部署** |

### 使用 BNB 链

**默认合约已内置** - 只需指定 `chainId` 即可开始使用!

```python
from agent0_sdk import SDK

# BNB 测试网 - 默认合约已配置好!
sdk = SDK(
    chainId=97,  # 这就够了 - SDK 会自动处理其他配置
    rpcUrl="https://data-seed-prebsc-1-s1.bnbchain.org:8545",
    signer="0xYOUR_PRIVATE_KEY"
)

# 在 BNB 测试网上注册代理
agent = sdk.createAgent(
    name="我的 BNB 代理",
    description="运行在 BNB 链上的 AI 代理"
)
agent.registerIPFS()  # 需要 IPFS 配置 (pinata 等)
print(f"代理已在 BNB 测试网注册: {agent.agentId}")  # 例如: "97:1"

# BNB 主网（上线后可用）
sdk_mainnet = SDK(
    chainId=56,
    rpcUrl="https://bsc-dataseed.binance.org/",
    signer="0xYOUR_PRIVATE_KEY"
)
```

**测试自定义合约**（可选 - 高级用户使用）:

```python
# 方式 1: 使用环境变量（在 .env 中设置）
# BNB_TESTNET_IDENTITY=0xYourCustomContract
sdk = SDK(chainId=97, rpcUrl="...", signer="...")

# 方式 2: 使用 registryOverrides 参数
sdk = SDK(
    chainId=97,
    rpcUrl="...",
    signer="...",
    registryOverrides={
        97: {
            "IDENTITY": "0xYourTestContract",
            "REPUTATION": "0xYourTestContract2",
            "VALIDATION": "0xYourTestContract3"
        }
    }
)
```

**获取测试网 BNB:**
- 访问 [BNB 测试网水龙头](https://testnet.bnbchain.org/faucet-smart)
- 连接钱包并申请测试网 BNB 代币
- 在 [BNB 测试网浏览器](https://testnet.bscscan.com/) 查看交易

**默认合约地址:**
- IDENTITY: `0xf04A7eEeB7f99631DD08D9C6418ED8f9a8A03292`
- REPUTATION: `0x50100029Ac4E6F42505F5773841c03bcfB60181F`
- VALIDATION: `0x8366684cCE2266aD632bfE78E784007848E05E3a`

### 跨链操作

使用 `chainId:agentId` 格式可以跨链操作代理:

```python
# 获取不同链上的代理
eth_agent = sdk.getAgent("11155111:123")  # Ethereum Sepolia
base_agent = sdk.getAgent("84532:456")    # Base Sepolia
bnb_agent = sdk.getAgent("97:789")        # BNB 测试网

# 在多条链上搜索
results = sdk.searchAgents(
    name="AI",
    chains=[11155111, 84532, 97],  # 在 Ethereum、Base 和 BNB 上搜索
    active=True
)

# 在所有链上搜索
results_all = sdk.searchAgents(
    name="AI",
    chains="all"  # 在所有支持的链上搜索
)
```

## ✨ 核心特性

### 🔧 双后端支持
- **IPFS**: 传统分布式存储，CID 寻址
- **Greenfield**: 新一代区块链存储，事务授权机制
- **无缝切换**: 通过环境变量一键切换后端
- **统一接口**: `ReputationStorage` 抽象接口

### 🚀 自动化工作流
- **CreateObject**: 自动在链上创建对象，获取事务哈希
- **PutObject**: 使用事务哈希上传数据到存储提供者
- **统一接口**: 一个 `put()` 调用完成整个流程

### 🧪 完整测试覆盖
- **单元测试**: 120+ 测试用例，覆盖率 95%
- **集成测试**: 8 个端到端场景，包括性能基准
- **中文输出**: 完整的中文错误信息和测试结果

## 📁 文档结构

```
docs/ref/agent0-py/
├── README_中文.md                 # 📋 中文总览
├── GREENFIELD_E2E_使用指南.md      # 🚀 详细 E2E 测试指南
├── GREENFIELD_E2E_快速使用指南.md    # ⚡ 5分钟快速开始
├── greenfield_integration_guide.md      # 📖 完整集成指南
├── greenfield_usage_examples.md        # 💡 代码示例和最佳实践
├── GREENFIELD_FAQ.md                   # ❓ 常见问题解答
├── storage_interfaces.py              # 🔌 存储接口抽象
├── ipfs_storage.py                  # 🌐 IPFS 实现
├── greenfield_storage.py             # ⛓️ Greenfield 实现
├── greenfield_cli.py                # 🔧 自动化 CreateObject 辅助
├── storage_factory.py                # 🏭️ 存储工厂
├── test_storage.py                  # 🧪 单元测试套件
├── test_greenfield_e2e_chinese.py # 🇨🇳 E2E 集成测试（中文）
└── run_greenfield_e2e.py             # 🎯 简化运行工具

配置文件/
├── .env.greenfield.example            # 📋 基础配置模板
├── .env.e2e.示例                    # 🚀 E2E 测试配置（英文）
└── .env.e2e.示例                  # 🎏 E2E 测试配置（中文）
```

## 🚀 快速开始

### 1. 环境配置
```bash
# 复制配置模板
cp .env.e2e.示例 .env

# 设置必需变量
nano .env
```

**必需配置**：
- `GREENFIELD_RPC_URL`: Greenfield RPC 端点
- `GREENFIELD_SP_HOST`: 存储提供者主机
- `GREENFIELD_BUCKET`: 存储桶名称
- `GREENFIELD_PRIVATE_KEY`: 私钥（不含 0x 前缀）

### 2. 运行 E2E 测试
```bash
# 使用 uv 运行（推荐）
uv run python run_greenfield_e2e.py all

# 或使用 python 运行
python run_greenfield_e2e.py all
```

### 3. 选择运行模式
```bash
uv run python run_greenfield_e2e.py small   # 小文本测试
uv run python run_greenfield_e2e.py json    # JSON 数据测试
uv run python run_greenfield_e2e.py binary  # 二进制数据测试
uv run python run_greenfield_e2e.py large    # 大数据性能测试
uv run python run_greenfield_e2e.py all     # 运行所有测试
```

## 🎯 测试覆盖

| 测试类型 | 文件 | 功能 | 覆盖内容 |
|---------|------|------|----------|-----------|
| 基础存储 | `test_storage.py` | 接口、IPFS、Greenfield 实现 |
| 集成测试 | `test_greenfield_e2e_chinese.py` | 端到端、中文输出、性能基准 |

## 🔧 核心组件

### GreenfieldAutoUploader 类
```python
from agent0_sdk.core.greenfield_cli import create_e2e_helper

# 自动创建和上传
uploader = await create_e2e_helper(config)

# 一个调用完成整个流程
key = await uploader.put_auto(
    key="reputation/agent-123",
    data=json.dumps(reputation_data).encode('utf-8')
)

# 自动检索
retrieved = await uploader.get(key=key)
```

### Storage Factory 类
```python
from agent0_sdk.core.storage_factory import create_reputation_storage

# 根据环境变量自动选择后端
storage = create_reputation_storage()

# 支持两种后端
# IPFS: REPUTATION_BACKEND=ipfs
# Greenfield: REPUTATION_BACKEND=greenfield
```

## 📖 详细文档

- **集成指南**: `greenfield_integration_guide.md`
  - 完整的测试网设置步骤
  - CreateObject/PutObject 工作流程说明
  - 故障排除和性能优化建议
  - 主网迁移清单

- **使用示例**: `greenfield_usage_examples.md`
  - 生产环境代码模式
  - 错误处理和重试最佳实践
  - 中文注释和说明

- **常见问题**: `GREENFIELD_FAQ.md`
  - 详细的流程解释和对比
  - 常见错误和解决方案

- **快速开始**: `GREENFIELD_QUICKSTART.md`
  - 5分钟快速上手指南
  - 环境配置模板

- **E2E 指南**: `GREENFIELD_E2E_使用指南.md`
  - 端到端测试完整说明
  - 性能基准和预期
  - 故障排除和调试技巧

## 🎊 技术优势

- **向后兼容**: 现有 IPFS 代码无需修改
- **渐进迁移**: 可以逐步从 IPFS 迁移到 Greenfield
- **生产就绪**: 包含完整的错误处理和监控
- **测试覆盖**: 单元和集成测试双重保障

## 🚀 开始使用

```bash
# 1. 克隆项目
git clone <repository-url>
cd agent0-py

# 2. 安装依赖
pip install agent0-sdk

# 3. 配置环境
cp .env.e2e.示例 .env

# 4. 运行测试
uv run python run_greenfield_e2e.py all
```

## 📞 支持和反馈

- **文档**: 完整的中文文档
- **测试**: 全面的测试套件
- **GitHub**: [项目地址](https://github.com/agent0lab/agent0-py)
- **Discord**: [BNB 链社区](https://discord.gg/bnbchain)

---

**立即体验完整的 BNB Greenfield 声誉存储解决方案！** 🎊
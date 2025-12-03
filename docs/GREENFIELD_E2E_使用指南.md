# BNB Greenfield 端到端测试指南

> 完整测试 Greenfield 存储工作流程

## 概述

本指南提供了运行全面的端到端（E2E）测试的说明，这些测试演示了完整的 Greenfield 存储工作流程：

1. **CreateObject**：在 BNB Greenfield 区块链上自动创建对象
2. **PutObject**：使用事务哈希将数据上传到存储提供者
3. **GetObject**：检索数据并验证完整性
4. **公开访问**：测试跨密钥检索以验证公开存储桶访问

## 快速开始

### 1. 前置条件

```bash
# 必需的 Python 包（使用 agent0-sdk 自动安装）
pip install web3>=6.0.0 eth-account>=0.9.0 aiohttp>=3.8.0

# 用于测试
pip install pytest>=7.0.0 pytest-asyncio>=0.21.0
```

### 2. 环境配置

创建 `.env` 文件或设置环境变量：

```bash
# 必需 - 测试网配置
GREENFIELD_RPC_URL=https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org
GREENFIELD_SP_HOST=gnfd-testnet-sp3.bnbchain.org
GREENFIELD_BUCKET=your-test-bucket
GREENFIELD_PRIVATE_KEY=your_private_key_without_0x_prefix

# 可选 - 测试配置
GREENFIELD_CHAIN_ID=5600  # 测试网（默认值，gnfd-cmd 需使用 greenfield_5600-1）
GREENFIELD_CLI_CHAIN_ID=greenfield_5600-1
GREENFIELD_TIMEOUT=60     # 请求超时时间（秒，默认值）
```

**获取测试资源：**

1. **测试网 BNB**：访问 https://gnfd-bsc-testnet-faucet.bnbchain.org/
2. **创建存储桶**：使用 https://dcellar.io/（测试网模式）
   - 存储桶名称：`your-test-bucket`
   - 可见性：设置为"公开读取"（用于测试）
3. **获取私钥**：从 MetaMask 导出（设置 → 安全与隐私 → 显示私钥）

### 3. 运行 E2E 测试

```bash
# 运行所有 E2E 测试
pytest tests/test_greenfield_e2e.py -v -m integration -s

# 运行特定测试
pytest tests/test_greenfield_e2e.py::TestGreenfieldE2E::test_create_and_upload_small_text -v -s -m integration

# 使用详细输出运行
pytest tests/test_greenfield_e2e.py -v -s --log-cli-level=DEBUG -m integration
```

## E2E 测试套件

### 测试覆盖

| 测试 # | 描述 | 数据类型 | 大小 | 验证内容 |
|---------|-------------|----------|------------------|------------------|
| 1 | 小文本上传下载 | UTF-8 文本 | 基础工作流和公开访问 |
| 2 | JSON 声誉数据 | 结构化 JSON | 实际使用模式 |
| 3 | 二进制数据完整性 | 所有字节值 (0x00-0xFF) | 二进制数据损坏处理 |
| 4 | 大数据性能 | 1MB 文件 | 较大载荷的性能 |
| 5 | 多对象工作流 | 3 个并发对象 | 事务哈希唯一性 |
| 7 | 错误处理 | 无效操作 | 正确错误处理 |
| 8 | 并发操作 | 5 个同时上传 | 负载下的性能 |

### 预期输出

```
🚀 E2E 测试配置：
  RPC URL: https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org
  SP 主机: gnfd-testnet-sp3.bnbchain.org
  存储桶: your-test-bucket
  链 ID: 5600
  超时: 60s

📝 测试 1: 小文本上传和下载
  键: e2e-test-small-1701234567890
  大小: 43 字节
  ⏳ 在区块链上创建对象...
  ✅ 对象创建成功: 0x1234567890abcdef1234567890abcdef1234567890abcdef
  ✅ 上传成功: e2e-test-small-1701234567890
  ✅ 检索成功: 43 字节
  ✅ 公开访问验证
通过

📊 测试 2: JSON 声誉数据
  ✅ JSON 结构验证
  代理 ID: test-agent-123
  声誉分数: 95
通过

...
✅ 所有 8 个 E2E 测试成功完成！
```

## 测试数据

### 测试 1: 小文本
```python
TEST_DATA_EXAMPLES["small_text"] = b"你好，Greenfield！这是一个 E2E 测试消息。"
```

### 测试 2: JSON 声誉数据
```python
TEST_DATA_EXAMPLES["json_data"] = json.dumps({
    "agent_id": "test-agent-123",
    "reputation": {
        "score": 95,
        "reviews": [
            {"rating": 5, "comment": "出色的工作"},
            {"rating": 4, "comment": "良好表现"}
        ],
        "created_at": "2024-11-28T14:30:00Z"
    }
}).encode('utf-8')
```

### 测试 3: 二进制数据
```python
TEST_DATA_EXAMPLES["binary_data"] = bytes([i % 256 for i in range(256)])
# 包含所有可能的字节值: 0x00, 0x01, ..., 0xFF
```

### 测试 4: 大数据
```python
TEST_DATA_EXAMPLES["large_data"] = b"X" * (100 * 1024)  # 100KB
```

## 架构

### E2E 工作流程图

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   测试运行器   │ →  │自动上传助手     │ →  │ Greenfield 区块链│ →  │  存储提供者     │
│               │    │                   │    │  CreateObject   │    │  PutObject     │
│- 生成       │    │- 构造事务      │    │- 返回        │    │- 验证        │
│  测试数据    │    │- 签名交易       │    │- 事务哈希     │    │- 事务哈希     │
│- 调用       │    │- 发送交易       │    │               │    │               │
│  上传        │    │- 等待确认       │    │               │    │               │
│- 验证        │    │               │    │               │    │               │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

### 组件

1. **TestGreenfieldE2E**：主测试运行器
   - 编排测试场景
   - 验证数据完整性
   - 测量性能
   - 测试错误处理

2. **GreenfieldCreateObjectHelper**：区块链操作
   - 在 Greenfield 链上创建对象
   - 处理交易签名
   - 管理燃气估算
   - 提供事务哈希

3. **GreenfieldAutoUploader**：完整工作流
   - 结合 CreateObject + PutObject
   - 自动处理授权
   - 提供统一的 put/get 接口
   - 管理 HTTP 会话

### 与基础 SDK 的关键差异

| 功能 | 基础 SDK | E2E 自动上传器 |
|----------|-------------|-------------------|
| **CreateObject** | 手动（外部） | 自动 |
| **工作流** | 2 步骤（手动） | 1 步骤（自动） |
| **燃气处理** | 不可用 | 自动估算 |
| **错误处理** | 基础 | 增强 |

## 性能基准

### 测试 4 结果（1MB 上传）

| 指标 | 预期范围 | 含义 |
|--------|----------------|-------|
| **上传时间** | 10-60 秒 | 网络延迟 + 处理 |
| **下载时间** | 1-10 秒 | 存储提供者速度 |
| **上传速度** | 5-100 KB/s | 总体吞吐量 |
| **下载速度** | 50-500 KB/s | 检索性能 |

### 性能因素

- **网络**：测试网拥堵会影响时间
- **SP 位置**：到存储提供者的距离
- **对象大小**：较大对象可能需要更长时间
- **燃气价格**：燃气价格更高 = 交易更慢

## 故障排除

### 常见问题

#### "交易失败"错误
**原因**：测试网 BNB 不足或网络问题
**解决方案**：
1. 检查余额：https://greenfieldscan.com/address/YOUR_WALLET
2. 获取更多测试网 BNB：https://gnfd-bsc-testnet-faucet.bnbchain.org/
3. 在非高峰时段重试

#### "对象未找到"错误
**原因**：上传成功但对象尚未传播
**解决方案**：
1. 上传后等待 5-10 秒
2. 在 DCellar 中验证对象存在
3. 检查 SP 状态：https://greenfieldscan.com/

#### "燃气估算失败"警告
**原因**：网络拥堵或参数无效
**解决方案**：
1. 首先测试较小对象
2. 检查存储桶存在且可访问
3. 尝试不同的 SP 端点

#### "签名验证失败"错误
**原因**：CreateObject 和 PutObject 签名不匹配
**解决方案**：
1. 验证私钥正确
2. 检查链 ID 是否与存储桶网络匹配
3. 确保交易在上传前已确认

### 调试模式

启用详细日志记录：

```bash
# 使用调试日志运行
pytest tests/test_greenfield_e2e.py -v -s --log-cli-level=DEBUG -m integration

# 或在代码中启用
import logging
logging.basicConfig(level=logging.DEBUG)
```

**调试输出显示**：
- 事务构造详情
- 授权头生成
- HTTP 请求/响应详情
- 燃气估算结果

### 清理

测试后清理创建的对象：

```python
# 手动清理
from agent0_sdk.core.greenfield_cli import create_e2e_helper

async def cleanup():
    uploader = await create_e2e_helper(config)

    # 要清理的对象列表（来自测试输出）
    objects_to_clean = [
        "e2e-test-small-...",
        "e2e-test-json-...",
        "e2e-test-binary-...",
        # ... 添加来自测试输出的实际对象键
    ]

    for obj_key in objects_to_clean:
        try:
            await uploader.delete(obj_key)  # 注意：需要实现删除
            print(f"清理成功: {obj_key}")
        except Exception as e:
            print(f"清理失败: {obj_key}: {e}")

    await uploader.close()
```

## 生产环境考虑

### 从 E2E 到生产环境

1. **规模测试**：增加对象大小以匹配生产数据
2. **性能**：使用实际载荷（100KB-10MB）进行测量
3. **并发性**：测试 10+ 个同时上传
4. **监控**：添加指标收集和警报
5. **错误恢复**：实现带指数退避的重试逻辑

### 生产环境工作流

```python
# 生产环境使用（未来增强）
from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

# 对于生产环境，你仍需要管理事务哈希
storage = GreenfieldReputationStorage(
    sp_host="gnfd-sp1.bnbchain.org",  # 主网
    bucket="production-bucket",
    private_key="production_private_key",
    # 来自你的 CreateObject 批处理
)

# 选项 1：预创建事务哈希

def upload_with_auto_create(key: str, data: bytes) -> str:

# 选项 2：按需创建
async def upload_with_auto_create(key: str, data: bytes) -> str:
```

### 成本估算

对于生产环境部署，估算成本：

| 操作 | 成本组件 | 估算 |
|-----------|-----------------|------------|
| **CreateObject** | 燃气费 | 根据网络拥堵而变化 |
| **PutObject** | 存储费 | 每月每 GB $0.0023 |
| **GetObject** | 带宽费 | 每下载 GB $0.0001 |
| **维护** | SP 维护 | 包含在存储费中 |

**总计**：约每 GB 存储数据 $0.0023 + 数据传输费用

## 下一步

### 对于开发者

1. **运行 E2E 测试**：
   ```bash
   pytest tests/test_greenfield_e2e.py -v -s -m integration
   ```

2. **检查性能**：
   - 监控上传/下载速度
   - 检查错误率
   - 验证数据完整性

3. **使用你的数据测试**：
   - 用你的实际声誉数据替换测试数据
   - 验证 JSON 结构兼容性
   - 测试现实文件大小

### 对于运维

1. **监控测试结果**：
   - 跟踪成功/失败率
   - 测量时间指标
   - 记录任何网络特定问题

2. **规划生产部署**：
   - 检查性能基准
   - 估算预期用量的存储成本
   - 设置监控和警报

3. **准备主网迁移**：
   - 创建主网存储桶
   - 获取主网 BNB 用于 CreateObject 操作
   - 更新主网端点的配置

## 相关文档

- **集成指南**：[greenfield_integration_guide.md](greenfield_integration_guide.md) - 完整设置
- **使用示例**：[greenfield_usage_examples.md](greenfield_usage_examples.md) - 代码模式
- **快速开始**：[GREENFIELD_QUICKSTART.md](GREENFIELD_QUICKSTART.md) - 5分钟设置
- **架构**：[20251128_1340_bnb_greenfield_reputation.plan.md](20251128_1340_bnb_greenfield_reputation.plan.md) - 技术设计

## 支持

- **Greenfield 文档**：https://docs.bnbchain.org/bnb-greenfield/
- **测试网水龙头**：https://gnfd-bsc-testnet-faucet.bnbchain.org/
- **DCellar**：https://dcellar.io/
- **浏览器**：https://greenfieldscan.com/
- **BNB 链 Discord**：https://discord.gg/bnbchain

---

**准备好进行完整的 Greenfield 工作流程测试！** 🚀

E2E 测试提供以下保证：
- ✅ CreateObject → PutObject 工作流正常运行
- ✅ 上传/下载过程中保持数据完整性
- ✅ 事务哈希正确生成和使用
- ✅ 公开访问按预期运行
- ✅ 错误处理健壮
- ✅ 性能满足预期
- ✅ 并发操作稳定运行

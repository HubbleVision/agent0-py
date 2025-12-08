# BNB Greenfield 集成测试指南

本指南提供有关设置和运行 BNB Greenfield 测试网集成测试的分步说明。

## 目录
- [先决条件](#先决条件)
- [测试网设置](#测试网设置)
- [创建测试桶](#创建测试桶)
- [获取交易哈希](#获取交易哈希)
- [环境配置](#环境配置)
- [运行集成测试](#运行集成测试)
- [公共读取设置](#公共读取设置)
- [故障排除](#故障排除)

## 先决条件

### 1. 安装必需的依赖项

```bash
# 核心依赖
pip install eth-utils>=2.0.0 eth-account>=0.9.0 requests>=2.31.0

# 测试依赖
pip install pytest>=7.0.0
```

### 2. 获取测试网 BNB

您需要测试网 BNB 来支付存储操作：

1. 创建或使用现有 EVM 钱包（MetaMask 等）
2. 获取您的钱包地址（0x...）
3. 访问 BNB Greenfield 测试网水龙头：
   - 官方水龙头：https://gnfd-bsc-testnet-faucet.bnbchain.org/
   - 文档：https://docs.bnbchain.org/bnb-greenfield/getting-started/get-test-bnb/
4. 请求测试网 BNB（通常每天可用）

### 3. 导出您的私钥

⚠️ **安全警告**：仅使用测试网密钥，切勿使用主网密钥！

从 MetaMask 或您的钱包：
1. 导出私钥（设置 → 安全与隐私 → 显示私钥）
2. 复制密钥（应该是 64 个字符的十六进制字符串）
3. 安全存储在您的 `.env` 文件中（参见 [环境配置](#环境配置)）

## 测试网设置

### 网络信息

**BNB Greenfield 测试网：**
- 链 ID：`5600`（Greenfield 测试网）
- RPC 端点：`https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org`
- 存储提供商（SP）端点：
  - 主要：`gnfd-testnet-sp1.bnbchain.org`
  - 备选：`gnfd-testnet-sp2.bnbchain.org`，`gnfd-testnet-sp3.bnbchain.org`
- 浏览器：https://greenfieldscan.com/（测试网模式）

## 创建测试桶

您可以使用官方 Greenfield DCellar 网页应用或 CLI 工具创建桶。

### 选项 A：使用 DCellar 网页应用（推荐用于测试）

1. 访问 DCellar 测试网：https://dcellar.io/（选择测试网）
2. 连接您的钱包（带有测试网 BNB 的 MetaMask）
3. 点击"创建桶"
4. 配置：
   - **桶名称**：选择一个唯一名称（例如，`hubble-reputation-test`）
   - **主要 SP**：选择一个存储提供商（例如，`SP1`）
   - **可见性**：设置为"公共读取"，如果您想测试公共访问
   - **支付账户**：您连接的钱包
5. 确认交易并等待确认
6. 记下您的桶名称

### 选项 B：使用 Greenfield CLI

```bash
# 安装 Greenfield CLI
# 遵循：https://docs.bnbchain.org/bnb-greenfield/for-developers/get-started-dev/

# 创建桶
gnfd-cli bucket create gnfd://hubble-reputation-test \
  --primarySP=gnfd-testnet-sp1.bnbchain.org \
  --visibility=public-read
```

## 获取交易哈希

### 理解 Greenfield 的两步上传过程

⚠️ **重要**：Greenfield 使用独特的两步过程来上传数据：

**步骤 1：CreateObject（链上）**
- 在 Greenfield 区块链上创建对象元数据
- 返回一个**交易哈希**（txn hash）
- 此步骤验证权限并预留存储空间

**步骤 2：PutObject（链下）**
- 将实际数据上传到存储提供商
- **必须在请求头中包含**第 1 步的 txn hash
- SP 在接受数据之前在链上验证 txn hash

**为什么这样设计？**
- ✅ 防止垃圾信息：只有授权上传（通过链上交易证明）
- ✅ 将元数据（链上）与数据（链下）分离
- ✅ 确保链和存储之间的一致性

**与其他系统的比较：**
- **IPFS**：上传数据 → 获取 CID
- **S3**：上传数据 → 获取确认
- **Greenfield**：CreateObject → 获取 txn hash → 使用 txn hash 上传

### 如何获取交易哈希

要将对象上传到 Greenfield，您需要首先在链上创建对象（步骤 1）并获取交易哈希以在 PutObject（步骤 2）中使用。

### 方法 1：使用 Python 脚本

将此脚本保存为 `create_object.py`：

```python
#!/usr/bin/env python3
"""
在 Greenfield 测试网创建对象并获取交易哈希。
"""

import os
from web3 import Web3

# 配置
GREENFIELD_RPC = "https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org"
PRIVATE_KEY = os.getenv("GREENFIELD_PRIVATE_KEY")  # 不带 0x 前缀
BUCKET_NAME = "hubble-reputation-test"
OBJECT_NAME = "test-object-1"

# 连接到 Greenfield
w3 = Web3(Web3.HTTPProvider(GREENFIELD_RPC))

# 获取账户
account = w3.eth.account.from_key(PRIVATE_KEY)
print(f"账户：{account.address}")

# 准备 CreateObject 交易
# 注意：这是一个简化示例。在生产中，您需要使用
# Greenfield SDK 或根据 Greenfield 协议构建正确的交易。

# 目前，您可以使用 DCellar 网页应用创建对象并获取 tx 哈希

print(f"\n获取交易哈希：")
print(f"1. 访问 https://dcellar.io/（测试网）")
print(f"2. 导航到您的桶：{BUCKET_NAME}")
print(f"3. 点击'上传'并选择文件（或创建空对象）")
print(f"4. 确认交易")
print(f"5. 从 MetaMask 或浏览器复制交易哈希")
```

运行：
```bash
export GREENFIELD_PRIVATE_KEY=your_private_key_without_0x
python create_object.py
```

### 方法 2：使用 DCellar 网页应用（更简单）

1. 访问 https://dcellar.io/（测试网模式）
2. 连接您的钱包
3. 导航到您的桶
4. 点击"上传"或"创建文件夹"
5. 上传小测试文件或创建空对象
6. 交易确认后，找到交易哈希：
   - 检查 MetaMask 活动/历史记录
   - 或访问 https://greenfieldscan.com/ 并搜索您的钱包地址
7. 复制交易哈希（0x...）

### 交易哈希的重要注意事项


交易哈希**不是**上传数据的结果。相反：

**要点：**
- **工作流程**：
  ```
  ```

**当前 SDK 限制：**
- 用于生产：需要在代码中实现 CreateObject（未来增强功能）

**未来增强功能：**
未来，SDK 应在 PutObject 之前自动调用 CreateObject：
```python
# 未来的理想用法（尚未实现）
key = storage.put(key="file", data=b"data")
```

## 环境配置

在您的项目根目录创建 `.env` 文件（或导出这些作为环境变量）：

```bash
# 所有测试都需要
GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
GREENFIELD_BUCKET=hubble-reputation-test
GREENFIELD_PRIVATE_KEY=your_private_key_here  # 不带 0x 前缀

# PUT 操作需要（参见"获取交易哈希"）

# 可选：故障转移测试的备用 SP 主机
GREENFIELD_SP_HOST_ALT=gnfd-testnet-sp2.bnbchain.org


# 可选：为公共读取测试预创建的公共对象键
GREENFIELD_PUBLIC_TEST_OBJECT=public-test-object-key

# 可选：自定义超时（默认：30 秒）
GREENFIELD_TIMEOUT=60
```

### 安全最佳实践

1. **切勿将 `.env` 提交到版本控制**
   - 将 `.env` 添加到 `.gitignore`
   - 使用 `.env.example` 作为模板

2. **仅使用测试网密钥**
   - 创建专用测试网钱包
   - 切勿使用主网私钥

3. **定期轮换密钥**
   - 定期生成新的测试网密钥
   - 使旧密钥失效

## 运行集成测试

### 运行所有集成测试

```bash
# 运行所有集成测试
pytest tests/test_greenfield_integration.py -v -m integration

# 以详细输出运行
pytest tests/test_greenfield_integration.py -v -s -m integration
```

### 运行特定测试类

```bash
# 仅运行基本集成测试
pytest tests/test_greenfield_integration.py::TestGreenfieldIntegration -v -m integration

# 仅运行公共访问测试
pytest tests/test_greenfield_integration.py::TestGreenfieldPublicAccess -v -m integration

# 仅运行工厂测试
pytest tests/test_greenfield_integration.py::TestGreenfieldStorageFactory -v -m integration
```

### 运行特定测试

```bash
# 测试 PUT/GET 循环
pytest tests/test_greenfield_integration.py::TestGreenfieldIntegration::test_put_and_get_roundtrip -v -m integration

# 测试公共读取
pytest tests/test_greenfield_integration.py::TestGreenfieldPublicAccess::test_get_public_object_without_auth -v -m integration
```

### 跳过集成测试

```bash
# 运行除集成测试外的所有测试（用于本地开发）
pytest tests/ -v -m "not integration"
```

### 预期输出

成功测试输出应如下所示：

```
tests/test_greenfield_integration.py::TestGreenfieldIntegration::test_put_and_get_roundtrip
上传到 Greenfield：key=integration-test-1701234567, size=42 字节
上传成功：integration-test-1701234567
从 Greenfield 检索：key=integration-test-1701234567
检索成功：42 字节匹配
PASSED

tests/test_greenfield_integration.py::TestGreenfieldPublicAccess::test_get_public_object_without_auth
尝试公共读取（无授权）：https://hubble-reputation-test.gnfd-testnet-sp1.bnbchain.org/public-test-object
公共读取成功：256 字节
这确认桶允许公共读取访问
PASSED
```

## 公共读取设置

要测试公共读取访问（无授权），您需要配置您的桶 ACL。

### 设置桶为公共读取

#### 使用 DCellar

1. 访问 https://dcellar.io/（测试网）
2. 导航到您的桶
3. 点击"设置"或"权限"
4. 将"可见性"设置为"公共读取"
5. 确认交易

#### 使用 CLI

```bash
gnfd-cli bucket update gnfd://hubble-reputation-test \
  --visibility=public-read
```

### 创建公共测试对象

1. 通过 DCellar 将测试文件上传到您的桶
2. 记下对象键（文件名）
3. 设置环境变量：
   ```bash
   export GREENFIELD_PUBLIC_TEST_OBJECT=my-test-file.txt
   ```
4. 运行公共读取测试：
   ```bash
   pytest tests/test_greenfield_integration.py::TestGreenfieldPublicAccess::test_get_public_object_without_auth -v -m integration
   ```

### 验证公共访问

使用 curl 手动测试：

```bash
# 应在无授权标头的情况下成功
curl -v https://hubble-reputation-test.gnfd-testnet-sp1.bnbchain.org/public-test-object

# 应返回 200 OK 和对象内容
```

## 故障排除

### 常见问题

#### 1. PUT 上的"403 禁止"

**症状**：上传失败并显示 403 错误

**可能原因**：
- 无效或过期的交易哈希
- 签名不匹配
- 权限不足

**解决方案**：
```bash
# 验证您的钱包是否有测试网 BNB
curl https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org/balance/{your_address}

# 遵循"获取交易哈希"部分

# 验证私钥与创建桶的钱包匹配
# 检查日志中的账户地址
```

#### 2. GET 上的"404 未找到"

**症状**：检索失败并显示 404 错误

**可能原因**：
- 对象不存在
- 错误的桶/对象键
- 对象尚未传播

**解决方案**：
```bash
# 在 DCellar 网页界面中验证对象是否存在

# 等待更长时间传播（在测试中增加睡眠时间）
time.sleep(5)  # 而不是 time.sleep(2)

# 检查对象键是否完全匹配（区分大小写）
```

#### 3. "测试跳过"消息

**症状**：所有集成测试都跳过

**原因**：缺少必需的环境变量

**解决方案**：
```bash
# 验证 .env 文件存在并已加载
cat .env | grep GREENFIELD

# 手动导出进行测试
export GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
export GREENFIELD_BUCKET=hubble-reputation-test
export GREENFIELD_PRIVATE_KEY=your_key

# 运行测试
pytest tests/test_greenfield_integration.py -v -m integration
```

#### 4. "连接超时"

**症状**：测试在 30-60 秒后超时

**可能原因**：
- 网络问题
- SP 端点关闭
- 防火墙阻止请求

**解决方案**：
```bash
# 尝试备用 SP 端点
export GREENFIELD_SP_HOST=gnfd-testnet-sp2.bnbchain.org

# 增加超时
export GREENFIELD_TIMEOUT=120

# 测试连接
curl -v https://gnfd-testnet-sp1.bnbchain.org/
```

#### 5. 签名验证失败

**症状**："无效签名"或"授权失败"

**可能原因**：
- 错误的标准请求格式
- 错误的签名密钥
- 时钟偏移（过期时间戳）

**解决方案**：
```bash
# 验证系统时钟是否正确
date

# 检查私钥格式（应为 64 个十六进制字符，不带 0x）
echo $GREENFIELD_PRIVATE_KEY | wc -c  # 应输出 65（64 + 换行符）

# 启用调试日志
export GREENFIELD_DEBUG=1
pytest tests/test_greenfield_integration.py::TestGreenfieldIntegration::test_put_and_get_roundtrip -v -s -m integration
```

### 获取帮助

如果遇到此处未涵盖的问题：

1. **检查 Greenfield 文档**：
   - https://docs.bnbchain.org/bnb-greenfield/
   - https://github.com/bnb-chain/greenfield-storage-provider/blob/master/docs/

2. **使用 DCellar 验证**：
   - 尝试通过 DCellar 网页应用执行相同操作
   - 如果 DCellar 工作但 SDK 不工作，请比较请求格式

3. **启用调试日志**：
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

4. **检查 Greenfield 状态**：
   - https://greenfieldscan.com/（测试网模式）
   - 验证 SP 端点是否在线

5. **社区支持**：
   - BNB Chain Discord：https://discord.gg/bnbchain
   - GitHub Issues：https://github.com/bnb-chain/greenfield

## 主网迁移

从测试网迁移到主网时：

### 配置更改

```bash
# 主网配置
GREENFIELD_SP_HOST=gnfd-sp1.bnbchain.org  # 移除 'testnet'
GREENFIELD_BUCKET=hubble-reputation-prod  # 新生产桶
GREENFIELD_PRIVATE_KEY=production_key_here  # 专用主网密钥

# 主网需要真实 BNB 用于存储费用
# 估算费用：https://docs.bnbchain.org/bnb-greenfield/core-concept/billing-payment/
```

### 主网上线前检查清单

- [ ] 在测试网上成功测试所有操作
- [ ] 验证签名生成是否正确
- [ ] 用真实数据大小测试
- [ ] 估算预期使用的存储费用
- [ ] 为运行设置监控
- [ ] 创建带有生产 BNB 的专用主网钱包
- [ ] 用适当的 ACL（公共/私有）配置桶
- [ ] 设置备份/冗余策略
- [ ] 记录主网部署程序
- [ ] 计划回滚策略

### 主网存储费用

Greenfield 收费项目：
- **存储**：每月每 GB
- **带宽**：每 GB 下载
- **交易费用**：链上操作的 gas 费用

在以下位置估算费用：https://docs.bnbchain.org/bnb-greenfield/core-concept/billing-payment/

## 附录：快速参考

### 环境变量摘要

| 变量 | 必需 | 描述 | 示例 |
|----------|----------|-------------|---------|
| `GREENFIELD_SP_HOST` | 是 | 存储提供商端点 | `gnfd-testnet-sp1.bnbchain.org` |
| `GREENFIELD_BUCKET` | 是 | 桶名称 | `hubble-reputation-test` |
| `GREENFIELD_PRIVATE_KEY` | 是 | 钱包私钥（无 0x） | `abc123...` |
| `GREENFIELD_PUBLIC_TEST_OBJECT` | 对于公共测试 | 公共对象键 | `test-file.txt` |
| `GREENFIELD_TIMEOUT` | 可选 | 请求超时（秒） | `60` |

### 有用链接

- **测试网水龙头**：https://gnfd-bsc-testnet-faucet.bnbchain.org/
- **DCellar 应用**：https://dcellar.io/
- **浏览器**：https://greenfieldscan.com/
- **文档**：https://docs.bnbchain.org/bnb-greenfield/
- **SP API 文档**：https://github.com/bnb-chain/greenfield-storage-provider/blob/master/docs/storage-provider-rest-api/

### 测试命令速查表

```bash
# 运行所有集成测试
pytest tests/test_greenfield_integration.py -v -m integration

# 使用输出运行单个测试
pytest tests/test_greenfield_integration.py::TestGreenfieldIntegration::test_put_and_get_roundtrip -v -s -m integration

# 跳过集成测试
pytest tests/ -v -m "not integration"

# 使用调试日志运行
pytest tests/test_greenfield_integration.py -v -s --log-cli-level=DEBUG -m integration
```

## 相关文档

- **❓ FAQ**：[GREENFIELD_FAQ.md](GREENFIELD_FAQ.md) - 常见问题，特别是关于交易哈希工作流程
- **⚡ 快速入门**：[GREENFIELD_QUICKSTART.md](GREENFIELD_QUICKSTART.md) - 5 分钟设置指南
- **💡 使用示例**：[greenfield_usage_examples.md](greenfield_usage_examples.md) - 代码模式和最佳实践
- **📋 架构**：[20251128_1340_bnb_greenfield_reuptation.plan.md](20251128_1340_bnb_greenfield_reuptation.plan.md) - 技术设计
- **✅ 第四阶段摘要**：[PHASE4_COMPLETION_SUMMARY.md](PHASE4_COMPLETION_SUMMARY.md) - 集成测试完成
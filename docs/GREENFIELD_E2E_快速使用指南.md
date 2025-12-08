# BNB Greenfield E2E 测试快速使用指南

> 5分钟完成完整的 Greenfield 存储端到端测试

## 🎯 开始使用

### 1. 快速配置

创建 `.env` 文件：

```bash
# 复制配置模板
cp .env.e2e.示例 .env

# 编辑配置（最少需要前4个配置）
nano .env
```

**必需配置**：
```bash
GREENFIELD_BUCKET=hubble-reputation-test
GREENFIELD_PRIVATE_KEY=your_private_key_here
```

**可选配置**：
```bash
GREENFIELD_RPC_URL=https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org
GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
GREENFIELD_CHAIN_ID=5600
GREENFIELD_TIMEOUT=60
```

### 2. 获取测试资源

1. **测试网 BNB**：
   - 访问：https://gnfd-bsc-testnet-faucet.bnbchain.org/
   - 连接钱包，请求测试网 BNB

2. **创建测试存储桶**：
   - 访问：https://dcellar.io/
   - 选择测试网模式
   - 创建存储桶：`hubble-reputation-test`
   - 设置主 SP：`SP1`
   - 可见性：`公开读取`

3. **导出私钥**：
   - MetaMask：设置 → 安全与隐私 → 显示私钥
   - 复制私钥（移除 0x 前缀）

4. **验证配置**：
   - 确保存储桶名称匹配
   - 确保钱包有测试网 BNB

### 3. 运行测试

**简单运行**：
```bash
# 运行单个测试
uv run python run_greenfield_e2e.py small

# 运行所有测试
uv run python run_greenfield_e2e.py all

# 运行特定测试
uv run python run_greenfield_e2e.py json
uv run python run_greenfield_e2e.py binary
uv run python run_greenfield_e2e.py large
```

## 📋 测试覆盖

### 8 个完整测试

| 测试 | 功能 | 数据类型 | 运行命令 | 验证内容 |
|------|------|----------|-----------|-----------|------------------|
| **小文本** | 基础工作流 | `uv run python run_greenfield_e2e.py small` | 文本完整性、公开访问 |
| **JSON数据** | 实际使用模式 | `uv run python run_greenfield_e2e.py json` | JSON 结构、嵌套对象 |
| **二进制** | 数据完整性 | `uv run python run_greenfield_e2e.py binary` | 所有字节值、无损传输 |
| **大数据** | 性能基准 | `uv run python run_greenfield_e2e.py large` | 1KB 传输、速度测量 |
| **多对象** | 并发工作流 | `uv run python run_greenfield_e2e.py multi` | 3 个并发对象、唯一密钥 |
| **错误处理** | 异常处理 | `uv run python run_greenfield_e2e.py error` | 不存在对象、无效输入 |

## 🔍 预期输出

```
🌟 BNB Greenfield E2E 测试工具
============================================================

🔍 检查环境配置...
✅ 环境配置检查通过
  - 存储桶: hubble-reputation-test
  - SP 主机: gnfd-testnet-sp1.bnbchain.org
  - 链 ID: 5600

选择运行模式：
  python run_greenfield_e2e.py small   - 运行小文本测试
  python run_greenfield_e2e.py json     - 运行 JSON 数据测试
  python run_greenfield_e2e.py binary  - 运行二进制数据测试
  python run_greenfield_e2e.py large     - 运行大数据性能测试
  python run_greenfield_e2e.py all       - 运行所有测试
  python run_greenfield_e2e.py error    - 运行错误处理测试

```

## 📊 完整工作流程演示

### 自动化 CreateObject → PutObject 流程

```python
# 1. 在区块链上创建对象
print("⏳ 在区块链上创建对象...")

# 2. 获取事务哈希

# 3. 使用事务哈希上传数据
print("✅ 对象创建成功，开始上传...")

# 4. 上传到存储提供者

print(f"✅ 上传完成，密钥: {response}")
```

### 性能测量

```
📦 大数据性能测试
对象大小: 1024 字节 (1.0 KB)
上传时间: 15.3 秒
上传速度: 66.8 KB/s
下载时间: 2.1 秒
下载速度: 487.6 KB/s
总体性能: 优秀 ✅
```

## 🎯 关键优势

### 自动化工作流
- ✅ **一步操作**：`put_auto()` 自动完成 CreateObject + PutObject
- ✅ **错误处理**：完整的异常捕获和重试
- ✅ **性能优化**：连接池、超时管理

### 实际应用场景
```python
# 在你的应用中使用
from agent0_sdk.core.greenfield_cli import create_e2e_helper

async def store_reputation(agent_id: str, reputation_data: dict):
    """存储声誉数据到 Greenfield"""
    config = {
        "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
        "GREENFIELD_BUCKET": "your-production-bucket",
        "GREENFIELD_PRIVATE_KEY": "your_private_key"
    }

    uploader = await create_e2e_helper(config)

    key = f"reputation/{agent_id}"
    await uploader.put_auto(
        key=key,
        data=json.dumps(reputation_data).encode('utf-8')
    )

    return key

# 获取声誉数据
async def get_reputation(agent_id: str):
    """从 Greenfield 获取声誉数据"""
    config = {
        "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
        "GREENFIELD_BUCKET": "your-production-bucket",
        "GREENFIELD_PRIVATE_KEY": "your_private_key"
    }

    uploader = await create_e2e_helper(config)

    try:
        key = f"reputation/{agent_id}"
        data = await uploader.get(key=key)
        return json.loads(data.decode('utf-8'))
    except Exception:
        return None
```

## 📚 相关文档

- **完整指南**：[GREENFIELD_E2E_使用指南.md](GREENFIELD_E2E_使用指南.md) - 详细说明
- **集成测试**：[test_greenfield_e2e.py](test_greenfield_e2e.py) - 完整测试套件
- **基础配置**：[.env.e2e.示例](.env.e2e.示例) - 配置模板
- **原始测试**：[test_greenfield_e2e_chinese.py](test_greenfield_e2e_chinese.py) - 中文版本

## 🚀 开始测试

```bash
# 配置环境
cp .env.e2e.示例 .env

# 快速运行
uv run python run_greenfield_e2e.py small

# 完整测试
uv run python run_greenfield_e2e.py all
```

**准备好进行完整的 Greenfield 工作流测试！** 🎉
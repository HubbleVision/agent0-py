# BNB Greenfield E2E 测试运行指南

本指南详细说明如何运行 BNB Greenfield 存储的端到端测试。

## 📋 前置条件

### 1. 安装依赖

确保已安装所有必要的依赖：

```bash
# 在 agent0-py 目录中
uv sync
```

### 2. 获取测试网 BNB

1. 访问测试网水龙头：https://gnfd-bsc-faucet.bnbchain.org/
2. 输入你的钱包地址获取测试网 BNB
3. 确保钱包中有足够的 BNB 用于创建对象和支付存储费用

### 3. 创建 Bucket 和获取 Txn Hash

#### 方法 1：使用 DCellar (推荐)

1. 访问 DCellar：https://dcellar.bnbchain.org/
2. 连接你的钱包
3. 切换到 Greenfield 测试网
4. 创建一个 bucket（例如：`hubble-reputation-test`）
5. 在 bucket 中创建一个对象（可以是任意内容）
6. 获取该创建操作的 Transaction Hash

#### 方法 2：使用 CLI 工具

1. 安装 greenfield-cmd：
   ```bash
   # 安装 gfdcmd
   curl -LO https://github.com/bnb-chain/greenfield-cmd/releases/latest/download/gfdcmd-darwin-amd64.zip
   unzip gfdcmd-darwin-amd64.zip
   chmod +x gfdcmd
   ```

2. 配置并创建 bucket：
   ```bash
   # 配置私钥
   export PRIVATE_KEY=0xyour_private_key_here

   # 创建 bucket
   ./gfdcmd bucket create --bucket-name hubble-reputation-test

   ./gfdcmd object put --bucket-name hubble-reputation-test --object-name test-object --file /path/to/test/file
   ```

3. 从命令输出中复制 Transaction Hash

## ⚙️ 环境配置

更新 `.env` 文件中的 Greenfield 配置：

```bash
# 基本配置
GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
GREENFIELD_BUCKET=hubble-reputation-test
GREENFIELD_PRIVATE_KEY=0xyour_private_key_here

# 可选配置
GREENFIELD_CONTENT_TYPE=application/octet-stream
GREENFIELD_TIMEOUT=60
```

**重要提示**：
- `GREENFIELD_PRIVATE_KEY`: 必须与创建 bucket 和 object 的钱包私钥一致
- `GREENFIELD_BUCKET`: 必须是已存在的 bucket 名称

## 🚀 运行测试

### 基本用法

```bash
# 运行所有测试
uv run python tests/run_greenfield_e2e.py all

# 运行特定测试
uv run python tests/run_greenfield_e2e.py small    # 小文本测试
uv run python tests/run_greenfield_e2e.py json     # JSON 数据测试
uv run python tests/run_greenfield_e2e.py binary   # 二进制数据测试
uv run python tests/run_greenfield_e2e.py large    # 大数据性能测试
```

### 测试说明

1. **小文本测试**：测试中文文本的上传下载
2. **JSON 数据测试**：测试结构化 JSON 数据
3. **二进制数据测试**：测试二进制数据完整性
4. **大数据测试**：测试 1KB 数据的性能
5. **完整测试套件**：包含所有上述测试 + 错误处理 + 性能测试

## 📊 测试内容详解

### 1. 基础上传下载测试

- ✅ 测试不同类型数据的上传下载
- ✅ 验证数据完整性（SHA256 哈希比较）
- ✅ 计算上传下载速度
- ✅ 自动生成和手动指定对象键测试

### 2. 错误处理测试

- ✅ 测试获取不存在的对象（应该抛出异常）
- ✅ 验证异常类型和错误信息

### 3. 性能测试

- ✅ 测试不同大小数据的性能（小数据到 100KB）
- ✅ 计算上传下载速度
- ✅ 性能统计和总结

### 4. 大数据测试

- ✅ 测试 ~320KB 数据的上传下载
- ✅ 验证大数据的完整性

## 🔧 故障排查

### 常见错误及解决方案



**原因**：缺少有效的 Transaction Hash

**解决方案**：
- 确保已执行 CreateObject 操作并获取真实的 Transaction Hash
- 确认 Transaction Hash 格式正确（以 0x 开头）

#### 2. `403 Forbidden`

**错误**：HTTP 403 错误

**原因**：权限不足或签名问题

**解决方案**：
- 确认私钥与创建 bucket 的钱包一致
- 检查 bucket 的权限设置
- 确认 Transaction Hash 对应的 CreateObject 操作已成功

#### 3. `404 Not Found`

**错误**：HTTP 404 错误

**原因**：Bucket 或对象不存在

**解决方案**：
- 确认 bucket 名称正确且已存在
- 检查 SP 主机地址配置
- 确认网络设置（测试网 vs 主网）

#### 4. 网络超时

**错误**：`requests.exceptions.Timeout`

**原因**：网络连接问题

**解决方案**：
- 增加超时时间：`GREENFIELD_TIMEOUT=60`
- 检查网络连接
- 尝试不同的 SP 端点（gnfd-testnet-sp2.bnbchain.org 等）

#### 5. 私钥格式错误

**错误**：`ValueError: Invalid private key format`

**原因**：私钥格式不正确

**解决方案**：
- 确保私钥以 0x 开头
- 私钥应为 64 位十六进制字符
- 不要包含其他字符或空格

### 调试技巧

1. **启用详细日志**：
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **检查环境变量**：
   ```python
   import os
       print(f"{key}: {os.getenv(key)}")
   ```

3. **手动测试 API**：
   ```bash
   # 测试 SP 连接
   curl -I https://gnfd-testnet-sp1.bnbchain.org/
   ```

## 📈 成功标准

测试成功时应看到类似输出：

```
🎉 所有测试通过！Greenfield 存储工作正常。

📊 性能总结:
描述           大小       上传速度        下载速度
------------------------------------------------------------
小数据         11         1100.25        2200.50
1KB 数据       1024       10240.00       15360.00
10KB 数据      10240      51200.00       76800.00
100KB 数据     102400     204800.00      307200.00
```

## 📚 参考资源

- [BNB Greenfield 文档](https://docs.bnbchain.org/bnb-greenfield/)
- [Storage Provider API](https://github.com/bnb-chain/greenfield-storage-provider/tree/master/docs/storage-provider-rest-api)
- [DCellar 界面](https://dcellar.bnbchain.org/)
- [测试网水龙头](https://gnfd-bsc-faucet.bnbchain.org/)

## 💡 提示

1. **测试网费用**：Greenfield 测试网是免费的，但仍需要少量 BNB 作为 gas
2. **数据持久性**：测试网数据可能会被清理，不要存储重要数据
3. **性能差异**：测试网性能可能不如主网，这是正常现象
4. **批量测试**：避免短时间内运行大量测试，以免达到速率限制
# Etherscan v2 API Migration Guide

## Overview

本项目已迁移到 **Etherscan v2 API**,这是Etherscan在2024年推出的统一多链API服务。

## 主要变化

### 单一API Key支持多链

**旧方式 (v1)**:
- 每条链需要单独的API key
- BscScan API key (for BSC)
- BaseScan API key (for Base)
- Etherscan API key (for Ethereum)

**新方式 (v2)**:
- **一个Etherscan API key可以访问60+条链**
- 包括: Ethereum, BSC, Base, Arbitrum, Polygon, Avalanche等
- 通过 `chainid` 参数区分链

### API端点变化

**旧端点**:
```
https://api.bscscan.com/api
https://api-sepolia.basescan.org/api
https://api.etherscan.io/api
```

**新端点 (v2)**:
```
https://api.etherscan.io/v2/api?chainid=56     # BSC Mainnet
https://api.etherscan.io/v2/api?chainid=97     # BSC Testnet
https://api.etherscan.io/v2/api?chainid=84532  # Base Sepolia
https://api.etherscan.io/v2/api?chainid=1      # Ethereum Mainnet
```

## 本项目配置

### 环境变量

只需要一个API key:

```bash
# .env
ETHERSCAN_API_KEY=your_etherscan_api_key
```

获取API key:
1. 访问 https://etherscan.io/myapikey
2. 注册/登录Etherscan账户
3. 创建API key
4. 该key自动支持所有链

### Hardhat配置

```javascript
// hardhat.config.js
export default {
  etherscan: {
    // 单一API key
    apiKey: process.env.ETHERSCAN_API_KEY,

    // 自定义链配置
    customChains: [
      {
        network: "bnbTestnet",
        chainId: 97,
        urls: {
          apiURL: "https://api.etherscan.io/v2/api?chainid=97",
          browserURL: "https://testnet.bscscan.com"
        }
      },
      {
        network: "bnbMainnet",
        chainId: 56,
        urls: {
          apiURL: "https://api.etherscan.io/v2/api?chainid=56",
          browserURL: "https://bscscan.com"
        }
      },
      {
        network: "baseSepolia",
        chainId: 84532,
        urls: {
          apiURL: "https://api.etherscan.io/v2/api?chainid=84532",
          browserURL: "https://sepolia.basescan.org"
        }
      }
    ]
  }
}
```

## 支持的链

Etherscan v2 API支持60+条链,包括:

| Chain | Chain ID | Status |
|-------|----------|--------|
| Ethereum Mainnet | 1 | ✅ Available |
| Ethereum Sepolia | 11155111 | ✅ Available |
| BNB Smart Chain | 56 | ✅ Available |
| BNB Testnet | 97 | ✅ Available |
| Base | 8453 | ✅ Available |
| Base Sepolia | 84532 | ✅ Available |
| Polygon | 137 | ✅ Available |
| Arbitrum One | 42161 | ✅ Available |
| Optimism | 10 | ✅ Available |
| Avalanche | 43114 | ✅ Available |

完整列表: https://docs.etherscan.io/supported-chains

## 合约验证

### 自动验证

使用Hardhat插件自动验证:

```bash
# 单一命令验证任何链上的合约
npx hardhat verify --network bnbTestnet <CONTRACT_ADDRESS>
npx hardhat verify --network bnbMainnet <CONTRACT_ADDRESS>
npx hardhat verify --network baseSepolia <CONTRACT_ADDRESS>
```

### 批量验证

使用项目的验证脚本:

```bash
# 自动验证所有已部署的合约
npx hardhat run scripts/verify.js --network bnbTestnet
```

## 重要说明

### 免费层级限制

虽然v2 API统一了多链访问,但有些功能在免费层级有限制:

- ✅ **合约验证**: 所有链免费
- ✅ **合约ABI获取**: 所有链免费
- ✅ **合约源码获取**: 所有链免费
- ⚠️ **交易查询**: 部分链有限制
- ⚠️ **余额查询**: 部分链有限制

对于本项目的核心需求(合约部署和验证),免费层级完全够用。

### API限制

- 免费层级: 5 calls/second
- 需要更高限制可以升级到付费计划

## 迁移步骤

如果你的项目还在使用旧的BscScan API key:

1. **获取Etherscan API key**:
   ```bash
   # 访问 https://etherscan.io/myapikey
   ```

2. **更新 .env**:
   ```bash
   # 删除旧的
   # BSCSCAN_API_KEY=xxx
   # BASESCAN_API_KEY=xxx

   # 使用新的
   ETHERSCAN_API_KEY=your_etherscan_api_key
   ```

3. **测试验证**:
   ```bash
   npx hardhat verify --network bnbTestnet <ADDRESS>
   ```

## 好处

### 1. 简化配置
- 单一API key管理
- 减少环境变量
- 统一配置方式

### 2. 多链支持
- 一次配置,支持60+链
- 未来新链自动支持
- 无需更新配置

### 3. 一致的API
- 统一的endpoint格式
- 统一的响应格式
- 简化代码逻辑

### 4. 更好的文档
- 集中的文档
- 统一的示例
- 更新更及时

## 参考资料

- [Etherscan v2 API文档](https://docs.etherscan.io/etherscan-v2)
- [v2迁移指南](https://docs.etherscan.io/v2-migration)
- [支持的链列表](https://docs.etherscan.io/supported-chains)
- [获取API Key](https://etherscan.io/myapikey)

## 常见问题

### Q: 我还能用BscScan网站查看合约吗?

A: 可以! BscScan网站不变,只是API统一了。验证后的合约依然在 https://bscscan.com 或 https://testnet.bscscan.com 查看。

### Q: 旧的BscScan API key还能用吗?

A: 理论上可以,但不推荐。新的Etherscan v2 API提供更好的支持和功能。

### Q: API key会过期吗?

A: 不会自动过期,但建议定期更新以获得最新的功能支持。

### Q: 如何申请更高的rate limit?

A: 访问 https://etherscan.io/apis 升级到付费计划。对于大多数项目,免费层级足够。

### Q: v2 API支持所有v1的功能吗?

A: 是的,v2向后兼容,并增加了新功能。详见迁移文档。

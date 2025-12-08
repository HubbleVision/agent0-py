# BNB Chain Subgraph 部署指南

> **状态**: 可选优化项 - 当前 BNB 链使用链上调用，功能完全可用
>
> **建议时机**: Phase 4 或之后，当性能成为瓶颈时

## 📋 概述

本指南介绍如何为 BNB 链部署 The Graph Subgraph，以提升 agent0 SDK 的查询性能。

### 为什么需要 Subgraph？

| 特性 | 链上调用 (当前) | Subgraph |
|------|----------------|----------|
| **功能** | ✅ 完全可用 | ✅ 完全可用 |
| **搜索速度** | 1-3秒 | ~100ms |
| **查询速度** | ~500ms | ~50ms |
| **复杂查询** | 受限 | 支持 |
| **设置成本** | 免费 | $2,000-4,000 |
| **月度成本** | 免费 | $50-200 |

**结论**: Phase 2-5 无需 Subgraph 即可完成所有功能开发和测试。

## 🎯 The Graph 支持状态

- ✅ **BNB Mainnet (Chain ID 56)**: The Graph Network 官方支持
- ⚠️ **BNB Testnet (Chain ID 97)**: 需确认支持情况

检查最新支持列表: https://thegraph.com/docs/en/developing/supported-networks/

## 📁 Subgraph 项目结构

```
bnb-agent0-subgraph/
├── schema.graphql              # GraphQL 数据模型
├── subgraph.yaml               # 配置文件
├── src/
│   ├── identity-mapping.ts     # Identity Registry 事件处理
│   ├── reputation-mapping.ts   # Reputation Registry 事件处理
│   └── validation-mapping.ts   # Validation Registry 事件处理
├── abis/
│   ├── IdentityRegistry.json
│   ├── ReputationRegistry.json
│   └── ValidationRegistry.json
├── package.json
└── tsconfig.json
```

## 📝 步骤 1: 创建项目

### 1.1 安装工具

```bash
# 安装 Graph CLI
npm install -g @graphprotocol/graph-cli

# 验证安装
graph --version
```

### 1.2 初始化项目

```bash
# 创建项目目录
mkdir bnb-agent0-subgraph && cd bnb-agent0-subgraph

# 初始化 (或手动创建文件)
graph init --studio bnb-agent0

# 初始化 npm 项目
npm init -y
```

### 1.3 安装依赖

```bash
npm install --save-dev @graphprotocol/graph-cli @graphprotocol/graph-ts
```

## 📊 步骤 2: 定义数据模型

创建 `schema.graphql`:

```graphql
"""
Agent entity representing an ERC-8004 agent
"""
type Agent @entity {
  id: ID!                          # Format: chainId:tokenId (e.g., "97:1")
  tokenId: BigInt!                 # On-chain token ID
  chainId: BigInt!                 # Chain ID (97 for testnet, 56 for mainnet)
  owner: Bytes!                    # Owner wallet address
  tokenURI: String                 # IPFS or HTTP URI
  metadataUri: String              # Additional metadata URI
  active: Boolean!                 # Whether agent is active
  createdAt: BigInt!               # Creation timestamp
  updatedAt: BigInt!               # Last update timestamp

  # Relations
  feedbacks: [Feedback!]! @derivedFrom(field: "agent")
  validations: [Validation!]! @derivedFrom(field: "agent")
}

"""
Feedback entity for agent reputation
"""
type Feedback @entity {
  id: ID!                          # Format: txHash-logIndex
  agentId: String!                 # Reference to agent (chainId:tokenId)
  agent: Agent!                    # Agent relation
  clientAddress: Bytes!            # Address of feedback giver
  feedbackIndex: BigInt!           # Index of feedback (1-indexed)
  score: Int!                      # Score (0-100)
  tag1: Bytes!                     # First tag
  tag2: Bytes!                     # Second tag
  feedbackUri: String              # URI to feedback content
  feedbackHash: Bytes!             # Hash of feedback
  isRevoked: Boolean!              # Whether feedback is revoked
  createdAt: BigInt!               # Creation timestamp
  revokedAt: BigInt                # Revocation timestamp (if revoked)

  # Relations
  responses: [FeedbackResponse!]! @derivedFrom(field: "feedback")
}

"""
Response to feedback
"""
type FeedbackResponse @entity {
  id: ID!                          # Format: feedbackId-responderAddress-index
  feedback: Feedback!              # Parent feedback
  responderAddress: Bytes!         # Address of responder
  responseUri: String!             # URI to response content
  responseHash: Bytes!             # Hash of response
  createdAt: BigInt!               # Creation timestamp
}

"""
Validation request and response
"""
type Validation @entity {
  id: ID!                          # Format: requestHash (bytes32)
  requestHash: Bytes!              # Unique request hash
  validatorAddress: Bytes!         # Validator address
  agentId: String!                 # Reference to agent
  agent: Agent!                    # Agent relation
  response: Int!                   # Validation response (0 = pending)
  responseUri: String              # URI to response content
  responseHash: Bytes!             # Hash of response
  tag: Bytes!                      # Validation tag
  lastUpdate: BigInt!              # Last update timestamp
  createdAt: BigInt!               # Creation timestamp
}

"""
Global statistics (optional)
"""
type GlobalStats @entity {
  id: ID!                          # Always "global"
  totalAgents: BigInt!             # Total number of agents
  totalFeedbacks: BigInt!          # Total number of feedbacks
  totalValidations: BigInt!        # Total number of validations
  lastUpdated: BigInt!             # Last update timestamp
}
```

## ⚙️ 步骤 3: 配置 Subgraph

创建 `subgraph.yaml`:

```yaml
specVersion: 0.0.5
schema:
  file: ./schema.graphql
dataSources:
  # ==================== Identity Registry ====================
  - kind: ethereum/contract
    name: IdentityRegistry
    network: bsc                                    # BNB Mainnet (use 'chapel' for testnet if supported)
    source:
      address: "0xf04A7eEeB7f99631DD08D9C6418ED8f9a8A03292"  # BNB Testnet address
      abi: IdentityRegistry
      startBlock: 45123456                          # Replace with actual deployment block
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
        - Agent
        - GlobalStats
      abis:
        - name: IdentityRegistry
          file: ./abis/IdentityRegistry.json
      eventHandlers:
        - event: Registered(indexed uint256,string,indexed address)
          handler: handleRegistered
        - event: MetadataSet(indexed uint256,indexed string,string,bytes)
          handler: handleMetadataSet
        - event: UriUpdated(indexed uint256,string,indexed address)
          handler: handleUriUpdated
      file: ./src/identity-mapping.ts

  # ==================== Reputation Registry ====================
  - kind: ethereum/contract
    name: ReputationRegistry
    network: bsc
    source:
      address: "0x50100029Ac4E6F42505F5773841c03bcfB60181F"  # BNB Testnet address
      abi: ReputationRegistry
      startBlock: 45123456
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
        - Feedback
        - FeedbackResponse
        - Agent
        - GlobalStats
      abis:
        - name: ReputationRegistry
          file: ./abis/ReputationRegistry.json
      eventHandlers:
        - event: NewFeedback(indexed uint256,indexed address,uint8,indexed bytes32,bytes32,string,bytes32)
          handler: handleNewFeedback
        - event: FeedbackRevoked(indexed uint256,indexed address,indexed uint64)
          handler: handleFeedbackRevoked
        - event: ResponseAppended(indexed uint256,indexed address,uint64,indexed address,string,bytes32)
          handler: handleResponseAppended
      file: ./src/reputation-mapping.ts

  # ==================== Validation Registry ====================
  - kind: ethereum/contract
    name: ValidationRegistry
    network: bsc
    source:
      address: "0x8366684cCE2266aD632bfE78E784007848E05E3a"  # BNB Testnet address
      abi: ValidationRegistry
      startBlock: 45123456
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
        - Validation
        - Agent
        - GlobalStats
      abis:
        - name: ValidationRegistry
          file: ./abis/ValidationRegistry.json
      eventHandlers:
        - event: ValidationRequest(indexed address,indexed uint256,string,indexed bytes32)
          handler: handleValidationRequest
        - event: ValidationResponse(indexed address,indexed uint256,indexed bytes32,uint8,string,bytes32,bytes32)
          handler: handleValidationResponse
      file: ./src/validation-mapping.ts
```

## 💻 步骤 4: 实现事件处理

### 4.1 获取合约 ABI

从 Hardhat 编译产物复制 ABI:

```bash
# 从 onchain 项目复制 ABI
mkdir -p abis
cp ../onchain/artifacts/contracts/Agent8004Bundle.sol/IdentityRegistryUpgradeable.json abis/IdentityRegistry.json
cp ../onchain/artifacts/contracts/Agent8004Bundle.sol/ReputationRegistryUpgradeable.json abis/ReputationRegistry.json
cp ../onchain/artifacts/contracts/Agent8004Bundle.sol/ValidationRegistryUpgradeable.json abis/ValidationRegistry.json

# 或手动提取 ABI 部分到 abis/ 目录
```

### 4.2 创建 identity-mapping.ts

```typescript
import {
  Registered,
  MetadataSet,
  UriUpdated
} from "../generated/IdentityRegistry/IdentityRegistry"
import { Agent, GlobalStats } from "../generated/schema"
import { BigInt } from "@graphprotocol/graph-ts"

const CHAIN_ID = BigInt.fromI32(97)  // BNB Testnet (use 56 for mainnet)
const GLOBAL_STATS_ID = "global"

export function handleRegistered(event: Registered): void {
  let agentId = CHAIN_ID.toString() + ":" + event.params.agentId.toString()
  let agent = new Agent(agentId)

  agent.tokenId = event.params.agentId
  agent.chainId = CHAIN_ID
  agent.owner = event.params.owner
  agent.tokenURI = event.params.tokenURI
  agent.active = true
  agent.createdAt = event.block.timestamp
  agent.updatedAt = event.block.timestamp

  agent.save()

  // Update global stats
  let stats = GlobalStats.load(GLOBAL_STATS_ID)
  if (stats == null) {
    stats = new GlobalStats(GLOBAL_STATS_ID)
    stats.totalAgents = BigInt.fromI32(0)
    stats.totalFeedbacks = BigInt.fromI32(0)
    stats.totalValidations = BigInt.fromI32(0)
  }
  stats.totalAgents = stats.totalAgents.plus(BigInt.fromI32(1))
  stats.lastUpdated = event.block.timestamp
  stats.save()
}

export function handleMetadataSet(event: MetadataSet): void {
  let agentId = CHAIN_ID.toString() + ":" + event.params.agentId.toString()
  let agent = Agent.load(agentId)

  if (agent != null) {
    agent.updatedAt = event.block.timestamp
    agent.save()
  }
}

export function handleUriUpdated(event: UriUpdated): void {
  let agentId = CHAIN_ID.toString() + ":" + event.params.agentId.toString()
  let agent = Agent.load(agentId)

  if (agent != null) {
    agent.metadataUri = event.params.newUri
    agent.updatedAt = event.block.timestamp
    agent.save()
  }
}
```

### 4.3 创建 reputation-mapping.ts

```typescript
import {
  NewFeedback,
  FeedbackRevoked,
  ResponseAppended
} from "../generated/ReputationRegistry/ReputationRegistry"
import { Feedback, FeedbackResponse, Agent, GlobalStats } from "../generated/schema"
import { BigInt } from "@graphprotocol/graph-ts"

const CHAIN_ID = BigInt.fromI32(97)
const GLOBAL_STATS_ID = "global"

export function handleNewFeedback(event: NewFeedback): void {
  let feedbackId = event.transaction.hash.toHex() + "-" + event.logIndex.toString()
  let feedback = new Feedback(feedbackId)

  let agentId = CHAIN_ID.toString() + ":" + event.params.agentId.toString()

  feedback.agentId = agentId
  feedback.agent = agentId
  feedback.clientAddress = event.params.clientAddress
  feedback.feedbackIndex = BigInt.fromI32(0)  // Would need to track this
  feedback.score = event.params.score
  feedback.tag1 = event.params.tag1
  feedback.tag2 = event.params.tag2
  feedback.feedbackUri = event.params.feedbackUri
  feedback.feedbackHash = event.params.feedbackHash
  feedback.isRevoked = false
  feedback.createdAt = event.block.timestamp

  feedback.save()

  // Update global stats
  let stats = GlobalStats.load(GLOBAL_STATS_ID)
  if (stats != null) {
    stats.totalFeedbacks = stats.totalFeedbacks.plus(BigInt.fromI32(1))
    stats.lastUpdated = event.block.timestamp
    stats.save()
  }
}

export function handleFeedbackRevoked(event: FeedbackRevoked): void {
  // Find feedback by agent and client
  // Note: This requires querying, which is complex in mapping
  // Consider storing a mapping of agentId:clientAddress:index -> feedbackId
}

export function handleResponseAppended(event: ResponseAppended): void {
  // Create response entity
  let responseId = event.transaction.hash.toHex() + "-" + event.logIndex.toString()
  let response = new FeedbackResponse(responseId)

  // Link to feedback (would need proper lookup)
  response.responderAddress = event.params.responder
  response.responseUri = event.params.responseUri
  response.responseHash = event.params.responseHash
  response.createdAt = event.block.timestamp

  response.save()
}
```

### 4.4 创建 validation-mapping.ts

```typescript
import {
  ValidationRequest,
  ValidationResponse
} from "../generated/ValidationRegistry/ValidationRegistry"
import { Validation, Agent, GlobalStats } from "../generated/schema"
import { BigInt } from "@graphprotocol/graph-ts"

const CHAIN_ID = BigInt.fromI32(97)
const GLOBAL_STATS_ID = "global"

export function handleValidationRequest(event: ValidationRequest): void {
  let validation = new Validation(event.params.requestHash.toHex())

  let agentId = CHAIN_ID.toString() + ":" + event.params.agentId.toString()

  validation.requestHash = event.params.requestHash
  validation.validatorAddress = event.params.validatorAddress
  validation.agentId = agentId
  validation.agent = agentId
  validation.response = 0  // Pending
  validation.responseHash = event.params.requestHash  // Use request hash initially
  validation.tag = event.params.requestHash  // Placeholder
  validation.createdAt = event.block.timestamp
  validation.lastUpdate = event.block.timestamp

  validation.save()

  // Update global stats
  let stats = GlobalStats.load(GLOBAL_STATS_ID)
  if (stats != null) {
    stats.totalValidations = stats.totalValidations.plus(BigInt.fromI32(1))
    stats.lastUpdated = event.block.timestamp
    stats.save()
  }
}

export function handleValidationResponse(event: ValidationResponse): void {
  let validation = Validation.load(event.params.requestHash.toHex())

  if (validation != null) {
    validation.response = event.params.response
    validation.responseUri = event.params.responseUri
    validation.responseHash = event.params.responseHash
    validation.tag = event.params.tag
    validation.lastUpdate = event.block.timestamp
    validation.save()
  }
}
```

## 🔨 步骤 5: 构建

```bash
# 生成 TypeScript 类型
graph codegen

# 构建 Subgraph
graph build

# 检查编译产物
ls build/
```

## 🚀 步骤 6: 部署

### 选项 A: The Graph Studio (推荐)

```bash
# 1. 访问 https://thegraph.com/studio/
# 2. 创建新的 Subgraph "bnb-agent0"
# 3. 获取 Deploy Key

# 4. 认证
graph auth --studio YOUR_DEPLOY_KEY

# 5. 部署
graph deploy --studio bnb-agent0
```

### 选项 B: 自托管 Graph Node

参见计划文档中的 Docker Compose 配置。

## ✅ 步骤 7: 验证

```bash
# 测试 GraphQL 查询
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "{ agents(first: 5) { id tokenId owner } }"}' \
  https://api.studio.thegraph.com/query/YOUR_SUBGRAPH_ID/bnb-agent0/v0.0.1
```

## 📝 步骤 8: 更新 SDK

更新 `agent0_sdk/core/contracts.py`:

```python
DEFAULT_SUBGRAPH_URLS: Dict[int, str] = {
    # ...
    97: "https://gateway.thegraph.com/api/YOUR_API_KEY/subgraphs/id/YOUR_SUBGRAPH_ID",
    56: "https://gateway.thegraph.com/api/YOUR_API_KEY/subgraphs/id/YOUR_SUBGRAPH_ID",
}
```

## 💰 成本估算

- **The Graph Network**:
  - 初始策展: ~10,000 GRT (约 $2,000-4,000)
  - 月度查询费: $50-200 (取决于流量)

- **自托管**:
  - 服务器: $50-200/月
  - 维护: 技术人员时间

## 📚 参考资料

- [The Graph 官方文档](https://thegraph.com/docs/)
- [支持的网络列表](https://thegraph.com/docs/en/developing/supported-networks/)
- [AssemblyScript API](https://thegraph.com/docs/en/developing/assemblyscript-api/)
- [Graph Node GitHub](https://github.com/graphprotocol/graph-node)
- [BNB Chain 文档](https://docs.bnbchain.org/)

## ⚠️ 注意事项

1. **测试网支持**: 确认 The Graph 是否支持 BNB Testnet (Chapel)
2. **起始区块**: 使用合约实际部署的区块号
3. **网络名称**: 确认 `network` 字段的正确值 (`bsc` 或 `chapel`)
4. **ABI 版本**: 确保 ABI 与部署的合约版本匹配
5. **成本**: 策展需要 GRT tokens，测试网可能不需要

## 🎯 成功标准

- [ ] Subgraph 成功部署并同步
- [ ] GraphQL 查询返回正确数据
- [ ] SDK 查询速度提升 10x+
- [ ] 监控和告警已配置
- [ ] 文档已更新

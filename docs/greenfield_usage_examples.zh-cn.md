# BNB Greenfield 存储使用示例

本文档提供在 agent0 SDK 中使用 BNB Greenfield 存储的实用代码示例。

## 目录
- [基本用法](#基本用法)
- [配置](#配置)
- [存储操作](#存储操作)
- [错误处理](#错误处理)
- [高级用法](#高级用法)
- [生产注意事项](#生产注意事项)

## 重要：Greenfield 的两步上传过程

⚠️ **开始之前**：Greenfield 要求在上传数据**之前**提供交易哈希。

与 IPFS 或 S3 不同，您直接上传并获得 ID 返回，Greenfield 使用：

1. **CreateObject**（链上）→ 获取 `txn_hash`
2. **PutObject**（上传数据）→ 使用 `txn_hash` 进行授权

**当前 SDK 限制**：您必须在使用 `storage.put()` 之前通过外部方式获取 `txn_hash`（通过 DCellar/CLI）。

详细说明请参见[集成指南](greenfield_integration_guide.md#understanding-greenfields-two-step-upload-process)。

## 基本用法

### 使用存储工厂（推荐）

存储工厂提供统一接口，可与 IPFS 和 Greenfield 配合使用：

```python
from agent0_sdk.core.storage_factory import create_reputation_storage

# 创建存储实例（后端由配置确定）
storage = create_reputation_storage()

# 上传数据
data = b"XYZ 代理的声誉数据"
object_key = storage.put(key="agent-xyz-reputation", data=data)
print(f"上传到：{object_key}")

# 检索数据
retrieved_data = storage.get(key=object_key)
assert retrieved_data == data
```

### 直接使用 Greenfield

对于明确需要 Greenfield 存储的情况：

```python
from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

# 使用配置初始化
storage = GreenfieldReputationStorage(
    sp_host="gnfd-testnet-sp1.bnbchain.org",
    bucket="my-reputation-bucket",
    private_key="your_private_key_without_0x_prefix",
    txn_hash="0xabcdef123456...",  # 来自 CreateObject 交易
)

# 上传
key = storage.put(key="reputation-1", data=b"声誉数据")

# 下载
data = storage.get(key=key)
```

## 配置

### 环境变量

创建 `.env` 文件：

```bash
# 后端选择
REPUTATION_BACKEND=greenfield  # 或 "ipfs"

# Greenfield 配置
GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
GREENFIELD_BUCKET=hubble-reputation-test
GREENFIELD_PRIVATE_KEY=abc123def456...  # 不带 0x 前缀
GREENFIELD_TXN_HASH=0x123abc456def...   # 可选默认值
GREENFIELD_TIMEOUT=60
```

### 编程配置

```python
from agent0_sdk.core.storage_factory import create_reputation_storage

# 使用字典配置
config = {
    "REPUTATION_BACKEND": "greenfield",
    "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
    "GREENFIELD_BUCKET": "my-bucket",
    "GREENFIELD_PRIVATE_KEY": "your_private_key",
    "GREENFIELD_TXN_HASH": "0x...",
}

storage = create_reputation_storage(config=config)
```

### 运行时切换后端

```python
# 使用 IPFS
ipfs_storage = create_reputation_storage(config={
    "REPUTATION_BACKEND": "ipfs"
})

# 使用 Greenfield
greenfield_storage = create_reputation_storage(config={
    "REPUTATION_BACKEND": "greenfield",
    "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
    "GREENFIELD_BUCKET": "my-bucket",
    "GREENFIELD_PRIVATE_KEY": "key",
})
```

## 存储操作

### 使用自动生成键上传

```python
# 让存储生成基于 UUID 的键
data = b"一些声誉数据"
key = storage.put(key="", data=data)  # 空键 = 自动生成

print(f"生成的键：{key}")  # 例如，"a1b2c3d4e5f6..."
```

### 使用自定义键上传

```python
# 使用您自己的键（例如，代理 ID、CID、哈希）
agent_id = "agent-12345"
data = b"代理 12345 的声誉"

key = storage.put(key=f"reputation/{agent_id}", data=data)
# 键将是 "reputation/agent-12345"
```

### 每对象交易哈希

如果您有不同的对象有不同的交易哈希：

```python
# 上传具有不同交易哈希的多个对象
storage = GreenfieldReputationStorage(
    sp_host="gnfd-testnet-sp1.bnbchain.org",
    bucket="my-bucket",
    private_key="key",
    txn_hash=None,  # 无默认值
)

# 上传对象 1 及其交易哈希
key1 = storage.put(
    key="object-1",
    data=b"data 1",
    txn_hash="0xabc123..."
)

# 上传对象 2 及不同交易哈希
key2 = storage.put(
    key="object-2",
    data=b"data 2",
    txn_hash="0xdef456..."
)
```

### 检索数据

```python
# 简单检索
data = storage.get(key="reputation/agent-12345")

# 处理不存在的对象
try:
    data = storage.get(key="nonexistent-key")
except RuntimeError as e:
    print(f"对象未找到：{e}")
```

### 大数据上传

```python
import json

# 上传结构化声誉数据
reputation_data = {
    "agent_id": "agent-xyz",
    "score": 95,
    "reviews": [
        {"rating": 5, "comment": "优秀"},
        {"rating": 4, "comment": "良好"}
    ],
    "timestamp": "2024-01-15T10:30:00Z"
}

# 序列化为字节
data_bytes = json.dumps(reputation_data).encode('utf-8')

# 上传
key = storage.put(key="agent-xyz/reputation", data=data_bytes)

# 检索和解析
retrieved_bytes = storage.get(key=key)
retrieved_data = json.loads(retrieved_bytes.decode('utf-8'))
```

## 错误处理

### 具有重试的健壮上传

```python
import time
from typing import Optional

def upload_with_retry(
    storage,
    key: str,
    data: bytes,
    max_retries: int = 3,
    txn_hash: Optional[str] = None
) -> Optional[str]:
    """上传失败时自动重试。"""
    for attempt in range(max_retries):
        try:
            result_key = storage.put(key=key, data=data, txn_hash=txn_hash)
            print(f"上传成功：{result_key}")
            return result_key
        except RuntimeError as e:
            print(f"尝试 {attempt + 1} 失败：{e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"{wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"经过 {max_retries} 次尝试后上传失败")
                raise

# 用法
key = upload_with_retry(
    storage,
    key="important-data",
    data=b"关键声誉数据",
    max_retries=3
)
```

### 处理缺少的交易哈希

```python
try:
    key = storage.put(key="test", data=b"test data")
except ValueError as e:
    if "txn_hash is required" in str(e):
        print("错误：您必须提供交易哈希")
        print("首先在链上创建对象并使用其交易哈希")
    raise
```

### 优雅降级

```python
def get_reputation_data(storage, agent_id: str) -> Optional[bytes]:
    """使用优雅错误处理获取声誉数据。"""
    try:
        data = storage.get(key=f"reputation/{agent_id}")
        return data
    except RuntimeError as e:
        print(f"检索 {agent_id} 的声誉失败：{e}")
        return None

# 用法
data = get_reputation_data(storage, "agent-123")
if data:
    print(f"获取 {len(data)} 字节")
else:
    print("使用默认声誉")
```

## 高级用法

### 多版本存储

```python
from datetime import datetime

def store_versioned_reputation(storage, agent_id: str, data: bytes) -> str:
    """存储带版本控制的声誉数据。"""
    timestamp = datetime.utcnow().isoformat()
    version_key = f"reputation/{agent_id}/v-{timestamp}"

    key = storage.put(key=version_key, data=data)

    # 也存储为"最新"
    latest_key = f"reputation/{agent_id}/latest"
    storage.put(key=latest_key, data=data)

    return version_key

# 用法
key = store_versioned_reputation(storage, "agent-123", b"声誉数据")
print(f"存储的版本：{key}")
# 输出：reputation/agent-123/v-2024-01-15T10:30:00
```

### 批量操作

```python
def upload_batch(storage, items: dict) -> dict:
    """上传多个项目并返回其键。"""
    results = {}

    for key, data in items.items():
        try:
            result_key = storage.put(key=key, data=data)
            results[key] = {"status": "success", "key": result_key}
        except Exception as e:
            results[key] = {"status": "error", "error": str(e)}

    return results

# 用法
items = {
    "agent-1/reputation": b"data 1",
    "agent-2/reputation": b"data 2",
    "agent-3/reputation": b"data 3",
}

results = upload_batch(storage, items)
for key, result in results.items():
    print(f"{key}: {result['status']}")
```

### 元数据存储

```python
import json

def store_with_metadata(storage, object_key: str, data: bytes, metadata: dict) -> str:
    """存储数据及元数据作为包装器。"""
    wrapper = {
        "metadata": metadata,
        "data": data.hex(),  # 存储二进制为十六进制
    }

    wrapper_bytes = json.dumps(wrapper).encode('utf-8')
    key = storage.put(key=object_key, data=wrapper_bytes)

    return key

def retrieve_with_metadata(storage, object_key: str) -> tuple:
    """检索数据和元数据。"""
    wrapper_bytes = storage.get(key=object_key)
    wrapper = json.loads(wrapper_bytes.decode('utf-8'))

    metadata = wrapper["metadata"]
    data = bytes.fromhex(wrapper["data"])

    return data, metadata

# 用法
metadata = {
    "agent_id": "agent-123",
    "created_at": "2024-01-15T10:30:00Z",
    "version": "1.0"
}

key = store_with_metadata(
    storage,
    "agent-123/reputation",
    b"声誉数据",
    metadata
)

data, meta = retrieve_with_metadata(storage, key)
print(f"数据：{data}")
print(f"元数据：{meta}")
```

### 内容寻址（CID 类似键）

```python
import hashlib

def compute_content_hash(data: bytes) -> str:
    """计算内容的 SHA256 哈希（类似于 IPFS CID）。"""
    return hashlib.sha256(data).hexdigest()

def store_content_addressed(storage, data: bytes) -> str:
    """使用内容哈希作为键存储数据。"""
    content_hash = compute_content_hash(data)
    key = f"reputation/by-hash/{content_hash}"

    storage.put(key=key, data=data)
    return content_hash

def get_by_content_hash(storage, content_hash: str) -> bytes:
    """通过内容哈希检索数据。"""
    key = f"reputation/by-hash/{content_hash}"
    return storage.get(key=key)

# 用法
data = b"声誉数据"
hash_id = store_content_addressed(storage, data)
print(f"内容哈希：{hash_id}")

# 通过哈希检索
retrieved = get_by_content_hash(storage, hash_id)
assert retrieved == data
```

## 生产注意事项

### 监控和日志

```python
import logging

logger = logging.getLogger(__name__)

class MonitoredStorage:
    """为存储操作添加监控的包装器。"""

    def __init__(self, storage):
        self.storage = storage
        self.upload_count = 0
        self.download_count = 0
        self.error_count = 0

    def put(self, key: str, data: bytes, txn_hash=None) -> str:
        try:
            logger.info(f"上传：key={key}, size={len(data)} 字节")
            result = self.storage.put(key=key, data=data, txn_hash=txn_hash)
            self.upload_count += 1
            logger.info(f"上传成功：{result}")
            return result
        except Exception as e:
            self.error_count += 1
            logger.error(f"上传失败：{e}")
            raise

    def get(self, key: str) -> bytes:
        try:
            logger.info(f"下载：key={key}")
            result = self.storage.get(key=key)
            self.download_count += 1
            logger.info(f"下载成功：{len(result)} 字节")
            return result
        except Exception as e:
            self.error_count += 1
            logger.error(f"下载失败：{e}")
            raise

    def get_stats(self) -> dict:
        return {
            "uploads": self.upload_count,
            "downloads": self.download_count,
            "errors": self.error_count
        }

# 用法
storage = create_reputation_storage()
monitored = MonitoredStorage(storage)

monitored.put(key="test", data=b"data")
monitored.get(key="test")

print(f"统计：{monitored.get_stats()}")
```

### 缓存层

```python
from typing import Optional
import time

class CachedStorage:
    """带内存缓存的存储。"""

    def __init__(self, storage, cache_ttl: int = 300):
        self.storage = storage
        self.cache = {}
        self.cache_ttl = cache_ttl

    def put(self, key: str, data: bytes, txn_hash=None) -> str:
        result = self.storage.put(key=key, data=data, txn_hash=txn_hash)
        # 缓存数据
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
        return result

    def get(self, key: str) -> bytes:
        # 首先检查缓存
        if key in self.cache:
            entry = self.cache[key]
            age = time.time() - entry["timestamp"]
            if age < self.cache_ttl:
                print(f"缓存命中：{key}")
                return entry["data"]

        # 缓存未命中 - 从存储获取
        print(f"缓存未命中：{key}")
        data = self.storage.get(key=key)

        # 更新缓存
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

        return data

# 用法
storage = create_reputation_storage()
cached = CachedStorage(storage, cache_ttl=300)  # 5 分钟缓存

# 第一次调用从 Greenfield 获取
data1 = cached.get(key="test")  # 缓存未命中

# 第二次调用使用缓存
data2 = cached.get(key="test")  # 缓存命中
```

### 健康检查

```python
def check_storage_health(storage) -> dict:
    """对存储后端执行健康检查。"""
    health = {
        "status": "unknown",
        "can_read": False,
        "can_write": False,
        "error": None
    }

    test_key = f"health-check-{int(time.time())}"
    test_data = b"health check"

    try:
        # 测试写入（如果 txn_hash 可用）
        try:
            storage.put(key=test_key, data=test_data)
            health["can_write"] = True
        except ValueError as e:
            if "txn_hash is required" in str(e):
                health["can_write"] = "skipped_no_txn_hash"

        # 测试读取（尝试已知的公共对象）
        # 或在写入不成功时跳过
        if health["can_write"] == True:
            time.sleep(2)
            retrieved = storage.get(key=test_key)
            health["can_read"] = (retrieved == test_data)

        # 整体状态
        if health["can_write"] and health["can_read"]:
            health["status"] = "healthy"
        else:
            health["status"] = "degraded"

    except Exception as e:
        health["status"] = "unhealthy"
        health["error"] = str(e)

    return health

# 用法
storage = create_reputation_storage()
health = check_storage_health(storage)
print(f"存储健康状况：{health}")
```

### 配置验证

```python
def validate_greenfield_config(config: dict) -> bool:
    """在使用前验证 Greenfield 配置。"""
    required = ["GREENFIELD_SP_HOST", "GREENFIELD_BUCKET", "GREENFIELD_PRIVATE_KEY"]

    for key in required:
        if key not in config or not config[key]:
            print(f"缺少必需的配置：{key}")
            return False

    # 验证 SP 主机格式
    if not config["GREENFIELD_SP_HOST"].endswith(".bnbchain.org"):
        print(f"无效的 SP 主机：{config['GREENFIELD_SP_HOST']}")
        return False

    # 验证私钥格式（64 个十六进制字符）
    private_key = config["GREENFIELD_PRIVATE_KEY"]
    if private_key.startswith("0x"):
        private_key = private_key[2:]

    if len(private_key) != 64 or not all(c in "0123456789abcdefABCDEF" for c in private_key):
        print(f"无效的私钥格式")
        return False

    print("配置有效")
    return True

# 用法
config = {
    "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
    "GREENFIELD_BUCKET": "my-bucket",
    "GREENFIELD_PRIVATE_KEY": "abc123...",
}

if validate_greenfield_config(config):
    storage = create_reputation_storage(config=config)
```

## 完整示例：声誉存储服务

```python
import logging
from typing import Optional
from agent0_sdk.core.storage_factory import create_reputation_storage

logger = logging.getLogger(__name__)

class ReputationStorageService:
    """生产就绪的声誉存储服务。"""

    def __init__(self, config: dict = None):
        self.storage = create_reputation_storage(config=config)
        self.stats = {
            "uploads": 0,
            "downloads": 0,
            "errors": 0
        }

    def store_reputation(self, agent_id: str, data: bytes, txn_hash: Optional[str] = None) -> str:
        """存储代理的声誉数据。"""
        key = f"reputation/{agent_id}"

        try:
            logger.info(f"存储声誉：agent={agent_id}, size={len(data)}")
            result = self.storage.put(key=key, data=data, txn_hash=txn_hash)
            self.stats["uploads"] += 1
            logger.info(f"存储成功：{result}")
            return result
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"存储声誉失败：{e}")
            raise

    def get_reputation(self, agent_id: str) -> Optional[bytes]:
        """检索代理的声誉数据。"""
        key = f"reputation/{agent_id}"

        try:
            logger.info(f"检索声誉：agent={agent_id}")
            data = self.storage.get(key=key)
            self.stats["downloads"] += 1
            logger.info(f"检索：{len(data)} 字节")
            return data
        except RuntimeError as e:
            logger.error(f"检索声誉失败：{e}")
            self.stats["errors"] += 1
            return None

    def get_statistics(self) -> dict:
        """获取服务统计。"""
        return self.stats.copy()

# 用法
service = ReputationStorageService(config={
    "REPUTATION_BACKEND": "greenfield",
    "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
    "GREENFIELD_BUCKET": "reputation-data",
    "GREENFIELD_PRIVATE_KEY": "your_key",
    "GREENFIELD_TXN_HASH": "0x...",
})

# 存储
service.store_reputation("agent-123", b"reputation data")

# 检索
data = service.get_reputation("agent-123")

# 统计
print(f"统计：{service.get_statistics()}")
```

## 下一步

- 检查[FAQ](GREENFIELD_FAQ.md)了解常见问题（特别是关于 txn_hash）
- 查看[集成测试指南](greenfield_integration_guide.md)了解测试程序
- 参见[快速入门](GREENFIELD_QUICKSTART.md)了解 5 分钟设置
- 查看[计划文档](20251128_1340_bnb_greenfield_reuptation.plan.md)了解架构详细信息
- 查看[TODO](20251128_1415_bnb_greenfield_reputation.todo.md)了解实现状态
# BNB Greenfield Storage Usage Examples

This document provides practical code examples for using BNB Greenfield storage in the agent0 SDK.

## Table of Contents
- [Basic Usage](#basic-usage)
- [Configuration](#configuration)
- [Storage Operations](#storage-operations)
- [Error Handling](#error-handling)
- [Advanced Usage](#advanced-usage)
- [Production Considerations](#production-considerations)

## Important: Greenfield's Two-Step Upload Process

⚠️ **Before you start**: Greenfield requires a transaction hash **before** uploading data.

Unlike IPFS or S3 where you directly upload and get an ID back, Greenfield uses:

1. **CreateObject** (on-chain) → Get `txn_hash`
2. **PutObject** (upload data) → Use `txn_hash` for authorization

**Current SDK Limitation**: You must obtain `txn_hash` externally (via DCellar/CLI) before using `storage.put()`.

See [Integration Guide](greenfield_integration_guide.md#understanding-greenfields-two-step-upload-process) for detailed explanation.

## Basic Usage

### Using the Storage Factory (Recommended)

The storage factory provides a unified interface that works with both IPFS and Greenfield:

```python
from agent0_sdk.core.storage_factory import create_reputation_storage

# Create storage instance (backend determined by config)
storage = create_reputation_storage()

# Upload data
data = b"Reputation data for agent XYZ"
object_key = storage.put(key="agent-xyz-reputation", data=data)
print(f"Uploaded to: {object_key}")

# Retrieve data
retrieved_data = storage.get(key=object_key)
assert retrieved_data == data
```

### Direct Greenfield Usage

For cases where you explicitly want Greenfield storage:

```python
from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

# Initialize with configuration
storage = GreenfieldReputationStorage(
    sp_host="gnfd-testnet-sp1.bnbchain.org",
    bucket="my-reputation-bucket",
    private_key="your_private_key_without_0x_prefix",
    txn_hash="0xabcdef123456...",  # From CreateObject transaction
)

# Upload
key = storage.put(key="reputation-1", data=b"reputation data")

# Download
data = storage.get(key=key)
```

## Configuration

### Environment Variables

Create a `.env` file:

```bash
# Backend selection
REPUTATION_BACKEND=greenfield  # or "ipfs"

# Greenfield configuration
GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
GREENFIELD_BUCKET=hubble-reputation-test
GREENFIELD_PRIVATE_KEY=abc123def456...  # Without 0x prefix
GREENFIELD_TXN_HASH=0x123abc456def...   # Optional default
GREENFIELD_TIMEOUT=60
```

### Programmatic Configuration

```python
from agent0_sdk.core.storage_factory import create_reputation_storage

# Using dict configuration
config = {
    "REPUTATION_BACKEND": "greenfield",
    "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
    "GREENFIELD_BUCKET": "my-bucket",
    "GREENFIELD_PRIVATE_KEY": "your_private_key",
    "GREENFIELD_TXN_HASH": "0x...",
}

storage = create_reputation_storage(config=config)
```

### Switching Backends at Runtime

```python
# Use IPFS
ipfs_storage = create_reputation_storage(config={
    "REPUTATION_BACKEND": "ipfs"
})

# Use Greenfield
greenfield_storage = create_reputation_storage(config={
    "REPUTATION_BACKEND": "greenfield",
    "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
    "GREENFIELD_BUCKET": "my-bucket",
    "GREENFIELD_PRIVATE_KEY": "key",
})
```

## Storage Operations

### Upload with Auto-Generated Key

```python
# Let storage generate UUID-based key
data = b"Some reputation data"
key = storage.put(key="", data=data)  # Empty key = auto-generate

print(f"Generated key: {key}")  # e.g., "a1b2c3d4e5f6..."
```

### Upload with Custom Key

```python
# Use your own key (e.g., agent ID, CID, hash)
agent_id = "agent-12345"
data = b"Reputation for agent 12345"

key = storage.put(key=f"reputation/{agent_id}", data=data)
# Key will be "reputation/agent-12345"
```

### Per-Object Transaction Hash

If you have different transaction hashes for different objects:

```python
# Upload multiple objects with different tx hashes
storage = GreenfieldReputationStorage(
    sp_host="gnfd-testnet-sp1.bnbchain.org",
    bucket="my-bucket",
    private_key="key",
    txn_hash=None,  # No default
)

# Upload object 1 with its tx hash
key1 = storage.put(
    key="object-1",
    data=b"data 1",
    txn_hash="0xabc123..."
)

# Upload object 2 with different tx hash
key2 = storage.put(
    key="object-2",
    data=b"data 2",
    txn_hash="0xdef456..."
)
```

### Retrieving Data

```python
# Simple retrieval
data = storage.get(key="reputation/agent-12345")

# Handling non-existent objects
try:
    data = storage.get(key="nonexistent-key")
except RuntimeError as e:
    print(f"Object not found: {e}")
```

### Large Data Upload

```python
import json

# Upload structured reputation data
reputation_data = {
    "agent_id": "agent-xyz",
    "score": 95,
    "reviews": [
        {"rating": 5, "comment": "Excellent"},
        {"rating": 4, "comment": "Good"}
    ],
    "timestamp": "2024-01-15T10:30:00Z"
}

# Serialize to bytes
data_bytes = json.dumps(reputation_data).encode('utf-8')

# Upload
key = storage.put(key="agent-xyz/reputation", data=data_bytes)

# Retrieve and parse
retrieved_bytes = storage.get(key=key)
retrieved_data = json.loads(retrieved_bytes.decode('utf-8'))
```

## Error Handling

### Robust Upload with Retry

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
    """Upload with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            result_key = storage.put(key=key, data=data, txn_hash=txn_hash)
            print(f"Upload successful: {result_key}")
            return result_key
        except RuntimeError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Upload failed after {max_retries} attempts")
                raise

# Usage
key = upload_with_retry(
    storage,
    key="important-data",
    data=b"Critical reputation data",
    max_retries=3
)
```

### Handling Missing Transaction Hash

```python
try:
    key = storage.put(key="test", data=b"test data")
except ValueError as e:
    if "txn_hash is required" in str(e):
        print("Error: You must provide a transaction hash")
        print("Create an object on-chain first and use its tx hash")
    raise
```

### Graceful Degradation

```python
def get_reputation_data(storage, agent_id: str) -> Optional[bytes]:
    """Get reputation data with graceful error handling."""
    try:
        data = storage.get(key=f"reputation/{agent_id}")
        return data
    except RuntimeError as e:
        print(f"Failed to retrieve reputation for {agent_id}: {e}")
        return None

# Usage
data = get_reputation_data(storage, "agent-123")
if data:
    print(f"Got {len(data)} bytes")
else:
    print("Using default reputation")
```

## Advanced Usage

### Multi-Version Storage

```python
from datetime import datetime

def store_versioned_reputation(storage, agent_id: str, data: bytes) -> str:
    """Store reputation data with versioning."""
    timestamp = datetime.utcnow().isoformat()
    version_key = f"reputation/{agent_id}/v-{timestamp}"

    key = storage.put(key=version_key, data=data)

    # Also store as "latest"
    latest_key = f"reputation/{agent_id}/latest"
    storage.put(key=latest_key, data=data)

    return version_key

# Usage
key = store_versioned_reputation(storage, "agent-123", b"reputation data")
print(f"Stored version: {key}")
# Output: reputation/agent-123/v-2024-01-15T10:30:00
```

### Batch Operations

```python
def upload_batch(storage, items: dict) -> dict:
    """Upload multiple items and return their keys."""
    results = {}

    for key, data in items.items():
        try:
            result_key = storage.put(key=key, data=data)
            results[key] = {"status": "success", "key": result_key}
        except Exception as e:
            results[key] = {"status": "error", "error": str(e)}

    return results

# Usage
items = {
    "agent-1/reputation": b"data 1",
    "agent-2/reputation": b"data 2",
    "agent-3/reputation": b"data 3",
}

results = upload_batch(storage, items)
for key, result in results.items():
    print(f"{key}: {result['status']}")
```

### Metadata Storage

```python
import json

def store_with_metadata(storage, object_key: str, data: bytes, metadata: dict) -> str:
    """Store data along with metadata as a wrapper."""
    wrapper = {
        "metadata": metadata,
        "data": data.hex(),  # Store binary as hex
    }

    wrapper_bytes = json.dumps(wrapper).encode('utf-8')
    key = storage.put(key=object_key, data=wrapper_bytes)

    return key

def retrieve_with_metadata(storage, object_key: str) -> tuple:
    """Retrieve data and metadata."""
    wrapper_bytes = storage.get(key=object_key)
    wrapper = json.loads(wrapper_bytes.decode('utf-8'))

    metadata = wrapper["metadata"]
    data = bytes.fromhex(wrapper["data"])

    return data, metadata

# Usage
metadata = {
    "agent_id": "agent-123",
    "created_at": "2024-01-15T10:30:00Z",
    "version": "1.0"
}

key = store_with_metadata(
    storage,
    "agent-123/reputation",
    b"reputation data",
    metadata
)

data, meta = retrieve_with_metadata(storage, key)
print(f"Data: {data}")
print(f"Metadata: {meta}")
```

### Content Addressing (CID-like keys)

```python
import hashlib

def compute_content_hash(data: bytes) -> str:
    """Compute SHA256 hash of content (similar to IPFS CID)."""
    return hashlib.sha256(data).hexdigest()

def store_content_addressed(storage, data: bytes) -> str:
    """Store data using its content hash as key."""
    content_hash = compute_content_hash(data)
    key = f"reputation/by-hash/{content_hash}"

    storage.put(key=key, data=data)
    return content_hash

def get_by_content_hash(storage, content_hash: str) -> bytes:
    """Retrieve data by content hash."""
    key = f"reputation/by-hash/{content_hash}"
    return storage.get(key=key)

# Usage
data = b"reputation data"
hash_id = store_content_addressed(storage, data)
print(f"Content hash: {hash_id}")

# Retrieve by hash
retrieved = get_by_content_hash(storage, hash_id)
assert retrieved == data
```

## Production Considerations

### Monitoring and Logging

```python
import logging

logger = logging.getLogger(__name__)

class MonitoredStorage:
    """Wrapper that adds monitoring to storage operations."""

    def __init__(self, storage):
        self.storage = storage
        self.upload_count = 0
        self.download_count = 0
        self.error_count = 0

    def put(self, key: str, data: bytes, txn_hash=None) -> str:
        try:
            logger.info(f"Uploading: key={key}, size={len(data)} bytes")
            result = self.storage.put(key=key, data=data, txn_hash=txn_hash)
            self.upload_count += 1
            logger.info(f"Upload success: {result}")
            return result
        except Exception as e:
            self.error_count += 1
            logger.error(f"Upload failed: {e}")
            raise

    def get(self, key: str) -> bytes:
        try:
            logger.info(f"Downloading: key={key}")
            result = self.storage.get(key=key)
            self.download_count += 1
            logger.info(f"Download success: {len(result)} bytes")
            return result
        except Exception as e:
            self.error_count += 1
            logger.error(f"Download failed: {e}")
            raise

    def get_stats(self) -> dict:
        return {
            "uploads": self.upload_count,
            "downloads": self.download_count,
            "errors": self.error_count
        }

# Usage
storage = create_reputation_storage()
monitored = MonitoredStorage(storage)

monitored.put(key="test", data=b"data")
monitored.get(key="test")

print(f"Stats: {monitored.get_stats()}")
```

### Caching Layer

```python
from typing import Optional
import time

class CachedStorage:
    """Storage with in-memory caching."""

    def __init__(self, storage, cache_ttl: int = 300):
        self.storage = storage
        self.cache = {}
        self.cache_ttl = cache_ttl

    def put(self, key: str, data: bytes, txn_hash=None) -> str:
        result = self.storage.put(key=key, data=data, txn_hash=txn_hash)
        # Cache the data
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
        return result

    def get(self, key: str) -> bytes:
        # Check cache first
        if key in self.cache:
            entry = self.cache[key]
            age = time.time() - entry["timestamp"]
            if age < self.cache_ttl:
                print(f"Cache hit: {key}")
                return entry["data"]

        # Cache miss - fetch from storage
        print(f"Cache miss: {key}")
        data = self.storage.get(key=key)

        # Update cache
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

        return data

# Usage
storage = create_reputation_storage()
cached = CachedStorage(storage, cache_ttl=300)  # 5-minute cache

# First call fetches from Greenfield
data1 = cached.get(key="test")  # Cache miss

# Second call uses cache
data2 = cached.get(key="test")  # Cache hit
```

### Health Check

```python
def check_storage_health(storage) -> dict:
    """Perform health check on storage backend."""
    health = {
        "status": "unknown",
        "can_read": False,
        "can_write": False,
        "error": None
    }

    test_key = f"health-check-{int(time.time())}"
    test_data = b"health check"

    try:
        # Test write (if txn_hash available)
        try:
            storage.put(key=test_key, data=test_data)
            health["can_write"] = True
        except ValueError as e:
            if "txn_hash is required" in str(e):
                health["can_write"] = "skipped_no_txn_hash"

        # Test read (try a known public object)
        # Or skip if write wasn't successful
        if health["can_write"] == True:
            time.sleep(2)
            retrieved = storage.get(key=test_key)
            health["can_read"] = (retrieved == test_data)

        # Overall status
        if health["can_write"] and health["can_read"]:
            health["status"] = "healthy"
        else:
            health["status"] = "degraded"

    except Exception as e:
        health["status"] = "unhealthy"
        health["error"] = str(e)

    return health

# Usage
storage = create_reputation_storage()
health = check_storage_health(storage)
print(f"Storage health: {health}")
```

### Configuration Validation

```python
def validate_greenfield_config(config: dict) -> bool:
    """Validate Greenfield configuration before use."""
    required = ["GREENFIELD_SP_HOST", "GREENFIELD_BUCKET", "GREENFIELD_PRIVATE_KEY"]

    for key in required:
        if key not in config or not config[key]:
            print(f"Missing required config: {key}")
            return False

    # Validate SP host format
    if not config["GREENFIELD_SP_HOST"].endswith(".bnbchain.org"):
        print(f"Invalid SP host: {config['GREENFIELD_SP_HOST']}")
        return False

    # Validate private key format (64 hex chars)
    private_key = config["GREENFIELD_PRIVATE_KEY"]
    if private_key.startswith("0x"):
        private_key = private_key[2:]

    if len(private_key) != 64 or not all(c in "0123456789abcdefABCDEF" for c in private_key):
        print(f"Invalid private key format")
        return False

    print("Configuration valid")
    return True

# Usage
config = {
    "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
    "GREENFIELD_BUCKET": "my-bucket",
    "GREENFIELD_PRIVATE_KEY": "abc123...",
}

if validate_greenfield_config(config):
    storage = create_reputation_storage(config=config)
```

## Complete Example: Reputation Storage Service

```python
import logging
from typing import Optional
from agent0_sdk.core.storage_factory import create_reputation_storage

logger = logging.getLogger(__name__)

class ReputationStorageService:
    """Production-ready reputation storage service."""

    def __init__(self, config: dict = None):
        self.storage = create_reputation_storage(config=config)
        self.stats = {
            "uploads": 0,
            "downloads": 0,
            "errors": 0
        }

    def store_reputation(self, agent_id: str, data: bytes, txn_hash: Optional[str] = None) -> str:
        """Store reputation data for an agent."""
        key = f"reputation/{agent_id}"

        try:
            logger.info(f"Storing reputation: agent={agent_id}, size={len(data)}")
            result = self.storage.put(key=key, data=data, txn_hash=txn_hash)
            self.stats["uploads"] += 1
            logger.info(f"Stored successfully: {result}")
            return result
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to store reputation: {e}")
            raise

    def get_reputation(self, agent_id: str) -> Optional[bytes]:
        """Retrieve reputation data for an agent."""
        key = f"reputation/{agent_id}"

        try:
            logger.info(f"Retrieving reputation: agent={agent_id}")
            data = self.storage.get(key=key)
            self.stats["downloads"] += 1
            logger.info(f"Retrieved: {len(data)} bytes")
            return data
        except RuntimeError as e:
            logger.error(f"Failed to retrieve reputation: {e}")
            self.stats["errors"] += 1
            return None

    def get_statistics(self) -> dict:
        """Get service statistics."""
        return self.stats.copy()

# Usage
service = ReputationStorageService(config={
    "REPUTATION_BACKEND": "greenfield",
    "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
    "GREENFIELD_BUCKET": "reputation-data",
    "GREENFIELD_PRIVATE_KEY": "your_key",
    "GREENFIELD_TXN_HASH": "0x...",
})

# Store
service.store_reputation("agent-123", b"reputation data")

# Retrieve
data = service.get_reputation("agent-123")

# Stats
print(f"Stats: {service.get_statistics()}")
```

## Next Steps

- Check the [FAQ](GREENFIELD_FAQ.md) for common questions (especially about txn_hash)
- Review the [Integration Testing Guide](greenfield_integration_guide.md) for testing procedures
- See [Quick Start](GREENFIELD_QUICKSTART.md) for 5-minute setup
- Check the [Plan Document](20251128_1340_bnb_greenfield_reuptation.plan.md) for architecture details
- See [TODO](20251128_1415_bnb_greenfield_reputation.todo.md) for implementation status

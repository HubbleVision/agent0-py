# BNB Greenfield Storage Backend

This document explains how to use BNB Greenfield as the reputation storage backend in agent0 SDK.

## Overview

The agent0 SDK supports multiple storage backends for reputation data:
- **IPFS** (default): Decentralized storage via IPFS network
- **Greenfield** (Phase 2+): BNB Greenfield decentralized storage network

The storage backend can be switched via configuration without code changes, using the unified `ReputationStorage` interface.

## Why Greenfield?

BNB Greenfield offers several advantages:
- **Native Web3 Integration**: Built-in blockchain integration for access control and payments
- **High Performance**: Optimized for large-scale data storage and retrieval
- **Cost-Effective**: Competitive pricing with transparent on-chain billing
- **Cross-Chain**: Seamless integration with BSC and other BNB Chain ecosystems

## Quick Start

### 1. Prerequisites

- Python 3.8+
- agent0-sdk installed
- BNB wallet with testnet/mainnet BNB tokens
- Access to a Greenfield Storage Provider (SP)

### 2. Install Dependencies

The Greenfield backend requires `eth-utils`:

```bash
pip install eth-utils>=2.0.0
```

Or install agent0-sdk with all dependencies:

```bash
pip install agent0-sdk[all]
```

### 3. Configure Environment

Copy the example configuration:

```bash
cp .env.greenfield.example .env
```

Edit `.env` and set:

```bash
# Switch to Greenfield backend
REPUTATION_BACKEND=greenfield

# Configure Greenfield connection
GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
GREENFIELD_BUCKET=my-reputation-bucket
GREENFIELD_PRIVATE_KEY=0x1234... # Your wallet private key
```

### 4. Create Bucket and Object

Before using Greenfield storage, you need to:

1. **Create a Bucket** on Greenfield (using greenfield-cmd or SDK)
2. **Create Objects** and obtain transaction hashes for each object

Example using greenfield-cmd:

```bash
# Create bucket
gnfd-cmd bucket create gnfd://my-reputation-bucket

# Create object (will get txn hash in response)
gnfd-cmd object create gnfd://my-reputation-bucket/object-name
```

**Two Usage Patterns:**

**Pattern A: Single Default Transaction Hash** (for simple use cases)
- Create one object and use its txn hash as default
- All uploads use the same txn hash

**Pattern B: Per-Object Transaction Hash** (recommended for production)
- Create objects individually via Greenfield SDK
- Obtain each object's txn hash from CreateObject operation

### 5. Use in Code


```python
from agent0_sdk.core.storage_factory import create_reputation_storage

# Creates Greenfield storage based on environment config
storage = create_reputation_storage()

key = storage.put(key="", data=b"reputation data")

# Retrieve data
data = storage.get(key=key)
```


```python
from agent0_sdk.core.storage_factory import create_reputation_storage

config = {
    "REPUTATION_BACKEND": "greenfield",
    "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
    "GREENFIELD_BUCKET": "my-bucket",
    "GREENFIELD_PRIVATE_KEY": "0x...",
}
storage = create_reputation_storage(config=config)


# Or use auto-generated keys
```

## Configuration Reference

### Required Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `REPUTATION_BACKEND` | Storage backend type | `greenfield` |
| `GREENFIELD_SP_HOST` | Storage Provider endpoint | `gnfd-testnet-sp1.bnbchain.org` |
| `GREENFIELD_BUCKET` | Bucket name | `my-reputation-bucket` |
| `GREENFIELD_PRIVATE_KEY` | Wallet private key (hex) | `0x1234...` |

### Optional Configuration

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `GREENFIELD_CONTENT_TYPE` | Content-Type for objects | `application/octet-stream` | - |
| `GREENFIELD_TIMEOUT` | Request timeout (seconds) | `30` | - |

## Network Information

### Testnet

- **Chain ID**: 5600
- **RPC**: https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org
- **SP Endpoints**: gnfd-testnet-sp{1-7}.bnbchain.org
- **Faucet**: https://gnfd-bsc-faucet.bnbchain.org/

### Mainnet

- **Chain ID**: 1017
- **RPC**: https://greenfield-chain.bnbchain.org
- **SP Endpoints**: gnfd-sp{1-7}.bnbchain.org

## Advanced Usage

### Programmatic Configuration

You can configure storage backend programmatically:

```python
from agent0_sdk.core.storage_factory import create_reputation_storage

config = {
    "REPUTATION_BACKEND": "greenfield",
    "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
    "GREENFIELD_BUCKET": "test-bucket",
    "GREENFIELD_PRIVATE_KEY": "0x...",
}

storage = create_reputation_storage(config=config)
```

### Switching Backends at Runtime

You can easily switch between IPFS and Greenfield:

```python
# Use IPFS
ipfs_storage = create_reputation_storage(config={"REPUTATION_BACKEND": "ipfs"})

# Use Greenfield
greenfield_storage = create_reputation_storage(config={"REPUTATION_BACKEND": "greenfield", ...})
```

### Error Handling

The implementation includes robust error handling:

```python
try:
    key = storage.put(key="", data=b"data")
except RuntimeError as e:
    # Handle upload failures
    print(f"Upload failed: {e}")

try:
    data = storage.get(key="some-key")
except RuntimeError as e:
    # Handle retrieval failures
    print(f"Retrieval failed: {e}")
```

## Security Best Practices

1. **Never commit private keys** to version control
2. **Use environment variables** for sensitive configuration
3. **Rotate keys regularly** in production environments
4. **Use testnet** for development and testing
5. **Validate transaction hashes** from trusted sources only

## Troubleshooting


**Cause**: No transaction hash available (neither in constructor nor put() parameter).



### "Failed to upload to Greenfield"

Check:
- SP endpoint is accessible (try curl/ping)
- Wallet has sufficient BNB for gas fees
- Bucket exists and you have write permissions
- Transaction hash is valid and matches the bucket/object

### "Authorization failed"

Check:
- Private key is correct and properly formatted (with 0x prefix)
- Wallet address matches the bucket owner
- Canonical request is built correctly (check logs)

## Migration from IPFS

To migrate existing IPFS-based deployments to Greenfield:

1. Keep IPFS as fallback (set `REPUTATION_BACKEND=ipfs`)
2. Set up Greenfield configuration in parallel
3. Test with `REPUTATION_BACKEND=greenfield` in staging
4. Gradually migrate data (optional)
5. Switch production to Greenfield when ready

The interface is identical, so no code changes are required!

## References

- [BNB Greenfield Documentation](https://docs.bnbchain.org/bnb-greenfield/)
- [Storage Provider API](https://github.com/bnb-chain/greenfield-storage-provider/tree/master/docs/storage-provider-rest-api)
- [Greenfield SDK (JavaScript)](https://docs.bnbchain.org/bnb-greenfield/for-developers/apis-and-sdks/sdk-js/)
- [Getting Started Guide](https://docs.bnbchain.org/bnb-greenfield/for-developers/get-started-dev/)

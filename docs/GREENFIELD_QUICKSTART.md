# BNB Greenfield Quick Start Guide

> 5-minute guide to get started with BNB Greenfield storage in agent0 SDK

## Overview

The agent0 SDK now supports **BNB Greenfield** as an alternative to IPFS for storing reputation data. You can switch between backends with a simple configuration change.

## Quick Setup (Testnet)

### 1. Install Dependencies

```bash
pip install eth-utils>=2.0.0 eth-account>=0.9.0 requests>=2.31.0
```

### 2. Get Testnet Resources

1. **Get testnet BNB**: https://gnfd-bsc-testnet-faucet.bnbchain.org/
2. **Create bucket**: https://dcellar.io/ (testnet mode)
   - Click "Create Bucket"
   - Name: `my-test-bucket`
   - Set visibility to "Public Read" (for testing)
3. **Get transaction hash**:
   - Upload a test file in DCellar (this creates object on-chain)
   - Copy the transaction hash from MetaMask or explorer
   - ⚠️ **Important**: This txn hash is needed **before** you can upload data via SDK

**Why need txn hash?** Greenfield uses a two-step process:
1. CreateObject (on-chain) → Returns txn_hash
2. PutObject (upload data) → Uses txn_hash as authorization

See [detailed explanation](greenfield_integration_guide.md#understanding-greenfields-two-step-upload-process)

### 3. Configure Environment

```bash
# Copy example configuration
cp .env.greenfield.example .env

# Edit .env and set:
export REPUTATION_BACKEND=greenfield
export GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
export GREENFIELD_BUCKET=my-test-bucket
export GREENFIELD_PRIVATE_KEY=your_private_key_without_0x
export GREENFIELD_TXN_HASH=0x...  # From step 2
```

### 4. Use in Code

```python
from agent0_sdk.core.storage_factory import create_reputation_storage

# Create storage (uses Greenfield based on env config)
storage = create_reputation_storage()

# Upload reputation data
data = b"Agent reputation data"
key = storage.put(key="agent-123-reputation", data=data)
print(f"Uploaded: {key}")

# Retrieve data
retrieved = storage.get(key=key)
assert retrieved == data
print("Data verified!")
```

### 5. Run Integration Tests

```bash
# Run all integration tests
pytest tests/test_greenfield_integration.py -v -m integration

# Expected output:
# ✅ test_put_and_get_roundtrip PASSED
# ✅ test_put_with_auto_generated_key PASSED
# ✅ test_get_public_object_without_auth PASSED
# ... (10 tests total)
```

## Switching Between IPFS and Greenfield

### Use IPFS (Default)

```bash
export REPUTATION_BACKEND=ipfs
# or just unset REPUTATION_BACKEND
```

```python
storage = create_reputation_storage()  # Uses IPFS
```

### Use Greenfield

```bash
export REPUTATION_BACKEND=greenfield
export GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
export GREENFIELD_BUCKET=my-bucket
export GREENFIELD_PRIVATE_KEY=...
```

```python
storage = create_reputation_storage()  # Uses Greenfield
```

## Common Use Cases

### Upload with Auto-Generated Key

```python
storage = create_reputation_storage()
data = b"Reputation data"
key = storage.put(key="", data=data)  # Empty key = auto-generate UUID
print(f"Generated key: {key}")
```

### Upload JSON Data

```python
import json

reputation = {
    "agent_id": "agent-123",
    "score": 95,
    "reviews": ["Excellent", "Great work"]
}

data = json.dumps(reputation).encode('utf-8')
key = storage.put(key="reputation/agent-123", data=data)

# Retrieve and parse
retrieved = storage.get(key=key)
parsed = json.loads(retrieved.decode('utf-8'))
```

### Error Handling

```python
try:
    data = storage.get(key="nonexistent-key")
except RuntimeError as e:
    print(f"Object not found: {e}")
```

## Troubleshooting

### Tests Skip with "Environment not configured"

✅ **Solution**: Set required environment variables (see step 3)

### 403 Forbidden on Upload

✅ **Solution**:
- Verify you have testnet BNB
- Check private key is correct
- Get fresh transaction hash from CreateObject

### 404 Not Found on Download

✅ **Solution**:
- Wait 2-5 seconds after upload for propagation
- Verify object key matches exactly
- Check object exists in DCellar

### Connection Timeout

✅ **Solution**:
- Try alternative SP: `GREENFIELD_SP_HOST=gnfd-testnet-sp2.bnbchain.org`
- Increase timeout: `GREENFIELD_TIMEOUT=60`

## Next Steps

### Learn More

- ❓ **FAQ**: `docs/GREENFIELD_FAQ.md` (common questions, especially about txn_hash)
- 📖 **Complete Guide**: `docs/greenfield_integration_guide.md` (detailed setup)
- 💡 **Usage Examples**: `docs/greenfield_usage_examples.md` (code patterns)
- 📋 **Architecture**: `docs/20251128_1340_bnb_greenfield_reuptation.plan.md`
- ✅ **Phase 4 Summary**: `docs/PHASE4_COMPLETION_SUMMARY.md`

### Production Deployment

For mainnet deployment:
1. Read "Mainnet Migration" section in `greenfield_integration_guide.md`
2. Review the 15-item pre-mainnet checklist
3. Estimate storage costs at https://docs.bnbchain.org/bnb-greenfield/core-concept/billing-payment/
4. Create production bucket on mainnet
5. Update environment variables for mainnet endpoints

## Quick Reference

### Testnet Endpoints

- **SP Host**: `gnfd-testnet-sp1.bnbchain.org`
- **Chain ID**: `5600`
- **RPC**: `https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org`
- **Faucet**: https://gnfd-bsc-testnet-faucet.bnbchain.org/
- **DCellar**: https://dcellar.io/

### Environment Variables

| Variable | Required | Example |
|----------|----------|---------|
| `REPUTATION_BACKEND` | No | `greenfield` |
| `GREENFIELD_SP_HOST` | Yes | `gnfd-testnet-sp1.bnbchain.org` |
| `GREENFIELD_BUCKET` | Yes | `my-bucket` |
| `GREENFIELD_PRIVATE_KEY` | Yes | `abc123...` |
| `GREENFIELD_TXN_HASH` | Optional* | `0x...` |

*Required for upload operations unless provided per-object

### Test Commands

```bash
# Run all integration tests
pytest tests/test_greenfield_integration.py -v -m integration

# Run single test
pytest tests/test_greenfield_integration.py::TestGreenfieldIntegration::test_put_and_get_roundtrip -v -m integration

# Skip integration tests
pytest tests/ -v -m "not integration"

# Debug mode
pytest tests/test_greenfield_integration.py -v -s --log-cli-level=DEBUG -m integration
```

## Support

- **Documentation**: https://docs.bnbchain.org/bnb-greenfield/
- **Discord**: https://discord.gg/bnbchain
- **GitHub**: https://github.com/bnb-chain/greenfield

---

**Ready in 5 minutes** | **Switch backends anytime** | **Production-ready**

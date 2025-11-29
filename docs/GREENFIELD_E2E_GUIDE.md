# BNB Greenfield E2E Testing Guide

> Complete end-to-end testing of the Greenfield storage workflow

## Overview

This guide provides instructions for running comprehensive E2E (end-to-end) tests that demonstrate the complete Greenfield storage workflow:

1. **CreateObject**: Automatically creates objects on BNB Greenfield blockchain
2. **PutObject**: Uploads data to Storage Provider using transaction hash
3. **GetObject**: Retrieves data and verifies integrity
4. **Public Access**: Tests cross-key retrieval for public buckets

## Quick Start

### 1. Prerequisites

```bash
# Required Python packages (automatically installed with agent0-sdk)
pip install web3>=6.0.0 eth-account>=0.9.0 aiohttp>=3.8.0

# For testing
pip install pytest>=7.0.0 pytest-asyncio>=0.21.0
```

### 2. Environment Configuration

Create a `.env` file or set environment variables:

```bash
# Required - Testnet Configuration
GREENFIELD_RPC_URL=https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org
GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
GREENFIELD_BUCKET=your-test-bucket
GREENFIELD_PRIVATE_KEY=your_private_key_without_0x_prefix

# Optional - Testing Configuration
GREENFIELD_CHAIN_ID=5600  # Testnet (default)
GREENFIELD_TIMEOUT=60     # Request timeout in seconds (default)
```

**Getting Test Resources:**

1. **Testnet BNB**: Visit https://gnfd-bsc-testnet-faucet.bnbchain.org/
2. **Create Bucket**: Use https://dcellar.io/ (testnet mode)
   - Bucket name: `your-test-bucket`
   - Visibility: Set to "Public Read" (for testing)
3. **Get Private Key**: Export from MetaMask (Settings → Security & Privacy)

### 3. Run E2E Tests

```bash
# Run all E2E tests
pytest tests/test_greenfield_e2e.py -v -m integration -s

# Run specific test
pytest tests/test_greenfield_e2e.py::TestGreenfieldE2E::test_create_and_upload_small_text -v -s -m integration

# Run with detailed output
pytest tests/test_greenfield_e2e.py -v -s --log-cli-level=DEBUG -m integration
```

## E2E Test Suite

### Test Coverage

| Test # | Description | Data Type | Size | What it Verifies |
|---------|-------------|----------|------------------|
| 1 | Small Text Upload | UTF-8 text | Basic workflow & public access |
| 2 | JSON Reputation Data | JSON structured | Real-world usage pattern |
| 3 | Binary Data Integrity | All byte values (0x00-0xFF) | Binary data corruption handling |
| 4 | Large Data Performance | 1MB file | Performance with larger payloads |
| 5 | Multiple Objects | 3 concurrent objects | Transaction hash uniqueness |
| 6 | Transaction Hash Uniqueness | 2 objects | Each upload gets unique txn_hash |
| 7 | Error Handling | Invalid operations | Proper error handling |
| 8 | Concurrent Operations | 5 simultaneous uploads | Performance under load |

### Expected Output

```
🚀 E2E Test Configuration:
  RPC URL: https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org
  SP Host: gnfd-testnet-sp1.bnbchain.org
  Bucket: your-test-bucket
  Chain ID: 5600
  Timeout: 60s

📝 Test 1: Small Text Upload & Download
  Key: e2e-test-small-1701234567890
  Size: 43 bytes
  ⏳ Creating object on blockchain...
  ✅ Object created successfully: 0x1234567890abcdef1234567890abcdef1234567890abcdef
  ✅ Upload successful: e2e-test-small-1701234567890
  ✅ Retrieval successful: 43 bytes
  ✅ Public access verified
PASSED

📊 Test 2: JSON Reputation Data
  Key: e2e-test-json-1701234567891
  Size: 256 bytes
  ⏳ Creating object on blockchain...
  ✅ Object created successfully: 0xabcdef1234567890abcdef1234567890abcdef1234567890
  ✅ JSON upload successful
  ✅ JSON structure verified
  Agent ID: test-agent-123
  Reputation Score: 95
PASSED
...
✅ All 8 E2E tests completed successfully!
```

## Test Data

### Test 1: Small Text
```python
TEST_DATA_EXAMPLES["small_text"] = b"Hello, Greenfield! This is a test message for E2E testing."
```

### Test 2: JSON Reputation Data
```python
TEST_DATA_EXAMPLES["json_data"] = json.dumps({
    "agent_id": "test-agent-123",
    "reputation": {
        "score": 95,
        "reviews": [
            {"rating": 5, "comment": "Excellent work"},
            {"rating": 4, "comment": "Good performance"}
        ],
        "created_at": "2024-11-28T14:30:00Z"
    }
}).encode('utf-8')
```

### Test 3: Binary Data
```python
TEST_DATA_EXAMPLES["binary_data"] = bytes([i % 256 for i in range(256)])
# Contains all possible byte values: 0x00, 0x01, ..., 0xFF
```

### Test 4: Large Data
```python
TEST_DATA_EXAMPLES["large_data"] = b"X" * (100 * 1024)  # 100KB
```

## Architecture

### E2E Workflow Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Test Runner │ →  │AutoUploader Helper│ →  │Greenfield Chain │ →  │Storage Provider │
│               │    │                   │    │ CreateObject   │    │  PutObject     │
│- Generates    │    │- Constructs     │    │- Returns      │    │- Verifies    │
│  test data   │    │  transaction     │    │  transaction  │    │  transaction  │
│- Calls       │    │  calldata        │    │  hash         │    │  hash         │
│  upload      │    │- Signs tx        │    │               │    │               │
│- Verifies    │    │- Sends tx        │    │               │    │               │
│  retrieval    │    │- Waits for      │    │               │    │               │
│- Validates   │    │  confirmation     │    │               │    │               │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

### Components

1. **TestGreenfieldE2E**: Main test runner
   - Orchestrates test scenarios
   - Validates data integrity
   - Measures performance
   - Tests error handling

2. **GreenfieldCreateObjectHelper**: Blockchain operations
   - Creates objects on Greenfield chain
   - Handles transaction signing
   - Manages gas estimation
   - Provides transaction hashes

3. **GreenfieldAutoUploader**: Complete workflow
   - Combines CreateObject + PutObject
   - Handles authorization automatically
   - Provides unified put/get interface
   - Manages HTTP sessions

### Key Differences from Basic SDK

| Feature | Basic SDK | E2E AutoUploader |
|----------|-------------|-------------------|
| **CreateObject** | Manual (external) | Automatic |
| **PutObject** | Requires txn_hash | Automatic |
| **Workflow** | 2 steps (manual) | 1 step (automatic) |
| **Gas Handling** | N/A | Automatic estimation |
| **Error Handling** | Basic | Enhanced |

## Performance Benchmarks

### Test 4 Results (1MB Upload)

| Metric | Expected Range | What it Means |
|--------|----------------|-----------------|
| **Upload Time** | 10-60 seconds | Network latency + processing |
| **Download Time** | 1-10 seconds | Storage provider speed |
| **Upload Speed** | 5-100 KB/s | Overall throughput |
| **Download Speed** | 50-500 KB/s | Retrieval performance |

### Performance Factors

- **Network**: Testnet congestion affects times
- **SP Location**: Distance to storage provider
- **Object Size**: Larger objects may take longer
- **Gas Price**: Higher gas = slower transactions

## Troubleshooting

### Common Issues

#### "Transaction failed" Error
**Cause**: Insufficient testnet BNB or network issues
**Solution**:
1. Check balance: https://greenfieldscan.com/address/YOUR_WALLET
2. Get more testnet BNB: https://gnfd-bsc-testnet-faucet.bnbchain.org/
3. Try again during off-peak hours

#### "Object not found" Error
**Cause**: Upload succeeded but object not yet propagated
**Solution**:
1. Wait 5-10 seconds after upload
2. Verify object exists in DCellar
3. Check SP status: https://greenfieldscan.com/

#### "Gas estimation failed" Warning
**Cause**: Network congestion or invalid parameters
**Solution**:
1. Test with smaller objects first
2. Check bucket exists and is accessible
3. Try different SP endpoint

#### "Signature verification failed" Error
**Cause**: Mismatch between CreateObject and PutObject signatures
**Solution**:
1. Verify private key is correct
2. Check chain ID matches bucket network
3. Ensure transaction is confirmed before upload

### Debug Mode

Enable detailed logging:

```bash
# Run with debug logging
pytest tests/test_greenfield_e2e.py -v -s --log-cli-level=DEBUG -m integration

# Or enable in code
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Debug Output Shows**:
- Transaction construction details
- Authorization header generation
- HTTP request/response details
- Gas estimation results

### Clean Up

After testing, clean up created objects:

```python
# Manual cleanup
from agent0_sdk.core.greenfield_cli import create_e2e_helper

async def cleanup():
    uploader = await create_e2e_helper(config)

    # List of objects to clean (from test output)
    objects_to_clean = [
        "e2e-test-small-...",
        "e2e-test-json-...",
        "e2e-test-binary-...",
        # ... add actual object keys from test output
    ]

    for obj_key in objects_to_clean:
        try:
            await uploader.delete(obj_key)  # Note: Need to implement delete
            print(f"Cleaned up: {obj_key}")
        except Exception as e:
            print(f"Failed to clean {obj_key}: {e}")

    await uploader.close()
```

## Production Considerations

### From E2E to Production

1. **Scale Testing**: Increase object sizes to match production data
2. **Performance**: Measure with realistic payloads (100KB-10MB)
3. **Concurrency**: Test with 10+ simultaneous uploads
4. **Monitoring**: Add metrics collection and alerting
5. **Error Recovery**: Implement retry logic with exponential backoff

### Production Workflow

```python
# Production usage (future enhancement)
from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

# For production, you'll still need to manage transaction hashes
storage = GreenfieldReputationStorage(
    sp_host="gnfd-sp1.bnbchain.org",  # Mainnet
    bucket="production-bucket",
    private_key="production_private_key",
    # txn_hash from your CreateObject batch
)

# Option 1: Pre-create transaction hashes
txn_hash_pool = await batch_create_objects(count=1000)

# Option 2: Create on-demand
async def upload_with_auto_create(key: str, data: bytes) -> str:
    txn_hash = await create_object_on_demand(key, len(data))
    return storage.put(key=key, data=data, txn_hash=txn_hash)
```

### Cost Estimation

For production deployment, estimate costs:

| Operation | Cost Component | Estimation |
|-----------|-----------------|------------|
| **CreateObject** | Gas fee | Variable by network congestion |
| **PutObject** | Storage fee | $0.0023 per GB/month |
| **GetObject** | Bandwidth fee | $0.0001 per GB downloaded |
| **Maintenance** | SP maintenance | Included in storage fee |

**Total**: ~$0.003 per GB stored + data transfer costs

## Related Documentation

- **Integration Guide**: [greenfield_integration_guide.md](greenfield_integration_guide.md) - Complete setup
- **Usage Examples**: [greenfield_usage_examples.md](greenfield_usage_examples.md) - Code patterns
- **Quick Start**: [GREENFIELD_QUICKSTART.md](GREENFIELD_QUICKSTART.md) - 5-minute setup
- **Architecture**: [20251128_1340_bnb_greenfield_reputation.plan.md](20251128_1340_bnb_greenfield_reputation.plan.md) - Technical design

## Next Steps

### For Developers

1. **Run E2E Tests**:
   ```bash
   pytest tests/test_greenfield_e2e.py -v -s -m integration
   ```

2. **Review Performance**:
   - Monitor upload/download speeds
   - Check error rates
   - Verify data integrity

3. **Test with Your Data**:
   - Replace test data with your actual reputation data
   - Verify JSON structure compatibility
   - Test realistic file sizes

### For Operations

1. **Monitor Test Results**:
   - Track success/failure rates
   - Measure timing metrics
   - Document any network-specific issues

2. **Plan Production Deployment**:
   - Review performance benchmarks
   - Estimate storage costs for expected usage
   - Set up monitoring and alerting

3. **Prepare Mainnet Migration**:
   - Create mainnet bucket
   - Get mainnet BNB for CreateObject operations
   - Update configuration for mainnet endpoints

## Support

- **Greenfield Documentation**: https://docs.bnbchain.org/bnb-greenfield/
- **Testnet Faucet**: https://gnfd-bsc-testnet-faucet.bnbchain.org/
- **DCellar**: https://dcellar.io/
- **Explorer**: https://greenfieldscan.com/
- **BNB Chain Discord**: https://discord.gg/bnbchain

---

**Ready for complete Greenfield workflow testing!** 🚀

The E2E tests provide confidence that:
- ✅ CreateObject → PutObject workflow works correctly
- ✅ Data integrity is maintained through upload/download
- ✅ Transaction hashes are properly generated and used
- ✅ Public access functions as expected
- ✅ Error handling is robust
- ✅ Performance meets expectations
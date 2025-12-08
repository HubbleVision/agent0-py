# BNB Greenfield Integration Testing Guide

This guide provides step-by-step instructions for setting up and running integration tests with BNB Greenfield testnet.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Testnet Setup](#testnet-setup)
- [Creating Test Bucket](#creating-test-bucket)
- [Getting Transaction Hash](#getting-transaction-hash)
- [Environment Configuration](#environment-configuration)
- [Running Integration Tests](#running-integration-tests)
- [Public Read Setup](#public-read-setup)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### 1. Install Required Dependencies

```bash
# Core dependencies
pip install eth-utils>=2.0.0 eth-account>=0.9.0 requests>=2.31.0

# Testing dependencies
pip install pytest>=7.0.0
```

### 2. Get Testnet BNB

You'll need testnet BNB to pay for storage operations:

1. Create or use an existing EVM wallet (MetaMask, etc.)
2. Get your wallet address (0x...)
3. Visit the BNB Greenfield testnet faucet:
   - Official faucet: https://gnfd-bsc-testnet-faucet.bnbchain.org/
   - Documentation: https://docs.bnbchain.org/bnb-greenfield/getting-started/get-test-bnb/
4. Request testnet BNB (usually available daily)

### 3. Export Your Private Key

⚠️ **Security Warning**: Only use testnet keys, NEVER mainnet keys!

From MetaMask or your wallet:
1. Export your private key (Settings → Security & Privacy → Reveal Private Key)
2. Copy the key (it should be a 64-character hex string)
3. Store it securely in your `.env` file (see [Environment Configuration](#environment-configuration))

## Testnet Setup

### Network Information

**BNB Greenfield Testnet:**
- Chain ID: `5600` (Greenfield testnet)
- RPC Endpoint: `https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org`
- Storage Provider (SP) Endpoints:
  - Primary: `gnfd-testnet-sp1.bnbchain.org`
  - Alternative: `gnfd-testnet-sp2.bnbchain.org`, `gnfd-testnet-sp3.bnbchain.org`
- Explorer: https://greenfieldscan.com/ (testnet mode)

## Creating Test Bucket

You can create a bucket using either the official Greenfield DCellar web app or CLI tools.

### Option A: Using DCellar Web App (Recommended for Testing)

1. Visit DCellar testnet: https://dcellar.io/ (select testnet network)
2. Connect your wallet (MetaMask with testnet BNB)
3. Click "Create Bucket"
4. Configure:
   - **Bucket Name**: Choose a unique name (e.g., `hubble-reputation-test`)
   - **Primary SP**: Select a storage provider (e.g., `SP1`)
   - **Visibility**: Set to "Public Read" if you want to test public access
   - **Payment Account**: Your connected wallet
5. Confirm transaction and wait for confirmation
6. Note down your bucket name

### Option B: Using Greenfield CLI

```bash
# Install Greenfield CLI
# Follow: https://docs.bnbchain.org/bnb-greenfield/for-developers/get-started-dev/

# Create bucket
gnfd-cli bucket create gnfd://hubble-reputation-test \
  --primarySP=gnfd-testnet-sp1.bnbchain.org \
  --visibility=public-read
```

## Getting Transaction Hash

### Understanding Greenfield's Two-Step Upload Process

⚠️ **Important**: Greenfield uses a unique two-step process for uploading data:

**Step 1: CreateObject (On-Chain)**
- Create object metadata on Greenfield blockchain
- Returns a **transaction hash** (txn hash)
- This step validates permissions and reserves storage

**Step 2: PutObject (Off-Chain)**
- Upload actual data to Storage Provider
- **Must include the txn hash** from Step 1 in headers
- SP verifies txn hash on-chain before accepting data

**Why this design?**
- ✅ Prevents spam: Only authorized uploads (proven by on-chain txn)
- ✅ Separates metadata (on-chain) from data (off-chain)
- ✅ Ensures consistency between chain and storage

**Comparison with other systems:**
- **IPFS**: Upload data → Get CID
- **S3**: Upload data → Get confirmation
- **Greenfield**: CreateObject → Get txn hash → Upload with txn hash

### How to Get Transaction Hash

To upload objects to Greenfield, you need to first create an object on-chain (Step 1) and get the transaction hash for use in PutObject (Step 2).

### Method 1: Using Python Script

Save this script as `create_object.py`:

```python
#!/usr/bin/env python3
"""
Create object on Greenfield testnet and get transaction hash.
"""

import os
from web3 import Web3

# Configuration
GREENFIELD_RPC = "https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org"
PRIVATE_KEY = os.getenv("GREENFIELD_PRIVATE_KEY")  # Without 0x prefix
BUCKET_NAME = "hubble-reputation-test"
OBJECT_NAME = "test-object-1"

# Connect to Greenfield
w3 = Web3(Web3.HTTPProvider(GREENFIELD_RPC))

# Get account
account = w3.eth.account.from_key(PRIVATE_KEY)
print(f"Account: {account.address}")

# Prepare CreateObject transaction
# Note: This is a simplified example. In production, you'll need to use
# the Greenfield SDK or construct the proper transaction according to
# the Greenfield protocol.

# For now, you can use the DCellar web app to create objects and get tx hashes

print(f"\nTo get transaction hash:")
print(f"1. Visit https://dcellar.io/ (testnet)")
print(f"2. Navigate to your bucket: {BUCKET_NAME}")
print(f"3. Click 'Upload' and select a file (or create empty object)")
print(f"4. Confirm the transaction")
print(f"5. Copy the transaction hash from MetaMask or the explorer")
```

Run:
```bash
export GREENFIELD_PRIVATE_KEY=your_private_key_without_0x
python create_object.py
```

### Method 2: Using DCellar Web App (Easier)

1. Visit https://dcellar.io/ (testnet mode)
2. Connect your wallet
3. Navigate to your bucket
4. Click "Upload" or "Create Folder"
5. Upload a small test file or create an empty object
6. After transaction confirms, find the transaction hash:
   - Check MetaMask activity/history
   - Or visit https://greenfieldscan.com/ and search for your wallet address
7. Copy the transaction hash (0x...)

### Important Notes on Transaction Hash


The transaction hash is **NOT** the result of uploading data. Instead:

**Key Points:**
- **Workflow**:
  ```
  ```

**Current SDK Limitation:**
- For production: Need to implement CreateObject in code (future enhancement)

**Future Enhancement:**
In the future, the SDK should automatically call CreateObject before PutObject:
```python
# Future ideal usage (not yet implemented)
key = storage.put(key="file", data=b"data")
```

## Environment Configuration

Create a `.env` file in your project root (or export these as environment variables):

```bash
# Required for all tests
GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
GREENFIELD_BUCKET=hubble-reputation-test
GREENFIELD_PRIVATE_KEY=your_private_key_here  # Without 0x prefix

# Required for PUT operations (see "Getting Transaction Hash")

# Optional: Alternative SP hosts for failover testing
GREENFIELD_SP_HOST_ALT=gnfd-testnet-sp2.bnbchain.org


# Optional: Pre-created public object key for public read testing
GREENFIELD_PUBLIC_TEST_OBJECT=public-test-object-key

# Optional: Custom timeout (default: 30 seconds)
GREENFIELD_TIMEOUT=60
```

### Security Best Practices

1. **Never commit `.env` to version control**
   - Add `.env` to `.gitignore`
   - Use `.env.example` for templates

2. **Use testnet keys only**
   - Create a dedicated testnet wallet
   - Never use mainnet private keys

3. **Rotate keys regularly**
   - Generate new testnet keys periodically
   - Invalidate old keys

## Running Integration Tests

### Run All Integration Tests

```bash
# Run all integration tests
pytest tests/test_greenfield_integration.py -v -m integration

# Run with detailed output
pytest tests/test_greenfield_integration.py -v -s -m integration
```

### Run Specific Test Classes

```bash
# Run only basic integration tests
pytest tests/test_greenfield_integration.py::TestGreenfieldIntegration -v -m integration

# Run only public access tests
pytest tests/test_greenfield_integration.py::TestGreenfieldPublicAccess -v -m integration

# Run only factory tests
pytest tests/test_greenfield_integration.py::TestGreenfieldStorageFactory -v -m integration
```

### Run Specific Tests

```bash
# Test PUT/GET roundtrip
pytest tests/test_greenfield_integration.py::TestGreenfieldIntegration::test_put_and_get_roundtrip -v -m integration

# Test public read
pytest tests/test_greenfield_integration.py::TestGreenfieldPublicAccess::test_get_public_object_without_auth -v -m integration
```

### Skip Integration Tests

```bash
# Run all tests EXCEPT integration tests (for local development)
pytest tests/ -v -m "not integration"
```

### Expected Output

Successful test output should look like:

```
tests/test_greenfield_integration.py::TestGreenfieldIntegration::test_put_and_get_roundtrip
Uploading to Greenfield: key=integration-test-1701234567, size=42 bytes
Upload successful: integration-test-1701234567
Retrieving from Greenfield: key=integration-test-1701234567
Retrieval successful: 42 bytes matched
PASSED

tests/test_greenfield_integration.py::TestGreenfieldPublicAccess::test_get_public_object_without_auth
Attempting public read (no Authorization): https://hubble-reputation-test.gnfd-testnet-sp1.bnbchain.org/public-test-object
Public read successful: 256 bytes
This confirms bucket allows public read access
PASSED
```

## Public Read Setup

For testing public read access (without Authorization), you need to configure your bucket ACL.

### Setting Bucket to Public Read

#### Using DCellar

1. Visit https://dcellar.io/ (testnet)
2. Navigate to your bucket
3. Click "Settings" or "Permissions"
4. Set "Visibility" to "Public Read"
5. Confirm transaction

#### Using CLI

```bash
gnfd-cli bucket update gnfd://hubble-reputation-test \
  --visibility=public-read
```

### Creating a Public Test Object

1. Upload a test file to your bucket via DCellar
2. Note the object key (filename)
3. Set environment variable:
   ```bash
   export GREENFIELD_PUBLIC_TEST_OBJECT=my-test-file.txt
   ```
4. Run public read test:
   ```bash
   pytest tests/test_greenfield_integration.py::TestGreenfieldPublicAccess::test_get_public_object_without_auth -v -m integration
   ```

### Verifying Public Access

Test manually with curl:

```bash
# Should succeed without Authorization header
curl -v https://hubble-reputation-test.gnfd-testnet-sp1.bnbchain.org/public-test-object

# Should return 200 OK and object content
```

## Troubleshooting

### Common Issues

#### 1. "403 Forbidden" on PUT

**Symptom**: Upload fails with 403 error

**Possible Causes**:
- Invalid or expired transaction hash
- Signature mismatch
- Insufficient permissions

**Solutions**:
```bash
# Verify your wallet has testnet BNB
curl https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org/balance/{your_address}

# Follow "Getting Transaction Hash" section

# Verify private key matches the wallet that created the bucket
# Check account address in logs
```

#### 2. "404 Not Found" on GET

**Symptom**: Retrieval fails with 404 error

**Possible Causes**:
- Object doesn't exist
- Wrong bucket/object key
- Object not yet propagated

**Solutions**:
```bash
# Verify object exists in DCellar web interface

# Wait longer for propagation (increase sleep time in tests)
time.sleep(5)  # Instead of time.sleep(2)

# Check object key matches exactly (case-sensitive)
```

#### 3. "Tests Skipped" Message

**Symptom**: All integration tests skipped

**Cause**: Missing required environment variables

**Solution**:
```bash
# Verify .env file exists and is loaded
cat .env | grep GREENFIELD

# Export manually for testing
export GREENFIELD_SP_HOST=gnfd-testnet-sp1.bnbchain.org
export GREENFIELD_BUCKET=hubble-reputation-test
export GREENFIELD_PRIVATE_KEY=your_key

# Run tests
pytest tests/test_greenfield_integration.py -v -m integration
```

#### 4. "Connection Timeout"

**Symptom**: Tests timeout after 30-60 seconds

**Possible Causes**:
- Network issues
- SP endpoint down
- Firewall blocking requests

**Solutions**:
```bash
# Try alternative SP endpoint
export GREENFIELD_SP_HOST=gnfd-testnet-sp2.bnbchain.org

# Increase timeout
export GREENFIELD_TIMEOUT=120

# Test connectivity
curl -v https://gnfd-testnet-sp1.bnbchain.org/
```

#### 5. Signature Verification Failed

**Symptom**: "Invalid signature" or "Authorization failed"

**Possible Causes**:
- Incorrect canonical request format
- Wrong signing key
- Clock skew (expiry timestamp)

**Solutions**:
```bash
# Verify system clock is correct
date

# Check private key format (should be 64 hex chars without 0x)
echo $GREENFIELD_PRIVATE_KEY | wc -c  # Should output 65 (64 + newline)

# Enable debug logging
export GREENFIELD_DEBUG=1
pytest tests/test_greenfield_integration.py::TestGreenfieldIntegration::test_put_and_get_roundtrip -v -s -m integration
```

### Getting Help

If you encounter issues not covered here:

1. **Check Greenfield Documentation**:
   - https://docs.bnbchain.org/bnb-greenfield/
   - https://github.com/bnb-chain/greenfield-storage-provider/blob/master/docs/

2. **Verify with DCellar**:
   - Try the same operation via DCellar web app
   - If DCellar works but SDK doesn't, compare request formats

3. **Enable Debug Logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

4. **Check Greenfield Status**:
   - https://greenfieldscan.com/ (testnet mode)
   - Verify SP endpoints are online

5. **Community Support**:
   - BNB Chain Discord: https://discord.gg/bnbchain
   - GitHub Issues: https://github.com/bnb-chain/greenfield

## Mainnet Migration

When moving from testnet to mainnet:

### Configuration Changes

```bash
# Mainnet configuration
GREENFIELD_SP_HOST=gnfd-sp1.bnbchain.org  # Remove 'testnet'
GREENFIELD_BUCKET=hubble-reputation-prod  # New production bucket
GREENFIELD_PRIVATE_KEY=production_key_here  # Dedicated mainnet key

# Mainnet requires real BNB for storage fees
# Estimate costs: https://docs.bnbchain.org/bnb-greenfield/core-concept/billing-payment/
```

### Pre-Mainnet Checklist

- [ ] Test all operations on testnet successfully
- [ ] Verify signature generation is correct
- [ ] Test with realistic data sizes
- [ ] Estimate storage costs for expected usage
- [ ] Set up monitoring for mainnet operations
- [ ] Create dedicated mainnet wallet with production BNB
- [ ] Configure bucket with appropriate ACL (public/private)
- [ ] Set up backup/redundancy strategy
- [ ] Document mainnet deployment procedure
- [ ] Plan rollback strategy

### Mainnet Storage Costs

Greenfield charges for:
- **Storage**: Per GB per month
- **Bandwidth**: Per GB downloaded
- **Transaction fees**: Gas fees for on-chain operations

Estimate costs at: https://docs.bnbchain.org/bnb-greenfield/core-concept/billing-payment/

## Appendix: Quick Reference

### Environment Variables Summary

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GREENFIELD_SP_HOST` | Yes | Storage Provider endpoint | `gnfd-testnet-sp1.bnbchain.org` |
| `GREENFIELD_BUCKET` | Yes | Bucket name | `hubble-reputation-test` |
| `GREENFIELD_PRIVATE_KEY` | Yes | Wallet private key (no 0x) | `abc123...` |
| `GREENFIELD_PUBLIC_TEST_OBJECT` | For public tests | Public object key | `test-file.txt` |
| `GREENFIELD_TIMEOUT` | Optional | Request timeout (seconds) | `60` |

### Useful Links

- **Testnet Faucet**: https://gnfd-bsc-testnet-faucet.bnbchain.org/
- **DCellar App**: https://dcellar.io/
- **Explorer**: https://greenfieldscan.com/
- **Documentation**: https://docs.bnbchain.org/bnb-greenfield/
- **SP API Docs**: https://github.com/bnb-chain/greenfield-storage-provider/blob/master/docs/storage-provider-rest-api/

### Test Command Cheat Sheet

```bash
# Run all integration tests
pytest tests/test_greenfield_integration.py -v -m integration

# Run single test with output
pytest tests/test_greenfield_integration.py::TestGreenfieldIntegration::test_put_and_get_roundtrip -v -s -m integration

# Skip integration tests
pytest tests/ -v -m "not integration"

# Run with debug logging
pytest tests/test_greenfield_integration.py -v -s --log-cli-level=DEBUG -m integration
```

## Related Documentation

- **❓ FAQ**: [GREENFIELD_FAQ.md](GREENFIELD_FAQ.md) - Common questions, especially about transaction hash workflow
- **⚡ Quick Start**: [GREENFIELD_QUICKSTART.md](GREENFIELD_QUICKSTART.md) - 5-minute setup guide
- **💡 Usage Examples**: [greenfield_usage_examples.md](greenfield_usage_examples.md) - Code patterns and best practices
- **📋 Architecture**: [20251128_1340_bnb_greenfield_reuptation.plan.md](20251128_1340_bnb_greenfield_reuptation.plan.md) - Technical design
- **✅ Phase 4 Summary**: [PHASE4_COMPLETION_SUMMARY.md](PHASE4_COMPLETION_SUMMARY.md) - Integration testing completion

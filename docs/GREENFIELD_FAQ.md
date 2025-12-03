# BNB Greenfield Storage - Frequently Asked Questions

Common questions about using BNB Greenfield for reputation data storage in agent0 SDK.

## Upload Process

### Q: Why do I need a transaction hash BEFORE uploading data?

**A:** This is Greenfield's unique design. Unlike IPFS or S3, Greenfield separates metadata from data:

**Traditional storage (IPFS/S3):**
```
You: Upload data →
Storage: Here's your ID/hash
```

**Greenfield:**
```
You: CreateObject on blockchain →
```

**Why this design?**
- ✅ **Prevents spam**: Only uploads with valid on-chain authorization
- ✅ **Decouples layers**: Metadata on-chain, data off-chain
- ✅ **Ensures consistency**: Chain and storage stay synchronized

### Q: Isn't the upload process backwards? Shouldn't uploading give me a hash?

**A:** It seems backwards compared to traditional storage, but it's intentional:

1. **Step 1 (CreateObject)**: You're telling the blockchain "I want to create an object"
   - Blockchain checks permissions, quotas

2. **Step 2 (PutObject)**: You're uploading data to Storage Provider
   - If valid, accepts your data

Think of it like:
- **Traditional**: Upload package → Get tracking number
- **Greenfield**: Get authorization → Upload package with authorization



- If you want to upload 10 objects, you need 10 CreateObject transactions

**Example:**
```python
# Wrong - won't work

```

### Q: How do I get a transaction hash?

**A:** Use one of these methods:

**Method 1: DCellar Web App (Easiest for testing)**
1. Visit https://dcellar.io/ (testnet mode)
2. Click "Upload" in your bucket
3. Select a file to upload
4. Confirm transaction in MetaMask
5. Copy the transaction hash from MetaMask or explorer

**Method 2: Greenfield CLI**
```bash
# Create object on-chain
gnfd-cli object create gnfd://my-bucket/my-file.txt
# Output: txn hash: 0xabc123...

# Upload data using txn hash
gnfd-cli object put --txnHash 0xabc123... my-file.txt gnfd://my-bucket/my-file.txt
```

**Method 3: Programmatically (Future)**
In the future, the SDK should automate this:
```python
# Not yet implemented - future enhancement
key = storage.put(key="file", data=b"data")
```


**A:** You'll get an error:

```python
storage = GreenfieldReputationStorage(
    sp_host="...",
    bucket="...",
    private_key="...",
)

try:
except ValueError as e:
    print(e)
```

## Current SDK Limitations

### Q: Why can't the SDK create objects automatically?

**A:** Current limitation - the SDK only implements PutObject (Step 2), not CreateObject (Step 1).


**Future**: SDK should provide:
```python
# Future API (not yet implemented)
from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

storage = GreenfieldReputationStorage(
    sp_host="...",
    bucket="...",
    private_key="...",
)

key = storage.put(key="file", data=b"data")
```


**A:** Yes, but with limitations:

```python
storage = GreenfieldReputationStorage(
    sp_host="...",
    bucket="...",
    private_key="...",
)

storage.put(key="file1", data=b"data1")  # ✅ Works

```

```python
storage = GreenfieldReputationStorage(
    sp_host="...",
    bucket="...",
    private_key="...",
)

```

## Configuration



```bash
# .env
```

```python
storage = create_reputation_storage()

storage.put(key="file", data=b"data")
```


**Recommendation**: For testing with multiple uploads, either:
2. Get a fresh CreateObject for each upload


**A:** No. Even for public buckets:
- **Download** (GetObject): Public buckets don't need Authorization header (read permission)

```python

# Download - public bucket doesn't need auth
import requests
url = "https://my-bucket.gnfd-testnet-sp1.bnbchain.org/file"
response = requests.get(url)  # No Authorization header needed
```

## Testing

### Q: How do I test uploads without creating objects each time?

**A:** For integration tests, create a test object once and reuse for initial testing:

```python

def test_first_upload():
    storage = create_reputation_storage()
    key = storage.put(key="test1", data=b"data1")  # ✅ Works
    assert storage.get(key=key) == b"data1"

def test_second_upload():
    storage = create_reputation_storage()

    # Option 2: Skip upload tests, only test downloads
    key = "existing-object"  # Already uploaded
    data = storage.get(key=key)  # Just test retrieval
```



Tests gracefully skip if:
```python
# Integration test checks for required config
```

**Solution**: Set it in your environment:
```bash
pytest tests/test_greenfield_integration.py -v -m integration
```

## Comparison with IPFS

### Q: How does this compare to IPFS workflow?

| Aspect | IPFS | Greenfield |
|--------|------|------------|
| **Steps** | 1 step | 2 steps |
| **Authorization** | Optional pinning services | Required on-chain txn |
| **Metadata** | None (unless custom) | On-chain (ownership, ACL, etc.) |
| **Download** | `ipfs.cat(CID)` | GET with optional auth |
| **Key format** | Content-addressed (CID) | Custom (user-defined) |

### Q: Can I use IPFS-style content addressing with Greenfield?

**A:** Yes, manually:

```python
import hashlib

def compute_cid(data: bytes) -> str:
    """Compute content hash (similar to CID)"""
    return hashlib.sha256(data).hexdigest()

# Upload with content-addressed key
data = b"reputation data"
content_hash = compute_cid(data)

storage.put(
    key=f"reputation/by-hash/{content_hash}",
    data=data,
)

# Retrieve by content hash
retrieved = storage.get(key=f"reputation/by-hash/{content_hash}")
```

See [Content Addressing example](greenfield_usage_examples.md#content-addressing-cid-like-keys) for more.

## Production Deployment

### Q: How do I handle CreateObject in production?

**A:** You'll need to implement CreateObject before each upload:

**Option 1: Use Greenfield SDK (recommended future approach)**
```python
# Future enhancement - integrate Greenfield SDK
from greenfield_sdk import GreenfieldClient

client = GreenfieldClient(...)

# Create object on-chain

# Upload data
```

**Option 2: Pre-create objects in batch**
```python
# Before deployment, create 1000 objects via CLI


def upload_reputation(agent_id: str, data: bytes):
```

**Option 3: Create object dynamically (requires blockchain integration)**
```python
from web3 import Web3

def create_object_txn(bucket: str, object_name: str, size: int) -> str:
    """Call CreateObject on Greenfield blockchain"""
    # Implementation depends on Greenfield contract ABI
    # Returns transaction hash
    pass

def upload_with_create(key: str, data: bytes) -> str:
    # Step 1: Create object on-chain

    # Step 2: Upload data
```

### Q: What's the cost of CreateObject operations?

**A:** Each CreateObject is a blockchain transaction with:
- **Gas fees**: Paid in BNB (varies by network congestion)
- **Storage fees**: Charged based on object size and duration

**Estimate costs**: https://docs.bnbchain.org/bnb-greenfield/core-concept/billing-payment/

**Optimization**:
- Batch create objects during off-peak hours
- Use appropriate object sizes (don't create 1KB objects if you'll store 1MB)
- Monitor gas prices and create objects when fees are low

## Troubleshooting

### Q: I get "403 Forbidden" when uploading

**Possible causes:**
2. Signature mismatch (private key doesn't match CreateObject wallet)
3. Insufficient BNB for fees

**Solutions:**
```bash

# 2. Verify private key
# Ensure the private key matches the wallet that created the object

# 3. Check BNB balance
# Visit faucet: https://gnfd-bsc-testnet-faucet.bnbchain.org/
```

### Q: Can I see CreateObject transactions on blockchain?

**A:** Yes:

1. Visit https://greenfieldscan.com/ (testnet mode)
2. Search for your wallet address
3. View "Transactions" tab
4. Look for "CreateObject" transactions
5. Each transaction has a unique hash that you can use for PutObject

## Additional Resources

- **Integration Guide**: [greenfield_integration_guide.md](greenfield_integration_guide.md)
- **Usage Examples**: [greenfield_usage_examples.md](greenfield_usage_examples.md)
- **Quick Start**: [GREENFIELD_QUICKSTART.md](GREENFIELD_QUICKSTART.md)
- **Official Docs**: https://docs.bnbchain.org/bnb-greenfield/

## Still Have Questions?

- Open an issue: https://github.com/agent0lab/agent0-py/issues
- BNB Chain Discord: https://discord.gg/bnbchain
- Greenfield Docs: https://docs.bnbchain.org/bnb-greenfield/

# RPC URL Configuration Fix

## Problem

The original `get_rpc_url()` function in `tests/config.py` had a bug where it always prioritized the global `RPC_URL` environment variable over chain-specific RPC URLs. This caused issues when users had a global RPC URL set (e.g., for Ethereum Sepolia) but wanted to test agents on other chains like BNB Testnet.

**Before Fix:**
```python
def get_rpc_url(chain_id: int) -> str:
    # This always returned RPC_URL regardless of chain_id
    return os.getenv("RPC_URL", DEFAULT_RPC_URLS.get(chain_id, DEFAULT_RPC_URLS[DEFAULT_CHAIN_ID]))
```

## Solution

Fixed the priority order in `get_rpc_url()` and `get_subgraph_url()` functions:

1. **Chain-specific override** (e.g., `RPC_URL_97`, `SUBGRAPH_URL_97`)
2. **Global fallback** (e.g., `RPC_URL`, `SUBGRAPH_URL`)
3. **Default values** from `DEFAULT_RPC_URLS`/`DEFAULT_SUBGRAPH_URLS`

**After Fix:**
```python
def get_rpc_url(chain_id: int) -> str:
    # 1. Check chain-specific override first
    chain_specific_env_var = f"RPC_URL_{chain_id}"
    chain_specific_url = os.getenv(chain_specific_env_var)
    if chain_specific_url:
        return chain_specific_url

    # 2. Fall back to global override for backward compatibility
    global_rpc_url = os.getenv("RPC_URL")
    if global_rpc_url:
        return global_rpc_url

    # 3. Finally, use the default RPC URL for the requested chain
    return DEFAULT_RPC_URLS.get(chain_id, DEFAULT_RPC_URLS[DEFAULT_CHAIN_ID])
```

## Usage

### Chain-Specific Configuration (Recommended)

Set RPC URLs for specific chains:

```bash
# BNB Testnet
export RPC_URL_97=https://custom-bnb-rpc.example.com

# Base Sepolia
export RPC_URL_84532=https://custom-base-rpc.example.com

# Polygon Amoy
export RPC_URL_80002=https://custom-polygon-rpc.example.com
```

Similarly for Subgraph URLs:

```bash
# BNB Testnet Subgraph
export SUBGRAPH_URL_97=https://custom-bnb-subgraph.example.com

# Base Sepolia Subgraph
export SUBGRAPH_URL_84532=https://custom-base-subgraph.example.com
```

### Global Configuration (Legacy)

Set a single RPC URL that affects all chains (maintains backward compatibility):

```bash
# This will be used for all chains unless overridden by chain-specific settings
export RPC_URL=https://global-rpc.example.com
export SUBGRAPH_URL=https://global-subgraph.example.com
```

## Code Usage

```python
from tests.config import get_rpc_url, get_subgraph_url

# Get the correct RPC URL for any chain
bnb_rpc = get_rpc_url(97)          # BNB Testnet
base_rpc = get_rpc_url(84532)      # Base Sepolia
eth_rpc = get_rpc_url(11155111)    # Ethereum Sepolia

# Get Subgraph URLs (returns empty string if not available)
bnb_subgraph = get_subgraph_url(97)    # BNB Testnet subgraph
base_subgraph = get_subgraph_url(84532) # Base Sepolia subgraph
bnb_mainnet_subgraph = get_subgraph_url(56)  # Returns "" (no subgraph available)

# Initialize SDK with chain-specific configuration
sdk = SDK(
    chainId=97,
    rpcUrl=get_rpc_url(97),
    signer=AGENT_PRIVATE_KEY
)
```

## Testing

Run the test suite to verify the fix:

```bash
uv run python tests/test_config_fix.py
```

## Environment Variables Reference

| Variable | Example | Description |
|----------|---------|-------------|
| `RPC_URL_97` | `https://data-seed-prebsc-1-s1.bnbchain.org:8545` | BNB Testnet RPC override |
| `RPC_URL_84532` | `https://sepolia.base.org` | Base Sepolia RPC override |
| `RPC_URL_80002` | `https://rpc-amoy.polygon.technology` | Polygon Amoy RPC override |
| `RPC_URL_59141` | `https://rpc.sepolia.linea.build` | Linea Sepolia RPC override |
| `RPC_URL_11155111` | `https://eth-sepolia.g.alchemy.com/v2/demo` | Ethereum Sepolia RPC override |
| `RPC_URL_56` | `https://bsc-dataseed.binance.org/` | BNB Mainnet RPC override |
| `SUBGRAPH_URL_97` | `https://api.studio.thegraph.com/query/...` | BNB Testnet Subgraph override |
| `SUBGRAPH_URL_84532` | `https://gateway.thegraph.com/api/...` | Base Sepolia Subgraph override |
| `RPC_URL` | `https://global-rpc.example.com` | Global RPC fallback (affects all chains) |
| `SUBGRAPH_URL` | `https://global-subgraph.example.com` | Global Subgraph fallback (affects all chains) |

## Backward Compatibility

This fix maintains full backward compatibility:

1. Existing `RPC_URL` and `SUBGRAPH_URL` environment variables continue to work
2. Existing code using `get_rpc_url()` and `get_subgraph_url()` continues to work
3. No breaking changes to the API

The fix simply adds support for chain-specific overrides while preserving existing behavior for configurations that don't use them.
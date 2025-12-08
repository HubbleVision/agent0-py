"""
Shared configuration loader for test examples.
Loads configuration from environment variables (.env file).

Note: CHAIN_ID is NOT read from environment - tests should specify it directly
when initializing the SDK. Environment variables are only used for optional
overrides (custom contracts, RPC endpoints, etc.).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Look for .env in parent directory (project root)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# ===== Test Configuration =====
# These are used by test scripts when they need default values

# Default chain for tests (Ethereum Sepolia)
# Individual tests can override this by passing chainId to SDK()
DEFAULT_CHAIN_ID = 11155111

# Default RPC URLs for different chains
# Tests can override by passing rpcUrl to SDK()
DEFAULT_RPC_URLS = {
    11155111: "https://eth-sepolia.g.alchemy.com/v2/7nkA4bJ0tKWcl2-5Wn15c5eRdpGZ8DDr",
    84532: "https://sepolia.base.org",
    80002: "https://rpc-amoy.polygon.technology",
    59141: "https://rpc.sepolia.linea.build",
    97: "https://data-seed-prebsc-1-s1.bnbchain.org:8545",
    56: "https://bsc-dataseed.binance.org/",
}

# ===== Optional Environment Variable Overrides =====
# These are OPTIONAL - only needed for testing custom deployments

# Private key for signing transactions
AGENT_PRIVATE_KEY = os.getenv("AGENT_PRIVATE_KEY", "")

# IPFS Configuration (Pinata)
PINATA_JWT = os.getenv("PINATA_JWT", "")

# ===== Deprecated: Legacy Environment Variables =====
# These are kept for backward compatibility with existing tests
# New tests should pass chainId/rpcUrl directly to SDK()

CHAIN_ID = int(os.getenv("CHAIN_ID", str(DEFAULT_CHAIN_ID)))
RPC_URL = os.getenv("RPC_URL", DEFAULT_RPC_URLS.get(CHAIN_ID, DEFAULT_RPC_URLS[DEFAULT_CHAIN_ID]))

# Default Subgraph URLs for different chains
DEFAULT_SUBGRAPH_URLS = {
    11155111: "https://gateway.thegraph.com/api/00a452ad3cd1900273ea62c1bf283f93/subgraphs/id/6wQRC7geo9XYAhckfmfo8kbMRLeWU8KQd3XsJqFKmZLT",
    84532: "https://gateway.thegraph.com/api/00a452ad3cd1900273ea62c1bf283f93/subgraphs/id/GjQEDgEKqoh5Yc8MUgxoQoRATEJdEiH7HbocfR1aFiHa",
    80002: "https://gateway.thegraph.com/api/00a452ad3cd1900273ea62c1bf283f93/subgraphs/id/2A1JB18r1mF2VNP4QBH4mmxd74kbHoM6xLXC8ABAKf7j",
    97: "https://api.studio.thegraph.com/query/1717296/erc-8004-bsc-testnet/version/latest",  # BNB Testnet subgraph
    56: "",  # BNB Mainnet - no subgraph yet, will use on-chain calls
}

SUBGRAPH_URL = os.getenv(
    "SUBGRAPH_URL",
    DEFAULT_SUBGRAPH_URLS.get(CHAIN_ID, DEFAULT_SUBGRAPH_URLS[DEFAULT_CHAIN_ID])
)

# Agent ID for testing (can be overridden via env)
AGENT_ID = os.getenv("AGENT_ID", "11155111:374")


def get_rpc_url(chain_id: int) -> str:
    """Get RPC URL for a specific chain.

    Recommended usage in tests:
        sdk = SDK(
            chainId=97,
            rpcUrl=get_rpc_url(97),
            signer=AGENT_PRIVATE_KEY
        )
    """
    # First check for chain-specific RPC URL override (e.g., RPC_URL_97)
    chain_specific_env_var = f"RPC_URL_{chain_id}"
    chain_specific_url = os.getenv(chain_specific_env_var)
    if chain_specific_url:
        return chain_specific_url

    # Fall back to global RPC URL override for backward compatibility
    # (This maintains existing behavior while allowing chain-specific overrides)
    global_rpc_url = os.getenv("RPC_URL")
    if global_rpc_url:
        return global_rpc_url

    # Finally, use the default RPC URL for the requested chain
    return DEFAULT_RPC_URLS.get(chain_id, DEFAULT_RPC_URLS[DEFAULT_CHAIN_ID])


def get_subgraph_url(chain_id: int) -> str:
    """Get Subgraph URL for a specific chain (if available).

    Returns empty string if no subgraph is available (will use on-chain calls).

    Environment variable priority:
    1. Chain-specific: SUBGRAPH_URL_97, SUBGRAPH_URL_84532, etc.
    2. Global fallback: SUBGRAPH_URL (for backward compatibility)
    3. Default: DEFAULT_SUBGRAPH_URLS for the chain
    """
    # First check for chain-specific subgraph URL override (e.g., SUBGRAPH_URL_97)
    chain_specific_env_var = f"SUBGRAPH_URL_{chain_id}"
    chain_specific_url = os.getenv(chain_specific_env_var)
    if chain_specific_url:
        return chain_specific_url

    # Fall back to global subgraph URL override for backward compatibility
    global_subgraph_url = os.getenv("SUBGRAPH_URL")
    if global_subgraph_url:
        return global_subgraph_url

    # Finally, use the default subgraph URL for the requested chain
    return DEFAULT_SUBGRAPH_URLS.get(chain_id, "")


def print_config():
    """Print current configuration (hiding sensitive values)."""
    print("Configuration:")
    print(f"  DEFAULT_CHAIN_ID: {DEFAULT_CHAIN_ID}")
    print(f"  CHAIN_ID (legacy): {CHAIN_ID}")
    print(f"  RPC_URL: {RPC_URL[:50]}...")
    print(f"  AGENT_PRIVATE_KEY: {'***' if AGENT_PRIVATE_KEY else 'NOT SET'}")
    print(f"  PINATA_JWT: {'***' if PINATA_JWT else 'NOT SET'}")
    print(f"  SUBGRAPH_URL: {SUBGRAPH_URL[:50] if SUBGRAPH_URL else '(empty - use on-chain)'}...")
    print(f"  AGENT_ID: {AGENT_ID}")
    print()
    print("Environment Variable Overrides:")
    print("  Chain-specific RPC URLs: RPC_URL_97, RPC_URL_84532, etc.")
    print("  Chain-specific Subgraph URLs: SUBGRAPH_URL_97, SUBGRAPH_URL_84532, etc.")
    print("  Global fallbacks: RPC_URL, SUBGRAPH_URL (for backward compatibility)")
    print()
    print("Supported Chains:")
    for chain_id, rpc in DEFAULT_RPC_URLS.items():
        chain_names = {
            11155111: "Ethereum Sepolia",
            84532: "Base Sepolia",
            80002: "Polygon Amoy",
            59141: "Linea Sepolia",
            97: "BNB Testnet",
            56: "BNB Mainnet",
        }

        # Show current RPC URL for this chain
        current_rpc = get_rpc_url(chain_id)
        current_subgraph = get_subgraph_url(chain_id)

        print(f"  {chain_id} ({chain_names.get(chain_id, 'Unknown')}):")
        print(f"    Default RPC: {rpc[:50]}...")
        print(f"    Current RPC: {current_rpc[:50]}...")
        if current_subgraph:
            print(f"    Current Subgraph: {current_subgraph[:50]}...")
        else:
            print(f"    Current Subgraph: (on-chain calls only)")
    print()

#!/usr/bin/env python3
"""
Manual test script: register an agent on BSC Testnet (chainId 97) and
verify that the new BSC Testnet subgraph can read it.

Prerequisites:
- Environment variable AGENT_PRIVATE_KEY set to a funded BSC testnet account
- Optional: SUBGRAPH_URL_BNB_TESTNET to override the default subgraph URL
- Optional: RPC_URL to override the default BSC testnet RPC endpoint

Usage:
    python scripts/bsc_testnet_agent_subgraph_check.py
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is on the Python path when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent0_sdk import SDK as _SDK  # noqa: E402
from agent0_sdk.core.contracts import DEFAULT_SUBGRAPH_URLS  # noqa: E402
from tests.config import get_rpc_url  # noqa: E402

if _SDK is None:
    raise ImportError("agent0_sdk.SDK 未正确加载，请确认依赖已安装 (web3 等)")

SDK = _SDK


BNB_TESTNET_CHAIN_ID = 97


def load_private_key() -> str:
    """Load the signing key from environment."""
    private_key = os.getenv("AGENT_PRIVATE_KEY")
    if not private_key:
        raise SystemExit("AGENT_PRIVATE_KEY is required to send transactions on BSC Testnet")
    return private_key


def build_sdk(private_key: str) -> SDK:
    """Initialize SDK with BSC testnet RPC and subgraph settings."""
    rpc_url = get_rpc_url(BNB_TESTNET_CHAIN_ID)
    subgraph_url = os.getenv(
        "SUBGRAPH_URL_BNB_TESTNET",
        DEFAULT_SUBGRAPH_URLS.get(BNB_TESTNET_CHAIN_ID, "")
    )
    overrides = {BNB_TESTNET_CHAIN_ID: subgraph_url} if subgraph_url else None

    sdk = SDK(
        chainId=BNB_TESTNET_CHAIN_ID,
        rpcUrl=rpc_url,
        signer=private_key,
        subgraphOverrides=overrides,
    )

    print(f"Chain ID: {sdk.chainId}")
    print(f"RPC URL: {rpc_url}")
    print(f"Subgraph URL: {subgraph_url or '(not set)'}")
    print(f"Identity registry: {sdk.identity_registry.address}")
    print(f"Reputation registry: {sdk.reputation_registry.address}")
    print(f"Validation registry: {sdk.validation_registry.address}")

    if sdk.web3_client.account:
        balance = sdk.web3_client.get_balance(sdk.web3_client.account.address) / 1e18
        print(f"Signer: {sdk.web3_client.account.address}")
        print(f"Balance: {balance:.6f} BNB")

    return sdk


def extract_agent_id_from_receipt(sdk: SDK, receipt: Dict[str, Any]) -> Optional[int]:
    """Extract agent ID from a transaction receipt using the Registered event."""
    try:
        events = sdk.identity_registry.events.Registered().process_receipt(receipt)
        if events:
            return int(events[0]["args"].get("agentId"))
    except Exception as exc:  # pragma: no cover - best effort parsing
        print(f"Failed to decode Registered event: {exc}")
    return None


def register_agent(sdk: SDK) -> Dict[str, Any]:
    """Send the register transaction and return agent info."""
    ts = int(time.time())
    agent_uri = f"ipfs://bsc-subgraph-check-{ts}"

    print("\nSubmitting register() transaction...")
    tx_hash = sdk.web3_client.transact_contract(
        sdk.identity_registry,
        "register",
        agent_uri,
    )
    print(f"Tx hash: {tx_hash}")

    receipt = sdk.web3_client.wait_for_transaction(tx_hash, timeout=180)
    if receipt.status != 1:
        raise RuntimeError(f"Transaction failed with status {receipt.status}")

    agent_id_numeric = extract_agent_id_from_receipt(sdk, receipt)
    if agent_id_numeric is None:
        # Fallback: use totalSupply as a last resort (may be off if concurrent mints happen)
        agent_id_numeric = sdk.identity_registry.functions.totalSupply().call()

    agent_id = f"{sdk.chainId}:{agent_id_numeric}"

    print("Registration confirmed:")
    print(f"  Agent URI: {agent_uri}")
    print(f"  Agent ID: {agent_id}")
    print(f"  Block: {receipt.blockNumber}")
    print(f"  Gas used: {receipt.gasUsed}")

    return {
        "agent_uri": agent_uri,
        "agent_id": agent_id,
        "token_id": agent_id_numeric,
        "receipt": receipt,
    }


def wait_for_subgraph(agent_id: str, token_id: int, owner: str, sdk: SDK, timeout: int = 240, interval: int = 8) -> Optional[Dict[str, Any]]:
    """Poll the subgraph until the agent appears or timeout occurs.

    兼容当前 BSC Testnet 子图将 chainId 存成 0 的已知问题，优先尝试
    真实 ID（chainId:tokenId），找不到则回退尝试 "0:tokenId"，再按 owner 搜索。
    """
    client = sdk.get_subgraph_client(BNB_TESTNET_CHAIN_ID)
    if not client:
        print("No subgraph client available for BSC Testnet")
        return None

    deadline = time.time() + timeout
    attempt = 1
    candidate_ids = [agent_id, f"0:{token_id}"]
    while time.time() < deadline:
        try:
            # 1) 按 ID 查询（正常应是 chainId:tokenId）
            for cid in candidate_ids:
                agent = client.get_agent_by_id(cid)
                if agent:
                    return agent

            # 2) 按 owner 降级查询（避免 chainId 处理 bug）
            owner_query = f"""
            {{
              agents(where: {{ owner: \"{owner.lower()}\" }}, first: 5, orderBy: createdAt, orderDirection: desc) {{
                id agentId chainId owner agentURI createdAt
              }}
            }}
            """
            owner_result = client.query(owner_query).get("agents", [])
            if owner_result:
                return owner_result[0]
        except Exception as exc:  # pragma: no cover - external call
            print(f"Subgraph query failed (attempt {attempt}): {exc}")

        remaining = int(deadline - time.time())
        print(f"Subgraph not indexed yet, retrying in {interval}s... (remaining ~{remaining}s)")
        attempt += 1
        time.sleep(interval)

    return None


def main() -> bool:
    print("\n=== BSC Testnet agent creation + subgraph verification ===")
    private_key = load_private_key()
    sdk = build_sdk(private_key)

    created = register_agent(sdk)
    agent_id = created["agent_id"]
    token_id = created["token_id"]
    owner = sdk.web3_client.account.address

    print("\nWaiting for subgraph to index the new agent...")
    agent_record = wait_for_subgraph(agent_id, token_id, owner, sdk)

    if not agent_record:
        print("\n❌ Subgraph did not return the agent within the timeout")
        return False

    print("\n✅ Subgraph query succeeded")
    print(f"Agent ID: {agent_record.get('id')}")
    print(f"Chain ID: {agent_record.get('chainId')}")
    print(f"Owner: {agent_record.get('owner')}")
    print(f"Created at: {agent_record.get('createdAt')}")
    print(f"Agent URI: {agent_record.get('agentURI')}")

    return True


if __name__ == "__main__":
    try:
        success = main()
    except KeyboardInterrupt:
        raise SystemExit("Interrupted by user")
    raise SystemExit(0 if success else 1)

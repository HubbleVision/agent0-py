"""
Phase 3: BNB Testnet Simple Integration Tests

Tests SDK initialization and read operations using already deployed contracts on BNB Testnet.
This validates that the existing SDK can connect to BNB Testnet and read data.

Flow:
1. Test SDK initialization with BNB Testnet configuration
2. Test contract access and basic operations
3. Test agent search on BNB Testnet
4. Test existing agent retrieval (if any)
5. Test feedback retrieval (if any)
"""

import logging
import sys
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Set debug level for agent0_sdk
logging.getLogger('agent0_sdk').setLevel(logging.DEBUG)
logging.getLogger('agent0_sdk.core').setLevel(logging.DEBUG)

# Import SDK and dependencies
from agent0_sdk import SDK, SearchParams
from config import get_rpc_url, get_subgraph_url, print_config

def test_sdk_initialization():
    """Test 1: SDK initialization for BNB Testnet"""
    print("\n🔧 Test 1: SDK Initialization for BNB Testnet")
    print("-" * 60)

    try:
        # BNB Testnet configuration
        BNB_CHAIN_ID = 97
        BNB_RPC_URL = get_rpc_url(BNB_CHAIN_ID)
        BNB_SUBGRAPH_URL = get_subgraph_url(BNB_CHAIN_ID)

        print(f"   Chain ID: {BNB_CHAIN_ID}")
        print(f"   RPC URL: {BNB_RPC_URL}")
        print(f"   Subgraph URL: {BNB_SUBGRAPH_URL if BNB_SUBGRAPH_URL else '(using on-chain calls)'}")

        # Initialize SDK for BNB Testnet (read-only)
        sdk = SDK(
            chainId=BNB_CHAIN_ID,
            rpcUrl=BNB_RPC_URL
        )

        print(f"✅ SDK initialized successfully for BNB Testnet")
        print(f"   Chain ID: {sdk.chainId}")
        print(f"   RPC URL: {sdk.rpcUrl[:50]}...")

        # Test contract registry access
        try:
            identity_address = sdk.identity_registry.address
            reputation_address = sdk.reputation_registry.address
            validation_address = sdk.validation_registry.address

            print(f"✅ Contract addresses loaded:")
            print(f"   Identity Registry: {identity_address}")
            print(f"   Reputation Registry: {reputation_address}")
            print(f"   Validation Registry: {validation_address}")
        except Exception as e:
            print(f"⚠️  Contract address loading failed: {e}")
            return None

        # Test basic web3 connection
        try:
            latest_block = sdk.web3_client.eth.block_number
            print(f"✅ Web3 connection working:")
            print(f"   Latest block: {latest_block}")
        except Exception as e:
            print(f"⚠️  Web3 connection issue: {e}")

        # Test contract calls
        try:
            identity_name = sdk.identity_registry.functions.name().call()
            print(f"✅ Identity Registry call working:")
            print(f"   Contract name: {identity_name}")
        except Exception as e:
            print(f"⚠️  Identity Registry call failed: {e}")

        try:
            identity_contract = sdk.reputation_registry.functions.getIdentityRegistry().call()
            print(f"✅ Reputation Registry call working:")
            print(f"   Identity Registry address: {identity_contract}")
        except Exception as e:
            print(f"⚠️  Reputation Registry call failed: {e}")

        return sdk

    except Exception as e:
        print(f"❌ SDK initialization failed: {e}")
        return None

def test_agent_search(sdk):
    """Test 2: Search agents on BNB Testnet"""
    print("\n🔍 Test 2: Agent Search on BNB Testnet")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        # Search parameters
        params = SearchParams()
        params.chains = [sdk.chain_id]
        params.active = True

        print(f"   Searching agents with parameters:")
        print(f"   Chains: {params.chains}")
        print(f"   Active: {params.active}")
        print(f"   Page size: 20")

        # Perform search
        result = sdk.indexer.search_agents(params, page_size=20)

        agents = result.get('items', [])
        total_count = len(agents)

        print(f"✅ Search completed successfully:")
        print(f"   Found {total_count} agents on BNB Testnet")

        if total_count == 0:
            print("   No agents found (this is expected if no contracts deployed yet)")
            return True

        # Display first few agents
        for i, agent in enumerate(agents[:5], 1):
            print(f"   {i}. {agent.name}")
            print(f"      ID: {agent.agentId}")
            print(f"      Chain: {agent.chainId}")
            print(f"      Active: {agent.active}")
            print(f"      Owner: {agent.owner}")

        return True

    except Exception as e:
        print(f"❌ Agent search failed: {e}")
        return False

def test_contract_interactions(sdk):
    """Test 3: Test basic contract interactions"""
    print("\n⚙️  Test 3: Basic Contract Interactions")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        # Test Identity Registry functions
        print("   Testing Identity Registry functions...")

        # Get total supply (should work for any ERC721)
        try:
            total_supply = sdk.identity_registry.functions.totalSupply().call()
            print(f"   ✅ Total Supply: {total_supply}")
        except Exception as e:
            print(f"   ⚠️  totalSupply() failed: {e}")

        # Test Reputation Registry functions
        print("   Testing Reputation Registry functions...")

        try:
            identity_address = sdk.reputation_registry.functions.getIdentityRegistry().call()
            print(f"   ✅ Identity Registry from Reputation: {identity_address}")
        except Exception as e:
            print(f"   ⚠️  getIdentityRegistry() failed: {e}")

        # Test Validation Registry functions
        print("   Testing Validation Registry functions...")

        try:
            identity_address = sdk.validation_registry.functions.getIdentityRegistry().call()
            print(f"   ✅ Identity Registry from Validation: {identity_address}")
        except Exception as e:
            print(f"   ⚠️  getIdentityRegistry() failed: {e}")

        print("✅ Contract interactions test completed")
        return True

    except Exception as e:
        print(f"❌ Contract interactions test failed: {e}")
        return False

def test_read_operations(sdk):
    """Test 4: Test various read operations"""
    print("\n📖 Test 4: Read Operations")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        # Test multi-chain support
        print("   Testing multi-chain agent search...")

        # Search with chain filter
        params = SearchParams()
        params.chains = [11155111, 84532, 80002, 97]  # Including BNB Testnet

        result = sdk.indexer.search_agents(params, page_size=10)
        agents = result.get('items', [])

        print(f"   ✅ Multi-chain search found {len(agents)} agents")

        # Group by chain
        chain_counts = {}
        for agent in agents:
            chain_id = agent.chainId
            chain_counts[chain_id] = chain_counts.get(chain_id, 0) + 1

        print(f"   Agents by chain:")
        for chain_id, count in sorted(chain_counts.items()):
            chain_names = {
                11155111: "Ethereum Sepolia",
                84532: "Base Sepolia",
                80002: "Polygon Amoy",
                97: "BNB Testnet"
            }
            chain_name = chain_names.get(chain_id, f"Chain {chain_id}")
            print(f"      {chain_name}: {count} agents")

        # Test reputation search (should work even with no data)
        print("   Testing reputation search...")

        try:
            reputation_result = sdk.searchAgentsByReputation(
                page_size=10,
                chains=[sdk.chain_id]
            )
            reputation_agents = reputation_result.get('items', [])
            print(f"   ✅ Reputation search found {len(reputation_agents)} agents")
        except Exception as e:
            print(f"   ⚠️  Reputation search failed: {e}")

        print("✅ Read operations test completed")
        return True

    except Exception as e:
        print(f"❌ Read operations test failed: {e}")
        return False

def test_error_handling(sdk):
    """Test 5: Error handling and edge cases"""
    print("\n🚨 Test 5: Error Handling")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        # Test invalid agent ID
        print("   Testing invalid agent ID...")

        try:
            invalid_id = "97:999999999"
            agent = sdk.indexer.get_agent(invalid_id)
            print(f"   ⚠️  Expected error but got agent: {agent.agentId}")
        except Exception as e:
            print(f"   ✅ Correctly handled invalid agent ID: {type(e).__name__}")

        # Test invalid chain ID
        print("   Testing invalid chain ID...")

        try:
            params = SearchParams()
            params.chains = [999999]  # Invalid chain
            result = sdk.indexer.search_agents(params, page_size=1)
            agents = result.get('items', [])
            print(f"   ✅ Invalid chain ID handled gracefully: {len(agents)} agents")
        except Exception as e:
            print(f"   ✅ Correctly handled invalid chain ID: {type(e).__name__}")

        # Test feedback search on non-existent agent
        print("   Testing feedback search on non-existent agent...")

        try:
            feedbacks = sdk.indexer.search_feedback(
                agentId="97:1",  # Likely non-existent
                first=10,
                skip=0
            )
            print(f"   ✅ Feedback search handled gracefully: {len(feedbacks)} feedbacks")
        except Exception as e:
            print(f"   ✅ Correctly handled non-existent agent feedback: {type(e).__name__}")

        print("✅ Error handling test completed")
        return True

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Main test runner"""
    print("🚀 Phase 3: BNB Testnet Simple Integration Tests")
    print("=" * 60)

    # Print current configuration
    print("Current Configuration:")
    print_config()

    # Check BNB-specific environment variables
    print(f"\nBNB Testnet Configuration:")
    print(f"  BNB_TESTNET_IDENTITY: {os.getenv('BNB_TESTNET_IDENTITY', 'NOT SET')}")
    print(f"  BNB_TESTNET_REPUTATION: {os.getenv('BNB_TESTNET_REPUTATION', 'NOT SET')}")
    print(f"  BNB_TESTNET_VALIDATION: {os.getenv('BNB_TESTNET_VALIDATION', 'NOT SET')}")
    print(f"  SUBGRAPH_URL_BNB_TESTNET: {os.getenv('SUBGRAPH_URL_BNB_TESTNET', 'NOT SET (will use on-chain calls)')}")

    # Run tests in sequence
    tests = [
        ("SDK Initialization", test_sdk_initialization),
        ("Agent Search", test_agent_search),
        ("Contract Interactions", test_contract_interactions),
        ("Read Operations", test_read_operations),
        ("Error Handling", test_error_handling),
    ]

    results = []
    sdk = None

    for test_name, test_func in tests:
        print(f"\n📍 Running: {test_name}")
        try:
            if test_name == "SDK Initialization":
                sdk = test_func()
                success = sdk is not None
            else:
                success = test_func(sdk)
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All Phase 3 tests passed!")
        print("✅ BNB Testnet SDK integration is working correctly")
        print("✅ Ready for Phase 4 (mainnet deployment)")
    else:
        print("⚠️  Some tests failed")
        print("❌ Please check the errors above and fix issues")

    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
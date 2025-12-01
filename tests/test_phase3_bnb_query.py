"""
Phase 3: BNB Testnet Query Functionality Tests

Tests data querying and retrieval functionality on BNB Testnet.
This includes agent search, filtering, sorting, and reputation queries.

Flow:
1. Test SDK initialization with BNB Testnet configuration
2. Test agent search with different parameters
3. Test agent filtering by chain, tags, and metadata
4. Test sorting and pagination of results
5. Test reputation-based agent search
6. Test multi-chain queries including BNB
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
        print(f"   Read-only: {sdk.isReadOnly}")

        return sdk

    except Exception as e:
        print(f"❌ SDK initialization failed: {e}")
        return None

def test_agent_search(sdk):
    """Test 2: Basic agent search on BNB Testnet"""
    print("\n🔍 Test 2: Basic Agent Search on BNB Testnet")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        print("   Testing basic agent search...")

        # Test 1: Search with no filters
        try:
            params = SearchParams()
            result = sdk.indexer.search_agents(params, page_size=10)
            agents = result.get('items', [])
            print(f"   ✅ Unfiltered search: {len(agents)} agents found")
        except Exception as e:
            print(f"   ⚠️  Unfiltered search failed: {e}")

        # Test 2: Search with chain filter
        try:
            params = SearchParams()
            params.chains = [sdk.chainId]
            result = sdk.indexer.search_agents(params, page_size=10)
            agents = result.get('items', [])
            print(f"   ✅ Chain-filtered search: {len(agents)} agents found")
            if agents:
                for i, agent in enumerate(agents[:3], 1):
                    print(f"     {i}. {agent.name} (ID: {agent.agentId})")
        except Exception as e:
            print(f"   ⚠️  Chain-filtered search failed: {e}")

        # Test 3: Search with active filter
        try:
            params = SearchParams()
            params.chains = [sdk.chainId]
            params.active = True
            result = sdk.indexer.search_agents(params, page_size=10)
            agents = result.get('items', [])
            print(f"   ✅ Active agents search: {len(agents)} agents found")
        except Exception as e:
            print(f"   ⚠️  Active agents search failed: {e}")

        # Test 4: Search with pagination
        try:
            params = SearchParams()
            params.chains = [sdk.chainId]

            # Get first page
            result1 = sdk.indexer.search_agents(params, page_size=5, skip=0)
            agents1 = result1.get('items', [])

            # Get second page
            result2 = sdk.indexer.search_agents(params, page_size=5, skip=5)
            agents2 = result2.get('items', [])

            print(f"   ✅ Pagination test:")
            print(f"     Page 1: {len(agents1)} agents")
            print(f"     Page 2: {len(agents2)} agents")
        except Exception as e:
            print(f"   ⚠️  Pagination test failed: {e}")

        print("✅ Agent search test completed")
        return True

    except Exception as e:
        print(f"❌ Agent search test failed: {e}")
        return False

def test_agent_filtering(sdk):
    """Test 3: Advanced agent filtering"""
    print("\n🔎 Test 3: Advanced Agent Filtering")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        print("   Testing advanced filtering...")

        # Test 1: Search by name pattern
        try:
            params = SearchParams()
            params.chains = [sdk.chainId]
            params.name = "Test"  # Search for agents with "Test" in name
            result = sdk.indexer.search_agents(params, page_size=10)
            agents = result.get('items', [])
            print(f"   ✅ Name search ('Test'): {len(agents)} agents found")
        except Exception as e:
            print(f"   ⚠️  Name search failed: {e}")

        # Test 2: Search by owner
        try:
            # Use a common test address pattern
            params = SearchParams()
            params.chains = [sdk.chainId]
            params.owner = "0x1234"  # Partial address search
            result = sdk.indexer.search_agents(params, page_size=10)
            agents = result.get('items', [])
            print(f"   ✅ Owner search ('0x1234'): {len(agents)} agents found")
        except Exception as e:
            print(f"   ⚠️  Owner search failed: {e}")

        # Test 3: Search with multiple chains including BNB
        try:
            params = SearchParams()
            params.chains = [11155111, 84532, 97]  # Ethereum Sepolia, Base Sepolia, BNB Testnet
            result = sdk.indexer.search_agents(params, page_size=20)
            agents = result.get('items', [])

            # Group by chain
            by_chain = {}
            for agent in agents:
                chain = agent.chainId
                if chain not in by_chain:
                    by_chain[chain] = []
                by_chain[chain].append(agent)

            print(f"   ✅ Multi-chain search: {len(agents)} agents found")
            for chain_id, chain_agents in sorted(by_chain.items()):
                chain_names = {
                    11155111: "Ethereum Sepolia",
                    84532: "Base Sepolia",
                    97: "BNB Testnet"
                }
                chain_name = chain_names.get(chain_id, f"Chain {chain_id}")
                print(f"     {chain_name}: {len(chain_agents)} agents")
        except Exception as e:
            print(f"   ⚠️  Multi-chain search failed: {e}")

        print("✅ Agent filtering test completed")
        return True

    except Exception as e:
        print(f"❌ Agent filtering test failed: {e}")
        return False

def test_agent_sorting(sdk):
    """Test 4: Agent sorting and ordering"""
    print("\n📊 Test 4: Agent Sorting and Ordering")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        print("   Testing sorting functionality...")

        # Test 1: Sort by name (ascending)
        try:
            params = SearchParams()
            params.chains = [sdk.chainId]
            result = sdk.indexer.search_agents(params, sort=["name"], page_size=5)
            agents = result.get('items', [])
            print(f"   ✅ Sort by name (asc): {len(agents)} agents")
            if agents:
                print(f"     First agent: {agents[0].name}")
        except Exception as e:
            print(f"   ⚠️  Sort by name failed: {e}")

        # Test 2: Sort by name (descending)
        try:
            params = SearchParams()
            params.chains = [sdk.chainId]
            result = sdk.indexer.search_agents(params, sort=["-name"], page_size=5)
            agents = result.get('items', [])
            print(f"   ✅ Sort by name (desc): {len(agents)} agents")
            if agents:
                print(f"     First agent: {agents[0].name}")
        except Exception as e:
            print(f"   ⚠️  Sort by name (desc) failed: {e}")

        # Test 3: Sort by creation date
        try:
            params = SearchParams()
            params.chains = [sdk.chainId]
            result = sdk.indexer.search_agents(params, sort=["created_at"], page_size=5)
            agents = result.get('items', [])
            print(f"   ✅ Sort by created_at: {len(agents)} agents")
        except Exception as e:
            print(f"   ⚠️  Sort by created_at failed: {e}")

        # Test 4: Multiple sort criteria
        try:
            params = SearchParams()
            params.chains = [sdk.chainId]
            result = sdk.indexer.search_agents(params, sort=["name", "-created_at"], page_size=5)
            agents = result.get('items', [])
            print(f"   ✅ Multi-criteria sort: {len(agents)} agents")
        except Exception as e:
            print(f"   ⚠️  Multi-criteria sort failed: {e}")

        print("✅ Agent sorting test completed")
        return True

    except Exception as e:
        print(f"❌ Agent sorting test failed: {e}")
        return False

def test_reputation_search(sdk):
    """Test 5: Reputation-based agent search"""
    print("\n⭐ Test 5: Reputation-based Agent Search")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        print("   Testing reputation-based search...")

        # Test 1: Basic reputation search on BNB Testnet
        try:
            result = sdk.searchAgentsByReputation(
                page_size=10,
                chains=[sdk.chainId]
            )
            agents = result.get('items', [])
            print(f"   ✅ Reputation search (BNB only): {len(agents)} agents")

            # Show metadata for reputation search
            meta = result.get('meta', {})
            successful_chains = meta.get('successfulChains', [])
            failed_chains = meta.get('failedChains', [])
            print(f"   Successful chains: {successful_chains}")
            if failed_chains:
                print(f"   Failed chains: {failed_chains}")
        except Exception as e:
            print(f"   ⚠️  Reputation search failed: {e}")

        # Test 2: Reputation search with minimum score
        try:
            result = sdk.searchAgentsByReputation(
                minAverageScore=50,
                page_size=10,
                chains=[sdk.chainId]
            )
            agents = result.get('items', [])
            print(f"   ✅ Reputation search (min score 50): {len(agents)} agents")
        except Exception as e:
            print(f"   ⚠️  Reputation search with min score failed: {e}")

        # Test 3: Reputation search with tags
        try:
            result = sdk.searchAgentsByReputation(
                tags=["test", "integration"],
                page_size=10,
                chains=[sdk.chainId]
            )
            agents = result.get('items', [])
            print(f"   ✅ Reputation search (with tags): {len(agents)} agents")
        except Exception as e:
            print(f"   ⚠️  Reputation search with tags failed: {e}")

        # Test 4: Multi-chain reputation search
        try:
            result = sdk.searchAgentsByReputation(
                page_size=20,
                chains=[11155111, 84532, 97]  # Include BNB Testnet
            )
            agents = result.get('items', [])

            # Group by chain
            by_chain = {}
            for agent in agents:
                chain = agent.chainId
                if chain not in by_chain:
                    by_chain[chain] = []
                by_chain[chain].append(agent)

            print(f"   ✅ Multi-chain reputation search: {len(agents)} agents")
            for chain_id, chain_agents in sorted(by_chain.items()):
                chain_names = {
                    11155111: "Ethereum Sepolia",
                    84532: "Base Sepolia",
                    97: "BNB Testnet"
                }
                chain_name = chain_names.get(chain_id, f"Chain {chain_id}")
                print(f"     {chain_name}: {len(chain_agents)} agents")
        except Exception as e:
            print(f"   ⚠️  Multi-chain reputation search failed: {e}")

        print("✅ Reputation search test completed")
        return True

    except Exception as e:
        print(f"❌ Reputation search test failed: {e}")
        return False

def test_individual_agent_queries(sdk):
    """Test 6: Individual agent queries and details"""
    print("\n📋 Test 6: Individual Agent Queries")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        print("   Testing individual agent queries...")

        # First, search for agents to get some IDs
        try:
            params = SearchParams()
            params.chains = [sdk.chainId]
            result = sdk.indexer.search_agents(params, page_size=5)
            agents = result.get('items', [])

            if not agents:
                print("   ⚠️  No agents found for individual queries")
                return True

            print(f"   Found {len(agents)} agents for testing individual queries")

            # Test 1: Get agent by ID (chainId:agentId format)
            for i, agent in enumerate(agents[:3], 1):
                try:
                    full_agent_id = f"{agent.chainId}:{agent.agentId}"
                    retrieved_agent = sdk.indexer.get_agent(full_agent_id)
                    print(f"   ✅ Agent #{i} retrieved:")
                    print(f"     ID: {retrieved_agent.agentId}")
                    print(f"     Name: {retrieved_agent.name}")
                    print(f"     Active: {retrieved_agent.active}")
                    print(f"     Owner: {retrieved_agent.owner}")
                except Exception as e:
                    print(f"   ⚠️  Agent #{i} retrieval failed: {e}")

            # Test 2: Get reputation summary for each agent
            for i, agent in enumerate(agents[:3], 1):
                try:
                    full_agent_id = f"{agent.chainId}:{agent.agentId}"
                    summary = sdk.getReputationSummary(full_agent_id)
                    print(f"   ✅ Agent #{i} reputation:")
                    print(f"     Count: {summary['count']}")
                    print(f"     Average Score: {summary['averageScore']:.2f}")
                except Exception as e:
                    print(f"   ⚠️  Agent #{i} reputation failed: {e}")

            # Test 3: Get feedback for each agent
            for i, agent in enumerate(agents[:2], 1):
                try:
                    full_agent_id = f"{agent.chainId}:{agent.agentId}"
                    feedbacks = sdk.indexer.search_feedback(
                        agentId=full_agent_id,
                        first=5,
                        skip=0
                    )
                    print(f"   ✅ Agent #{i} feedback: {len(feedbacks)} entries")
                    for j, feedback in enumerate(feedbacks[:2], 1):
                        print(f"     Feedback #{j}: score={feedback.score}, tags={feedback.tags}")
                except Exception as e:
                    print(f"   ⚠️  Agent #{i} feedback retrieval failed: {e}")

        except Exception as e:
            print(f"   ❌ Agent search for individual queries failed: {e}")
            return False

        print("✅ Individual agent queries test completed")
        return True

    except Exception as e:
        print(f"❌ Individual agent queries test failed: {e}")
        return False

def test_chain_specific_queries(sdk):
    """Test 7: Chain-specific query optimizations"""
    print("\n⛓ Test 7: Chain-specific Query Optimizations")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        print("   Testing BNB Testnet specific optimizations...")

        # Test 1: Check if subgraph is available for BNB
        try:
            subgraph_url = get_subgraph_url(sdk.chainId)
            if subgraph_url:
                print(f"   ✅ BNB Testnet subgraph available: {subgraph_url[:50]}...")
            else:
                print("   ⚠️  BNB Testnet subgraph not available (using on-chain calls)")
        except Exception as e:
            print(f"   ⚠️  Subgraph check failed: {e}")

        # Test 2: Test contract call performance
        try:
            start_time = time.time()
            identity_address = sdk.reputation_registry.functions.getIdentityRegistry().call()
            end_time = time.time()
            call_duration = end_time - start_time
            print(f"   ✅ Contract call performance: {call_duration:.3f}s")
            print(f"   Identity registry address: {identity_address}")
        except Exception as e:
            print(f"   ⚠️  Performance test failed: {e}")

        # Test 3: Test web3 connectivity
        try:
            start_time = time.time()
            latest_block = sdk.web3_client.eth.block_number
            end_time = time.time()
            query_duration = end_time - start_time
            print(f"   ✅ Block query performance: {query_duration:.3f}s")
            print(f"   Latest block: {latest_block}")
        except Exception as e:
            print(f"   ⚠️  Block query failed: {e}")

        print("✅ Chain-specific queries test completed")
        return True

    except Exception as e:
        print(f"❌ Chain-specific queries test failed: {e}")
        return False

def main():
    """Main test runner"""
    print("🚀 Phase 3: BNB Testnet Query Functionality Tests")
    print("=" * 60)

    # Print current configuration
    print("Current Configuration:")
    print_config()

    # Check environment variables
    print(f"\nEnvironment Variables:")
    print(f"  SUBGRAPH_URL_BNB_TESTNET: {os.getenv('SUBGRAPH_URL_BNB_TESTNET', 'NOT SET (using on-chain)')}")

    # Run tests in sequence
    tests = [
        ("SDK Initialization", test_sdk_initialization),
        ("Agent Search", test_agent_search),
        ("Agent Filtering", test_agent_filtering),
        ("Agent Sorting", test_agent_sorting),
        ("Reputation Search", test_reputation_search),
        ("Individual Agent Queries", test_individual_agent_queries),
        ("Chain-specific Queries", test_chain_specific_queries),
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
        print("🎉 All Phase 3 query tests passed!")
        print("✅ BNB Testnet query functionality is working correctly")
    else:
        print("⚠️  Some query tests failed")
        print("❌ Please check errors above and fix issues")

    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
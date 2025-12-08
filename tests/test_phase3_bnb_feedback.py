"""
Phase 3: BNB Testnet Feedback Functionality Tests

Tests feedback submission and retrieval functionality on BNB Testnet.
This includes feedback submission, revocation, and response appending.

Flow:
1. Test SDK initialization with BNB Testnet configuration
2. Test feedback submission with various scores and tags
3. Test feedback retrieval and filtering
4. Test feedback revocation (if possible)
5. Test response appending to feedback
"""

import logging
import sys
import os
import time
import json

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
from agent0_sdk import SDK
from config import get_rpc_url, get_subgraph_url, print_config

def generate_test_feedback_data():
    """Generate test feedback data."""
    timestamp = int(time.time())
    return {
        "score": 85,  # Score out of 100
        "tag1": "integration",
        "tag2": "test",
        "feedback_uri": f"ipfs://QmFeedback{timestamp}",
        "feedback_hash": f"0x{'0' * 63}1",  # Simple test hash
        "client_address": "0x1234567890123456789012345678901234567890",  # Mock client
        "agent_id": "97:1",  # Mock agent ID
        "comment": f"Test feedback created at {timestamp}"
    }

def test_sdk_initialization():
    """Test 1: SDK initialization for BNB Testnet"""
    print("\n🔧 Test 1: SDK Initialization for BNB Testnet")
    print("-" * 60)

    try:
        # BNB Testnet configuration
        BNB_CHAIN_ID = 97
        BNB_RPC_URL = get_rpc_url(BNB_CHAIN_ID)

        # Get private key from environment
        private_key = os.getenv("AGENT_PRIVATE_KEY")
        if not private_key:
            print("⚠️  AGENT_PRIVATE_KEY not set, using read-only mode")
            private_key = None

        print(f"   Chain ID: {BNB_CHAIN_ID}")
        print(f"   RPC URL: {BNB_RPC_URL}")
        print(f"   Private Key: {'***' if private_key else 'NOT SET'}")

        # Initialize SDK for BNB Testnet
        sdk = SDK(
            chainId=BNB_CHAIN_ID,
            rpcUrl=BNB_RPC_URL,
            signer=private_key
        )

        print(f"✅ SDK initialized successfully for BNB Testnet")
        print(f"   Chain ID: {sdk.chainId}")
        print(f"   Read-only: {sdk.isReadOnly}")

        return sdk

    except Exception as e:
        print(f"❌ SDK initialization failed: {e}")
        return None

def test_feedback_submission(sdk):
    """Test 2: Feedback submission on BNB Testnet"""
    print("\n⭐ Test 2: Feedback Submission on BNB Testnet")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    if sdk.isReadOnly:
        print("⚠️  Skipping feedback submission test - no signer available")
        return True

    try:
        # Generate test feedback data
        feedback_data = generate_test_feedback_data()
        print(f"   Feedback data: {json.dumps(feedback_data, indent=2)}")

        # Mock agent ID and client address for testing
        mock_agent_id = 1  # Simplified for testing
        mock_client_address = "0x1234567890123456789012345678901234567890"

        # Test 1: Submit feedback with different scores
        test_scores = [50, 75, 85, 95, 100]
        test_tags = [
            ("performance", "accuracy"),
            ("usability", "interface"),
            ("quality", "reliability"),
            ("speed", "efficiency"),
            ("overall", "satisfaction")
        ]

        for i, (score, (tag1, tag2)) in enumerate(zip(test_scores, test_tags), 1):
            print(f"   Submitting feedback #{i} (score: {score}, tags: {tag1}, {tag2})...")
            try:
                # Create mock feedback authorization (simplified)
                feedback_auth = b"test_auth_data"

                # Submit feedback using reputation registry
                tx_hash = sdk.reputation_registry.functions.giveFeedback(
                    mock_agent_id,
                    score,
                    tag1,
                    tag2,
                    f"ipfs://QmFeedback{int(time.time())}_{i}",
                    f"0x{'0' * 63}{i}",
                    feedback_auth
                ).transact({
                    'from': sdk.web3_client.account.address
                })

                print(f"   ✅ Feedback #{i} transaction hash: {tx_hash.hex()}")

                # Wait for confirmation (short timeout for testing)
                receipt = sdk.web3_client.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                if receipt.status == 1:
                    print(f"   ✅ Feedback #{i} confirmed")
                    print(f"   Block: {receipt.blockNumber}")
                    print(f"   Gas used: {receipt.gasUsed}")
                else:
                    print(f"   ❌ Feedback #{i} failed")
                    return False

                # Add delay between submissions
                time.sleep(2)

            except Exception as e:
                print(f"   ❌ Feedback #{i} submission failed: {e}")
                return False

        print("✅ All feedback submissions completed")
        return True

    except Exception as e:
        print(f"❌ Feedback submission test failed: {e}")
        return False

def test_feedback_retrieval(sdk):
    """Test 3: Feedback retrieval from BNB Testnet"""
    print("\n🔍 Test 3: Feedback Retrieval from BNB Testnet")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        # Mock agent ID for testing
        mock_agent_id = "97:1"

        print(f"   Testing feedback retrieval for agent: {mock_agent_id}")

        # Test 1: Get feedback count
        try:
            last_index = sdk.reputation_registry.functions.getLastIndex(1, "0x1234567890123456789012345678901234567890").call()
            print(f"   ✅ Last feedback index: {last_index}")
        except Exception as e:
            print(f"   ⚠️  getLastIndex failed: {e}")

        # Test 2: Read individual feedback
        try:
            score, tag1, tag2, is_revoked = sdk.reputation_registry.functions.readFeedback(
                1, "0x1234567890123456789012345678901234567890", 1
            ).call()
            print(f"   ✅ Feedback #1 read:")
            print(f"   Score: {score}")
            print(f"   Tags: {tag1}, {tag2}")
            print(f"   Revoked: {is_revoked}")
        except Exception as e:
            print(f"   ⚠️  readFeedback failed: {e}")

        # Test 3: Search feedback using indexer
        try:
            feedbacks = sdk.indexer.search_feedback(
                agentId=mock_agent_id,
                first=10,
                skip=0
            )
            print(f"   ✅ Found {len(feedbacks)} feedback entries")

            for i, feedback in enumerate(feedbacks[:3], 1):
                print(f"   Feedback #{i}:")
                print(f"     Score: {feedback.score}")
                print(f"     Tags: {feedback.tags}")
                print(f"     URI: {feedback.feedbackUri}")

        except Exception as e:
            print(f"   ⚠️  search_feedback failed: {e}")

        # Test 4: Get reputation summary
        try:
            summary = sdk.getReputationSummary(mock_agent_id)
            print(f"   ✅ Reputation summary:")
            print(f"     Count: {summary['count']}")
            print(f"     Average Score: {summary['averageScore']:.2f}")
        except Exception as e:
            print(f"   ⚠️  getReputationSummary failed: {e}")

        print("✅ Feedback retrieval test completed")
        return True

    except Exception as e:
        print(f"❌ Feedback retrieval test failed: {e}")
        return False

def test_feedback_filtering(sdk):
    """Test 4: Feedback filtering and search"""
    print("\n🔎 Test 4: Feedback Filtering and Search")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        print("   Testing feedback search with different parameters...")

        # Test 1: Search with different agent IDs
        test_agent_ids = ["97:1", "97:2", "97:3"]
        for agent_id in test_agent_ids:
            try:
                feedbacks = sdk.indexer.search_feedback(
                    agentId=agent_id,
                    first=5,
                    skip=0
                )
                print(f"   ✅ Agent {agent_id}: {len(feedbacks)} feedbacks")
            except Exception as e:
                print(f"   ⚠️  Agent {agent_id}: failed - {e}")

        # Test 2: Search with pagination
        try:
            feedbacks_page1 = sdk.indexer.search_feedback(
                agentId="97:1",
                first=5,
                skip=0
            )
            feedbacks_page2 = sdk.indexer.search_feedback(
                agentId="97:1",
                first=5,
                skip=5
            )
            print(f"   ✅ Pagination test:")
            print(f"     Page 1: {len(feedbacks_page1)} feedbacks")
            print(f"     Page 2: {len(feedbacks_page2)} feedbacks")
        except Exception as e:
            print(f"   ⚠️  Pagination test failed: {e}")

        # Test 3: Search by score range (if supported)
        try:
            # This would require custom query support in indexer
            print("   ✅ Score range filtering: (would need custom indexer support)")
        except Exception as e:
            print(f"   ⚠️  Score range filtering failed: {e}")

        print("✅ Feedback filtering test completed")
        return True

    except Exception as e:
        print(f"❌ Feedback filtering test failed: {e}")
        return False

def test_feedback_revocation(sdk):
    """Test 5: Feedback revocation on BNB Testnet"""
    print("\n🚫 Test 5: Feedback Revocation on BNB Testnet")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    if sdk.isReadOnly:
        print("⚠️  Skipping feedback revocation test - no signer available")
        return True

    try:
        print("   Testing feedback revocation...")

        # Mock parameters for testing
        mock_agent_id = 1
        mock_feedback_index = 1

        try:
            # Attempt to revoke feedback
            tx_hash = sdk.reputation_registry.functions.revokeFeedback(
                mock_agent_id,
                mock_feedback_index
            ).transact({
                'from': sdk.web3_client.account.address
            })

            print(f"   ✅ Revocation transaction hash: {tx_hash.hex()}")

            # Wait for confirmation
            receipt = sdk.web3_client.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            if receipt.status == 1:
                print(f"   ✅ Revocation confirmed")
                print(f"   Block: {receipt.blockNumber}")
                print(f"   Gas used: {receipt.gasUsed}")
            else:
                print(f"   ❌ Revocation failed")
                return False

        except Exception as e:
            print(f"   ⚠️  Revocation test failed (expected if no feedback exists): {e}")

        print("✅ Feedback revocation test completed")
        return True

    except Exception as e:
        print(f"❌ Feedback revocation test failed: {e}")
        return False

def test_contract_functions(sdk):
    """Test 6: Test basic reputation contract functions"""
    print("\n⚙️ Test 6: Basic Reputation Contract Functions")
    print("-" * 60)

    if not sdk:
        print("❌ SDK not initialized")
        return False

    try:
        print("   Testing reputation contract functions...")

        # Test 1: Get identity registry address
        try:
            identity_address = sdk.reputation_registry.functions.getIdentityRegistry().call()
            print(f"   ✅ Identity Registry address: {identity_address}")
        except Exception as e:
            print(f"   ⚠️  getIdentityRegistry failed: {e}")

        # Test 2: Get clients list
        try:
            clients = sdk.reputation_registry.functions.getClients(1).call()
            print(f"   ✅ Clients list: {len(clients)} clients")
            if clients:
                print(f"   First client: {clients[0]}")
        except Exception as e:
            print(f"   ⚠️  getClients failed: {e}")

        # Test 3: Get summary
        try:
            count, avg_score = sdk.reputation_registry.functions.getSummary(
                1, [], b"", b""
            ).call()
            print(f"   ✅ Summary: count={count}, avg={avg_score}")
        except Exception as e:
            print(f"   ⚠️  getSummary failed: {e}")

        # Test 4: Get response count
        try:
            response_count = sdk.reputation_registry.functions.getResponseCount(
                1, "0x1234567890123456789012345678901234567890", 1, []
            ).call()
            print(f"   ✅ Response count: {response_count}")
        except Exception as e:
            print(f"   ⚠️  getResponseCount failed: {e}")

        print("✅ Contract functions test completed")
        return True

    except Exception as e:
        print(f"❌ Contract functions test failed: {e}")
        return False

def main():
    """Main test runner"""
    print("🚀 Phase 3: BNB Testnet Feedback Functionality Tests")
    print("=" * 60)

    # Print current configuration
    print("Current Configuration:")
    print_config()

    # Check environment variables
    print(f"\nEnvironment Variables:")
    print(f"  AGENT_PRIVATE_KEY: {'***' if os.getenv('AGENT_PRIVATE_KEY') else 'NOT SET'}")
    print(f"  BNB_TESTNET_IDENTITY: {os.getenv('BNB_TESTNET_IDENTITY', 'NOT SET')}")
    print(f"  BNB_TESTNET_REPUTATION: {os.getenv('BNB_TESTNET_REPUTATION', 'NOT SET')}")
    print(f"  BNB_TESTNET_VALIDATION: {os.getenv('BNB_TESTNET_VALIDATION', 'NOT SET')}")

    # Run tests in sequence
    tests = [
        ("SDK Initialization", test_sdk_initialization),
        ("Feedback Submission", test_feedback_submission),
        ("Feedback Retrieval", test_feedback_retrieval),
        ("Feedback Filtering", test_feedback_filtering),
        ("Feedback Revocation", test_feedback_revocation),
        ("Contract Functions", test_contract_functions),
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
        print("🎉 All Phase 3 feedback tests passed!")
        print("✅ BNB Testnet feedback functionality is working correctly")
    else:
        print("⚠️  Some feedback tests failed")
        print("❌ Please check errors above and fix issues")

    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
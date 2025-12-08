"""
Tests for SDK content storage integration (Phase 2).

Tests cover:
- SDK initialization with content_storage
- FeedbackManager using content_storage
- Agent.registerIPFS using content_storage
- Indexer Greenfield URI support
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, ANY

from agent0_sdk.core.sdk import SDK
from agent0_sdk.core.storage_interfaces import ReputationStorage
from agent0_sdk.core.ipfs_storage import IpfsReputationStorage
from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage


class TestSDKContentStorageInitialization:
    """Test SDK initialization with content_storage."""

    @patch('agent0_sdk.core.sdk.Web3Client')
    @patch('agent0_sdk.core.sdk.create_reputation_storage')
    def test_sdk_initializes_content_storage_with_ipfs_backend(self, mock_create_storage, mock_web3):
        """Test that SDK initializes content_storage with IPFS backend."""
        # Setup: Mock storage creation
        mock_storage = Mock(spec=ReputationStorage)
        mock_create_storage.return_value = mock_storage
        mock_web3.return_value.chain_id = 84532

        # Execute: Create SDK with IPFS backend
        sdk = SDK(
            chainId=84532,
            rpcUrl="https://base-sepolia.g.alchemy.com/v2/test",
            signer="0x" + "1" * 64,
            reputationBackend="ipfs"
        )

        # Verify: create_reputation_storage was called with correct config
        assert mock_create_storage.called
        call_kwargs = mock_create_storage.call_args
        config = call_kwargs[1]['config']
        assert config['REPUTATION_BACKEND'] == 'ipfs'

        # Verify: SDK has content_storage
        assert sdk.content_storage is mock_storage

    @patch('agent0_sdk.core.sdk.Web3Client')
    @patch('agent0_sdk.core.sdk.create_reputation_storage')
    def test_sdk_initializes_content_storage_with_greenfield_backend(self, mock_create_storage, mock_web3):
        """Test that SDK initializes content_storage with Greenfield backend."""
        # Setup: Mock storage creation
        mock_storage = Mock(spec=ReputationStorage)
        mock_create_storage.return_value = mock_storage
        mock_web3.return_value.chain_id = 84532

        # Execute: Create SDK with Greenfield backend
        sdk = SDK(
            chainId=84532,
            rpcUrl="https://base-sepolia.g.alchemy.com/v2/test",
            signer="0x" + "1" * 64,
            reputationBackend="greenfield",
            greenfield={
                "spHost": "gnfd-testnet-sp1.bnbchain.org",
                "bucket": "test-bucket",
                "privateKey": "0x" + "2" * 64,
                "txnHash": "0xabcdef"
            }
        )

        # Verify: create_reputation_storage was called with Greenfield config
        assert mock_create_storage.called
        call_kwargs = mock_create_storage.call_args
        config = call_kwargs[1]['config']
        assert config['REPUTATION_BACKEND'] == 'greenfield'
        assert config['GREENFIELD_SP_HOST'] == 'gnfd-testnet-sp1.bnbchain.org'
        assert config['GREENFIELD_BUCKET'] == 'test-bucket'

        # Verify: SDK has content_storage
        assert sdk.content_storage is mock_storage

    @patch('agent0_sdk.core.sdk.Web3Client')
    @patch.dict('os.environ', {
        'REPUTATION_BACKEND': 'greenfield',
        'GREENFIELD_SP_HOST': 'gnfd-testnet-sp3.bnbchain.org',
        'GREENFIELD_BUCKET': 'env-bucket',
        'GREENFIELD_PRIVATE_KEY': '0x' + '3' * 64
    })
    @patch('agent0_sdk.core.sdk.create_reputation_storage')
    def test_sdk_reads_content_storage_config_from_environment(self, mock_create_storage, mock_web3):
        """Test that SDK reads content storage config from environment."""
        # Setup: Mock storage creation
        mock_storage = Mock(spec=ReputationStorage)
        mock_create_storage.return_value = mock_storage
        mock_web3.return_value.chain_id = 84532

        # Execute: Create SDK without explicit config (should read from env)
        sdk = SDK(
            chainId=84532,
            rpcUrl="https://base-sepolia.g.alchemy.com/v2/test",
            signer="0x" + "1" * 64
        )

        # Verify: create_reputation_storage was called with env values
        assert mock_create_storage.called
        call_kwargs = mock_create_storage.call_args
        config = call_kwargs[1]['config']
        assert config['REPUTATION_BACKEND'] == 'greenfield'
        assert config['GREENFIELD_SP_HOST'] == 'gnfd-testnet-sp3.bnbchain.org'
        assert config['GREENFIELD_BUCKET'] == 'env-bucket'

    @patch('agent0_sdk.core.sdk.Web3Client')
    @patch('agent0_sdk.core.sdk.create_reputation_storage')
    def test_sdk_passes_content_storage_to_feedback_manager(self, mock_create_storage, mock_web3):
        """Test that SDK passes content_storage to FeedbackManager."""
        # Setup: Mock storage creation
        mock_storage = Mock(spec=ReputationStorage)
        mock_create_storage.return_value = mock_storage
        mock_web3.return_value.chain_id = 84532

        # Execute: Create SDK
        sdk = SDK(
            chainId=84532,
            rpcUrl="https://base-sepolia.g.alchemy.com/v2/test",
            signer="0x" + "1" * 64,
            reputationBackend="ipfs"
        )

        # Verify: FeedbackManager received content_storage
        assert sdk.feedback_manager.content_storage is mock_storage


class TestFeedbackManagerContentStorage:
    """Test FeedbackManager with content_storage."""

    def test_give_feedback_uses_content_storage(self):
        """Test that giveFeedback uses content_storage to store feedback."""
        # Setup: Mock dependencies
        mock_web3 = Mock()
        mock_web3.account.address = "0x1234567890123456789012345678901234567890"
        mock_web3.call_contract.return_value = 0  # lastIndex
        mock_web3.keccak256.return_value = b"\x00" * 32
        mock_web3.transact_contract.return_value = "0xtxhash"
        mock_web3.wait_for_transaction.return_value = {"status": 1}

        mock_storage = Mock(spec=ReputationStorage)
        mock_storage.put.return_value = "test-key-123"
        mock_storage.build_uri.return_value = "https://test-bucket.gnfd-testnet-sp1.bnbchain.org/test-key-123"

        mock_reputation_registry = Mock()
        mock_identity_registry = Mock()

        # Create FeedbackManager with content_storage
        from agent0_sdk.core.feedback_manager import FeedbackManager
        manager = FeedbackManager(
            web3_client=mock_web3,
            content_storage=mock_storage,
            reputation_registry=mock_reputation_registry,
            identity_registry=mock_identity_registry
        )

        # Execute: Give feedback
        feedback_file = {
            "score": 85,
            "text": "Great agent!",
            "tag1": "helpful"
        }

        feedback = manager.giveFeedback(
            agentId="84532:1",
            feedbackFile=feedback_file,
            feedbackAuth=b"\x00" * 96
        )

        # Verify: content_storage.put was called
        assert mock_storage.put.called
        call_args = mock_storage.put.call_args
        assert call_args.kwargs["key"] == ""

        # Verify: content_storage.build_uri was called
        assert mock_storage.build_uri.called
        assert mock_storage.build_uri.call_args[0][0] == "test-key-123"

        # Verify: blockchain transaction used the storage URI
        tx_call = mock_web3.transact_contract.call_args
        assert "https://test-bucket.gnfd-testnet-sp1.bnbchain.org/test-key-123" in str(tx_call)

    def test_give_feedback_falls_back_to_ipfs_client(self):
        """Test that giveFeedback falls back to ipfs_client when content_storage is None."""
        # Setup: Mock dependencies
        mock_web3 = Mock()
        mock_web3.account.address = "0x1234567890123456789012345678901234567890"
        mock_web3.call_contract.return_value = 0
        mock_web3.keccak256.return_value = b"\x00" * 32
        mock_web3.transact_contract.return_value = "0xtxhash"
        mock_web3.wait_for_transaction.return_value = {"status": 1}

        mock_ipfs = Mock()
        mock_ipfs.add_json.return_value = "QmTestCID123"

        mock_reputation_registry = Mock()
        mock_identity_registry = Mock()

        # Create FeedbackManager WITHOUT content_storage
        from agent0_sdk.core.feedback_manager import FeedbackManager
        manager = FeedbackManager(
            web3_client=mock_web3,
            ipfs_client=mock_ipfs,
            content_storage=None,  # No content_storage
            reputation_registry=mock_reputation_registry,
            identity_registry=mock_identity_registry
        )

        # Execute: Give feedback
        feedback_file = {
            "score": 85,
            "text": "Great agent!"
        }

        feedback = manager.giveFeedback(
            agentId="84532:1",
            feedbackFile=feedback_file,
            feedbackAuth=b"\x00" * 96
        )

        # Verify: ipfs_client.add_json was called
        assert mock_ipfs.add_json.called

        # Verify: blockchain transaction used IPFS URI
        tx_call = mock_web3.transact_contract.call_args
        assert "ipfs://QmTestCID123" in str(tx_call)


class TestAgentRegisterWithContentStorage:
    """Test Agent.registerIPFS with content_storage."""

    @patch('agent0_sdk.core.sdk.Web3Client')
    @patch('agent0_sdk.core.sdk.create_reputation_storage')
    def test_register_ipfs_uses_content_storage(self, mock_create_storage, mock_web3):
        """Test that registerIPFS uses content_storage to store registration file."""
        # Setup: Mock storage and web3
        mock_storage = Mock(spec=ReputationStorage)
        mock_storage.put_json.return_value = "registration-key-123"
        mock_storage.build_uri.return_value = "https://test-bucket.gnfd-testnet-sp1.bnbchain.org/registration-key-123"
        mock_create_storage.return_value = mock_storage

        mock_web3_instance = Mock()
        mock_web3_instance.chain_id = 84532
        mock_web3_instance.account.address = "0x1234567890123456789012345678901234567890"
        mock_web3_instance.transact_contract.return_value = "0xminthash"
        mock_web3_instance.wait_for_transaction.return_value = {"status": 1, "logs": []}
        mock_web3_instance.get_contract.return_value = Mock()
        mock_web3.return_value = mock_web3_instance

        # Create SDK
        sdk = SDK(
            chainId=84532,
            rpcUrl="https://base-sepolia.g.alchemy.com/v2/test",
            signer="0x" + "1" * 64,
            reputationBackend="greenfield",
            greenfield={"spHost": "gnfd-testnet-sp1.bnbchain.org", "bucket": "test-bucket", "privateKey": "0x" + "2" * 64}
        )

        # Create agent
        agent = sdk.createAgent("Test Agent", "A test agent")

        # Mock the _registerWithoutUri to set agentId
        with patch.object(agent, '_registerWithoutUri') as mock_register:
            def set_agent_id():
                agent.registration_file.agentId = "84532:1"
            mock_register.side_effect = set_agent_id

            # Execute: Register agent
            result = agent.registerIPFS()

        # Verify: content_storage.put_json was called
        assert mock_storage.put_json.called
        call_args = mock_storage.put_json.call_args
        reg_data = call_args.kwargs['data']
        assert reg_data['name'] == 'Test Agent'
        assert reg_data['description'] == 'A test agent'

        # Verify: content_storage.build_uri was called
        assert mock_storage.build_uri.called

        # Verify: setAgentUri was called with Greenfield URI
        set_uri_calls = [call for call in mock_web3_instance.transact_contract.call_args_list
                         if 'setAgentUri' in str(call)]
        assert len(set_uri_calls) > 0
        assert "https://test-bucket.gnfd-testnet-sp1.bnbchain.org/registration-key-123" in str(set_uri_calls[0])


class TestIndexerGreenfieldSupport:
    """Test Indexer Greenfield URI support."""

    def test_detect_greenfield_https_uri(self):
        """Test that _detect_uri_type recognizes Greenfield HTTPS URIs."""
        from agent0_sdk.core.indexer import AgentIndexer

        indexer = AgentIndexer(
            web3_client=Mock(),
            store=None,
            embeddings=None,
            subgraph_client=None
        )

        # Test Greenfield HTTPS URI
        uri_type = indexer._detect_uri_type("https://my-bucket.gnfd-testnet-sp1.bnbchain.org/my-object")
        assert uri_type == "greenfield"

        # Test Greenfield gnfd:// URI
        uri_type = indexer._detect_uri_type("gnfd://my-bucket/my-object")
        assert uri_type == "greenfield"

        # Test regular HTTPS URI (not Greenfield)
        uri_type = indexer._detect_uri_type("https://example.com/file.json")
        assert uri_type == "https"

        # Test IPFS URI
        uri_type = indexer._detect_uri_type("ipfs://QmTestCID123")
        assert uri_type == "ipfs"

    @pytest.mark.asyncio
    async def test_fetch_registration_file_from_greenfield_https(self):
        """Test fetching registration file from Greenfield HTTPS URI."""
        from agent0_sdk.core.indexer import AgentIndexer

        indexer = AgentIndexer(
            web3_client=Mock(),
            store=None,
            embeddings=None,
            subgraph_client=None
        )

        # Mock HTTP fetch
        mock_data = {"name": "Test Agent", "description": "From Greenfield"}
        with patch.object(indexer, '_fetch_http_content', return_value=mock_data) as mock_fetch:
            # Execute: Fetch from Greenfield HTTPS URI
            result = await indexer._fetch_registration_file(
                "https://test-bucket.gnfd-testnet-sp1.bnbchain.org/registration-key-123"
            )

            # Verify: HTTP fetch was called
            assert mock_fetch.called
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_fetch_registration_file_from_greenfield_gnfd_protocol(self):
        """Test fetching registration file from Greenfield gnfd:// URI."""
        from agent0_sdk.core.indexer import AgentIndexer

        indexer = AgentIndexer(
            web3_client=Mock(),
            store=None,
            embeddings=None,
            subgraph_client=None
        )

        # Mock HTTP fetch
        mock_data = {"name": "Test Agent", "description": "From Greenfield"}
        with patch.object(indexer, '_fetch_http_content', return_value=mock_data) as mock_fetch:
            with patch.dict('os.environ', {'GREENFIELD_SP_HOST': 'gnfd-testnet-sp1.bnbchain.org'}):
                # Execute: Fetch from gnfd:// URI
                result = await indexer._fetch_registration_file("gnfd://test-bucket/registration-key-123")

                # Verify: HTTP fetch was called with converted HTTPS URI
                assert mock_fetch.called
                call_uri = mock_fetch.call_args[0][0]
                assert call_uri == "https://test-bucket.gnfd-testnet-sp1.bnbchain.org/registration-key-123"
                assert result == mock_data

    @pytest.mark.asyncio
    async def test_fetch_feedback_file_from_greenfield(self):
        """Test fetching feedback file from Greenfield URI."""
        from agent0_sdk.core.indexer import AgentIndexer

        indexer = AgentIndexer(
            web3_client=Mock(),
            store=None,
            embeddings=None,
            subgraph_client=None
        )

        # Mock HTTP fetch
        mock_data = {"score": 95, "text": "Excellent!", "tag1": "helpful"}
        with patch.object(indexer, '_fetch_http_content', return_value=mock_data) as mock_fetch:
            # Execute: Fetch feedback from Greenfield HTTPS URI
            result = await indexer._fetch_feedback_file(
                "https://test-bucket.gnfd-testnet-sp1.bnbchain.org/feedback-key-456"
            )

            # Verify: HTTP fetch was called
            assert mock_fetch.called
            assert result == mock_data

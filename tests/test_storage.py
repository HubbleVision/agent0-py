"""
Unit tests for ReputationStorage interface and implementations.

Tests cover:
- ReputationStorage interface contract
- IpfsReputationStorage adapter
- GreenfieldReputationStorage implementation
- Storage factory with backend switching
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, ANY

from agent0_sdk.core.storage_interfaces import ReputationStorage
from agent0_sdk.core.ipfs_storage import IpfsReputationStorage
from agent0_sdk.core.storage_factory import create_reputation_storage, build_ipfs_client
from agent0_sdk.core.ipfs_client import IPFSClient


class TestIpfsReputationStorage:
    """Test IPFS implementation of ReputationStorage interface."""

    def test_put_stores_data_and_returns_cid(self):
        """Test that put() stores data on IPFS and returns CID."""
        # Setup: Create mock IPFS client
        mock_ipfs = Mock(spec=IPFSClient)
        mock_ipfs.add.return_value = "QmTestCID12345"

        storage = IpfsReputationStorage(client=mock_ipfs)

        # Execute: Store binary data
        test_data = b"test reputation data"
        result_cid = storage.put(key="", data=test_data)

        # Verify: IPFS client was called with UTF-8 decoded string
        mock_ipfs.add.assert_called_once_with("test reputation data")
        assert result_cid == "QmTestCID12345"

    def test_put_handles_non_utf8_data(self):
        """Test that put() handles non-UTF-8 binary data by encoding as base64."""
        # Setup: Create mock IPFS client
        mock_ipfs = Mock(spec=IPFSClient)
        mock_ipfs.add.return_value = "QmBase64CID"

        storage = IpfsReputationStorage(client=mock_ipfs)

        # Execute: Store non-UTF-8 binary data
        test_data = bytes([0xFF, 0xFE, 0xFD])
        result_cid = storage.put(key="ignored_key", data=test_data)

        # Verify: IPFS client was called (data converted to base64)
        assert mock_ipfs.add.called
        assert result_cid == "QmBase64CID"

    def test_get_retrieves_data_by_cid(self):
        """Test that get() retrieves data from IPFS by CID."""
        # Setup: Create mock IPFS client
        mock_ipfs = Mock(spec=IPFSClient)
        mock_ipfs.get.return_value = "retrieved data"

        storage = IpfsReputationStorage(client=mock_ipfs)

        # Execute: Retrieve data by CID
        result_data = storage.get(key="QmTestCID12345")

        # Verify: IPFS client was called with correct CID
        mock_ipfs.get.assert_called_once_with("QmTestCID12345")
        assert result_data == b"retrieved data"

    def test_get_raises_runtime_error_on_failure(self):
        """Test that get() raises RuntimeError when IPFS retrieval fails."""
        # Setup: Create mock IPFS client that raises exception
        mock_ipfs = Mock(spec=IPFSClient)
        mock_ipfs.get.side_effect = Exception("IPFS unavailable")

        storage = IpfsReputationStorage(client=mock_ipfs)

        # Execute & Verify: Should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            storage.get(key="QmNonexistent")

        assert "Failed to retrieve data from IPFS" in str(exc_info.value)
        assert "QmNonexistent" in str(exc_info.value)

    def test_put_json_stores_json_data(self):
        """Test that put_json() stores JSON data on IPFS."""
        # Setup: Create mock IPFS client
        mock_ipfs = Mock(spec=IPFSClient)
        mock_ipfs.add_json.return_value = "QmJsonCID"

        storage = IpfsReputationStorage(client=mock_ipfs)

        # Execute: Store JSON data
        test_data = {"score": 5, "text": "great agent"}
        result_cid = storage.put_json(key="", data=test_data)

        # Verify: IPFS client was called with dict
        mock_ipfs.add_json.assert_called_once_with(test_data)
        assert result_cid == "QmJsonCID"

    def test_get_json_retrieves_json_data(self):
        """Test that get_json() retrieves and parses JSON data from IPFS."""
        # Setup: Create mock IPFS client
        mock_ipfs = Mock(spec=IPFSClient)
        mock_ipfs.get_json.return_value = {"score": 5, "text": "great agent"}

        storage = IpfsReputationStorage(client=mock_ipfs)

        # Execute: Retrieve JSON data
        result_data = storage.get_json(key="QmJsonCID")

        # Verify: IPFS client was called and data parsed
        mock_ipfs.get_json.assert_called_once_with("QmJsonCID")
        assert result_data == {"score": 5, "text": "great agent"}


class TestStorageFactory:
    """Test storage factory function."""

    def test_factory_returns_ipfs_by_default(self):
        """Test that factory returns IPFS storage when no backend specified."""
        # Setup: Create mock IPFS client
        mock_ipfs = Mock(spec=IPFSClient)

        # Execute: Create storage without config (should default to IPFS)
        storage = create_reputation_storage(config={}, ipfs_client=mock_ipfs)

        # Verify: Returns IpfsReputationStorage instance
        assert isinstance(storage, IpfsReputationStorage)
        assert storage.client is mock_ipfs

    @pytest.mark.parametrize("backend,expected_type", [
        ("ipfs", "IpfsReputationStorage"),
        ("IPFS", "IpfsReputationStorage"),  # Case insensitive
    ])
    def test_factory_backend_switching(self, backend, expected_type):
        """Test that factory correctly switches between backends."""
        # Setup: Create mock IPFS client
        mock_ipfs = Mock(spec=IPFSClient)

        # Execute: Create storage with specified backend
        storage = create_reputation_storage(
            config={"REPUTATION_BACKEND": backend},
            ipfs_client=mock_ipfs
        )

        # Verify: Correct type returned
        if expected_type == "IpfsReputationStorage":
            assert isinstance(storage, IpfsReputationStorage)
        # Note: Greenfield tests are in TestGreenfieldStorageFactory

    def test_factory_respects_backend_config(self):
        """Test that factory respects REPUTATION_BACKEND configuration."""
        # Setup: Create mock IPFS client
        mock_ipfs = Mock(spec=IPFSClient)

        # Execute: Create storage with explicit IPFS backend
        storage = create_reputation_storage(
            config={"REPUTATION_BACKEND": "ipfs"},
            ipfs_client=mock_ipfs
        )

        # Verify: Returns IpfsReputationStorage instance
        assert isinstance(storage, IpfsReputationStorage)

    def test_factory_raises_for_greenfield_in_phase1(self):
        """Test that factory raises NotImplementedError for Greenfield in Phase 1."""
        # Execute & Verify: Should raise NotImplementedError for Greenfield
        with pytest.raises(NotImplementedError) as exc_info:
            create_reputation_storage(config={"REPUTATION_BACKEND": "greenfield"})

        assert "Greenfield storage backend not yet implemented" in str(exc_info.value)

    def test_factory_falls_back_to_ipfs_for_unknown_backend(self):
        """Test that factory falls back to IPFS for unknown backend."""
        # Setup: Create mock IPFS client
        mock_ipfs = Mock(spec=IPFSClient)

        # Execute: Create storage with unknown backend
        storage = create_reputation_storage(
            config={"REPUTATION_BACKEND": "unknown"},
            ipfs_client=mock_ipfs
        )

        # Verify: Falls back to IPFS
        assert isinstance(storage, IpfsReputationStorage)

    @patch.dict('os.environ', {'REPUTATION_BACKEND': 'ipfs'})
    def test_factory_reads_from_environment(self):
        """Test that factory reads REPUTATION_BACKEND from environment."""
        # Setup: Create mock IPFS client
        mock_ipfs = Mock(spec=IPFSClient)

        # Execute: Create storage without config (should read from env)
        storage = create_reputation_storage(ipfs_client=mock_ipfs)

        # Verify: Returns IPFS storage based on environment variable
        assert isinstance(storage, IpfsReputationStorage)

    def test_factory_creates_ipfs_client_when_not_provided(self):
        """Test that factory creates IPFSClient when not provided."""
        # Execute: Create storage without providing IPFS client
        with patch('agent0_sdk.core.storage_factory.IPFSClient') as mock_ipfs_class:
            mock_ipfs_instance = Mock(spec=IPFSClient)
            mock_ipfs_class.return_value = mock_ipfs_instance

            storage = create_reputation_storage(config={"REPUTATION_BACKEND": "ipfs"})

            # Verify: IPFSClient was created
            assert mock_ipfs_class.called
            assert isinstance(storage, IpfsReputationStorage)


class TestBuildIpfsClient:
    """Test IPFS client builder helper function."""

    @patch('agent0_sdk.core.storage_factory.IPFSClient')
    def test_build_ipfs_client_with_config(self, mock_ipfs_class):
        """Test that build_ipfs_client creates client with correct parameters."""
        # Setup: Mock IPFSClient constructor
        mock_ipfs_instance = Mock(spec=IPFSClient)
        mock_ipfs_class.return_value = mock_ipfs_instance

        # Execute: Build client with config
        config = {
            "IPFS_API_URL": "http://localhost:5001",
            "PINATA_ENABLED": True,
            "PINATA_JWT": "test_jwt_token"
        }
        client = build_ipfs_client(config)

        # Verify: IPFSClient was created with correct parameters
        mock_ipfs_class.assert_called_once_with(
            url="http://localhost:5001",
            filecoin_pin_enabled=False,
            filecoin_private_key=None,
            pinata_enabled=True,
            pinata_jwt="test_jwt_token"
        )
        assert client is mock_ipfs_instance

    @patch('agent0_sdk.core.storage_factory.IPFSClient')
    @patch.dict('os.environ', {
        'IPFS_API_URL': 'http://localhost:5001',
        'FILECOIN_PIN_ENABLED': 'true',
        'FILECOIN_PRIVATE_KEY': '0xtest'
    })
    def test_build_ipfs_client_from_environment(self, mock_ipfs_class):
        """Test that build_ipfs_client reads from environment variables."""
        # Setup: Mock IPFSClient constructor
        mock_ipfs_instance = Mock(spec=IPFSClient)
        mock_ipfs_class.return_value = mock_ipfs_instance

        # Execute: Build client without config (should read from env)
        client = build_ipfs_client()

        # Verify: IPFSClient was created with env values
        mock_ipfs_class.assert_called_once()
        call_kwargs = mock_ipfs_class.call_args[1]
        assert call_kwargs['url'] == 'http://localhost:5001'
        assert call_kwargs['filecoin_pin_enabled'] is True
        assert call_kwargs['filecoin_private_key'] == '0xtest'


class TestReputationStorageInterface:
    """Test that implementations conform to ReputationStorage interface."""

    def test_ipfs_storage_implements_interface(self):
        """Test that IpfsReputationStorage implements ReputationStorage."""
        mock_ipfs = Mock(spec=IPFSClient)
        storage = IpfsReputationStorage(client=mock_ipfs)

        # Verify: Instance implements ReputationStorage interface
        assert isinstance(storage, ReputationStorage)
        assert hasattr(storage, 'put')
        assert hasattr(storage, 'get')
        assert callable(storage.put)
        assert callable(storage.get)


class TestGreenfieldReputationStorage:
    """Test Greenfield implementation of ReputationStorage interface."""

    @patch('agent0_sdk.core.greenfield_storage.requests.Session')
    def test_put_uploads_to_greenfield(self, mock_session_class):
        """Test that put() uploads data to Greenfield with correct URL and headers."""
        # Setup: Mock requests session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.headers = {"ETag": "test-etag", "X-Gnfd-Request-ID": "req-123"}
        mock_session.put.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Import here to avoid dependency issues in other tests
        from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

        storage = GreenfieldReputationStorage(
            sp_host="gnfd-testnet-sp1.bnbchain.org",
            bucket="test-bucket",
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            txn_hash="0xabcdef123456",
        )

        # Execute: Upload data
        test_data = b"test reputation data"
        result_key = storage.put(key="test-key", data=test_data)

        # Verify: Correct URL format (virtual-hosted-style)
        assert result_key == "test-key"
        mock_session.put.assert_called_once()
        call_args = mock_session.put.call_args
        url = call_args[0][0]
        assert url == "https://test-bucket.gnfd-testnet-sp1.bnbchain.org/test-key"

        # Verify: Required headers present
        headers = call_args[1]['headers']
        assert "Authorization" in headers
        assert headers["X-Gnfd-Txn-Hash"] == "0xabcdef123456"
        assert headers["Content-Type"] == "application/octet-stream"
        assert headers["Content-Length"] == str(len(test_data))
        assert headers["Authorization"].startswith("GNFD1-ECDSA, Signature=")

    @patch('agent0_sdk.core.greenfield_storage.requests.Session')
    def test_put_generates_key_when_empty(self, mock_session_class):
        """Test that put() generates UUID key when key is empty."""
        # Setup: Mock requests session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.headers = {"ETag": "test-etag"}
        mock_session.put.return_value = mock_response
        mock_session_class.return_value = mock_session

        from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

        storage = GreenfieldReputationStorage(
            sp_host="gnfd-testnet-sp1.bnbchain.org",
            bucket="test-bucket",
            private_key="0x" + "1" * 64,
            txn_hash="0xabcdef",
        )

        # Execute: Upload without key
        result_key = storage.put(key="", data=b"data")

        # Verify: Generated key is non-empty and looks like UUID (32 hex chars)
        assert result_key
        assert len(result_key) == 32
        assert all(c in "0123456789abcdef" for c in result_key)

    @patch('agent0_sdk.core.greenfield_storage.requests.Session')
    def test_get_retrieves_from_greenfield(self, mock_session_class):
        """Test that get() retrieves data from Greenfield."""
        # Setup: Mock requests session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b"retrieved data"
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

        storage = GreenfieldReputationStorage(
            sp_host="gnfd-testnet-sp1.bnbchain.org",
            bucket="test-bucket",
            private_key="0x" + "1" * 64,
            txn_hash="0xabcdef",
        )

        # Execute: Retrieve data
        result_data = storage.get(key="test-key")

        # Verify: Correct URL and returned data
        mock_session.get.assert_called_once()
        url = mock_session.get.call_args[0][0]
        assert url == "https://test-bucket.gnfd-testnet-sp1.bnbchain.org/test-key"
        assert result_data == b"retrieved data"

    def test_greenfield_storage_validates_required_params(self):
        """Test that GreenfieldReputationStorage validates required parameters."""
        from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

        # Verify: Missing sp_host raises ValueError
        with pytest.raises(ValueError, match="sp_host is required"):
            GreenfieldReputationStorage(
                sp_host="",
                bucket="test",
                private_key="0x" + "1" * 64,
                txn_hash="0xabc",
            )

        # Verify: Missing bucket raises ValueError
        with pytest.raises(ValueError, match="bucket is required"):
            GreenfieldReputationStorage(
                sp_host="test.bnbchain.org",
                bucket="",
                private_key="0x" + "1" * 64,
                txn_hash="0xabc",
            )

        # Verify: Missing private_key raises ValueError
        with pytest.raises(ValueError, match="private_key is required"):
            GreenfieldReputationStorage(
                sp_host="test.bnbchain.org",
                bucket="test",
                private_key="",
                txn_hash="0xabc",
            )

        # Verify: Missing txn_hash raises ValueError
        with pytest.raises(ValueError, match="txn_hash is required"):
            GreenfieldReputationStorage(
                sp_host="test.bnbchain.org",
                bucket="test",
                private_key="0x" + "1" * 64,
                txn_hash="",
            )

    @patch('agent0_sdk.core.greenfield_storage.requests.Session')
    def test_canonical_request_format(self, mock_session_class):
        """Test that canonical request is built correctly for signing."""
        # Setup: Mock requests session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.headers = {"ETag": "test"}
        mock_session.put.return_value = mock_response
        mock_session_class.return_value = mock_session

        from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

        storage = GreenfieldReputationStorage(
            sp_host="gnfd-testnet-sp1.bnbchain.org",
            bucket="my-bucket",
            private_key="0x" + "1" * 64,
            txn_hash="0xabcdef123456",
        )

        # Execute: Upload to trigger canonical request building
        storage.put(key="test-object", data=b"test data")

        # Verify: Authorization header exists and has correct format
        mock_session.put.assert_called_once()
        headers = mock_session.put.call_args[1]['headers']
        auth = headers["Authorization"]

        # Check format: "GNFD1-ECDSA, Signature=<hex>"
        assert auth.startswith("GNFD1-ECDSA, Signature=")
        signature_part = auth.split("Signature=")[1]
        # Ethereum signature should be 130 chars (65 bytes * 2)
        assert len(signature_part) == 130
        assert all(c in "0123456789abcdef" for c in signature_part)


class TestGreenfieldStorageFactory:
    """Test storage factory with Greenfield backend."""

    @patch('agent0_sdk.core.storage_factory._import_greenfield_storage')
    def test_factory_creates_greenfield_storage(self, mock_import):
        """Test that factory creates Greenfield storage when backend is 'greenfield'."""
        # Setup: Mock GreenfieldReputationStorage class
        from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage
        mock_import.return_value = GreenfieldReputationStorage

        # Execute: Create storage with Greenfield backend
        config = {
            "REPUTATION_BACKEND": "greenfield",
            "GREENFIELD_SP_HOST": "gnfd-testnet-sp1.bnbchain.org",
            "GREENFIELD_BUCKET": "test-bucket",
            "GREENFIELD_PRIVATE_KEY": "0x" + "1" * 64,
            "GREENFIELD_TXN_HASH": "0xabcdef123456",
        }

        with patch('agent0_sdk.core.greenfield_storage.requests.Session'):
            storage = create_reputation_storage(config=config)

            # Verify: Created GreenfieldReputationStorage instance
            assert isinstance(storage, GreenfieldReputationStorage)
            assert storage.bucket == "test-bucket"
            assert storage.sp_host == "gnfd-testnet-sp1.bnbchain.org"

    def test_factory_validates_greenfield_config(self):
        """Test that factory validates required Greenfield configuration."""
        # Verify: Missing sp_host raises ValueError
        with pytest.raises(ValueError, match="GREENFIELD_SP_HOST is required"):
            create_reputation_storage(config={"REPUTATION_BACKEND": "greenfield"})

        # Verify: Missing bucket raises ValueError
        config = {
            "REPUTATION_BACKEND": "greenfield",
            "GREENFIELD_SP_HOST": "test.bnbchain.org",
        }
        with pytest.raises(ValueError, match="GREENFIELD_BUCKET is required"):
            create_reputation_storage(config=config)

        # Verify: Missing private_key raises ValueError
        config = {
            "REPUTATION_BACKEND": "greenfield",
            "GREENFIELD_SP_HOST": "test.bnbchain.org",
            "GREENFIELD_BUCKET": "test-bucket",
        }
        with pytest.raises(ValueError, match="GREENFIELD_PRIVATE_KEY is required"):
            create_reputation_storage(config=config)

    @patch.dict('os.environ', {
        'REPUTATION_BACKEND': 'greenfield',
        'GREENFIELD_SP_HOST': 'gnfd-testnet-sp1.bnbchain.org',
        'GREENFIELD_BUCKET': 'env-bucket',
        'GREENFIELD_PRIVATE_KEY': '0x' + '2' * 64,
        'GREENFIELD_TXN_HASH': '0xenv123',
    })
    @patch('agent0_sdk.core.storage_factory._import_greenfield_storage')
    def test_factory_reads_greenfield_from_environment(self, mock_import):
        """Test that factory reads Greenfield config from environment."""
        from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage
        mock_import.return_value = GreenfieldReputationStorage

        # Execute: Create storage without config (should read from env)
        with patch('agent0_sdk.core.greenfield_storage.requests.Session'):
            storage = create_reputation_storage()

            # Verify: Created with env values
            assert isinstance(storage, GreenfieldReputationStorage)
            assert storage.bucket == "env-bucket"
            assert storage.sp_host == "gnfd-testnet-sp1.bnbchain.org"

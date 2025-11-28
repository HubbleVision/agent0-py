"""
Unit tests for ReputationStorage interface and implementations.

Tests cover:
- ReputationStorage interface contract
- IpfsReputationStorage adapter
- Storage factory default behavior
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch

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

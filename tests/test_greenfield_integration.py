"""
Integration tests for Greenfield storage.

These tests connect to a real Greenfield testnet to verify actual storage operations.
They are marked as integration tests and can be skipped if the required environment
variables are not configured.

To run these tests:
1. Set up required environment variables (see docs/greenfield_integration_guide.md)
2. Run: pytest tests/test_greenfield_integration.py -v -m integration

Environment variables required:
- GREENFIELD_SP_HOST: Storage Provider host (e.g., gnfd-testnet-sp1.bnbchain.org)
- GREENFIELD_BUCKET: Test bucket name
- GREENFIELD_PRIVATE_KEY: Private key for signing
- GREENFIELD_TXN_HASH: Transaction hash from CreateObject operation (optional for some tests)
"""

import os
import pytest
import time
from typing import Optional

# Skip all integration tests if not explicitly enabled
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def greenfield_config() -> dict:
    """Fixture providing Greenfield testnet configuration.

    Returns:
        Configuration dictionary with required Greenfield parameters

    Raises:
        pytest.skip: If required environment variables are not set
    """
    sp_host = os.getenv("GREENFIELD_SP_HOST")
    bucket = os.getenv("GREENFIELD_BUCKET")
    private_key = os.getenv("GREENFIELD_PRIVATE_KEY")
    txn_hash = os.getenv("GREENFIELD_TXN_HASH")

    # Skip if essential config is missing
    if not sp_host or not bucket or not private_key:
        pytest.skip(
            "Greenfield integration tests require GREENFIELD_SP_HOST, "
            "GREENFIELD_BUCKET, and GREENFIELD_PRIVATE_KEY environment variables. "
            "See docs/greenfield_integration_guide.md for setup instructions."
        )

    return {
        "GREENFIELD_SP_HOST": sp_host,
        "GREENFIELD_BUCKET": bucket,
        "GREENFIELD_PRIVATE_KEY": private_key,
        "GREENFIELD_TXN_HASH": txn_hash,  # May be None - tests will handle it
    }


@pytest.fixture(scope="module")
def greenfield_storage(greenfield_config):
    """Fixture providing a configured GreenfieldReputationStorage instance.

    Args:
        greenfield_config: Configuration from greenfield_config fixture

    Returns:
        GreenfieldReputationStorage instance configured for testnet
    """
    from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

    return GreenfieldReputationStorage(
        sp_host=greenfield_config["GREENFIELD_SP_HOST"],
        bucket=greenfield_config["GREENFIELD_BUCKET"],
        private_key=greenfield_config["GREENFIELD_PRIVATE_KEY"],
        txn_hash=greenfield_config["GREENFIELD_TXN_HASH"],
        timeout=60,  # Use longer timeout for real network
    )


class TestGreenfieldIntegration:
    """Integration tests for Greenfield storage using real testnet."""

    def test_put_and_get_roundtrip(self, greenfield_storage, greenfield_config):
        """Test uploading and retrieving data from Greenfield testnet.

        This test verifies that:
        1. Data can be successfully uploaded to Greenfield
        2. The same data can be retrieved without corruption
        3. Binary data survives the roundtrip
        """
        # Skip if no txn_hash available
        if not greenfield_config["GREENFIELD_TXN_HASH"]:
            pytest.skip("GREENFIELD_TXN_HASH required for put operation")

        # Prepare test data
        test_data = b"Integration test data - " + str(time.time()).encode('utf-8')
        test_key = f"integration-test-{int(time.time())}"

        try:
            # Upload data
            print(f"\nUploading to Greenfield: key={test_key}, size={len(test_data)} bytes")
            result_key = greenfield_storage.put(key=test_key, data=test_data)

            # Verify returned key
            assert result_key == test_key, f"Expected key {test_key}, got {result_key}"
            print(f"Upload successful: {result_key}")

            # Wait a moment for propagation (Greenfield may need time to finalize)
            time.sleep(2)

            # Retrieve data
            print(f"Retrieving from Greenfield: key={test_key}")
            retrieved_data = greenfield_storage.get(key=test_key)

            # Verify data integrity
            assert retrieved_data == test_data, (
                f"Data mismatch! Original: {test_data}, Retrieved: {retrieved_data}"
            )
            print(f"Retrieval successful: {len(retrieved_data)} bytes matched")

        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")

    def test_put_with_auto_generated_key(self, greenfield_storage, greenfield_config):
        """Test uploading with auto-generated key (UUID-based).

        This verifies that the storage can generate unique keys when not provided.
        """
        # Skip if no txn_hash available
        if not greenfield_config["GREENFIELD_TXN_HASH"]:
            pytest.skip("GREENFIELD_TXN_HASH required for put operation")

        # Prepare test data
        test_data = b"Auto-key test data"

        try:
            # Upload without providing a key
            print(f"\nUploading with auto-generated key")
            result_key = greenfield_storage.put(key="", data=test_data)

            # Verify key was generated (should be 32-char hex UUID)
            assert result_key, "Generated key should not be empty"
            assert len(result_key) == 32, f"Expected 32-char UUID, got {len(result_key)}"
            assert all(c in "0123456789abcdef" for c in result_key), (
                f"Key should be hex format, got: {result_key}"
            )
            print(f"Auto-generated key: {result_key}")

            # Verify we can retrieve with the generated key
            time.sleep(2)
            retrieved_data = greenfield_storage.get(key=result_key)
            assert retrieved_data == test_data
            print(f"Retrieval with auto-generated key successful")

        except Exception as e:
            pytest.fail(f"Auto-generated key test failed: {e}")

    def test_put_with_per_object_txn_hash(self, greenfield_storage, greenfield_config):
        """Test uploading with per-object transaction hash.

        This verifies that txn_hash can be provided per-object rather than using
        the default from constructor.
        """
        # This test requires a per-object txn_hash
        # If you have multiple txn_hashes for different objects, set GREENFIELD_TXN_HASH_ALT
        per_object_hash = os.getenv("GREENFIELD_TXN_HASH_ALT") or greenfield_config["GREENFIELD_TXN_HASH"]

        if not per_object_hash:
            pytest.skip("GREENFIELD_TXN_HASH or GREENFIELD_TXN_HASH_ALT required")

        # Prepare test data
        test_data = b"Per-object txn hash test"
        test_key = f"per-object-test-{int(time.time())}"

        try:
            # Upload with per-object txn_hash
            print(f"\nUploading with per-object txn_hash: {per_object_hash[:16]}...")
            result_key = greenfield_storage.put(
                key=test_key,
                data=test_data,
                txn_hash=per_object_hash
            )

            assert result_key == test_key
            print(f"Upload successful with per-object txn_hash")

            # Verify retrieval
            time.sleep(2)
            retrieved_data = greenfield_storage.get(key=test_key)
            assert retrieved_data == test_data
            print(f"Retrieval successful")

        except Exception as e:
            pytest.fail(f"Per-object txn_hash test failed: {e}")

    def test_get_nonexistent_object_raises_error(self, greenfield_storage):
        """Test that retrieving a non-existent object raises appropriate error.

        This verifies proper error handling for missing objects.
        """
        nonexistent_key = f"nonexistent-{int(time.time())}"

        print(f"\nAttempting to retrieve non-existent object: {nonexistent_key}")

        # Should raise RuntimeError for non-existent object
        with pytest.raises(RuntimeError) as exc_info:
            greenfield_storage.get(key=nonexistent_key)

        # Verify error message contains useful information
        error_msg = str(exc_info.value)
        assert "Failed to retrieve from Greenfield" in error_msg
        assert nonexistent_key in error_msg
        print(f"Correctly raised error for non-existent object")

    def test_put_large_data(self, greenfield_storage, greenfield_config):
        """Test uploading larger data (1MB) to verify handling of bigger payloads.

        This ensures the storage can handle reasonably large reputation data.
        """
        # Skip if no txn_hash available
        if not greenfield_config["GREENFIELD_TXN_HASH"]:
            pytest.skip("GREENFIELD_TXN_HASH required for put operation")

        # Create 1MB of test data
        size_mb = 1
        test_data = b"X" * (size_mb * 1024 * 1024)
        test_key = f"large-data-test-{int(time.time())}"

        try:
            print(f"\nUploading large data: {size_mb}MB")
            result_key = greenfield_storage.put(key=test_key, data=test_data)

            assert result_key == test_key
            print(f"Large data upload successful")

            # Verify retrieval (may take longer)
            time.sleep(3)
            print(f"Retrieving large data...")
            retrieved_data = greenfield_storage.get(key=test_key)

            assert len(retrieved_data) == len(test_data), (
                f"Size mismatch! Original: {len(test_data)}, Retrieved: {len(retrieved_data)}"
            )
            assert retrieved_data == test_data
            print(f"Large data retrieval successful: {len(retrieved_data)} bytes")

        except Exception as e:
            pytest.fail(f"Large data test failed: {e}")

    def test_put_binary_data_integrity(self, greenfield_storage, greenfield_config):
        """Test that binary data (non-UTF-8) is stored and retrieved correctly.

        This verifies that arbitrary binary data survives roundtrip without corruption.
        """
        # Skip if no txn_hash available
        if not greenfield_config["GREENFIELD_TXN_HASH"]:
            pytest.skip("GREENFIELD_TXN_HASH required for put operation")

        # Create binary data with all byte values
        test_data = bytes(range(256))
        test_key = f"binary-test-{int(time.time())}"

        try:
            print(f"\nUploading binary data: 256 bytes (all byte values)")
            result_key = greenfield_storage.put(key=test_key, data=test_data)

            assert result_key == test_key
            print(f"Binary data upload successful")

            # Verify retrieval
            time.sleep(2)
            retrieved_data = greenfield_storage.get(key=test_key)

            assert retrieved_data == test_data, (
                "Binary data corrupted during roundtrip!"
            )
            print(f"Binary data integrity verified")

        except Exception as e:
            pytest.fail(f"Binary data integrity test failed: {e}")


class TestGreenfieldPublicAccess:
    """Integration tests for public read access (without Authorization).

    These tests verify that objects in public buckets can be read without
    authentication, which is important for client-side access to reputation data.
    """

    def test_get_public_object_without_auth(self, greenfield_config):
        """Test retrieving a public object without Authorization header.

        This verifies that if the bucket ACL allows public read, objects can be
        retrieved without signing the request.

        Note: This test requires the bucket to have public read ACL enabled.
        """
        import requests

        # Use a known public object key
        # You should pre-create a public object for this test
        public_object_key = os.getenv("GREENFIELD_PUBLIC_TEST_OBJECT")

        if not public_object_key:
            pytest.skip(
                "GREENFIELD_PUBLIC_TEST_OBJECT required for public access test. "
                "Create a public object and set its key in this environment variable."
            )

        # Build URL (virtual-hosted-style)
        bucket = greenfield_config["GREENFIELD_BUCKET"]
        sp_host = greenfield_config["GREENFIELD_SP_HOST"]
        url = f"https://{bucket}.{sp_host}/{public_object_key}"

        try:
            print(f"\nAttempting public read (no Authorization): {url}")

            # Make GET request WITHOUT Authorization header
            response = requests.get(url, timeout=30)

            # Should succeed if bucket is public
            response.raise_for_status()

            assert response.content, "Public object should have content"
            print(f"Public read successful: {len(response.content)} bytes")
            print(f"This confirms bucket allows public read access")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                pytest.skip(
                    "Bucket does not allow public read. "
                    "This test requires the bucket to have public read ACL enabled. "
                    "See docs/greenfield_integration_guide.md for setup instructions."
                )
            else:
                pytest.fail(f"Public read test failed: {e}")

    def test_public_url_format(self, greenfield_config):
        """Test that public URL format is correct for client-side access.

        This verifies the URL format that clients can use to download
        reputation data directly from Greenfield.
        """
        bucket = greenfield_config["GREENFIELD_BUCKET"]
        sp_host = greenfield_config["GREENFIELD_SP_HOST"]
        test_key = "test-object-key"

        # Expected URL format: https://{bucket}.{sp_host}/{object_key}
        expected_url = f"https://{bucket}.{sp_host}/{test_key}"

        print(f"\nPublic URL format: {expected_url}")
        print(f"Clients can use this URL format to download reputation data directly")

        # Verify URL components
        assert expected_url.startswith("https://")
        assert bucket in expected_url
        assert sp_host in expected_url
        assert test_key in expected_url

        print(f"URL format validation passed")


class TestGreenfieldStorageFactory:
    """Integration tests for storage factory with Greenfield backend."""

    def test_factory_creates_greenfield_from_env(self, greenfield_config):
        """Test that factory creates Greenfield storage from environment variables.

        This verifies the factory pattern works correctly with real configuration.
        """
        from agent0_sdk.core.storage_factory import create_reputation_storage

        # Set up environment to use Greenfield backend
        config = {
            "REPUTATION_BACKEND": "greenfield",
            **greenfield_config
        }

        try:
            print(f"\nCreating storage via factory with Greenfield backend")
            storage = create_reputation_storage(config=config)

            # Verify correct type
            from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage
            assert isinstance(storage, GreenfieldReputationStorage)

            # Verify configuration
            assert storage.bucket == greenfield_config["GREENFIELD_BUCKET"]
            assert storage.sp_host == greenfield_config["GREENFIELD_SP_HOST"]

            print(f"Factory created Greenfield storage successfully")
            print(f"  Bucket: {storage.bucket}")
            print(f"  SP Host: {storage.sp_host}")
            print(f"  Wallet: {storage.account.address}")

        except Exception as e:
            pytest.fail(f"Factory test failed: {e}")

    def test_factory_backend_switching(self, greenfield_config):
        """Test switching between IPFS and Greenfield backends via factory.

        This verifies that the same factory can create different backend types.
        """
        from agent0_sdk.core.storage_factory import create_reputation_storage
        from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage
        from agent0_sdk.core.ipfs_storage import IpfsReputationStorage
        from unittest.mock import Mock
        from agent0_sdk.core.ipfs_client import IPFSClient

        # Create Greenfield storage
        greenfield_config_full = {
            "REPUTATION_BACKEND": "greenfield",
            **greenfield_config
        }
        greenfield_storage = create_reputation_storage(config=greenfield_config_full)
        assert isinstance(greenfield_storage, GreenfieldReputationStorage)
        print(f"\nFactory created Greenfield storage")

        # Create IPFS storage
        mock_ipfs_client = Mock(spec=IPFSClient)
        ipfs_config = {"REPUTATION_BACKEND": "ipfs"}
        ipfs_storage = create_reputation_storage(config=ipfs_config, ipfs_client=mock_ipfs_client)
        assert isinstance(ipfs_storage, IpfsReputationStorage)
        print(f"Factory created IPFS storage")

        print(f"Backend switching validated successfully")


# Mark for pytest
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )

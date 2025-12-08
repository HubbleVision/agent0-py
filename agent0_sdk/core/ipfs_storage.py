"""
IPFS implementation of ReputationStorage interface.

This module wraps the existing IPFSClient to implement the ReputationStorage interface,
maintaining backward compatibility while allowing transparent backend switching.
"""

import json
import logging
from typing import Any, Dict

from .ipfs_client import IPFSClient
from .storage_interfaces import ReputationStorage

logger = logging.getLogger(__name__)


class IpfsReputationStorage(ReputationStorage):
    """IPFS-based implementation of ReputationStorage.

    This class wraps the existing IPFSClient and adapts it to the ReputationStorage
    interface. It maintains all existing IPFS functionality while providing a consistent
    interface for reputation data storage.
    """

    def __init__(self, client: IPFSClient):
        """Initialize IPFS reputation storage.

        Args:
            client: IPFSClient instance (supports local IPFS, Pinata, or Filecoin Pin)
        """
        self.client = client

    def put(self, key: str, data: bytes) -> str:
        """Store data on IPFS and return CID.

        Args:
            key: Optional key (not used for IPFS, which generates CID automatically)
            data: Binary data to store

        Returns:
            IPFS CID (Content Identifier)
        """
        # IPFS generates CID automatically based on content, key parameter is ignored
        # Convert bytes to string for IPFSClient.add()
        try:
            data_str = data.decode('utf-8')
        except UnicodeDecodeError:
            # If data is not valid UTF-8, store as base64 with magic prefix
            import base64
            data_str = "__B64__:" + base64.b64encode(data).decode('utf-8')
            logger.warning("Data is not valid UTF-8, storing as base64 with magic prefix")

        cid = self.client.add(data_str)
        logger.debug(f"Stored data on IPFS with CID: {cid}")
        return cid

    def get(self, key: str) -> bytes:
        """Retrieve data from IPFS by CID.

        Args:
            key: IPFS CID (Content Identifier)

        Returns:
            Binary data

        Raises:
            RuntimeError: If data cannot be retrieved from IPFS
        """
        try:
            data_str = self.client.get(key)

            # Check if data was stored as base64 (with magic prefix)
            if data_str.startswith("__B64__:"):
                import base64
                # Decode base64 to get original binary data
                b64_data = data_str[8:]  # Remove "__B64__:" prefix
                return base64.b64decode(b64_data)
            else:
                # Normal UTF-8 string, encode back to bytes
                return data_str.encode('utf-8')
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve data from IPFS (CID: {key}): {e}") from e

    def put_json(self, key: str, data: Dict[str, Any]) -> str:
        """Store JSON data on IPFS (convenience method).

        Args:
            key: Optional key (not used for IPFS)
            data: Dictionary to store as JSON

        Returns:
            IPFS CID
        """
        cid = self.client.add_json(data)
        logger.debug(f"Stored JSON data on IPFS with CID: {cid}")
        return cid

    def get_json(self, key: str) -> Dict[str, Any]:
        """Retrieve JSON data from IPFS (convenience method).

        Args:
            key: IPFS CID

        Returns:
            Dictionary parsed from JSON

        Raises:
            RuntimeError: If data cannot be retrieved or parsed
        """
        try:
            return self.client.get_json(key)
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve JSON from IPFS (CID: {key}): {e}") from e

    def build_uri(self, key: str) -> str:
        """Build IPFS URI for the stored data.

        Args:
            key: IPFS CID (Content Identifier)

        Returns:
            IPFS URI in the format "ipfs://CID"
        """
        return f"ipfs://{key}"

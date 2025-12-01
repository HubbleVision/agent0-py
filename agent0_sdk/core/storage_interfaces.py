"""
Storage interfaces for reputation data.

This module defines abstract interfaces for reputation storage backends,
allowing multiple implementations (IPFS, Greenfield, etc.) to be swapped transparently.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ReputationStorage(ABC):
    """Abstract interface for reputation data storage.

    This interface defines the contract for storing and retrieving reputation data,
    allowing multiple backend implementations (IPFS, BNB Greenfield, etc.) to be used
    interchangeably without affecting upper-layer business logic.
    """

    @abstractmethod
    def put(self, key: str, data: bytes, txn_hash: Optional[str] = None) -> str:
        """Store data and return a unique identifier.

        Args:
            key: Unique key for the data (can be empty string for auto-generation)
            data: Binary data to store
            txn_hash: Optional transaction hash for Greenfield CreateObject operation.
                     Required for Greenfield, ignored for IPFS.
                     If not provided, uses the default from constructor (if available).

        Returns:
            Unique identifier (CID for IPFS, object key for Greenfield)
        """
        pass

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve data by key.

        Args:
            key: Unique identifier returned by put()

        Returns:
            Binary data

        Raises:
            RuntimeError: If data cannot be retrieved
        """
        pass

    @abstractmethod
    def put_json(self, key: str, data: Dict[str, Any], txn_hash: Optional[str] = None) -> str:
        """Store JSON data and return a unique identifier.

        Args:
            key: Unique key for the data (can be empty string for auto-generation)
            data: Dictionary to store as JSON
            txn_hash: Optional transaction hash for Greenfield CreateObject operation.
                     Required for Greenfield, ignored for IPFS.

        Returns:
            Unique identifier (CID for IPFS, object key for Greenfield)
        """
        pass

    @abstractmethod
    def get_json(self, key: str) -> Dict[str, Any]:
        """Retrieve JSON data by key.

        Args:
            key: Unique identifier returned by put_json()

        Returns:
            Dictionary parsed from JSON

        Raises:
            RuntimeError: If data cannot be retrieved or parsed
        """
        pass

    @abstractmethod
    def build_uri(self, key: str) -> str:
        """Build a URI for the stored data.

        Args:
            key: Unique identifier (CID for IPFS, object key for Greenfield)

        Returns:
            URI string (e.g., "ipfs://CID" or "https://bucket.sp_host/key")
        """
        pass

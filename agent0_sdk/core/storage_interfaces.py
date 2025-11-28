"""
Storage interfaces for reputation data.

This module defines abstract interfaces for reputation storage backends,
allowing multiple implementations (IPFS, Greenfield, etc.) to be swapped transparently.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class ReputationStorage(ABC):
    """Abstract interface for reputation data storage.

    This interface defines the contract for storing and retrieving reputation data,
    allowing multiple backend implementations (IPFS, BNB Greenfield, etc.) to be used
    interchangeably without affecting upper-layer business logic.
    """

    @abstractmethod
    def put(self, key: str, data: bytes) -> str:
        """Store data and return a unique identifier.

        Args:
            key: Unique key for the data (can be empty string for auto-generation)
            data: Binary data to store

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

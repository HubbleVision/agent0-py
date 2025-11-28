"""
Factory for creating ReputationStorage instances.

This module provides a factory function to create appropriate storage backend
instances based on configuration, enabling transparent switching between
IPFS, BNB Greenfield, and future storage implementations.
"""

import logging
import os
from typing import Any, Dict, Optional

from .ipfs_client import IPFSClient
from .ipfs_storage import IpfsReputationStorage
from .storage_interfaces import ReputationStorage

logger = logging.getLogger(__name__)


def create_reputation_storage(
    config: Optional[Dict[str, Any]] = None,
    ipfs_client: Optional[IPFSClient] = None
) -> ReputationStorage:
    """Create a ReputationStorage instance based on configuration.

    This factory function instantiates the appropriate storage backend
    (IPFS or Greenfield) based on the REPUTATION_BACKEND configuration.
    Defaults to IPFS for backward compatibility.

    Args:
        config: Configuration dictionary (optional). If None, reads from environment.
                Expected keys:
                - REPUTATION_BACKEND: "ipfs" (default) or "greenfield"
                - For IPFS: uses ipfs_client parameter or creates from config
                - For Greenfield (Phase 2):
                  - GREENFIELD_SP_HOST: SP endpoint (e.g., gnfd-testnet-sp1.bnbchain.org)
                  - GREENFIELD_BUCKET: Bucket name
                  - GREENFIELD_PRIVATE_KEY: Private key for signing
                  - GREENFIELD_TXN_HASH: Transaction hash from CreateObject
        ipfs_client: Pre-initialized IPFSClient instance (optional).
                     If provided and backend is IPFS, this client will be used.

    Returns:
        ReputationStorage implementation instance

    Raises:
        ValueError: If configuration is invalid or required parameters are missing
    """
    cfg = config or {}
    backend = cfg.get("REPUTATION_BACKEND") or os.getenv("REPUTATION_BACKEND", "ipfs")

    logger.info(f"Creating reputation storage with backend: {backend}")

    if backend == "greenfield":
        # Phase 2: Greenfield implementation will be added here
        # For now, raise NotImplementedError
        raise NotImplementedError(
            "Greenfield storage backend not yet implemented. "
            "Please use 'ipfs' backend or wait for Phase 2 completion."
        )

    # Default to IPFS backend
    if backend != "ipfs":
        logger.warning(
            f"Unknown reputation backend '{backend}', falling back to IPFS. "
            f"Valid options: 'ipfs' (currently), 'greenfield' (Phase 2+)"
        )

    # Use provided IPFS client or create a new one
    if ipfs_client is None:
        # Create IPFS client from config if not provided
        ipfs_url = cfg.get("IPFS_API_URL") or os.getenv("IPFS_API_URL")
        ipfs_client = IPFSClient(url=ipfs_url) if ipfs_url else IPFSClient()

    storage = IpfsReputationStorage(client=ipfs_client)
    logger.debug(f"Created IPFS reputation storage: {storage}")

    return storage


def build_ipfs_client(config: Optional[Dict[str, Any]] = None) -> IPFSClient:
    """Build an IPFSClient instance from configuration (helper function).

    This is a convenience function to create IPFSClient instances
    with the same configuration pattern used throughout the SDK.

    Args:
        config: Configuration dictionary (optional)
                Expected keys:
                - IPFS_API_URL: IPFS node URL (e.g., http://localhost:5001)
                - IPFS_GATEWAY_URL: IPFS gateway URL (optional)
                - FILECOIN_PIN_ENABLED: Enable Filecoin Pin (bool)
                - FILECOIN_PRIVATE_KEY: Private key for Filecoin Pin
                - PINATA_ENABLED: Enable Pinata (bool)
                - PINATA_JWT: JWT token for Pinata authentication

    Returns:
        IPFSClient instance
    """
    cfg = config or {}

    ipfs_url = cfg.get("IPFS_API_URL") or os.getenv("IPFS_API_URL")
    filecoin_pin_enabled = cfg.get("FILECOIN_PIN_ENABLED") or os.getenv("FILECOIN_PIN_ENABLED", "false").lower() == "true"
    filecoin_private_key = cfg.get("FILECOIN_PRIVATE_KEY") or os.getenv("FILECOIN_PRIVATE_KEY")
    pinata_enabled = cfg.get("PINATA_ENABLED") or os.getenv("PINATA_ENABLED", "false").lower() == "true"
    pinata_jwt = cfg.get("PINATA_JWT") or os.getenv("PINATA_JWT")

    return IPFSClient(
        url=ipfs_url,
        filecoin_pin_enabled=filecoin_pin_enabled,
        filecoin_private_key=filecoin_private_key,
        pinata_enabled=pinata_enabled,
        pinata_jwt=pinata_jwt
    )

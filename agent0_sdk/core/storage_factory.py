"""
Factory for creating ReputationStorage instances.

This module provides a factory function to create appropriate storage backend
instances based on configuration, enabling transparent switching between
IPFS, BNB Greenfield, and future storage implementations.
"""

import logging
import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional

from .ipfs_client import IPFSClient
from .ipfs_storage import IpfsReputationStorage
from .storage_interfaces import ReputationStorage

logger = logging.getLogger(__name__)

# Import Greenfield storage lazily to avoid dependency issues
def _import_greenfield_storage():
    """Lazy import of GreenfieldReputationStorage to avoid requiring eth-utils when not needed."""
    try:
        from .greenfield_storage import GreenfieldReputationStorage
        return GreenfieldReputationStorage
    except ImportError as e:
        raise ImportError(
            "Greenfield storage requires additional dependencies. "
            "Install with: pip install eth-utils>=2.0.0"
        ) from e


def _default_greenfield_cli_template() -> Optional[str]:
    """提供一个默认的 gnfd-cmd 模板，未配置时使用。"""
    repo_root = Path(__file__).resolve().parents[3]
    bin_name = "gnfd-cmd_mac" if platform.system().lower() == "darwin" else "gnfd-cmd"
    cli_path = repo_root / "bin" / bin_name
    if not cli_path.exists():
        return None
    return f"{cli_path} object put --contentType {{content_type}} {{file}} gnfd://{{bucket}}/{{object}}"


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
                - For Greenfield (CLI only):
                  - GREENFIELD_SP_HOST: SP endpoint (e.g., gnfd-testnet-sp1.bnbchain.org)
                  - GREENFIELD_BUCKET: Bucket name
                  - GREENFIELD_PRIVATE_KEY: Private key for signing
                  - GREENFIELD_CREATE_OBJECT_CMD_TEMPLATE: Optional; defaults to bundled gnfd-cmd template
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
        # Phase 2: Greenfield implementation
        GreenfieldReputationStorage = _import_greenfield_storage()

        # Load Greenfield configuration
        sp_host = cfg.get("GREENFIELD_SP_HOST") or os.getenv("GREENFIELD_SP_HOST")
        bucket = cfg.get("GREENFIELD_BUCKET") or os.getenv("GREENFIELD_BUCKET")
        private_key = cfg.get("GREENFIELD_PRIVATE_KEY") or os.getenv("GREENFIELD_PRIVATE_KEY")
        txn_hash = cfg.get("GREENFIELD_TXN_HASH") or os.getenv("GREENFIELD_TXN_HASH")
        content_type = cfg.get("GREENFIELD_CONTENT_TYPE") or os.getenv("GREENFIELD_CONTENT_TYPE", "application/octet-stream")
        timeout = int(cfg.get("GREENFIELD_TIMEOUT") or os.getenv("GREENFIELD_TIMEOUT", "30"))
        greenfield_rpc_url = cfg.get("GREENFIELD_RPC_URL") or os.getenv("GREENFIELD_RPC_URL") or "https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org:443"
        chain_id_val = cfg.get("GREENFIELD_CHAIN_ID") or os.getenv("GREENFIELD_CHAIN_ID") or 5600
        try:
            greenfield_chain_id = int(chain_id_val)
        except Exception:
            greenfield_chain_id = 5600
        cli_chain_id = cfg.get("GREENFIELD_CLI_CHAIN_ID") or os.getenv("GREENFIELD_CLI_CHAIN_ID")
        create_object_template = (
            cfg.get("GREENFIELD_CREATE_OBJECT_CMD_TEMPLATE")
            or os.getenv("GREENFIELD_CREATE_OBJECT_CMD_TEMPLATE")
            or _default_greenfield_cli_template()
        )

        # Validate required parameters
        if not sp_host:
            raise ValueError("GREENFIELD_SP_HOST is required when using Greenfield backend")
        if not bucket:
            raise ValueError("GREENFIELD_BUCKET is required when using Greenfield backend")
        if not private_key:
            raise ValueError("GREENFIELD_PRIVATE_KEY is required when using Greenfield backend")

        if not create_object_template:
            raise ValueError("GREENFIELD_CREATE_OBJECT_CMD_TEMPLATE is required (CLI-only Greenfield).")

        # If running inside Linux container but template points to mac binary, try swapping to gnfd-cmd
        if "gnfd-cmd_mac" in create_object_template and platform.system().lower() == "linux":
            adjusted = create_object_template.replace("gnfd-cmd_mac", "gnfd-cmd")
            if os.path.exists(adjusted.split()[0]):
                logger.info("Adjusted Greenfield CLI template for Linux: %s", adjusted)
                create_object_template = adjusted
            else:
                raise ValueError(f"gnfd-cmd not found for Linux runtime: {create_object_template}")

        try:
            from .greenfield_cli import GreenfieldCreateObjectHelper

            create_object_helper = GreenfieldCreateObjectHelper(
                rpc_url=greenfield_rpc_url,
                sp_host=sp_host,
                bucket_name=bucket,
                private_key=private_key,
                chain_id=greenfield_chain_id,
                cli_chain_id=cli_chain_id,
                cli_template=create_object_template,
            )
            logger.info("Greenfield CLI helper enabled for uploads")
        except Exception as helper_exc:
            raise ValueError(f"初始化 Greenfield CLI helper 失败：{helper_exc}") from helper_exc

        storage = GreenfieldReputationStorage(
            sp_host=sp_host,
            bucket=bucket,
            private_key=private_key,
            txn_hash=txn_hash,
            content_type=content_type,
            timeout=timeout,
            create_object_helper=create_object_helper,
        )
        logger.debug(f"Created Greenfield reputation storage: bucket={bucket}, sp_host={sp_host}")
        return storage

    # Default to IPFS backend
    if backend != "ipfs":
        logger.warning(
            f"Unknown reputation backend '{backend}', falling back to IPFS. "
            f"Valid options: 'ipfs', 'greenfield'"
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

    # Boolean flags: use dict.get() with env fallback as default
    # This ensures explicit False config values are respected (not treated as missing)
    filecoin_pin_val = cfg.get("FILECOIN_PIN_ENABLED", os.getenv("FILECOIN_PIN_ENABLED", "false"))
    filecoin_pin_enabled = str(filecoin_pin_val).lower() == "true"

    filecoin_private_key = cfg.get("FILECOIN_PRIVATE_KEY") or os.getenv("FILECOIN_PRIVATE_KEY")

    pinata_val = cfg.get("PINATA_ENABLED", os.getenv("PINATA_ENABLED", "false"))
    pinata_enabled = str(pinata_val).lower() == "true"

    pinata_jwt = cfg.get("PINATA_JWT") or os.getenv("PINATA_JWT")

    return IPFSClient(
        url=ipfs_url,
        filecoin_pin_enabled=filecoin_pin_enabled,
        filecoin_private_key=filecoin_private_key,
        pinata_enabled=pinata_enabled,
        pinata_jwt=pinata_jwt
    )

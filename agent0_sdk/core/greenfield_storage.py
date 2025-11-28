"""
BNB Greenfield implementation of ReputationStorage interface.

This module provides a Greenfield-based storage backend for reputation data,
using the Greenfield Storage Provider HTTP API for PutObject/GetObject operations.

Reference:
- SP API docs: https://github.com/bnb-chain/greenfield-storage-provider/blob/master/docs/storage-provider-rest-api/
- Authorization: https://github.com/bnb-chain/greenfield-storage-provider/blob/master/docs/storage-provider-rest-api/README.md#authorization-header
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import quote

import requests
from eth_account import Account
from eth_account.messages import encode_defunct

from .storage_interfaces import ReputationStorage

logger = logging.getLogger(__name__)


class GreenfieldReputationStorage(ReputationStorage):
    """BNB Greenfield-based implementation of ReputationStorage.

    This class implements reputation storage using BNB Greenfield's
    decentralized storage network via the Storage Provider HTTP API.
    """

    def __init__(
        self,
        sp_host: str,
        bucket: str,
        private_key: str,
        txn_hash: Optional[str] = None,
        content_type: str = "application/octet-stream",
        timeout: int = 30,
    ):
        """Initialize Greenfield reputation storage.

        Args:
            sp_host: Storage Provider host (e.g., gnfd-testnet-sp1.bnbchain.org)
            bucket: Bucket name for storing objects
            private_key: Private key for signing requests (hex string with or without 0x prefix)
            txn_hash: Optional default transaction hash from CreateObject operation.
                     Can be overridden per-object in put() method.
                     Required for PutObject unless provided in each put() call.
            content_type: Default Content-Type for objects (default: application/octet-stream)
            timeout: Request timeout in seconds (default: 30)

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not sp_host:
            raise ValueError("sp_host is required")
        if not bucket:
            raise ValueError("bucket is required")
        if not private_key:
            raise ValueError("private_key is required")

        self.sp_host = sp_host.strip()
        self.bucket = bucket.strip()
        self.default_txn_hash = txn_hash.strip() if txn_hash else None
        self.content_type = content_type
        self.timeout = timeout

        # Initialize account from private key
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key
        self.account = Account.from_key(private_key)
        self.session = requests.Session()

        if not self.default_txn_hash:
            logger.warning(
                "No default txn_hash provided. You must provide txn_hash in each put() call."
            )

        logger.info(
            f"Initialized Greenfield storage: bucket={bucket}, sp_host={sp_host}, "
            f"wallet={self.account.address}, has_default_txn_hash={bool(self.default_txn_hash)}"
        )

    def put(self, key: str, data: bytes, txn_hash: Optional[str] = None) -> str:
        """Store data on Greenfield and return object key.

        Args:
            key: Object key/name (if empty, auto-generates UUID-based key)
            data: Binary data to store
            txn_hash: Optional transaction hash from CreateObject operation for this specific object.
                     If not provided, uses the default from constructor.
                     At least one (parameter or default) must be available.

        Returns:
            Object key (name) that can be used to retrieve the data

        Raises:
            ValueError: If no txn_hash is available (neither provided nor default)
            RuntimeError: If upload fails
        """
        # Determine which txn_hash to use (prioritize parameter over default)
        effective_txn_hash = txn_hash if txn_hash else self.default_txn_hash

        if not effective_txn_hash:
            raise ValueError(
                "txn_hash is required for Greenfield PutObject operation. "
                "Provide it either in constructor or in put() call."
            )

        # Generate key if not provided
        object_key = key.strip() if key else self._gen_key()

        # Build URL (using virtual-hosted-style)
        url = f"https://{self.bucket}.{self.sp_host}/{quote(object_key, safe='')}"

        # Prepare expiry timestamp (24 hours from now)
        expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        expiry_str = expiry.isoformat().replace("+00:00", "Z")

        # Prepare headers (must include all x-gnfd-* headers BEFORE signing)
        headers = {
            "Content-Type": self.content_type,
            "Content-Length": str(len(data)),
            "X-Gnfd-Txn-Hash": effective_txn_hash,
            "X-Gnfd-Expiry-Timestamp": expiry_str,
        }

        # Build authorization (signs all headers including x-gnfd-* headers)
        auth_header = self._build_authorization(
            method="PUT",
            path=f"/{object_key}",
            headers=headers,
            body=data,
        )
        headers["Authorization"] = auth_header

        logger.debug(f"PUT {url} (key={object_key}, size={len(data)} bytes)")

        try:
            resp = self.session.put(url, headers=headers, data=data, timeout=self.timeout)
            resp.raise_for_status()

            etag = resp.headers.get("ETag", "")
            request_id = resp.headers.get("X-Gnfd-Request-ID", "")
            logger.info(
                f"Successfully uploaded to Greenfield: key={object_key}, "
                f"etag={etag}, request_id={request_id}"
            )

            return object_key

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to upload to Greenfield (key={object_key}): {e}"
            if hasattr(e, "response") and e.response is not None:
                error_msg += f" Response: {e.response.text}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get(self, key: str) -> bytes:
        """Retrieve data from Greenfield by object key.

        Args:
            key: Object key (name) to retrieve

        Returns:
            Binary data

        Raises:
            RuntimeError: If retrieval fails
        """
        # Build URL (using virtual-hosted-style)
        url = f"https://{self.bucket}.{self.sp_host}/{quote(key, safe='')}"

        logger.debug(f"GET {url} (key={key})")

        try:
            # For public buckets, GET doesn't require Authorization
            # For private buckets, you'd need to add Authorization header here
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()

            logger.info(f"Successfully retrieved from Greenfield: key={key}, size={len(resp.content)} bytes")
            return resp.content

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to retrieve from Greenfield (key={key}): {e}"
            if hasattr(e, "response") and e.response is not None:
                error_msg += f" Response: {e.response.text}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _gen_key(self) -> str:
        """Generate a unique object key using UUID.

        Returns:
            UUID-based key (hex format without hyphens)
        """
        return uuid.uuid4().hex

    def _build_authorization(
        self,
        method: str,
        path: str,
        headers: dict,
        body: Optional[bytes] = None,
    ) -> str:
        """Build Authorization header for Greenfield SP API.

        Implements GNFD1-ECDSA authentication as per:
        https://github.com/bnb-chain/greenfield-storage-provider/blob/master/docs/storage-provider-rest-api/README.md#authorization-header

        Args:
            method: HTTP method (e.g., "PUT", "GET")
            path: Request path (e.g., "/object-name")
            headers: Request headers dict
            body: Request body bytes (optional)

        Returns:
            Authorization header value (e.g., "GNFD1-ECDSA, Signature=0x...")
        """
        # Construct canonical request
        canonical_request = self._build_canonical_request(
            method=method,
            path=path,
            query_string="",  # No query parameters for basic PUT/GET
            headers=headers,
            body=body,
        )

        logger.debug(f"Canonical request:\n{canonical_request}")

        # Hash canonical request using Keccak256
        canonical_hash = self._keccak256(canonical_request.encode("utf-8"))

        # Sign the hash using secp256k1 (via eth_account)
        # eth_account expects the hash as bytes
        signature = self.account.signHash(canonical_hash)

        # Format signature as lowercase hex (without 0x prefix for the signature value)
        # Combine r, s, v into standard Ethereum signature format
        signature_hex = signature.signature.hex()

        # Build authorization header
        auth_header = f"GNFD1-ECDSA, Signature={signature_hex}"

        logger.debug(f"Authorization: {auth_header[:50]}...")

        return auth_header

    def _build_canonical_request(
        self,
        method: str,
        path: str,
        query_string: str,
        headers: dict,
        body: Optional[bytes] = None,
    ) -> str:
        """Build canonical request string for signing.

        Format (newline-separated):
        1. HTTPMethod
        2. CanonicalUri (URI-encoded path)
        3. CanonicalQueryString (URL-encoded params, alphabetically sorted)
        4. CanonicalHeaders (lowercase header:value pairs, alphabetically sorted)
        5. SignedHeaders (semicolon-separated header names)

        Args:
            method: HTTP method (uppercase)
            path: Request path (e.g., "/object-name")
            query_string: Query string (empty for basic operations)
            headers: Request headers
            body: Request body (optional, for payload hash if needed)

        Returns:
            Canonical request string
        """
        # 1. HTTP Method (uppercase)
        http_method = method.upper()

        # 2. Canonical URI (URI-encode the path, but preserve '/')
        canonical_uri = quote(path, safe="/") if path else "/"

        # 3. Canonical Query String (empty for PUT/GET without queries)
        canonical_query_string = query_string

        # 4. Canonical Headers
        # Include host and all x-gnfd-* headers, lowercase keys, alphabetically sorted
        canonical_headers_dict = {
            "host": f"{self.bucket}.{self.sp_host}",
        }

        # Add x-gnfd-* headers (lowercase keys)
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower.startswith("x-gnfd-"):
                canonical_headers_dict[key_lower] = str(value).strip()

        # Sort by key and format as "key:value\n"
        canonical_headers_list = sorted(canonical_headers_dict.items())
        canonical_headers = "\n".join(f"{k}:{v}" for k, v in canonical_headers_list) + "\n"

        # 5. Signed Headers (semicolon-separated, alphabetically sorted)
        signed_headers = ";".join(sorted(canonical_headers_dict.keys()))

        # Combine all parts with newlines
        canonical_request = "\n".join([
            http_method,
            canonical_uri,
            canonical_query_string,
            canonical_headers,
            signed_headers,
        ])

        return canonical_request

    def _keccak256(self, data: bytes) -> bytes:
        """Compute Keccak256 hash (compatible with Web3/Ethereum).

        Args:
            data: Input data bytes

        Returns:
            Keccak256 hash (32 bytes)
        """
        # Use Web3's keccak for compatibility with Greenfield
        from eth_utils import keccak
        return keccak(data)

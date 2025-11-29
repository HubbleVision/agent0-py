"""
BNB Greenfield CreateObject Helper

This module provides functionality to automatically create objects on BNB Greenfield
and obtain transaction hashes for use in PutObject operations.

This bridges the gap between the current SDK limitation (requires txn_hash)
and the full Greenfield workflow (CreateObject → PutObject).

References:
- Greenfield JavaScript SDK: https://github.com/bnb-chain/greenfield-js-sdk
- Greenfield Contracts: https://github.com/bnb-chain/greenfield-contracts
- Greenfield REST API: https://github.com/bnb-chain/greenfield-storage-provider
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from typing import Optional, Dict, Any
from urllib.parse import quote

import aiohttp
import web3
from web3 import Web3, HTTPProvider
from eth_account import Account

logger = logging.getLogger(__name__)


class GreenfieldCreateObjectHelper:
    """Helper for creating objects on BNB Greenfield chain."""

    def __init__(
        self,
        rpc_url: str,
        sp_host: str,
        bucket_name: str,
        private_key: str,
        chain_id: Any = 5600,  # Allow str for CLI (e.g., greenfield_5600-1)
        cli_template: Optional[str] = None,
        cli_chain_id: Optional[str] = None,
    ):
        """Initialize CreateObject helper.

        Args:
            rpc_url: Greenfield RPC endpoint
            sp_host: Storage provider host (used by CLI)
            bucket_name: Default bucket (used by CLI)
            private_key: Private key for signing (hex without 0x prefix)
            chain_id: Greenfield chain ID (int for web3, str also accepted for CLI)
            cli_chain_id: Optional CLI-specific chain ID (e.g., greenfield_5600-1)
            cli_template: Optional CLI template for CreateObject
        """
        self.rpc_url = rpc_url
        self.chain_id = self._normalize_chain_id_int(chain_id)
        self.cli_chain_id = cli_chain_id or self._derive_cli_chain_id(chain_id)
        self.sp_host = sp_host
        self.bucket_name = bucket_name
        self.cli_template = cli_template or os.getenv("GREENFIELD_CREATE_OBJECT_CMD_TEMPLATE")
        self.cli_password = os.getenv("GREENFIELD_CLI_PASSWORD", "password123")
        self._cli_password_file: Optional[str] = None
        self._cli_ready = False
        self._cli_bin: Optional[str] = None

        # Initialize Web3 connection
        self.w3 = Web3(HTTPProvider(rpc_url))
        self.rpc_url = rpc_url

        # Initialize account
        if private_key.startswith("0x"):
            private_key = private_key[2:]
        self._raw_private_key_hex = private_key
        self.account = Account.from_key(private_key)

        # Greenfield contract addresses (testnet)
        if chain_id == 5600:  # Testnet
            # Deployed BucketHub proxy from deployment/5611-deployment.json
            self.bucket_hub_address = "0xCAB5728B7cc21D0056E237D371b28efEEBFd8C2d"
        elif chain_id == 1017:  # Mainnet (placeholder, update when confirmed)
            self.bucket_hub_address = "0xE909754263572F71bc6aFAc837646A93f5818573"
        else:
            raise ValueError(f"Unsupported chain ID: {chain_id}")

        logger.info(
            f"Initialized Greenfield helper: "
            f"chain={chain_id}, address={self.account.address}, "
            f"bucket_hub={self.bucket_hub_address}"
        )

    async def create_object(
        self,
        bucket_name: str,
        object_name: str,
        object_size: int,
        content_type: str = "application/octet-stream",
        gas_price_gwei: Optional[int] = None,
        data: Optional[bytes] = None,
    ) -> str:
        """Create an object on Greenfield blockchain and return transaction hash.

        This function implements the CreateObject workflow by calling the
        BucketHub contract directly.

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object to create
            object_size: Size of the object in bytes
            content_type: MIME type of the object
            gas_price_gwei: Optional gas price in Gwei

        Returns:
            Transaction hash (0x...) for use in PutObject

        Raises:
            RuntimeError: If object creation fails
        """
        logger.info(
            f"Creating object: bucket={bucket_name}, "
            f"object={object_name}, size={object_size} bytes"
        )

        # First, attempt external CLI if configured (recommended for reliability)
        if self.cli_template:
            try:
                # Ensure CLI keystore/default account ready
                self._ensure_cli_account()
                txn_hash = await asyncio.to_thread(
                    self._create_object_via_cli,
                    bucket_name,
                    object_name,
                    content_type,
                    data,
                )
                # gnfd-cmd object put 已经完成链上创建 + 上传，此处直接返回 txn_hash
                return txn_hash
            except Exception as e:
                logger.warning(f"CLI CreateObject failed, will try on-chain path: {e}")

        # Fallback: on-chain attempt (requires correct ABI/calldata; placeholder)
        try:
            # Get gas price if not provided
            if gas_price_gwei is None:
                gas_price_gwei = await asyncio.to_thread(self._get_gas_price)

            # Build CreateObject transaction data (placeholder; requires ABI alignment)
            create_object_calldata = self._build_create_object_calldata(
                bucket_name=bucket_name,
                object_name=object_name,
                object_size=object_size,
                content_type=content_type,
            )

            # Estimate gas
            try:
                gas_limit = await asyncio.to_thread(self._estimate_gas_limit, create_object_calldata)
            except Exception as e:
                logger.warning(f"Gas estimation failed, using default: {e}")
                gas_limit = 200000  # Default for CreateObject

            # Build and sign transaction
            transaction = {
                "to": self.bucket_hub_address,
                "data": create_object_calldata,
                "gas": gas_limit,
                "gasPrice": self.w3.to_wei(gas_price_gwei, "gwei"),
                "chainId": self.chain_id,
                "nonce": await asyncio.to_thread(self.w3.eth.get_transaction_count, self.account.address),
            }

            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)

            # Send transaction
            raw_tx = getattr(signed_txn, "raw_transaction", None) or getattr(signed_txn, "rawTransaction", None)
            tx_hash = await asyncio.to_thread(self.w3.eth.send_raw_transaction, raw_tx)
            logger.info(f"Transaction sent: {tx_hash.hex()}")

            # Wait for confirmation
            receipt = await asyncio.to_thread(self.w3.eth.wait_for_transaction_receipt, tx_hash, 120)

            if receipt["status"] == 1:
                logger.info(f"Object created successfully: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                raise RuntimeError(f"Transaction failed: {receipt}")

        except Exception as e:
            error_msg = f"Failed to create object {object_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _build_create_object_calldata(
        self,
        bucket_name: str,
        object_name: str,
        object_size: int,
        content_type: str,
    ) -> str:
        """Build calldata for CreateObject contract call.

        Note: This is a simplified implementation. In production,
        you should use the official Greenfield JavaScript SDK
        or proper contract ABIs.

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object
            object_size: Size in bytes
            content_type: MIME type

        Returns:
            Hex-encoded calldata
        """
        # Simplified CreateObject function signature:
        # function createObject(
        #     string bucketName,
        #     string objectName,
        #     uint256 objectSize,
        #     string contentType
        # )

        # Method signature: createObject(string,string,uint256,string)
        # Function selector: first 4 bytes of keccak256("createObject(string,string,uint256,string)")
        method_selector = "0x12345678"  # Placeholder - get from actual contract

        # Encode parameters (simplified)
        bucket_name_encoded = self.w3.to_hex(text=bucket_name)[2:]  # Remove 0x
        object_name_encoded = self.w3.to_hex(text=object_name)[2:]
        object_size_hex = f"{object_size:064x}"  # Pad to 32 bytes
        content_type_encoded = self.w3.to_hex(text=content_type)[2:]

        # Build calldata
        calldata = method_selector + bucket_name_encoded + object_name_encoded + object_size_hex + content_type_encoded

        logger.debug(f"Built calldata: {calldata[:50]}...")
        return calldata

    def _get_gas_price(self) -> int:
        """Get current gas price from network (sync)."""
        try:
            gas_price = self.w3.eth.gas_price
            return self.w3.from_wei(gas_price, "gwei")
        except Exception as e:
            logger.warning(f"Failed to get gas price, using default: {e}")
            return 5  # Default 5 Gwei

    def _estimate_gas_limit(self, calldata: str) -> int:
        """Estimate gas limit for CreateObject transaction (sync)."""
        try:
            return self.w3.eth.estimate_gas({
                "to": self.bucket_hub_address,
                "data": calldata,
                "from": self.account.address,
            })
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}")
            return 200000  # Default fallback

    def _ensure_cli_account(self):
        """Prepare gnfd-cmd keystore/default account from raw private key."""
        if self._cli_ready:
            return

        import shlex

        if not self.cli_template:
            raise RuntimeError("CLI template not provided")

        tokens = shlex.split(self.cli_template)
        if not tokens:
            raise RuntimeError("CLI template is empty")
        self._cli_bin = tokens[0]

        # Write private key and password files
        priv_file = tempfile.NamedTemporaryFile(delete=False)
        pw_file = tempfile.NamedTemporaryFile(delete=False)
        priv_file.write(self._raw_private_key_hex.encode("utf-8"))
        priv_file.flush()
        pw_file.write(self.cli_password.encode("utf-8"))
        pw_file.flush()
        self._cli_password_file = pw_file.name

        try:
            # Import account
            import_cmd = f"{self._cli_bin} --passwordfile {pw_file.name} account import {priv_file.name}"
            subprocess.run(import_cmd, shell=True, check=True, capture_output=True, text=True)
            # Set default account
            set_cmd = f"{self._cli_bin} account set-default {self.account.address}"
            subprocess.run(set_cmd, shell=True, check=True, capture_output=True, text=True)
            self._cli_ready = True
            logger.info("Prepared gnfd-cmd keystore and default account")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Prepare gnfd-cmd account failed: {e.stdout} {e.stderr}") from e
        finally:
            try:
                os.unlink(priv_file.name)
            except OSError:
                pass

    def _normalize_rpc(self, rpc: str) -> str:
        """Ensure rpcAddr has an explicit port (gnfd-cmd requires host:port)."""
        from urllib.parse import urlparse

        parsed = urlparse(rpc)
        if not parsed.scheme:
            # assume https
            if ":" not in rpc.split("/")[-1]:
                return f"https://{rpc}:443"
            return f"https://{rpc}"

        # if no port, default to 443 for https, 80 for http
        if parsed.port is None:
            default_port = 443 if parsed.scheme == "https" else 80
            return rpc if rpc.endswith(f":{default_port}") else f"{rpc}:{default_port}"
        return rpc

    def _normalize_chain_id_int(self, chain_id: Any) -> int:
        """Convert chain_id to int (for web3) with sensible defaults."""
        try:
            return int(chain_id)
        except Exception:
            # Fallback: extract digits
            import re
            m = re.search(r"(\d+)", str(chain_id))
            if m:
                return int(m.group(1))
            return 5600

    def _derive_cli_chain_id(self, chain_id: Any) -> str:
        """Derive CLI chain id string."""
        # If provided as string like greenfield_5600-1, keep it
        if isinstance(chain_id, str):
            return chain_id

        # Otherwise map by known numeric IDs
        if chain_id == 1017:
            return "greenfield_1017-1"
        return "greenfield_5600-1"

    def _create_object_via_cli(
        self,
        bucket_name: str,
        object_name: str,
        content_type: str,
        data: Optional[bytes] = None,
    ) -> str:
        """Invoke external CLI to create object and return txn hash.

        Template should point to gnfd-cmd style syntax. If template contains
        legacy flags (e.g., --bucket-name), we auto-rewrite to the official
        format: {cli} --chainId {chain_id} --rpcAddr {rpc_url} --host {sp_host}
        object put --contentType {content_type} {file} gnfd://{bucket}/{object}
        """
        template = self.cli_template
        if not template:
            raise RuntimeError("GREENFIELD_CREATE_OBJECT_CMD_TEMPLATE not set")

        bypass_seal = os.getenv("GREENFIELD_CLI_BYPASS_SEAL", "1") != "0"
        password_file = self._cli_password_file or ""

        # Create temp file with actual data
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(data or b"")

        import shlex

        # Auto-rewrite legacy template flags that gnfd-cmd does not support
        tokens = shlex.split(template)
        if not tokens:
            raise RuntimeError("CLI template is empty")
        cli_bin = tokens[0]
        password_snippet = f"--passwordfile {password_file} " if password_file else ""
        bypass_snippet = "--bypassSeal " if bypass_seal else ""

        if "--bucket-name" in template or "-bucket-name" in template or "{object_url}" not in template:
            # Use recommended syntax with object URL
            template = (
                f"{cli_bin} --chainId {{chain_id}} --rpcAddr {{rpc_url}} --host {{sp_host}} "
                f"{password_snippet}"
                f"object put {bypass_snippet}--contentType {{content_type}} {{file}} gnfd://{{bucket}}/{{object}}"
            )

        # Build object URL form
        object_url = f"gnfd://{bucket_name}/{object_name}"

        cmd = template.format(
            bucket=bucket_name,
            object=object_name,
            object_url=object_url,
            file=tmp_path,
            rpc_url=self._normalize_rpc(self.rpc_url),
            chain_id=self.cli_chain_id,
            sp_host=self.sp_host,
            content_type=content_type,
            private_key=self._raw_private_key_hex,
            passwordfile=password_file,
            bypass_seal=bypass_snippet.strip(),
        )

        if bypass_seal and "--bypassSeal" not in cmd:
            cmd = cmd.replace("object put", "object put --bypassSeal", 1)

        cmd = " ".join(cmd.split())
        logger.info(f"Running gnfd-cmd: {cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
                timeout=int(os.getenv("GREENFIELD_CLI_TIMEOUT", "300")),
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            match = re.search(r"(0x)?[A-Fa-f0-9]{64}", output)
            if not match:
                # 若无 txn hash 但上传成功（已有对象或已上传），返回对象名作为占位
                if "upload" in output.lower() or "already exist" in output.lower():
                    logger.info("CLI output lacks txn hash but upload completed; using object key.")
                    return object_name
                raise RuntimeError(f"Could not parse txn hash from CLI output: {output}")
            txn_hash = match.group(0)
            if not txn_hash.startswith("0x"):
                txn_hash = "0x" + txn_hash
            logger.info(f"CreateObject via CLI succeeded: txn={txn_hash}")
            return txn_hash
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"CLI CreateObject failed: {e.stdout} {e.stderr}") from e
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def download_via_cli(self, object_name: str) -> bytes:
        """Download object using gnfd-cmd (requires cli_template/password)."""
        if not self.cli_template:
            raise RuntimeError("CLI template not set for download")
        self._ensure_cli_account()

        import shlex
        tokens = shlex.split(self.cli_template)
        if not tokens:
            raise RuntimeError("CLI template empty")
        cli_bin = tokens[0]

        with tempfile.NamedTemporaryFile(delete=False) as tmp_out:
            out_path = tmp_out.name

        # Build command
        cmd = (
            f"{cli_bin} --chainId {self.cli_chain_id} "
            f"--rpcAddr {self._normalize_rpc(self.rpc_url)} "
            f"--host {self.sp_host} "
            f"--passwordfile {self._cli_password_file} "
            f"object get gnfd://{self.bucket_name}/{object_name} {out_path}"
        )
        logger.info(f"Running gnfd-cmd (get): {cmd}")

        try:
            subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
                timeout=int(os.getenv("GREENFIELD_CLI_TIMEOUT", "300")),
            )
            with open(out_path, "rb") as f:
                return f.read()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"CLI download failed: {e.stdout} {e.stderr}") from e
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass

    def head_object_status_cli(self, bucket_name: str, object_name: str) -> Dict[str, Any]:
        """Call gnfd-cmd object head -f json to check sealing status."""
        if not self.cli_template:
            raise RuntimeError("CLI template not set for head")
        self._ensure_cli_account()

        cmd = (
            f"{self._cli_bin} --chainId {self.cli_chain_id} "
            f"--rpcAddr {self._normalize_rpc(self.rpc_url)} "
            f"--host {self.sp_host} "
            f"object head -f json gnfd://{bucket_name}/{object_name}"
        )

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            timeout=int(os.getenv("GREENFIELD_CLI_TIMEOUT", "300")),
        )
        output = (result.stdout or "") + (result.stderr or "")
        match = re.search(r"{.*}", output, flags=re.S)
        if not match:
            raise RuntimeError(f"Unable to parse head output: {output}")
        return json.loads(match.group(0))


class GreenfieldAutoUploader:
    """Enhanced Greenfield storage that automatically creates objects before uploading."""

    def __init__(
        self,
        rpc_url: str,
        sp_host: str,
        bucket_name: str,
        private_key: str,
        chain_id: Any = 5600,
        content_type: str = "application/octet-stream",
        timeout: int = 30,
        cli_chain_id: Optional[str] = None,
    ):
        """Initialize auto-uploader with CreateObject capability.

        Args:
            rpc_url: Greenfield RPC endpoint
            sp_host: Storage Provider host
            bucket_name: Bucket name for objects
            private_key: Private key for signing
            chain_id: Greenfield chain ID
            content_type: Default content type for objects
            timeout: Request timeout for storage operations
        """
        self.sp_host = sp_host
        self.bucket_name = bucket_name
        self.content_type = content_type
        self.timeout = timeout

        # Initialize CreateObject helper
        self.object_helper = GreenfieldCreateObjectHelper(
            rpc_url=rpc_url,
            sp_host=sp_host,
            bucket_name=bucket_name,
            private_key=private_key,
            chain_id=chain_id,
            cli_chain_id=cli_chain_id,
            cli_template=os.getenv("GREENFIELD_CREATE_OBJECT_CMD_TEMPLATE"),
        )

        # Initialize account for signing PutObject requests
        if private_key.startswith("0x"):
            private_key = private_key[2:]
        self.account = Account.from_key(private_key)

        # Prepare eth_keys PrivateKey for raw secp256k1 signing
        from eth_keys import keys
        self._priv_key = keys.PrivateKey(bytes.fromhex(private_key))

        # Initialize HTTP session
        self.session = aiohttp.ClientSession()

        logger.info(
            f"Initialized Greenfield auto-uploader: "
            f"bucket={bucket_name}, sp_host={sp_host}, "
            f"address={self.account.address}"
        )

    async def put_auto(
        self,
        key: str,
        data: bytes,
        gas_price_gwei: Optional[int] = None,
    ) -> str:
        """Upload data with automatic CreateObject generation.

        This is the enhanced version that doesn't require pre-created
        transaction hashes. It automatically:
        1. Calls CreateObject on-chain
        2. Uses the returned txn_hash for PutObject
        3. Returns the object key for retrieval

        Args:
            key: Object key/name
            data: Binary data to upload
            gas_price_gwei: Optional gas price in Gwei

        Returns:
            Object key that can be used for retrieval

        Raises:
            RuntimeError: If any step fails
        """
        logger.info(f"Auto-upload: key={key}, size={len(data)} bytes")

        # Step 1: Create object on-chain
        object_name = key.strip() if key else self._gen_key()

        try:
            txn_hash = await self.object_helper.create_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                object_size=len(data),
                content_type=self.content_type,
                gas_price_gwei=gas_price_gwei,
                data=data,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create object on-chain: {e}") from e

        # Step 2: Upload data to Storage Provider
        if self.object_helper.cli_template:
            logger.info(f"Upload already performed via gnfd-cmd for {object_name}")
            return object_name

        try:
            object_key = await self._upload_to_storage_provider(
                object_name=object_name,
                data=data,
                txn_hash=txn_hash,
            )
            logger.info(f"Auto-upload complete: {object_key}")
            return object_key
        except Exception as e:
            raise RuntimeError(f"Failed to upload to storage provider: {e}") from e

    async def _upload_to_storage_provider(
        self,
        object_name: str,
        data: bytes,
        txn_hash: str,
    ) -> str:
        """Upload data to Storage Provider using given transaction hash."""
        from datetime import datetime, timezone, timedelta
        from urllib.parse import quote

        # Build URL (virtual-hosted-style)
        url = f"https://{self.bucket_name}.{self.sp_host}/{quote(object_name, safe='/')}"

        # Prepare expiry timestamp (24 hours from now)
        expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        expiry_str = expiry.isoformat().replace("+00:00", "Z")

        # Prepare headers
        headers = {
            "Content-Type": self.content_type,
            "Content-Length": str(len(data)),
            "X-Gnfd-Txn-Hash": txn_hash,
            "X-Gnfd-Expiry-Timestamp": expiry_str,
        }

        # Build authorization (reuse from existing GreenfieldReputationStorage)
        auth_header = await self._build_authorization(
            method="PUT",
            path=f"/{object_name}",
            headers=headers,
            body=data,
        )
        headers["Authorization"] = auth_header

        # Upload data
        try:
            async with self.session.put(url, headers=headers, data=data, timeout=self.timeout) as resp:
                resp.raise_for_status()

                etag = resp.headers.get("ETag", "")
                request_id = resp.headers.get("X-Gnfd-Request-ID", "")

                logger.info(
                    f"Upload successful: key={object_name}, "
                    f"etag={etag}, request_id={request_id}"
                )

                return object_name

        except aiohttp.ClientError as e:
            error_msg = f"Failed to upload to Greenfield: {e}"
            if hasattr(e, "status") and e.status:
                error_msg += f" (HTTP {e.status})"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def _build_authorization(
        self,
        method: str,
        path: str,
        headers: dict,
        body: Optional[bytes] = None,
    ) -> str:
        """Build GNFD1-ECDSA authorization header."""
        from eth_utils import keccak

        # Build canonical request
        canonical_request = self._build_canonical_request(
            method=method,
            path=path,
            query_string="",
            headers=headers,
            body=body,
        )

        # Sign the hash
        canonical_hash = keccak(canonical_request.encode("utf-8"))
        signature_hex = self._priv_key.sign_msg_hash(canonical_hash).to_hex()
        if signature_hex.startswith("0x"):
            signature_hex = signature_hex[2:]

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
        """Build canonical request string for signing."""
        from urllib.parse import quote

        # HTTP Method
        http_method = method.upper()

        # Canonical URI
        canonical_uri = quote(path, safe="/") if path else "/"

        # Canonical Query String
        canonical_query_string = query_string

        # Canonical Headers
        canonical_headers_dict = {
            "host": f"{self.bucket_name}.{self.sp_host}",
        }

        # Add x-gnfd-* headers
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower.startswith("x-gnfd-"):
                canonical_headers_dict[key_lower] = str(value).strip()

        # Sort and format
        canonical_headers_list = sorted(canonical_headers_dict.items())
        canonical_headers = "\n".join(f"{k}:{v}" for k, v in canonical_headers_list) + "\n"

        # Signed Headers
        signed_headers = ";".join(sorted(canonical_headers_dict.keys()))

        # Combine all parts
        canonical_request = "\n".join([
            http_method,
            canonical_uri,
            canonical_query_string,
            canonical_headers,
            signed_headers,
        ])

        return canonical_request

    def _gen_key(self) -> str:
        """Generate a unique object key using UUID."""
        import uuid
        return uuid.uuid4().hex

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def wait_until_ready(self, object_name: str, timeout: int = 420, interval: int = 10) -> None:
        """Poll until object is sealed and downloadable."""
        deadline = time.time() + timeout
        last_err: Optional[Exception] = None
        while time.time() < deadline:
            try:
                # Prefer gnfd-cmd head (gives sealing status)
                if self.object_helper.cli_template:
                    status = await asyncio.to_thread(
                        self.object_helper.head_object_status_cli,
                        self.bucket_name,
                        object_name,
                    )
                    object_status = (status or {}).get("object_status", "")
                    if "SEALED" in object_status:
                        return
                    last_err = RuntimeError(f"status={object_status}")
                else:
                    await self._head_object(object_name)
                    return
            except Exception as exc:  # noqa: PERF203 - small loop count
                last_err = exc
            await asyncio.sleep(interval)
        raise RuntimeError(f"Object {object_name} not ready after {timeout}s: {last_err}")

    async def _head_object(self, object_name: str) -> None:
        """HEAD object using SP API with signed headers."""
        from datetime import datetime, timezone, timedelta

        url = f"https://{self.bucket_name}.{self.sp_host}/{quote(object_name, safe='/')}"
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        expiry_str = expiry.isoformat().replace("+00:00", "Z")
        headers = {
            "X-Gnfd-Expiry-Timestamp": expiry_str,
            "X-Gnfd-User-Address": self.account.address,
        }
        auth_header = await self._build_authorization(
            method="HEAD",
            path=f"/{object_name}",
            headers=headers,
            body=None,
        )
        headers["Authorization"] = auth_header

        async with self.session.head(url, headers=headers, timeout=self.timeout) as resp:
            resp.raise_for_status()


# Utility functions for E2E testing

async def create_e2e_helper(config: Dict[str, Any]) -> GreenfieldAutoUploader:
    """Create an E2E helper from configuration.

    Args:
        config: Configuration dictionary with required fields

    Returns:
        Configured GreenfieldAutoUploader instance

    Raises:
        ValueError: If required configuration is missing
    """
    required_fields = ["rpc_url", "sp_host", "bucket_name", "private_key"]

    for field in required_fields:
        if not config.get(field):
            raise ValueError(f"Missing required field: {field}")

    return GreenfieldAutoUploader(
        rpc_url=config["rpc_url"],
        sp_host=config["sp_host"],
        bucket_name=config["bucket_name"],
        private_key=config["private_key"],
        chain_id=config.get("chain_id", 5600),
        cli_chain_id=config.get("cli_chain_id"),
        content_type=config.get("content_type", "application/octet-stream"),
        timeout=config.get("timeout", 30),
    )


# E2E test data
TEST_DATA_EXAMPLES = {
    "small_text": b"Hello, Greenfield! This is a test message.",
    "json_data": json.dumps({
        "agent_id": "test-agent-123",
        "reputation": {
            "score": 95,
            "reviews": [
                {"rating": 5, "comment": "Excellent work"},
                {"rating": 4, "comment": "Good performance"}
            ],
            "created_at": "2024-11-28T14:30:00Z"
        }
    }).encode('utf-8'),
    "binary_data": bytes([i % 256 for i in range(256)]),  # All possible byte values
    "large_data": b"X" * (100 * 1024),  # 100KB
}

"""
基于 gnfd-cmd 的 BNB Greenfield ReputationStorage 实现，仅使用 CLI。
"""

import json
import logging
import os
import platform
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from .storage_interfaces import ReputationStorage

logger = logging.getLogger(__name__)


def _default_greenfield_cli_template() -> Optional[str]:
    """提供一个默认的 gnfd-cmd 模板，未配置时使用。"""
    repo_root = Path(__file__).resolve().parents[3]
    bin_name = "gnfd-cmd_mac" if platform.system().lower() == "darwin" else "gnfd-cmd"
    cli_path = repo_root / "bin" / bin_name
    if not cli_path.exists():
        return None
    return f"{cli_path} object put --contentType {{content_type}} {{file}} gnfd://{{bucket}}/{{object}}"


class GreenfieldReputationStorage(ReputationStorage):
    """仅通过 gnfd-cmd 进行 Greenfield 存取的实现。"""

    def __init__(
        self,
        sp_host: str,
        bucket: str,
        private_key: str,
        txn_hash: Optional[str] = None,  # 保留兼容参数但不再使用
        content_type: str = "application/octet-stream",
        timeout: int = 30,
        create_object_helper: Optional[Any] = None,
    ):
        """初始化，仅支持 CLI 上传/下载。"""
        if not sp_host:
            raise ValueError("sp_host is required")
        if not bucket:
            raise ValueError("bucket is required")
        if not private_key:
            raise ValueError("private_key is required")

        self.sp_host = sp_host.strip()
        self.bucket = bucket.strip()
        self.content_type = content_type
        self.timeout = timeout
        self._create_object_helper = create_object_helper or self._init_cli_helper(
            sp_host=sp_host,
            bucket=bucket,
            private_key=private_key,
        )

        if txn_hash:
            logger.warning("CLI-only 模式忽略 txn_hash（仅保留兼容参数）")

        logger.info("Initialized Greenfield CLI-only storage: bucket=%s, sp_host=%s", bucket, sp_host)

    def put(self, key: str, data: bytes, txn_hash: Optional[str] = None) -> str:
        """仅通过 gnfd-cmd 上传并返回对象 key。"""
        object_key = key.strip() if key else self._gen_key()

        if txn_hash:
            logger.warning("CLI-only 模式忽略 txn_hash 参数")

        txn_created = self._create_object_helper.upload_via_cli(
            object_name=object_key,
            data=data,
            content_type=self.content_type,
        )
        logger.info("Uploaded to Greenfield via CLI: key=%s, txn_hash=%s", object_key, txn_created)
        return object_key

    def get(self, key: str) -> bytes:
        """优先通过公开 HTTP 下载，若不可用再走 CLI，必要时等待封存后重试。"""
        retry_seconds = int(os.getenv("GREENFIELD_GET_RETRY_SECONDS", "300"))
        retry_interval = int(os.getenv("GREENFIELD_GET_RETRY_INTERVAL", "5"))
        deadline = time.time() + retry_seconds
        last_err: Optional[Exception] = None

        while True:
            try:
                data = self._http_download(key)
                if data:
                    return data
                last_err = RuntimeError("empty content via HTTP (likely not sealed yet)")
                logger.info("HTTP download empty for %s, will retry after waiting seal", key)
            except Exception as exc_http:
                last_err = exc_http

            try:
                data = self._create_object_helper.download_via_cli(object_name=key)
                if data:
                    return data
                last_err = RuntimeError("empty content (likely not sealed yet)")
                logger.info("Download empty for %s, will retry after waiting seal", key)
            except Exception as exc_cli:
                last_err = exc_cli

            if time.time() >= deadline:
                raise RuntimeError(f"Failed to download {key}: {last_err}") from last_err

            try:
                status = self._create_object_helper.head_object_status_cli(self.bucket, key)
                object_status = (status or {}).get("object_status", "")
                if "SEALED" in object_status:
                    logger.info("Object %s sealed, retrying download", key)
            except Exception:
                pass

            time.sleep(retry_interval)

    def _gen_key(self) -> str:
        return uuid.uuid4().hex

    def put_json(self, key: str, data: Dict[str, Any], txn_hash: Optional[str] = None) -> str:
        """Store JSON data on Greenfield and return object key.

        Args:
            key: Object key/name (if empty, auto-generates UUID-based key)
            data: Dictionary to store as JSON
            txn_hash: Optional transaction hash from CreateObject operation

        Returns:
            Object key (name) that can be used to retrieve the data
        """
        json_bytes = json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
        return self.put(key=key, data=json_bytes, txn_hash=txn_hash)

    def get_json(self, key: str) -> Dict[str, Any]:
        """Retrieve JSON data from Greenfield by object key.

        Args:
            key: Object key (name) to retrieve

        Returns:
            Dictionary parsed from JSON

        Raises:
            RuntimeError: If retrieval or parsing fails
        """
        try:
            data_bytes = self.get(key)
            return json.loads(data_bytes.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON from Greenfield (key: {key}): {e}") from e

    def build_uri(self, key: str) -> str:
        """Build Greenfield URI for the stored data.

        Args:
            key: Object key (name) in Greenfield

        Returns:
            HTTPS URI in the format "https://bucket.sp_host/key"
        """
        # Use virtual-hosted-style URL (bucket subdomain)
        return f"https://{self.bucket}.{self.sp_host}/{quote(key, safe='/')}"

    def _http_download(self, key: str) -> bytes:
        url = f"https://{self.sp_host}/view/{self.bucket}/{quote(key, safe='/')}"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.content

    def _init_cli_helper(self, sp_host: str, bucket: str, private_key: str):
        """初始化 CLI helper，支持默认模板与环境覆盖。"""
        cli_template = os.getenv("GREENFIELD_CREATE_OBJECT_CMD_TEMPLATE") or _default_greenfield_cli_template()
        if not cli_template:
            raise ValueError("GREENFIELD_CREATE_OBJECT_CMD_TEMPLATE 未配置且默认模板不可用")

        # Linux 环境自动替换 mac 版本
        if "gnfd-cmd_mac" in cli_template and platform.system().lower() == "linux":
            adjusted = cli_template.replace("gnfd-cmd_mac", "gnfd-cmd")
            if os.path.exists(adjusted.split()[0]):
                logger.info("Adjusted Greenfield CLI template for Linux: %s", adjusted)
                cli_template = adjusted
            else:
                raise ValueError(f"gnfd-cmd not found for Linux runtime: {cli_template}")

        rpc_url = os.getenv("GREENFIELD_RPC_URL") or "https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org:443"
        chain_id_val = os.getenv("GREENFIELD_CHAIN_ID") or 5600
        try:
            chain_id = int(chain_id_val)
        except Exception:
            chain_id = 5600
        cli_chain_id = os.getenv("GREENFIELD_CLI_CHAIN_ID")

        from .greenfield_cli import GreenfieldCreateObjectHelper

        return GreenfieldCreateObjectHelper(
            rpc_url=rpc_url,
            sp_host=sp_host,
            bucket_name=bucket,
            private_key=private_key,
            chain_id=chain_id,
            cli_chain_id=cli_chain_id,
            cli_template=cli_template,
        )

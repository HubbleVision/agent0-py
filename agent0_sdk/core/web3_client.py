"""
Web3 integration layer for smart contract interactions.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from web3 import Web3
    from web3.contract import Contract
    from eth_account import Account
    from eth_account.signers.base import BaseAccount
except ImportError:
    raise ImportError(
        "Web3 dependencies not installed. Install with: pip install web3 eth-account"
    )

# Optional PoA middleware (name differs across Web3 versions)
try:
    from web3.middleware import geth_poa_middleware  # Web3 v6
except Exception:  # pragma: no cover - compatibility import
    geth_poa_middleware = None

try:
    from web3.middleware import ExtraDataToPOAMiddleware  # Web3 v7+
except Exception:  # pragma: no cover - compatibility import
    ExtraDataToPOAMiddleware = None


class Web3Client:
    """Web3 client for interacting with ERC-8004 smart contracts."""

    def __init__(
        self,
        rpc_url: str,
        private_key: Optional[str] = None,
        account: Optional[BaseAccount] = None,
    ):
        """Initialize Web3 client."""
        self.rpc_url = rpc_url
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        # BSC/other PoA chains require extraData len workaround
        try:
            if geth_poa_middleware:
                self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            elif 'ExtraDataToPOAMiddleware' in globals() and ExtraDataToPOAMiddleware:
                self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        except ValueError:
            # Already injected or not supported; safe to ignore
            pass

        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum node")
        
        if account:
            self.account = account
        elif private_key:
            self.account = Account.from_key(private_key)
        else:
            # Read-only mode - no account
            self.account = None
        
        self.chain_id = self.w3.eth.chain_id

    def get_contract(self, address: str, abi: List[Dict[str, Any]]) -> Contract:
        """Get contract instance."""
        return self.w3.eth.contract(address=address, abi=abi)

    def call_contract(
        self,
        contract: Contract,
        method_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Call a contract method (view/pure)."""
        method = getattr(contract.functions, method_name)
        return method(*args, **kwargs).call()

    def transact_contract(
        self,
        contract: Contract,
        method_name: str,
        *args,
        gas_limit: Optional[int] = None,
        gas_price: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
        **kwargs
    ) -> str:
        """Execute a contract transaction."""
        if not self.account:
            raise ValueError("Cannot execute transaction: SDK is in read-only mode. Provide a signer to enable write operations.")
        
        method = getattr(contract.functions, method_name)
        
        # Build transaction with proper nonce management
        # Use 'pending' to get the next nonce including pending transactions
        nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
        tx = method(*args, **kwargs).build_transaction({
            'from': self.account.address,
            'nonce': nonce,
        })
        
        # Add gas settings
        if gas_limit:
            tx['gas'] = gas_limit
        if gas_price:
            tx['gasPrice'] = gas_price
        if max_fee_per_gas:
            tx['maxFeePerGas'] = max_fee_per_gas
        if max_priority_fee_per_gas:
            tx['maxPriorityFeePerGas'] = max_priority_fee_per_gas
        
        # Sign and send
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction)
        
        return tx_hash.hex()

    def wait_for_transaction(self, tx_hash: str, timeout: int = 60) -> Dict[str, Any]:
        """Wait for transaction to be mined."""
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

    def get_events(
        self,
        contract: Contract,
        event_name: str,
        from_block: int = 0,
        to_block: Optional[int] = None,
        argument_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get contract events."""
        if to_block is None:
            to_block = self.w3.eth.block_number
        
        event_filter = contract.events[event_name].create_filter(
            fromBlock=from_block,
            toBlock=to_block,
            argument_filters=argument_filters or {}
        )
        
        return event_filter.get_all_entries()

    def encodeFeedbackAuth(
        self,
        agentId: int,
        clientAddress: str,
        indexLimit: int,
        expiry: int,
        chainId: int,
        identityRegistry: str,
        signerAddress: str
    ) -> bytes:
        """Encode feedback authorization data."""
        return self.w3.codec.encode(
            ['uint256', 'address', 'uint64', 'uint256', 'uint256', 'address', 'address'],
            [agentId, clientAddress, indexLimit, expiry, chainId, identityRegistry, signerAddress]
        )

    def signMessage(self, message: bytes) -> bytes:
        """Sign a message with the account's private key."""
        # Create a SignableMessage from the raw bytes
        from eth_account.messages import encode_defunct
        signableMessage = encode_defunct(message)
        signedMessage = self.account.sign_message(signableMessage)
        return signedMessage.signature

    def recoverAddress(self, message: bytes, signature: bytes) -> str:
        """Recover address from message and signature."""
        from eth_account.messages import encode_defunct
        signable_message = encode_defunct(message)
        return self.w3.eth.account.recover_message(signable_message, signature=signature)

    def keccak256(self, data: bytes) -> bytes:
        """Compute Keccak-256 hash."""
        return self.w3.keccak(data)

    def to_checksum_address(self, address: str) -> str:
        """Convert address to checksum format."""
        return self.w3.to_checksum_address(address)
    
    def normalize_address(self, address: str) -> str:
        """Normalize address to lowercase for consistent storage and comparison.
        
        Ethereum addresses are case-insensitive but EIP-55 checksum addresses
        use mixed case. For storage and comparison purposes, we normalize to
        lowercase to avoid case-sensitivity issues.
        
        Args:
            address: Ethereum address (with or without checksum)
            
        Returns:
            Address in lowercase format
        """
        # Remove 0x prefix if present, convert to lowercase, re-add prefix
        if address.startswith("0x") or address.startswith("0X"):
            return "0x" + address[2:].lower()
        return address.lower()

    def is_address(self, address: str) -> bool:
        """Check if string is a valid Ethereum address."""
        return self.w3.is_address(address)

    def get_balance(self, address: str) -> int:
        """Get ETH balance of an address."""
        return self.w3.eth.get_balance(address)

    def get_transaction_count(self, address: str) -> int:
        """Get transaction count (nonce) of an address."""
        return self.w3.eth.get_transaction_count(address)

"""
End-to-End Greenfield E2E Test

This test demonstrates the complete Greenfield workflow:
1. CreateObject on-chain (automatically via helper)
2. PutObject upload to storage provider
3. GetObject download verification
4. Cross-key retrieval to verify public access

To run this test:
1. Set environment variables (see GREENFIELD_E2E_GUIDE.md or GREENFIELD_E2E_使用指南.md)
2. Run: pytest tests/test_greenfield_e2e.py -v -m integration -s

Environment variables required:
- GREENFIELD_RPC_URL (default: https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org)
- GREENFIELD_SP_HOST (default: gnfd-testnet-sp1.bnbchain.org)
- GREENFIELD_BUCKET
- GREENFIELD_PRIVATE_KEY
- Optional: GREENFIELD_CHAIN_ID (default: 5600 for testnet)

For Chinese documentation, see GREENFIELD_E2E_使用指南.md
For English documentation, see GREENFIELD_E2E_GUIDE.md
"""
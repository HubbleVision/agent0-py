# BNB Chain Deployment Guide

## Prerequisites Checklist

- [ ] Node.js 18.x or 20.x LTS installed (not 22.x+)
- [ ] Private key with BNB for gas fees
  - Testnet: Get free BNB from [BNB Testnet Faucet](https://testnet.bnbchain.org/faucet-smart)
  - Mainnet: Ensure sufficient BNB balance
- [ ] (Optional) Etherscan API key for contract verification (v2 API supports all chains including BNB)
- [ ] Environment variables configured in `.env`

## Step-by-Step Deployment

### 1. Environment Setup

```bash
# Install dependencies
npm install

# Copy and configure .env
cp .env.example .env
# Edit .env and fill in DEPLOYER_KEY
```

### 2. Compile Contracts

```bash
npx hardhat compile
```

Expected output: Compilation successful, artifacts generated.

### 3. Deploy to BNB Testnet

```bash
npx hardhat run scripts/deploy.js --network bnbTestnet
```

**Important**: Save the output! It contains:
- Proxy addresses (these are the permanent addresses)
- Implementation addresses
- Environment variables to add to `.env`
- Verification commands

### 4. Update Environment Variables

Add the deployed addresses to your `.env`:

```bash
BNB_TESTNET_IDENTITY=0x...     # From deployment output
BNB_TESTNET_REPUTATION=0x...   # From deployment output
BNB_TESTNET_VALIDATION=0x...   # From deployment output
```

### 5. Verify Contracts (Optional)

```bash
# Automatic verification
npx hardhat run scripts/verify.js --network bnbTestnet

# Or manual verification using commands from deployment output
```

### 6. Verify Contracts (Optional but Recommended)

```bash
# Configure ETHERSCAN_API_KEY in .env
# Get your key from: https://etherscan.io/myapikey
# Etherscan v2 API works for all chains including BNB
npx hardhat run scripts/verify.js --network bnbTestnet
```

### 7. Test Deployment

Use the test script or interact manually:

```bash
# Example: Check Identity contract version
npx hardhat console --network bnbTestnet
> const Identity = await ethers.getContractAt("IdentityRegistryUpgradeable", "0x...")
> await Identity.getVersion()
'1.0.0'
```

## Mainnet Deployment

⚠️ **Only deploy to mainnet after thorough testnet testing!**

```bash
# Deploy
npx hardhat run scripts/deploy.js --network bnbMainnet

# Verify
npx hardhat run scripts/verify.js --network bnbMainnet

# Update .env with mainnet addresses
BNB_MAINNET_IDENTITY=0x...
BNB_MAINNET_REPUTATION=0x...
BNB_MAINNET_VALIDATION=0x...
```

## Post-Deployment Checklist

- [ ] Proxy addresses saved to `.env`
- [ ] Deployment info saved to `deployments/bnbTestnet.json`
- [ ] Contracts verified on BscScan
- [ ] Test registration transaction successful
- [ ] Document addresses in main SDK README
- [ ] Update SDK `contracts.py` with deployed addresses

## Troubleshooting

### Node.js Version Issues

If you see "Node.js X.X.X is not supported by Hardhat":

```bash
# Install nvm (if not already installed)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Install and use Node.js 20 LTS
nvm install 20
nvm use 20

# Verify version
node --version  # Should be v20.x.x
```

### Gas Price Too High

If deployment fails due to high gas:

1. Check current gas price: https://bscscan.com/gastracker
2. Wait for lower gas period
3. Or increase gas limit in `hardhat.config.js`

### Deployment Fails Mid-Way

If deployment fails after deploying some contracts:

1. Check `deployments/bnbTestnet.json` for already deployed addresses
2. Use those addresses in subsequent deploys to avoid duplicates
3. Or start fresh with a new deployer account

### Verification Fails

Common issues:
- **"Already verified"**: Contract already verified, ignore error
- **"Contract source code not found"**: Wait 1-2 minutes for propagation
- **"Compiler version mismatch"**: Ensure Solidity 0.8.20 in config
- **"Constructor arguments mismatch"**: Proxy contracts have no constructor args

Try manual verification on BscScan UI if automatic fails.

## Emergency Procedures

### Contract Pause/Upgrade

If critical bug found:

1. **Immediate**: Notify all users to stop using contracts
2. **Prepare**: Fix bug in new implementation
3. **Test**: Deploy new implementation to testnet first
4. **Upgrade**: Use `scripts/upgrade.js` with proxy addresses
5. **Verify**: Test upgraded contract thoroughly

### Owner Key Compromise

If deployer private key is compromised:

1. **Immediately** transfer ownership to new secure address
2. Revoke any approvals/operators if applicable
3. Monitor all contracts for suspicious activity
4. Consider upgrading to new implementation with additional security

## Gas Estimates

Typical deployment costs on BNB Testnet (may vary):

- Identity Registry: ~0.05 BNB
- Reputation Registry: ~0.08 BNB
- Validation Registry: ~0.04 BNB
- **Total**: ~0.17 BNB

Mainnet costs are similar but check current gas prices.

## Next Steps

After successful deployment:

1. Update SDK configuration (`agent0_sdk/core/contracts.py`)
2. Run SDK integration tests against deployed contracts
3. Update documentation with contract addresses
4. Create first test agent registration
5. Test feedback and validation flows

## Support

- BNB Chain Docs: https://docs.bnbchain.org/
- Hardhat Docs: https://hardhat.org/docs
- OpenZeppelin Upgrades: https://docs.openzeppelin.com/upgrades-plugins/
- BscScan: https://testnet.bscscan.com (testnet) / https://bscscan.com (mainnet)

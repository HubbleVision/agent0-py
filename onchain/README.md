# ERC-8004 Smart Contracts - BNB Chain Deployment

This directory contains Hardhat project for deploying ERC-8004 Agent Registry contracts to BNB Chain (testnet and mainnet).

## Contract Overview

Three upgradeable contracts (UUPS pattern):

1. **IdentityRegistryUpgradeable** - Agent identity and metadata management (ERC-721)
2. **ReputationRegistryUpgradeable** - Feedback and reputation system
3. **ValidationRegistryUpgradeable** - Validation request/response system

All contracts are based on verified Base Sepolia implementations in `reference/base-sepolia/`.

## Prerequisites

- Node.js 18+
- npm or yarn
- Private key with BNB for gas (testnet: use [BNB Testnet Faucet](https://testnet.bnbchain.org/faucet-smart))
- (Optional) Etherscan API key for contract verification (works for all chains including BNB)

## Installation

```bash
npm install
```

## Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Fill in required environment variables:
```bash
# Required for deployment
DEPLOYER_KEY=your_private_key_here

# Optional: Custom RPC URLs
BNB_TESTNET_RPC=https://data-seed-prebsc-1-s1.bnbchain.org:8545
BNB_MAINNET_RPC=https://bsc-dataseed.binance.org/

# Optional: For contract verification (Etherscan v2 API supports all chains)
# Get your API key from: https://etherscan.io/myapikey
ETHERSCAN_API_KEY=your_etherscan_api_key
```

## Deployment

### BNB Testnet (Chain ID: 97)

```bash
npx hardhat run scripts/deploy.js --network bnbTestnet
```

### BNB Mainnet (Chain ID: 56)

```bash
npx hardhat run scripts/deploy.js --network bnbMainnet
```

The deployment script will:
- Deploy all three contracts with UUPS proxies
- Initialize each contract
- Save deployment info to `deployments/<network>.json`
- Print contract addresses for `.env` file
- Provide verification commands

## Contract Verification

### Automatic Verification

After deployment, run:

```bash
npx hardhat run scripts/verify.js --network bnbTestnet
```

### Manual Verification

Use the commands printed by deployment script:

```bash
npx hardhat verify --network bnbTestnet <PROXY_ADDRESS>
npx hardhat verify --network bnbTestnet <IMPLEMENTATION_ADDRESS>
```

## Upgrading Contracts

1. Update contract code in `contracts/Agent8004Bundle.sol`

2. Set proxy addresses in environment:
```bash
export PROXY_IDENTITY=0x...
export PROXY_REPUTATION=0x...
export PROXY_VALIDATION=0x...
```

3. Run upgrade script:
```bash
npx hardhat run scripts/upgrade.js --network bnbTestnet
```

**Important**: Only the contract owner (deployer) can upgrade contracts.

## Compile Contracts

```bash
npx hardhat compile
```

## Run Tests (Future)

```bash
npx hardhat test
```

## Network Info

### BNB Testnet (Chapel)
- Chain ID: 97
- RPC: https://data-seed-prebsc-1-s1.bnbchain.org:8545
- Explorer: https://testnet.bscscan.com
- Faucet: https://testnet.bnbchain.org/faucet-smart

### BNB Mainnet
- Chain ID: 56
- RPC: https://bsc-dataseed.binance.org/
- Explorer: https://bscscan.com

## Directory Structure

```
onchain/
├── contracts/
│   └── Agent8004Bundle.sol      # All three contracts in one file
├── scripts/
│   ├── deploy.js                # Deployment script
│   ├── upgrade.js               # Upgrade script
│   └── verify.js                # Verification script
├── deployments/                 # Deployment info (auto-generated)
│   ├── bnbTestnet.json
│   └── bnbMainnet.json
├── reference/
│   └── base-sepolia/            # Reference contracts from Base Sepolia
├── hardhat.config.js            # Hardhat configuration
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

## Troubleshooting

### Gas Price Issues

If deployment fails due to gas price, you can:

1. Wait for lower gas prices
2. Increase gas multiplier in `hardhat.config.js`
3. Manually set gas price in deployment script

### Verification Fails

Common reasons:
- Contract not fully propagated to BscScan (wait 1-2 minutes)
- Wrong constructor arguments
- Compiler version mismatch
- Source code mismatch

Try manual verification on BscScan UI if automatic fails.

### Proxy Admin Issues

The deployer address is the initial owner and can:
- Upgrade contracts
- Transfer ownership

To check current owner:
```bash
npx hardhat console --network bnbTestnet
> const contract = await ethers.getContractAt("IdentityRegistryUpgradeable", "0x...")
> await contract.owner()
```

## Security Notes

1. **Storage Layout**: Never reorder, remove, or change types of existing state variables when upgrading
2. **Initializers**: Never modify `initialize()` function signature after deployment
3. **Owner Key**: Keep deployer private key secure - it controls all upgrades
4. **Testing**: Always test upgrades on testnet before mainnet

## References

- [OpenZeppelin Upgrades](https://docs.openzeppelin.com/upgrades-plugins/1.x/)
- [Hardhat Documentation](https://hardhat.org/docs)
- [BNB Chain Docs](https://docs.bnbchain.org/)
- Base Sepolia Verified Contracts: `reference/base-sepolia/README.md`

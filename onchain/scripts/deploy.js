/**
 * Deploy ERC-8004 contracts (Identity, Reputation, Validation) with UUPS proxy pattern
 *
 * Usage:
 *   npx hardhat run scripts/deploy.js --network bnbTestnet
 *   npx hardhat run scripts/deploy.js --network bnbMainnet
 */

const { ethers, upgrades } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await ethers.getSigners();

  console.log("=========================================");
  console.log("Deploying ERC-8004 Contracts");
  console.log("=========================================");
  console.log("Network:", network.name);
  console.log("Chain ID:", (await ethers.provider.getNetwork()).chainId);
  console.log("Deployer address:", deployer.address);
  console.log("Deployer balance:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)), "ETH");
  console.log("=========================================\n");

  // Deploy Identity Registry (UUPS)
  console.log("📝 Deploying IdentityRegistryUpgradeable...");
  const IdentityFactory = await ethers.getContractFactory("IdentityRegistryUpgradeable");
  const identity = await upgrades.deployProxy(
    IdentityFactory,
    [],
    {
      initializer: "initialize",
      kind: "uups"
    }
  );
  await identity.waitForDeployment();
  const identityAddress = await identity.getAddress();
  console.log("✅ IdentityRegistryUpgradeable deployed to:", identityAddress);

  // Get implementation address
  const identityImplAddress = await upgrades.erc1967.getImplementationAddress(identityAddress);
  console.log("   Implementation address:", identityImplAddress);
  console.log("   Version:", await identity.getVersion());
  console.log("");

  // Deploy Reputation Registry (UUPS, init with identity)
  console.log("📝 Deploying ReputationRegistryUpgradeable...");
  const ReputationFactory = await ethers.getContractFactory("ReputationRegistryUpgradeable");
  const reputation = await upgrades.deployProxy(
    ReputationFactory,
    [identityAddress],
    {
      initializer: "initialize",
      kind: "uups"
    }
  );
  await reputation.waitForDeployment();
  const reputationAddress = await reputation.getAddress();
  console.log("✅ ReputationRegistryUpgradeable deployed to:", reputationAddress);

  const reputationImplAddress = await upgrades.erc1967.getImplementationAddress(reputationAddress);
  console.log("   Implementation address:", reputationImplAddress);
  console.log("   Version:", await reputation.getVersion());
  console.log("   Identity Registry:", await reputation.getIdentityRegistry());
  console.log("");

  // Deploy Validation Registry (UUPS, init with identity)
  console.log("📝 Deploying ValidationRegistryUpgradeable...");
  const ValidationFactory = await ethers.getContractFactory("ValidationRegistryUpgradeable");
  const validation = await upgrades.deployProxy(
    ValidationFactory,
    [identityAddress],
    {
      initializer: "initialize",
      kind: "uups"
    }
  );
  await validation.waitForDeployment();
  const validationAddress = await validation.getAddress();
  console.log("✅ ValidationRegistryUpgradeable deployed to:", validationAddress);

  const validationImplAddress = await upgrades.erc1967.getImplementationAddress(validationAddress);
  console.log("   Implementation address:", validationImplAddress);
  console.log("   Version:", await validation.getVersion());
  console.log("   Identity Registry:", await validation.getIdentityRegistry());
  console.log("");

  // Summary
  console.log("=========================================");
  console.log("📊 Deployment Summary");
  console.log("=========================================");
  console.log("Network:", network.name);
  console.log("Chain ID:", (await ethers.provider.getNetwork()).chainId);
  console.log("");
  console.log("Identity Registry Proxy:     ", identityAddress);
  console.log("Identity Registry Impl:      ", identityImplAddress);
  console.log("");
  console.log("Reputation Registry Proxy:   ", reputationAddress);
  console.log("Reputation Registry Impl:    ", reputationImplAddress);
  console.log("");
  console.log("Validation Registry Proxy:   ", validationAddress);
  console.log("Validation Registry Impl:    ", validationImplAddress);
  console.log("=========================================");

  // Save deployment info to file
  const deploymentInfo = {
    network: network.name,
    chainId: Number((await ethers.provider.getNetwork()).chainId),
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: {
      identity: {
        proxy: identityAddress,
        implementation: identityImplAddress,
      },
      reputation: {
        proxy: reputationAddress,
        implementation: reputationImplAddress,
      },
      validation: {
        proxy: validationAddress,
        implementation: validationImplAddress,
      },
    },
  };

  const deploymentFile = path.join(__dirname, `../deployments/${network.name}.json`);
  const deploymentsDir = path.join(__dirname, "../deployments");

  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }

  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
  console.log(`\n💾 Deployment info saved to: ${deploymentFile}`);

  // Print environment variables for .env file
  console.log("\n📝 Add these to your .env file:");
  console.log("=========================================");
  const prefix = network.name === "bnbTestnet" ? "BNB_TESTNET" : "BNB_MAINNET";
  console.log(`${prefix}_IDENTITY=${identityAddress}`);
  console.log(`${prefix}_REPUTATION=${reputationAddress}`);
  console.log(`${prefix}_VALIDATION=${validationAddress}`);
  console.log("=========================================\n");

  // Verification instructions
  console.log("📝 To verify contracts on BscScan:");
  console.log("=========================================");
  console.log(`npx hardhat verify --network ${network.name} ${identityAddress}`);
  console.log(`npx hardhat verify --network ${network.name} ${reputationAddress}`);
  console.log(`npx hardhat verify --network ${network.name} ${validationAddress}`);
  console.log("=========================================\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

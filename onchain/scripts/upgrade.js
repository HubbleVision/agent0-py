/**
 * Upgrade ERC-8004 contracts with new implementation
 *
 * Usage:
 *   PROXY_IDENTITY=0x... PROXY_REPUTATION=0x... PROXY_VALIDATION=0x... \
 *   npx hardhat run scripts/upgrade.js --network bnbTestnet
 */

const { ethers, upgrades } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();

  // Read proxy addresses from environment variables
  const proxyIdentity = process.env.PROXY_IDENTITY;
  const proxyReputation = process.env.PROXY_REPUTATION;
  const proxyValidation = process.env.PROXY_VALIDATION;

  if (!proxyIdentity || !proxyReputation || !proxyValidation) {
    throw new Error("Please set PROXY_IDENTITY, PROXY_REPUTATION, and PROXY_VALIDATION environment variables");
  }

  console.log("=========================================");
  console.log("Upgrading ERC-8004 Contracts");
  console.log("=========================================");
  console.log("Network:", network.name);
  console.log("Deployer:", deployer.address);
  console.log("");
  console.log("Identity Proxy:    ", proxyIdentity);
  console.log("Reputation Proxy:  ", proxyReputation);
  console.log("Validation Proxy:  ", proxyValidation);
  console.log("=========================================\n");

  // Upgrade Identity
  console.log("📝 Upgrading IdentityRegistryUpgradeable...");
  const IdentityFactory = await ethers.getContractFactory("IdentityRegistryUpgradeable");
  const identity = await upgrades.upgradeProxy(proxyIdentity, IdentityFactory, { kind: "uups" });
  await identity.waitForDeployment();
  const identityImplAddress = await upgrades.erc1967.getImplementationAddress(await identity.getAddress());
  console.log("✅ Identity upgraded to new implementation:", identityImplAddress);
  console.log("   Version:", await identity.getVersion());
  console.log("");

  // Upgrade Reputation
  console.log("📝 Upgrading ReputationRegistryUpgradeable...");
  const ReputationFactory = await ethers.getContractFactory("ReputationRegistryUpgradeable");
  const reputation = await upgrades.upgradeProxy(proxyReputation, ReputationFactory, { kind: "uups" });
  await reputation.waitForDeployment();
  const reputationImplAddress = await upgrades.erc1967.getImplementationAddress(await reputation.getAddress());
  console.log("✅ Reputation upgraded to new implementation:", reputationImplAddress);
  console.log("   Version:", await reputation.getVersion());
  console.log("");

  // Upgrade Validation
  console.log("📝 Upgrading ValidationRegistryUpgradeable...");
  const ValidationFactory = await ethers.getContractFactory("ValidationRegistryUpgradeable");
  const validation = await upgrades.upgradeProxy(proxyValidation, ValidationFactory, { kind: "uups" });
  await validation.waitForDeployment();
  const validationImplAddress = await upgrades.erc1967.getImplementationAddress(await validation.getAddress());
  console.log("✅ Validation upgraded to new implementation:", validationImplAddress);
  console.log("   Version:", await validation.getVersion());
  console.log("");

  // Summary
  console.log("=========================================");
  console.log("📊 Upgrade Summary");
  console.log("=========================================");
  console.log("Identity Implementation:    ", identityImplAddress);
  console.log("Reputation Implementation:  ", reputationImplAddress);
  console.log("Validation Implementation:  ", validationImplAddress);
  console.log("=========================================\n");

  console.log("📝 To verify new implementations on BscScan:");
  console.log("=========================================");
  console.log(`npx hardhat verify --network ${network.name} ${identityImplAddress}`);
  console.log(`npx hardhat verify --network ${network.name} ${reputationImplAddress}`);
  console.log(`npx hardhat verify --network ${network.name} ${validationImplAddress}`);
  console.log("=========================================\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

/**
 * Verify deployed contracts on BscScan
 *
 * Usage:
 *   npx hardhat run scripts/verify.js --network bnbTestnet
 *   npx hardhat run scripts/verify.js --network bnbMainnet
 */

const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("=========================================");
  console.log("Verifying Contracts on BscScan");
  console.log("=========================================");
  console.log("Network:", network.name);
  console.log("=========================================\n");

  // Load deployment info
  const deploymentFile = path.join(__dirname, `../deployments/${network.name}.json`);

  if (!fs.existsSync(deploymentFile)) {
    throw new Error(`Deployment file not found: ${deploymentFile}`);
  }

  const deployment = JSON.parse(fs.readFileSync(deploymentFile, "utf8"));

  // Verify Identity Registry Proxy
  console.log("📝 Verifying IdentityRegistryUpgradeable proxy...");
  try {
    await hre.run("verify:verify", {
      address: deployment.contracts.identity.proxy,
      constructorArguments: [],
    });
    console.log("✅ Identity proxy verified\n");
  } catch (error) {
    console.log("⚠️  Identity proxy verification failed:", error.message, "\n");
  }

  // Verify Identity Registry Implementation
  console.log("📝 Verifying IdentityRegistryUpgradeable implementation...");
  try {
    await hre.run("verify:verify", {
      address: deployment.contracts.identity.implementation,
      constructorArguments: [],
    });
    console.log("✅ Identity implementation verified\n");
  } catch (error) {
    console.log("⚠️  Identity implementation verification failed:", error.message, "\n");
  }

  // Verify Reputation Registry Proxy
  console.log("📝 Verifying ReputationRegistryUpgradeable proxy...");
  try {
    await hre.run("verify:verify", {
      address: deployment.contracts.reputation.proxy,
      constructorArguments: [],
    });
    console.log("✅ Reputation proxy verified\n");
  } catch (error) {
    console.log("⚠️  Reputation proxy verification failed:", error.message, "\n");
  }

  // Verify Reputation Registry Implementation
  console.log("📝 Verifying ReputationRegistryUpgradeable implementation...");
  try {
    await hre.run("verify:verify", {
      address: deployment.contracts.reputation.implementation,
      constructorArguments: [],
    });
    console.log("✅ Reputation implementation verified\n");
  } catch (error) {
    console.log("⚠️  Reputation implementation verification failed:", error.message, "\n");
  }

  // Verify Validation Registry Proxy
  console.log("📝 Verifying ValidationRegistryUpgradeable proxy...");
  try {
    await hre.run("verify:verify", {
      address: deployment.contracts.validation.proxy,
      constructorArguments: [],
    });
    console.log("✅ Validation proxy verified\n");
  } catch (error) {
    console.log("⚠️  Validation proxy verification failed:", error.message, "\n");
  }

  // Verify Validation Registry Implementation
  console.log("📝 Verifying ValidationRegistryUpgradeable implementation...");
  try {
    await hre.run("verify:verify", {
      address: deployment.contracts.validation.implementation,
      constructorArguments: [],
    });
    console.log("✅ Validation implementation verified\n");
  } catch (error) {
    console.log("⚠️  Validation implementation verification failed:", error.message, "\n");
  }

  console.log("=========================================");
  console.log("Verification Complete");
  console.log("=========================================\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

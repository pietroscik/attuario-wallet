import hardhat from "hardhat";

async function main() {
  const { ethers, network } = hardhat;

  console.log("🚀 Deploying AttuarioVault to Base Sepolia...");

  console.log("📡 Target network:", network.name);
  const [deployer] = await ethers.getSigners();
  console.log("🧾 Using deployer:", deployer.address);

  const Vault = await ethers.getContractFactory("AttuarioVault");
  const vault = await Vault.deploy();
  await vault.waitForDeployment();

  console.log("✅ AttuarioVault deployed at:", await vault.getAddress());
}

main().catch((err) => {
  console.error("❌ Errore:", err);
  process.exitCode = 1;
});

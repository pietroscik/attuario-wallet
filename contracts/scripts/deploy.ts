import hardhat from "hardhat";

async function main() {
  const { ethers } = hardhat;

  // Ottiene l'account del deployer dal wallet (.env -> PRIVATE_KEY)
  const [deployer] = await ethers.getSigners();
  console.log("🚀 Deploying AttuarioVault with account:", deployer.address);

  // Recupera il contratto
  const Vault = await ethers.getContractFactory("AttuarioVault");

  // Esegue il deploy on-chain
  const vault = await Vault.deploy();
  await vault.waitForDeployment();

  // Mostra indirizzo contratto
  const address = await vault.getAddress();
  console.log("✅ AttuarioVault deployed to:", address);
}

// Esegue e gestisce eventuali errori
main().catch((error) => {
  console.error("❌ Error during deployment:", error);
  process.exitCode = 1;
});

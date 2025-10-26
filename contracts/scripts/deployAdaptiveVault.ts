import hardhat from "hardhat";

async function main() {
  const { ethers } = hardhat;
  const [signer] = await ethers.getSigners();
  const initialPool = process.env.INIT_POOL ?? "unset";
  const intervalSec = Number(process.env.INIT_INTERVAL ?? 3600);

  console.log("🚀 Deploying AttuarioVaultV2_Adaptive...");
  console.log("👤 Deployer:", signer.address);
  console.log("🧩 Initial pool:", initialPool);
  console.log("⏱️  Interval (s):", intervalSec);

  const Factory = await ethers.getContractFactory("AttuarioVaultV2_Adaptive");
  const contract = await Factory.deploy(initialPool, intervalSec);
  await contract.waitForDeployment();

  const addr = await contract.getAddress();
  console.log("✅ Deployed at:", addr);
  console.log("ℹ️  Save VAULT_ADDRESS in your .env");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

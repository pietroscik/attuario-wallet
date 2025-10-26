import hardhat from "hardhat";

async function main() {
  const { ethers } = hardhat;

  const PRIVATE_KEY = process.env.PRIVATE_KEY;
  const RPC_URL = process.env.RPC_URL;

  if (!RPC_URL) {
    throw new Error("RPC_URL non impostata. Configurala prima di eseguire lo script.");
  }

  if (!PRIVATE_KEY) {
    throw new Error("PRIVATE_KEY non impostata. Aggiungila alle variabili d'ambiente o al file .env.");
  }

  const [signer] = await ethers.getSigners();
  if (!signer) {
    throw new Error("Nessun signer disponibile. Controlla la configurazione della rete.");
  }

  const address = await signer.getAddress();
  console.log("✅ Wallet address:", address);
  const balance = await ethers.provider.getBalance(address);
  console.log("💰 Balance:", ethers.formatEther(balance), "ETH");
}

main().catch((error) => {
  console.error("❌ Errore:", error);
  process.exitCode = 1;
});

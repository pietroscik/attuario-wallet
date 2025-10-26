import { AutomateSDK } from "@gelatonetwork/automate-sdk";
import { config as loadEnv } from "dotenv";
import { ethers } from "ethers";

loadEnv();

async function main() {
  const rpcUrl = process.env.RPC_URL;
  const privateKey = process.env.PRIVATE_KEY;
  const vaultAddress = process.env.VAULT_ADDRESS;
  const manualInterval = process.env.AUTOMATE_INTERVAL;

  if (!rpcUrl) {
    throw new Error("RPC_URL non impostata. Aggiungila al file .env o alle variabili d'ambiente.");
  }
  if (!privateKey) {
    throw new Error(
      "PRIVATE_KEY non impostata. Inserisci la chiave del deployer che possiede il contratto AttuarioVault."
    );
  }
  if (!vaultAddress) {
    throw new Error("VAULT_ADDRESS non impostato. Specifica l'indirizzo del contratto AttuarioVault distribuito.");
  }

  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const signer = new ethers.Wallet(privateKey, provider);

  console.log("🔐 Using operator:", await signer.getAddress());
  console.log("🏦 Target vault:", vaultAddress);

  const automate = await AutomateSDK.create(provider, signer);

  const vaultAbi = [
    "function executeStrategy() external",
    "function checker() external view returns (bool, bytes memory)",
    "function executionInterval() external view returns (uint256)"
  ];
  const vault = new ethers.Contract(vaultAddress, vaultAbi, signer);

  const execSelector = vault.interface.getFunction("executeStrategy")!.selector;
  const resolverData = vault.interface.encodeFunctionData("checker");
  const interval =
    manualInterval !== undefined && manualInterval !== ""
      ? BigInt(manualInterval)
      : await vault.executionInterval();

  console.log("⏱  Interval (seconds):", interval.toString());

  const { taskId, tx } = await automate.createTask({
    name: "AttuarioVault – Esecuzione Giornaliera",
    execAddress: vaultAddress,
    execSelector,
    resolverAddress: vaultAddress,
    resolverData,
    startTime: 0,
    interval,
    singleExec: false,
    dedicatedMsgSender: false
  });

  console.log("📝 Task creation submitted, waiting for confirmation...");
  const receipt = await tx.wait();

  console.log("✅ Gelato task creato con ID:", taskId);
  console.log("🔗 Tx hash:", receipt?.hash ?? tx.hash);
  console.log(
    "💡 Ricorda di ricaricare il saldo dell'Automate treasury su https://app.gelato.network/ per mantenere attiva l'esecuzione."
  );
}

main().catch((error) => {
  console.error("❌ Errore creazione task Gelato:", error);
  process.exitCode = 1;
});

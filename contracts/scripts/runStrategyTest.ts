import hardhat from "hardhat";

function requireEnv(value: string | undefined, name: string): string {
  if (!value) {
    throw new Error(`Variabile d'ambiente ${name} assente. Configurala prima di eseguire lo script.`);
  }
  return value;
}

function parseCapitalUnits(): bigint {
  const capitalUnitsEnv = process.env.CAPITAL_UNITS;
  if (capitalUnitsEnv) {
    return BigInt(capitalUnitsEnv);
  }

  const capital = process.env.CAPITAL || "1000";
  const decimals = Number(process.env.TOKEN_DECIMALS ?? "6");
  if (Number.isNaN(decimals) || decimals < 0) {
    throw new Error("TOKEN_DECIMALS deve essere un numero intero non negativo.");
  }

  return hardhat.ethers.parseUnits(capital, decimals);
}

function unwrapLatestExecution(latest: unknown) {
  const record = latest as Record<string, unknown>;
  const tuple = latest as unknown as [string?, bigint?, bigint?, bigint?];

  const pool = (record?.pool as string | undefined) ?? tuple?.[0] ?? "";
  const apyBps = (record?.apyBps as bigint | undefined) ?? tuple?.[1] ?? 0n;
  const capital = (record?.capital as bigint | undefined) ?? tuple?.[2] ?? 0n;
  const timestamp = (record?.timestamp as bigint | undefined) ?? tuple?.[3] ?? 0n;

  return { pool, apyBps, capital, timestamp };
}

async function main() {
  const { ethers, network } = hardhat;

  const vaultAddress = requireEnv(process.env.VAULT_ADDRESS, "VAULT_ADDRESS");
  const pool = process.env.POOL_NAME || "TEST-POOL";
  const apyBps = Number(process.env.APY_BPS ?? "1200");
  if (!Number.isInteger(apyBps) || apyBps < 0) {
    throw new Error("APY_BPS deve essere un intero positivo.");
  }
  const capital = parseCapitalUnits();

  console.log("🏁 Rete target:", network.name);
  const [signer] = await ethers.getSigners();
  console.log("👛 Signer:", signer.address);

  const vault = await ethers.getContractAt("AttuarioVault", vaultAddress);
  console.log("📄 Contratto:", vaultAddress);

  const executorAddress = process.env.EXECUTOR_ADDRESS || signer.address;
  const currentExecutor = await vault.gelatoExecutor();

  if (currentExecutor.toLowerCase() !== executorAddress.toLowerCase()) {
    console.log("🛠 Aggiornamento executor Gelato →", executorAddress);
    const tx = await vault.setGelatoExecutor(executorAddress);
    await tx.wait();
    console.log("✅ Executor aggiornato.");
  } else {
    console.log("ℹ️ Executor già impostato:", executorAddress);
  }

  let intervalOverrideApplied = false;
  if (process.env.AUTOMATE_INTERVAL) {
    const interval = Number(process.env.AUTOMATE_INTERVAL);
    if (!Number.isNaN(interval) && interval >= 3600) {
      const currentInterval = await vault.executionInterval();
      if (currentInterval.toString() !== interval.toString()) {
        console.log("⚙️ Imposto nuovo executionInterval:", interval, "secondi");
        const tx = await vault.setExecutionInterval(interval);
        await tx.wait();
        console.log("✅ executionInterval aggiornato.");
        intervalOverrideApplied = true;
      } else {
        console.log("ℹ️ executionInterval già impostato su", interval);
      }
    } else {
      console.warn("⚠️ AUTOMATE_INTERVAL ignorato: deve essere >= 3600 secondi.");
    }
  }

  let lastExecuted = await vault.lastExecuted();
  let executionInterval = await vault.executionInterval();

  const now = Math.floor(Date.now() / 1000);
  const nextAllowed = Number(lastExecuted) + Number(executionInterval);

  console.log("🕒 lastExecuted:", lastExecuted.toString());
  console.log("⏱ executionInterval:", executionInterval.toString());
  console.log("🕰 timestamp attuale:", now);
  console.log("🔜 prossimo timestamp consentito:", nextAllowed);

  if (Number(lastExecuted) !== 0 && now < nextAllowed && !intervalOverrideApplied) {
    const waitSeconds = nextAllowed - now;
    console.log(
      "⏳ Intervallo non soddisfatto. Prossima esecuzione consentita tra",
      waitSeconds,
      "secondi"
    );
  } else {
    console.log("🚀 Invio executeStrategy...");
    const execTx = await vault.executeStrategy(pool, apyBps, capital);
    const receipt = await execTx.wait();
    console.log("✅ executeStrategy confermata. Tx hash:", receipt?.hash);

    lastExecuted = await vault.lastExecuted();
    executionInterval = await vault.executionInterval();
    const updatedNextAllowed = Number(lastExecuted) + Number(executionInterval);
    console.log("🕒 lastExecuted (aggiornato):", lastExecuted.toString());
    console.log("⏱ executionInterval (aggiornato):", executionInterval.toString());
    console.log("🔜 prossimo timestamp consentito (aggiornato):", updatedNextAllowed);
  }

  const { pool: latestPool, apyBps: latestApy, capital: latestCapital, timestamp: latestTimestamp } =
    unwrapLatestExecution(await vault.latestExecution());

  console.log("📊 Ultima esecuzione registrata:");
  console.log("   • pool:", latestPool);
  console.log("   • apyBps:", latestApy.toString());
  console.log("   • capital:", latestCapital.toString());
  console.log("   • timestamp:", latestTimestamp.toString());
}

main().catch((err) => {
  console.error("❌ Errore nello script end-to-end:", err);
  process.exitCode = 1;
});

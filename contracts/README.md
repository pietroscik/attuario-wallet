# AttuarioVault Hardhat Project

This project contains the AttuarioVault smart contract together with Hardhat tooling (mocha + chai + ethers) to deploy and test it locally or on Base Sepolia.

To learn more about Hardhat, please visit the [Getting Started guide](https://hardhat.org/getting-started/).

## Project Overview

This example project includes:

- Una configurazione Hardhat per Solidity 0.8.28 e la rete Base Sepolia.
- Test TypeScript per il contratto AttuarioVault aggiornato.
- Script TypeScript di esempio per verificare il signer, distribuire il contratto e registrare il task di automazione su Gelato.

## Usage

### Running Tests

To run all the tests in the project, execute the following command:

```shell
npx hardhat test
```

### Distribuire su Base Sepolia

1. Imposta le variabili d'ambiente `PRIVATE_KEY` e `RPC_URL` (oppure salvale in un file `.env`).
2. Verifica che il signer sia corretto:

```shell
npx hardhat run scripts/checkSigner.ts --network base_sepolia
```

3. Distribuisci il contratto:

```shell
npx hardhat run scripts/deployVault.ts --network base_sepolia
```

> **Attenzione:** il file `.env` contiene chiavi sensibili, assicurati che non venga mai condiviso o tracciato da git.

### Configurare la strategia

Dopo il deploy:

1. Imposta l'executor Gelato autorizzato (`gelatoExecutor`) dal tuo wallet:

   ```shell
   npx hardhat console --network base_sepolia
   > const vault = await ethers.getContractAt("AttuarioVault", "VAULT_ADDRESS");
   > await vault.setGelatoExecutor("0xYourGelatoDedicatedMsgSender");
   ```

2. Registra i dati giornalieri tramite il bot:

   ```shell
   await vault.executeStrategy("POOL-NAME", 1200, capitalInUnits);
   ```

   - `POOL-NAME`: identificativo scelto dal bot.
   - `1200` rappresenta l'APY in basis points (12,00%).
   - `capitalInUnits`: capitale espresso nelle unità del token (es. USDC → 6 decimali).
   - Il contratto applica un vincolo minimo sull'intervallo tra esecuzioni (`executionInterval`, default 1 giorno). Puoi modificarlo via `setExecutionInterval`.

3. (Opzionale) interroga l'ultimo stato:

   ```shell
   const latest = await vault.latestExecution();
   console.log(latest.pool, latest.apyBps, latest.capital);
   ```

### Registrare l'automazione con Gelato

1. Aggiungi le variabili d'ambiente nel file `.env`:

   ```
   RPC_URL="https://base-sepolia.drpc.org"
   PRIVATE_KEY="0x..."
   VAULT_ADDRESS="0x..."
   ```

   In caso di intervallo personalizzato puoi aggiungere `AUTOMATE_INTERVAL` in secondi.

2. Crea il task su Gelato Automate (se desideri automatizzare on-chain l'esecuzione con un signer dedicato) utilizzando `scripts/registerGelatoTask.ts` come base. Il payload dovrà includere i parametri della funzione `executeStrategy(string,uint256,uint256)` ottenuti off-chain dal bot.

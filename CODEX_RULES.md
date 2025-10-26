CODEX_RULES.md — Attuario “Wave Rotation”
========================================

0) Scopo
--------

Implementare una strategia di rotazione che valuta i pool ogni finestra (default 5 minuti) e, al primo ciclo utile della giornata, sposta tutto il capitale verso il pool con miglior score. A fine giornata calcola il profitto, reinveste il 50% e accantona il 50% in treasury (USDC).
⚠️ Non introdurre filtri prudenziali ulteriori rispetto a quelli esplicitamente descritti qui.

1) Definizioni & Invarianti
---------------------------

- **Orizzonte:** valutazione continua con finestra minima di 5 minuti (configurabile). Gli aggiornamenti economici rimangono computati su base giornaliera.
- **Score per il pool** \(i\) al giorno \(t\):

  ```
  Score_i,t = r_i,t / (1 + c_i,t ⋅ (1 − ρ_i,t))
  ```

  - \(r_{i,t}\) = rendimento giornaliero (derivato da APY del giorno → \(r ≈ (1 + APY)^{1/365} − 1\) o da dato già giornaliero).
  - \(c_{i,t}\) = costo operativo stimato (gas + fee + slippage) espresso in percentuale sul capitale della giornata.
  - \(\rho_{i,t}\) = rischio protocollo, proxy in \([0,1]\) (se non disponibile, usare 0).

- **Regola di switch:** sposta il capitale sul nuovo pool solo se  
  \( Score_{\text{new}} ≥ Score_{\text{current}} ⋅ (1 + Δ) \) con \(Δ = 0.01\) (+1%).  
  Non abbassare \(Δ\) senza motivo; non alzarlo oltre 2% salvo richiesta esplicita.

- **Composizione a fine giornata:**
  - Profitto del giorno \(P = C_0 ⋅ r_{\text{day netto}}\).
  - Reinvest \(= 0.5 ⋅ P\) → \(C_1 = C_0 + 0.5 P = C_0 ⋅ (1 + 0.5 r_{\text{day netto}})\).
  - Treasury \(+= 0.5 ⋅ P\).

- **Stop/Take (essenziali, non “prudenziali”):**
  - Stop-loss: se perdita giornaliera < −10% → il capitale rimane invariato nella finestra e viene attivata l’autopause (vedi sotto) solo sulla parte esposta.
  - Take-profit parziale: se guadagno giornaliero ≥ +5% → nessuna azione extra, è già incorporato dal 50/50.

- **Esclusioni minime (tecniche, non prudenziali):**
  - Escludi pool con TVL < 100.000 USD o rating “not deployable” (se noto).
  - Non imporre altri filtri di stabilità o volatilità.

2) Struttura progetto (suggerita)
---------------------------------

```
attuario/
├─ bots/
│  └─ wave_rotation/
│     ├─ strategy.py
│     ├─ data_sources.py
│     ├─ scoring.py
│     ├─ executor.py
│     ├─ logger.py
│     └─ config.json
├─ contracts/
│  └─ AttuarioVault.sol
├─ scripts/
│  ├─ run_daily.sh
│  └─ register_gelato_task.ts
├─ .env.example
└─ CODEX_RULES.md
```

3) Configurazione (JSON Schema)
-------------------------------

`bots/wave_rotation/config.json`

```json
{
  "chains": ["base", "arbitrum", "polygon", "solana"],
  "min_tvl_usd": 100000,
  "delta_switch": 0.01,
  "reinvest_ratio": 0.5,
  "treasury_token": "USDC",
  "schedule_utc": "07:00",
  "stop_loss_daily": -0.10,
  "take_profit_daily": 0.05,
  "sources": {
    "defillama": true,
    "protocol_apis": ["aerodrome", "velodrome", "kamino"]
  },
  "vault": {
    "address": "0xVAULT",
    "chain": "base",
    "function_execute": "executeStrategy(string,uint256,uint256)"
  },
  "telegram": {
    "enabled": true,
    "bot_token_env": "TELEGRAM_TOKEN",
    "chat_id_env": "TELEGRAM_CHATID"
  },
  "autopause": {
    "streak": 3,
    "resume_wait_minutes": 360,
    "resume_cooldown_minutes": 5,
    "fast_signal_min": 0.0
  }
}
```

> Non cambiare `delta_switch`, `reinvest_ratio`, `stop_loss_daily`, `take_profit_daily` senza richiesta esplicita.

4) Variabili d’ambiente (.env.example)
--------------------------------------

```
# DATA
DEFILLAMA_API=https://yields.llama.fi
AERODROME_API=...
KAMINO_API=...

# VAULT / RPC
BASE_RPC=https://mainnet.base.org
VAULT_ADDRESS=0x...
PRIVATE_KEY=...

# TELEGRAM (opzionale)
TELEGRAM_TOKEN=...
TELEGRAM_CHATID=...

# LOG
LOG_PATH=./wave_rotation.log
```

5) Flusso del bot (obbligatorio)
--------------------------------

`strategy.py` deve implementare:

1. Fetch dati per tutti i pool (DeFiLlama + API specifiche se disponibili).
2. Normalizza i campi: chain, pool_id, apy (annuo), tvl_usd, risk_score \(\rho\) (0–1, default 0), fee/slippage stimati in % \(c\).
3. Calcola rendimento giornaliero \( r = (1 + APY)^{1/365} − 1 \) (se API forniscono già daily rate affidabile, usare quello).
4. Calcola score: \( Score = r / (1 + c ⋅ (1 − \rho)) \).
5. Filtra: `tvl_usd >= min_tvl_usd`.
6. Seleziona pool con score massimo e confronta con pool corrente.  
   Se `score_new >= score_current * (1 + delta_switch)` → switch.
7. Esegui giornata: simula/leggi rendimento effettivo netto del giorno \( r_{\text{net}} = r − c \), aggiorna:
   - `profitto P = C * r_net`
   - `capital = C * (1 + 0.5 * r_net)`
   - `treasury += 0.5 * P`
8. Stop/Take e autopause:
   - Se `r_net < stop_loss_daily` → non eseguire update capitale (mantieni C), registra lo stato "stopped" e incrementa `crisis_streak`.
   - Al raggiungimento di `autopause.streak` intervalli consecutivi in perdita il vault viene posto in pausa: il bot prosegue l'analisi ogni finestra ma non modifica capitale/treasury finché non arriva un segnale positivo ≥ `autopause.fast_signal_min` o trascorre `autopause.resume_wait_minutes`.
   - Se `r_net ≥ take_profit_daily` → nessuna azione extra (già 50/50).
9. On-chain log: chiamare `AttuarioVault.executeStrategy(poolName, apyBps, capitalInWei)` dove:
   - `apyBps = int(APY * 10000)` (bps annui per coerenza storica).
   - `capitalInWei` = capitale in unità del token (es. USDC → 6 decimali, normalizzare a 1e6 prima).
10. Telegram (se attivo): inviare messaggio strutturato con intestazione (switch o pool invariato), riepilogo previsto/realizzato, capitale, treasury, ROI, score (con delta) e stato formattato per punti elenco.

6) Interfacce minime (Python)
-----------------------------

`data_sources.py`

```python
from typing import List, Dict, Any

def fetch_pools() -> List[Dict[str, Any]]:
    """
    Return list of pools with fields:
    {
      "pool_id": str,
      "chain": str,
      "name": str,
      "apy": float,          # annuale in decimale (es. 0.25 = 25%)
      "tvl_usd": float,
      "risk_score": float,   # [0..1], default 0 se sconosciuto
      "fee_pct": float,      # % stimata di costi (slippage+fee), default 0.0005
    }
    """
    ...
```

`scoring.py`

```python
def daily_rate(apy: float) -> float:
    return (1.0 + apy)**(1/365.0) - 1.0

def score(r_day: float, cost_pct: float, risk: float) -> float:
    return r_day / (1.0 + cost_pct * (1.0 - risk))
```

`executor.py`

```python
def should_switch(score_new: float, score_old: float, delta: float) -> bool:
    return score_new >= score_old * (1.0 + delta)

def settle_day(capital: float, r_net: float, reinv: float = 0.5) -> tuple[float, float]:
    P = capital * r_net
    capital_new = capital * (1.0 + reinv * r_net)
    treasury_delta = (1.0 - reinv) * P
    return capital_new, treasury_delta
```

`logger.py`

```python
def log_daily(ts, pool, apy, r_day, r_net, capital_before, capital_after, treasury_add):
    # append CSV o JSONL
    ...
```

7) Contratto (ABI essenziale)
-----------------------------

`contracts/AttuarioVault.sol` deve esporre:

```solidity
function executeStrategy(string calldata pool, uint256 apyBps, uint256 capital) external;
```

- Solo owner/executor può chiamarla (impostato via owner o whitelist).
- Emit `StrategyExecuted(block.timestamp, pool, apyBps, capital)`.
- Non introdurre lock, cooldown complessi o soglie prudenziali non previste.

8) Test di accettazione (DoD)
-----------------------------

✅ Il bot:

- seleziona un pool con TVL ≥ 100k,
- calcola `r_day`, `score`, `r_net = r_day - cost_pct`,
- decide switch se Δscore ≥ +1%,
- aggiorna capital e treasury con 50/50,
-- chiama `executeStrategy(...)`,
- produce un log con le 8 colonne minime:  
  `date,pool,apy,r_day,r_net,capital_before,capital_after,treasury_delta`.

✅ Test giornaliero: eseguire il ciclo con 3 pool fittizi e verificare:

- che lo switch avvenga solo se Δscore ≥ 1%,
- che `capital_after = capital_before * (1 + 0.5*r_net)`,
- che la somma dei `treasury_delta` corrisponda al 50% dei profitti cumulati.

9) Cose da NON fare
-------------------

❌ Non annualizzare risultati nel report giornaliero.  
❌ Non inserire filtri “prudenziali” ulteriori (volatilità/momentum) senza richiesta.  
❌ Non frammentare il capitale su più pool (portafoglio multi-asset) a meno di richiesta esplicita.  
❌ Non cambiare `delta_switch`, `reinvest_ratio`, `stop_loss_daily`, `take_profit_daily`.

10) Esempio di messaggio Telegram
---------------------------------

```
🏁 Pool del giorno: {pool_name}
📈 APY: {apy:.2%} | r_day: {r_day:.4%} | r_net: {r_net:.4%}
💰 Capitale: {cap_before:.2f}€ → {cap_after:.2f}€
🏦 Treasury +{treasury_delta:.2f}€
⏱️ Next run: 24h (07:00 UTC)
```

11) Script di esecuzione (cron/Gelato)
--------------------------------------

`scripts/run_daily.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
python3 bots/wave_rotation/strategy.py --config bots/wave_rotation/config.json >> wave_rotation.log 2>&1
```

12) Nota finale
---------------

Queste regole sono vincolanti per Codex/Copilot: l’output deve rispettare esattamente la strategia Wave Rotation come definita (aggressiva, rotazione giornaliera, switch se Δscore ≥ 1%, reinvest 50% / treasury 50%, senza ulteriori criteri prudenziali). Ogni modifica ai parametri core deve essere esplicitamente richiesta.

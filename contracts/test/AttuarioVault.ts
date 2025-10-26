import { expect } from "chai";
import hardhat from "hardhat";
import { anyValue } from "@nomicfoundation/hardhat-chai-matchers/withArgs.js";

const { ethers, network } = hardhat;

async function deployVaultFixture() {
  const [owner, otherAccount] = await ethers.getSigners();
  const Vault = await ethers.getContractFactory("AttuarioVault");
  const vault = await Vault.deploy();
  await vault.waitForDeployment();

  return { vault, owner, otherAccount };
}

describe("AttuarioVault", function () {
  it("sets the deployer as owner", async function () {
    const { vault, owner } = await deployVaultFixture();
    expect(await vault.owner()).to.equal(owner.address);
  });

  it("allows the owner to execute and records the latest execution", async function () {
    const { vault, owner } = await deployVaultFixture();
    const pool = "BASE:USDC";
    const apyBps = 1250n;
    const capital = ethers.parseUnits("1000", 6);

    await expect(
      vault.executeStrategy(pool, apyBps, capital),
    ).to.emit(vault, "StrategyExecuted").withArgs(anyValue, pool, apyBps, capital, owner.address);

    const last = await vault.latestExecution();
    expect(last.pool).to.equal(pool);
    expect(last.apyBps).to.equal(apyBps);
    expect(last.capital).to.equal(capital);
    expect(last.timestamp).to.equal(await vault.lastExecuted());
    expect(await vault.totalExecutions()).to.equal(1n);
  });

  it("enforces the execution interval between runs", async function () {
    const { vault } = await deployVaultFixture();
    const pool = "BASE:USDC";
    const apyBps = 1000n;
    const capital = ethers.parseUnits("500", 6);

    await vault.executeStrategy(pool, apyBps, capital);
    await expect(
      vault.executeStrategy(pool, apyBps, capital),
    ).to.be.revertedWith("Execution interval not met");

    await network.provider.send("evm_increaseTime", [86400]);
    await network.provider.send("evm_mine");

    await expect(vault.executeStrategy(pool, apyBps, capital)).to.emit(vault, "StrategyExecuted");
    expect(await vault.totalExecutions()).to.equal(2n);
  });

  it("blocks unauthorized executors", async function () {
    const { vault, otherAccount } = await deployVaultFixture();
    await expect(
      vault.connect(otherAccount).executeStrategy("POOL", 100n, 1000n),
    ).to.be.revertedWith("Executor not authorized");
  });

  it("allows the gelato executor once whitelisted", async function () {
    const { vault } = await deployVaultFixture();
    const gelato = ethers.Wallet.createRandom().address;
    await expect(vault.setGelatoExecutor(gelato))
      .to.emit(vault, "GelatoExecutorUpdated")
      .withArgs(ethers.ZeroAddress, gelato);

    await network.provider.send("hardhat_impersonateAccount", [gelato]);
    const gelatoSigner = await ethers.getSigner(gelato);
    await network.provider.send("hardhat_setBalance", [gelato, "0x56BC75E2D63100000"]); // 1 ETH

    await expect(
      vault.connect(gelatoSigner).executeStrategy("AERO:USDC", 900n, 123_000_000n),
    )
      .to.emit(vault, "StrategyExecuted")
      .withArgs(anyValue, "AERO:USDC", 900n, 123_000_000n, gelato);

    await network.provider.send("hardhat_stopImpersonatingAccount", [gelato]);
  });
});

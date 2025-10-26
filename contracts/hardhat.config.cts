import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

dotenv.config();

const PRIVATE_KEY = process.env.PRIVATE_KEY || "";
const BASE_MAINNET_RPC =
  process.env.BASE_MAINNET_RPC ||
  process.env.BASE_RPC ||
  process.env.RPC_URL ||
  "https://mainnet.base.org";
const BASE_SEPOLIA_RPC =
  process.env.BASE_SEPOLIA_RPC || "https://base-sepolia.drpc.org";
const ACCOUNTS = PRIVATE_KEY ? [PRIVATE_KEY] : [];

const config: HardhatUserConfig = {
  solidity: "0.8.28",
  networks: {
    base: {
      url: BASE_MAINNET_RPC,
      chainId: 8453,
      accounts: ACCOUNTS,
    },
    base_sepolia: {
      url: BASE_SEPOLIA_RPC,
      chainId: 84532,
      accounts: ACCOUNTS,
    },
  },
};

export default config;

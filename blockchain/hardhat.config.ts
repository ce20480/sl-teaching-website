import { HardhatUserConfig } from "hardhat/config";
import "@nomiclabs/hardhat-ethers";
import "@nomicfoundation/hardhat-verify";
import "@typechain/hardhat";
import "dotenv/config";

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    hardhat: {
      // Local development network
    },
    filecoin: {
      url: "https://api.node.glif.io/rpc/v1",
      accounts: process.env.WEB3_PRIVATE_KEY
        ? [process.env.WEB3_PRIVATE_KEY]
        : [],
      chainId: 314,
    },
    filecoinTestnet: {
      url: "https://api.calibration.node.glif.io/rpc/v1",
      accounts: process.env.WEB3_PRIVATE_KEY
        ? [process.env.WEB3_PRIVATE_KEY]
        : [],
      chainId: 314159,
    },
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY,
  },
  typechain: {
    outDir: "typechain-types",
    target: "ethers-v5",
    alwaysGenerateOverloads: false,
    externalArtifacts: ["externalArtifacts/*.json"],
    dontOverrideCompile: false,
  },
};

export default config;

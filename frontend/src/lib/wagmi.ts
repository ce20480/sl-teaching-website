import { createConfig, configureChains } from "wagmi";
import { publicProvider } from "wagmi/providers/public";
import { MetaMaskConnector } from "wagmi/connectors/metaMask";
import { WalletConnectConnector } from "wagmi/connectors/walletConnect";
import { CoinbaseWalletConnector } from "wagmi/connectors/coinbaseWallet";
import { InjectedConnector } from "wagmi/connectors/injected";

// Define Filecoin networks
const filecoinMainnet = {
  id: 314,
  name: "Filecoin Mainnet",
  network: "filecoin",
  nativeCurrency: {
    name: "Filecoin",
    symbol: "FIL",
    decimals: 18,
  },
  rpcUrls: {
    default: {
      http: ["https://api.node.glif.io/rpc/v1"],
    },
    public: {
      http: ["https://api.node.glif.io/rpc/v1"],
    },
  },
  blockExplorers: {
    default: { name: "Filscan", url: "https://filscan.io" },
  },
  testnet: false,
};

const filecoinTestnet = {
  id: 314159,
  name: "Filecoin Calibration",
  network: "filecoin-calibration",
  nativeCurrency: {
    name: "Filecoin",
    symbol: "FIL",
    decimals: 18,
  },
  rpcUrls: {
    default: {
      http: ["https://api.calibration.node.glif.io/rpc/v1"],
    },
    public: {
      http: ["https://api.calibration.node.glif.io/rpc/v1"],
    },
  },
  blockExplorers: {
    default: { name: "Filscan", url: "https://calibration.filscan.io" },
  },
  testnet: true,
};

const { chains, publicClient } = configureChains(
  [filecoinMainnet, filecoinTestnet],
  [publicProvider()]
);

export const wagmiConfig = createConfig({
  autoConnect: false,
  connectors: [
    new MetaMaskConnector({ chains }),
    new WalletConnectConnector({
      chains,
      options: {
        projectId: import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID,
      },
    }),
    new CoinbaseWalletConnector({
      chains,
      options: {
        appName: "SL Teaching Website",
      },
    }),
    new InjectedConnector({
      chains,
      options: {
        name: "Browser Wallet",
        shimDisconnect: true,
      },
    }),
  ],
  publicClient,
});

// Export current network information for easy access
export const CURRENT_NETWORK = filecoinTestnet;

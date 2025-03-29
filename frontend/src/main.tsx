import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { WagmiConfig, createConfig, configureChains } from "wagmi";
import { publicProvider } from "wagmi/providers/public";
import { MetaMaskConnector } from "wagmi/connectors/metaMask";
import { WalletConnectConnector } from "wagmi/connectors/walletConnect";
import { CoinbaseWalletConnector } from "wagmi/connectors/coinbaseWallet";
import { createPublicClient, http } from "viem";
import reportWebVitals from "@/reportWebVitals";

// Initialize polyfills
import { Buffer } from 'buffer';
import process from 'process';
import { TextEncoder } from 'util';

// Set up global polyfills
window.Buffer = Buffer;
window.process = process;

// Only set TextEncoder if it's not already defined
if (typeof window.TextEncoder === 'undefined') {
  window.TextEncoder = TextEncoder;
}

// Define Filecoin networks
const filecoinMainnet = {
  id: 314,
  name: 'Filecoin Mainnet',
  network: 'filecoin',
  nativeCurrency: {
    name: 'Filecoin',
    symbol: 'FIL',
    decimals: 18
  },
  rpcUrls: {
    default: {
      http: ['https://api.node.glif.io/rpc/v1']
    },
    public: {
      http: ['https://api.node.glif.io/rpc/v1']
    }
  },
  blockExplorers: {
    default: { name: 'Filscan', url: 'https://filscan.io' }
  },
  testnet: false
};

const filecoinTestnet = {
  id: 314159,
  name: 'Filecoin Calibration',
  network: 'filecoin-calibration',
  nativeCurrency: {
    name: 'Filecoin',
    symbol: 'FIL',
    decimals: 18
  },
  rpcUrls: {
    default: {
      http: ['https://api.calibration.node.glif.io/rpc/v1']
    },
    public: {
      http: ['https://api.calibration.node.glif.io/rpc/v1']
    }
  },
  blockExplorers: {
    default: { name: 'Filscan', url: 'https://calibration.filscan.io' }
  },
  testnet: true
};

const { chains, publicClient } = configureChains(
  [filecoinMainnet, filecoinTestnet],
  [publicProvider()]
);

const config = createConfig({
  autoConnect: true,
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
  ],
  publicClient,
});

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement
);
root.render(
  <React.StrictMode>
    <WagmiConfig config={config}>
      <App />
    </WagmiConfig>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();

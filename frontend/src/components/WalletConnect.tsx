import React from 'react';
import { useAccount, useConnect, useDisconnect } from 'wagmi';
import { InjectedConnector } from 'wagmi/connectors/injected';
import { WalletConnectConnector } from 'wagmi/connectors/walletConnect';
import { CoinbaseWalletConnector } from 'wagmi/connectors/coinbaseWallet';
import { Web3Modal } from '@web3modal/react';
import { EthereumClient } from '@web3modal/ethereum';

// Configure Web3Modal
const projectId = import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID || '';

const chains = [
  {
    id: 314,
    name: 'Filecoin Mainnet',
    network: 'filecoin',
    nativeCurrency: { name: 'FIL', symbol: 'FIL', decimals: 18 },
    rpcUrls: {
      default: { http: ['https://api.node.glif.io/rpc/v1'] },
      public: { http: ['https://api.node.glif.io/rpc/v1'] }
    },
  },
  {
    id: 314159,
    name: 'Filecoin Testnet',
    network: 'filecoin-testnet',
    nativeCurrency: { name: 'FIL', symbol: 'FIL', decimals: 18 },
    rpcUrls: {
      default: { http: ['https://api.calibration.node.glif.io/rpc/v1'] },
      public: { http: ['https://api.calibration.node.glif.io/rpc/v1'] }
    },
  }
];

const injectedConnector = new InjectedConnector({ chains });
const walletConnectConnector = new WalletConnectConnector({
  chains,
  options: {
    projectId,
  },
});
const coinbaseConnector = new CoinbaseWalletConnector({
  chains,
  options: {
    appName: 'ASL Achievement Token',
  },
});

const wagmiConfig = {
  autoConnect: true,
  connectors: [injectedConnector, walletConnectConnector, coinbaseConnector],
};

const ethereumClient = new EthereumClient(wagmiConfig, chains);

export const WalletConnect: React.FC = () => {
  const { address, isConnected } = useAccount();
  const { connect } = useConnect();
  const { disconnect } = useDisconnect();

  const handleConnect = async () => {
    try {
      await connect({ connector: injectedConnector });
    } catch (error) {
      console.error('Failed to connect:', error);
    }
  };

  return (
    <div className="wallet-connect">
      <Web3Modal projectId={projectId} ethereumClient={ethereumClient} />
      {!isConnected ? (
        <button
          onClick={handleConnect}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Connect Wallet
        </button>
      ) : (
        <div className="flex items-center gap-4">
          <div className="text-sm">
            Connected: {address?.slice(0, 6)}...{address?.slice(-4)}
          </div>
          <button
            onClick={() => disconnect()}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Disconnect
          </button>
        </div>
      )}
    </div>
  );
};

export default WalletConnect; 
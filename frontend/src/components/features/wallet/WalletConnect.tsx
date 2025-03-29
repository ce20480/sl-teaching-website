import { useEffect, useState } from 'react';
import { useAccount, useConnect, useDisconnect, useNetwork } from 'wagmi';
import { InjectedConnector } from 'wagmi/connectors/injected';
import { WalletConnectConnector } from 'wagmi/connectors/walletConnect';
import { CoinbaseWalletConnector } from 'wagmi/connectors/coinbaseWallet';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/use-toast';
import { useContractRead, useContractWrite } from 'wagmi';
import { ASL_ACHIEVEMENT_ABI } from '@/constants/contracts';
import { ASL_ACHIEVEMENT_ADDRESS } from '@/constants/addresses';

// Filecoin FVM network configuration
const FILECOIN_NETWORK = {
  id: 314,
  name: 'Filecoin Mainnet',
  network: 'filecoin',
  nativeCurrency: {
    name: 'Filecoin',
    symbol: 'FIL',
    decimals: 18,
  },
  rpcUrls: {
    default: { http: ['https://api.node.glif.io'] },
  },
  blockExplorers: {
    default: { name: 'Filscan', url: 'https://filscan.io' },
  },
};

export function WalletConnect() {
  const { address, isConnected } = useAccount();
  const { connect, connectors, error, isLoading, pendingConnector } = useConnect({
    chainId: FILECOIN_NETWORK.id,
  });
  const { disconnect } = useDisconnect();
  const { chain } = useNetwork();
  const { toast } = useToast();
  const [achievements, setAchievements] = useState<any[]>([]);

  // Contract reads
  const { data: achievementCount } = useContractRead({
    address: ASL_ACHIEVEMENT_ADDRESS,
    abi: ASL_ACHIEVEMENT_ABI,
    functionName: 'getUserAchievementCount',
    args: [address],
    enabled: !!address,
  });

  // Contract writes
  const { write: mintAchievement } = useContractWrite({
    address: ASL_ACHIEVEMENT_ADDRESS,
    abi: ASL_ACHIEVEMENT_ABI,
    functionName: 'mintAchievement',
  });

  // Handle network mismatch
  useEffect(() => {
    if (chain && chain.id !== FILECOIN_NETWORK.id) {
      toast({
        title: 'Network Mismatch',
        description: 'Please switch to Filecoin Mainnet to continue.',
        variant: 'destructive',
      });
    }
  }, [chain, toast]);

  // Handle connection errors
  useEffect(() => {
    if (error) {
      toast({
        title: 'Connection Error',
        description: error.message,
        variant: 'destructive',
      });
    }
  }, [error, toast]);

  // Example function to mint an achievement
  const handleMintAchievement = async () => {
    if (!address) return;

    try {
      await mintAchievement({
        args: [address, 0, 'First Contribution'], // 0 = CONTRIBUTOR type
      });
      toast({
        title: 'Success',
        description: 'Achievement minted successfully!',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to mint achievement',
        variant: 'destructive',
      });
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle>Wallet Connection</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isConnected ? (
          <div className="space-y-2">
            {connectors.map((connector) => (
              <Button
                key={connector.uid}
                onClick={() => connect({ connector })}
                disabled={!connector.ready || isLoading}
                className="w-full"
              >
                {isLoading && connector.uid === pendingConnector?.uid
                  ? 'Connecting...'
                  : `Connect ${connector.name}`}
              </Button>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Connected Address:</span>
              <span className="text-sm text-muted-foreground">
                {address?.slice(0, 6)}...{address?.slice(-4)}
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Achievement Count:</span>
              <span className="text-sm text-muted-foreground">
                {achievementCount?.toString() || '0'}
              </span>
            </div>

            <Button
              onClick={handleMintAchievement}
              className="w-full"
            >
              Mint Example Achievement
            </Button>

            <Button
              onClick={() => disconnect()}
              variant="destructive"
              className="w-full"
            >
              Disconnect
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
} 
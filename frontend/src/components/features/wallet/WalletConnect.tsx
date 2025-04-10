import { useAccount, useConnect, useDisconnect, useNetwork, useSwitchNetwork } from "wagmi";
import { Button } from "@/components/ui/button";
import { 
  Wallet, 
  LogOut, 
  ExternalLink, 
  AlertTriangle,
  Loader2,
  ArrowRight
} from "lucide-react";
import { useState, useEffect } from "react";
import { toast } from "sonner";
import { CURRENT_NETWORK} from "@/lib/wagmi";

export function WalletConnect() {
  const { address, isConnected } = useAccount();
  const { connect, connectors, isLoading, pendingConnector, error } = useConnect();
  const { disconnect } = useDisconnect();
  const { chain } = useNetwork();
  const { switchNetwork, isLoading: isSwitchingNetwork } = useSwitchNetwork();
  const [networkMismatch, setNetworkMismatch] = useState(false);
  
  // Handle network mismatch
  useEffect(() => {
    if (chain && chain.id !== CURRENT_NETWORK.id && isConnected) {
      setNetworkMismatch(true);
      toast.error(`Please switch to ${CURRENT_NETWORK.name} network`);
    } else {
      setNetworkMismatch(false);
    }
  }, [chain, isConnected]);

  // Handle connection error display
  useEffect(() => {
    if (error) {
      // Only show non-user rejection errors
      if (!error.message.includes("User rejected") && 
          !error.message.includes("already pending")) {
        toast.error(error.message);
      }
      
      // For "already pending" errors, show a more helpful message
      if (error.message.includes("already pending")) {
        toast.info("Connection request already pending. Check your wallet extension.");
      }
    }
  }, [error]);

  // Store address in localStorage after successful connection
  useEffect(() => {
    if (isConnected && address) {
      // Store the address in localStorage for persistence
      localStorage.setItem('lastConnectedAddress', address);
      
      // Log success
      console.log(`Wallet connected: ${address}`);
    }
  }, [isConnected, address]);

  // Safe connect function with debounce
  const handleConnect = (connector: typeof connectors[number]) => {
    // Prevent multiple rapid connection attempts
    if (isLoading) {
      toast.info("Connection in progress. Please wait...");
      return;
    }
    
    try {
      connect({ connector });
    } catch (err) {
      console.error("Connection error:", err);
    }
  };

  // Handle network switching
  const handleSwitchNetwork = () => {
    if (switchNetwork && chain) {
      switchNetwork(CURRENT_NETWORK.id);
    } else {
      // Fallback for wallets without programmatic network switching
      toast.info(`Please manually switch to ${CURRENT_NETWORK.name} in your wallet`);
    }
  };

  return (
    <div className="flex flex-col space-y-2 w-full">
      {!isConnected ? (
        <div className="space-y-2">
          {connectors.map((connector) => {
            // Don't show connectors that aren't ready, except injected providers that might still work
            if (!connector.ready && !connector.id.includes("injected")) return null;
            
            return (
              <Button
                disabled={isLoading}
                key={connector.id}
                onClick={() => handleConnect(connector)}
                className="w-full flex items-center justify-center"
                variant={connector.id.includes("metaMask") ? "default" : "outline"}
                size="lg"
              >
                {isLoading && connector.id === pendingConnector?.id ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  getConnectorIcon(connector.id)
                )}
                {isLoading && connector.id === pendingConnector?.id
                  ? "Connecting..."
                  : `Connect ${connector.name}`}
                {!connector.ready && !connector.id.includes("injected") && ' (unsupported)'}
              </Button>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center space-y-3 py-2">
          {networkMismatch && (
            <div className="bg-amber-50 text-amber-700 px-4 py-2 rounded-md text-xs font-medium mb-2 w-full">
              <div className="flex justify-between items-center">
                <div className="flex items-center">
                  <AlertTriangle className="mr-2 h-4 w-4" />
                  Wrong network. Please switch to {CURRENT_NETWORK.name}.
                </div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="ml-2 text-xs h-7 bg-amber-100 border-amber-200 hover:bg-amber-200"
                  onClick={handleSwitchNetwork}
                  disabled={isSwitchingNetwork}
                >
                  {isSwitchingNetwork ? (
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  ) : (
                    <ArrowRight className="h-3 w-3 mr-1" />
                  )}
                  Switch
                </Button>
              </div>
            </div>
          )}
          
          <div className="bg-blue-50 text-blue-700 px-4 py-2 rounded-full text-sm font-medium flex items-center">
            <Wallet className="mr-2 h-4 w-4" />
            {address?.slice(0, 6)}...{address?.slice(-4)}
          </div>
          
          <div className="flex gap-2">
            <Button
              onClick={() => disconnect()}
              variant="outline"
              size="sm"
              className="text-red-600 border-red-200 hover:bg-red-50 flex items-center gap-1"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Disconnect</span>
            </Button>
            
            <a 
              href={`${CURRENT_NETWORK.blockExplorers.default.url}/address/${address}`}
              target="_blank"
              rel="noopener noreferrer" 
              className="text-blue-600 hover:underline flex items-center text-xs"
            >
              <Button
                variant="outline"
                size="sm"
                className="text-blue-600 border-blue-200 hover:bg-blue-50 flex items-center gap-1"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                <span>View on Explorer</span>
              </Button>
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper function to get the appropriate icon for each connector
function getConnectorIcon(connectorId: string) {
  if (connectorId.includes("metaMask") || connectorId.includes("injected")) {
    return (
      <img 
        src="https://upload.wikimedia.org/wikipedia/commons/3/36/MetaMask_Fox.svg" 
        alt="MetaMask" 
        className="w-5 h-5 mr-2" 
      />
    );
  } else if (connectorId.includes("walletConnect")) {
    return (
      <img
        src="https://avatars.githubusercontent.com/u/37784886"
        alt="WalletConnect"
        className="w-5 h-5 mr-2 rounded-full"
      />
    );
  } else if (connectorId.includes("coinbase")) {
    return (
      <img 
        src="https://avatars.githubusercontent.com/u/1885080" 
        alt="Coinbase" 
        className="w-5 h-5 mr-2 rounded-full" 
      />
    );
  }
  
  // Default wallet icon
  return <Wallet className="mr-2 h-5 w-5" />;
}
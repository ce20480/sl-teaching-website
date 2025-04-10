import { useAccount } from "wagmi";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Wallet,
  LogOut,
  Languages,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { useDisconnect, useConnect, useNetwork } from "wagmi";
import { useState, useEffect } from "react";
import { CURRENT_NETWORK } from "@/lib/wagmi";
import { toast } from "sonner";

const NavHeader = () => {
  const { address, isConnected } = useAccount();
  const { disconnect } = useDisconnect();
  const { connect, connectors, isLoading, error } = useConnect();
  const { chain } = useNetwork();
  const [networkMismatch, setNetworkMismatch] = useState(false);

  // Handle network mismatch
  useEffect(() => {
    if (chain && chain.id !== CURRENT_NETWORK.id && isConnected) {
      setNetworkMismatch(true);
    } else {
      setNetworkMismatch(false);
    }
  }, [chain, isConnected]);

  // Handle connection error display
  useEffect(() => {
    if (error) {
      toast.error(`Connection error: ${error.message}`);
    }
  }, [error]);

  // Find preferred connector (MetaMask or first injected)
  const handleConnect = () => {
    try {
      const preferredConnector = connectors.find(
        (c) => c.id.includes("metaMask") || c.id.includes("injected")
      );

      if (preferredConnector) {
        connect({ connector: preferredConnector });
      } else if (connectors.length > 0) {
        // Fallback to first available connector
        connect({ connector: connectors[0] });
      } else {
        toast.error("No wallet connectors available");
      }
    } catch (error) {
      console.error("Failed to connect:", error);
    }
  };

  return (
    <header className="border-b">
      <div className="container max-w-4xl mx-auto px-4 py-3 flex justify-between items-center">
        <Link to="/" className="flex items-center space-x-2">
          <Languages className="h-6 w-6 text-blue-500" />
          <span className="font-semibold text-lg">ASL Translator</span>
        </Link>

        <div>
          {isConnected ? (
            <div className="flex items-center gap-2">
              {networkMismatch && (
                <div className="text-amber-500 hidden sm:block text-xs">
                  <AlertTriangle className="h-3 w-3 inline mr-1" />
                  Wrong network
                </div>
              )}
              <Link
                to="/profile"
                className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-sm ${
                  networkMismatch
                    ? "bg-amber-50 text-amber-700"
                    : "bg-blue-50 text-blue-700"
                }`}
              >
                <Wallet className="h-3.5 w-3.5 mr-1" />
                <span className="hidden sm:inline">
                  {address?.slice(0, 6)}...{address?.slice(-4)}
                </span>
                <span className="sm:hidden">{address?.slice(0, 4)}...</span>
              </Link>

              <Button
                variant="ghost"
                size="icon"
                onClick={() => disconnect()}
                className="text-red-600 h-8 w-8"
              >
                <LogOut className="h-3.5 w-3.5" />
              </Button>
            </div>
          ) : (
            <Button
              variant="default"
              size="sm"
              className="flex items-center gap-2"
              onClick={handleConnect}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Wallet className="h-4 w-4 mr-1" />
              )}
              <span>{isLoading ? "Connecting..." : "Connect Wallet"}</span>
            </Button>
          )}
        </div>
      </div>
    </header>
  );
};

export default NavHeader;

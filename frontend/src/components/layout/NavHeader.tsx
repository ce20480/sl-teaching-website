import { useAccount } from "wagmi";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Wallet, LogOut, Languages } from "lucide-react";
import { useDisconnect } from "wagmi";
import { useConnect } from "wagmi";
import { InjectedConnector } from "wagmi/connectors/injected";

const NavHeader = () => {
  const { address, isConnected } = useAccount();
  const { disconnect } = useDisconnect();
  const { connect } = useConnect();

  const handleConnect = async () => {
    try {
      await connect({ connector: new InjectedConnector() });
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
              <Button
                variant="outline"
                size="sm"
                className="flex items-center gap-1"
              >
                <Wallet className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">
                  {address?.slice(0, 6)}...{address?.slice(-4)}
                </span>
                <span className="sm:hidden">{address?.slice(0, 4)}...</span>
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => disconnect()}
                className="text-red-600"
              >
                <LogOut className="h-3.5 w-3.5" />
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              className="flex items-center gap-2"
              onClick={handleConnect}
            >
              <Wallet className="h-4 w-4" />
              <span>Connect</span>
            </Button>
          )}
        </div>
      </div>
    </header>
  );
};

export default NavHeader;

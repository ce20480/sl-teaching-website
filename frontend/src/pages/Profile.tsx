import { useAccount, useDisconnect, useBalance, useNetwork } from "wagmi";
import { WalletConnect } from "@/components/features/wallet/WalletConnect";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import {
  Wallet,
  LogOut,
  ExternalLink,
  AlertTriangle,
  Network,
  History,
  ShieldCheck,
  Coins,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { CURRENT_NETWORK } from "@/lib/wagmi";

const Profile = () => {
  const { address, connector, isConnected } = useAccount();
  const { disconnect } = useDisconnect();
  const { chain } = useNetwork();
  const { data: balanceData } = useBalance({
    address: address,
  });

  if (!isConnected) {
    return (
      <div className="container max-w-md mx-auto px-4 py-8">
        <Card className="w-full">
          <CardHeader>
            <CardTitle>Wallet Connection</CardTitle>
            <CardDescription>
              Connect your wallet to view your profile
            </CardDescription>
          </CardHeader>
          <CardContent>
            <WalletConnect />
          </CardContent>
        </Card>
      </div>
    );
  }

  const networkMismatch = chain && chain.id !== CURRENT_NETWORK.id;

  return (
    <div className="container max-w-xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Your Profile</h1>

      <div className="grid gap-6">
        {/* Wallet Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Wallet className="mr-2 h-5 w-5" />
              Wallet Information
            </CardTitle>
            <CardDescription>Your connected wallet details</CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {/* Network Status */}
            <div className="flex items-start justify-between">
              <div className="flex items-center">
                <Network className="h-5 w-5 mr-2 text-blue-500" />
                <span className="text-sm font-medium">Network</span>
              </div>
              <div className="text-right">
                {networkMismatch ? (
                  <div className="flex items-center text-amber-600">
                    <AlertTriangle className="h-4 w-4 mr-1" />
                    <span className="text-sm font-medium">
                      Wrong network ({chain?.name})
                    </span>
                  </div>
                ) : (
                  <span className="text-sm font-medium text-green-600">
                    {CURRENT_NETWORK.name}
                  </span>
                )}
              </div>
            </div>

            {/* Address */}
            <div className="flex items-start justify-between">
              <div className="flex items-center">
                <ShieldCheck className="h-5 w-5 mr-2 text-blue-500" />
                <span className="text-sm font-medium">Address</span>
              </div>
              <div className="text-right">
                <span className="text-sm font-medium">
                  {address?.slice(0, 6)}...{address?.slice(-4)}
                </span>
                <a
                  href={`${CURRENT_NETWORK.blockExplorers.default.url}/address/${address}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:underline flex items-center justify-end mt-1"
                >
                  View on Explorer <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </div>
            </div>

            {/* Wallet Type */}
            {connector && (
              <div className="flex items-start justify-between">
                <div className="flex items-center">
                  <History className="h-5 w-5 mr-2 text-blue-500" />
                  <span className="text-sm font-medium">Wallet Type</span>
                </div>
                <span className="text-sm font-medium">{connector.name}</span>
              </div>
            )}

            {/* Balance */}
            {balanceData && (
              <div className="flex items-start justify-between">
                <div className="flex items-center">
                  <Coins className="h-5 w-5 mr-2 text-blue-500" />
                  <span className="text-sm font-medium">Balance</span>
                </div>
                <span className="text-sm font-medium">
                  {parseFloat(balanceData.formatted).toFixed(4)}{" "}
                  {balanceData.symbol}
                </span>
              </div>
            )}
          </CardContent>

          <CardFooter>
            <Button
              onClick={() => disconnect()}
              variant="destructive"
              className="w-full flex items-center"
            >
              <LogOut className="mr-2 h-4 w-4" />
              Disconnect Wallet
            </Button>
          </CardFooter>
        </Card>

        {/* Additional profile content can be added here */}
      </div>
    </div>
  );
};

export default Profile;

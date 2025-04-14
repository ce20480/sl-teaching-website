import { useState, useEffect } from "react";
import { createPublicClient, http, Chain } from "viem";

export type TransactionStatus = "pending" | "success" | "failed" | "unknown";

// Create a custom chain configuration for Filecoin Calibration testnet
const filecoinCalibration: Chain = {
  id: 314159,
  name: "Filecoin Calibration",
  network: "calibration",
  nativeCurrency: {
    decimals: 18,
    name: "testnet filecoin",
    symbol: "tFIL",
  },
  rpcUrls: {
    default: {
      http: ["https://api.calibration.node.glif.io/rpc/v1"],
    },
    public: {
      http: ["https://api.calibration.node.glif.io/rpc/v1"],
    },
  },
};

// Ensure transaction hash has 0x prefix
const ensureHashPrefix = (hash: string): `0x${string}` => {
  if (!hash.startsWith("0x")) {
    return `0x${hash}` as `0x${string}`;
  }
  return hash as `0x${string}`;
};

export function useTransactionStatus(txHash: string | null | undefined) {
  const [status, setStatus] = useState<TransactionStatus>("unknown");
  const [blockNumber, setBlockNumber] = useState<bigint | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!txHash) return;

    // Format the transaction hash correctly with 0x prefix
    const formattedTxHash = ensureHashPrefix(txHash);

    const publicClient = createPublicClient({
      chain: filecoinCalibration,
      transport: http(),
    });

    setIsPolling(true);

    // Initial check
    checkStatus();

    const intervalId = setInterval(checkStatus, 10000); // Poll every 10 seconds

    async function checkStatus() {
      try {
        console.log(
          `Checking Filecoin Calibration status for transaction: ${formattedTxHash}`
        );

        // First check if transaction exists
        let tx;
        try {
          tx = await publicClient.getTransaction({
            hash: formattedTxHash,
          });
        } catch (err) {
          console.log(`Transaction not found yet: ${formattedTxHash}`, err);
          return; // Continue polling if not found
        }

        if (!tx) {
          console.log(
            `Transaction ${formattedTxHash} not found on blockchain yet`
          );
          setStatus("pending");
          return;
        }

        // If transaction exists, check receipt
        try {
          const receipt = await publicClient.getTransactionReceipt({
            hash: formattedTxHash,
          });

          if (receipt) {
            // Transaction has been mined
            setBlockNumber(receipt.blockNumber);

            if (receipt.status === "success") {
              console.log(
                `Transaction ${formattedTxHash} confirmed successfully`
              );
              setStatus("success");
              clearInterval(intervalId);
              setIsPolling(false);
            } else {
              console.log(`Transaction ${formattedTxHash} failed or reverted`);
              setStatus("failed");
              clearInterval(intervalId);
              setIsPolling(false);
            }
          } else {
            // Transaction exists but not yet mined
            console.log(
              `Transaction ${formattedTxHash} is pending (found but no receipt)`
            );
            setStatus("pending");
          }
        } catch (err) {
          console.log(
            `Error getting receipt for ${formattedTxHash}, assuming pending`,
            err
          );
          setStatus("pending");
        }
      } catch (err) {
        console.error("Error checking transaction status:", err);
        setError(err instanceof Error ? err : new Error(String(err)));
      }
    }

    return () => {
      clearInterval(intervalId);
      setIsPolling(false);
    };
  }, [txHash]);

  return { status, blockNumber, isPolling, error };
}

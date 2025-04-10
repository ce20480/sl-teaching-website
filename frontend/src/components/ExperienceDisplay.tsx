import React, { useEffect, useState } from "react";
import { useAccount, useContractRead } from "wagmi";
import { formatUnits } from "ethers/lib/utils";
import { Progress } from "@/components/ui/progress";
import { ASLExperienceToken__factory } from "../types/contracts/types/factories/contracts/ASLExperienceToken__factory";

interface XPActivity {
  amount: string;
  timestamp: number;
  activityType: string;
}

const activityTypeToString = (type: number): string => {
  const types = [
    "Lesson Completion",
    "Dataset Contribution",
    "Daily Practice",
    "Quiz Completion",
    "Achievement Earned",
  ];
  return types[type] || "Unknown Activity";
};

export function ExperienceDisplay() {
  const { address, isConnected } = useAccount();
  const [recentActivity, setRecentActivity] = useState<XPActivity[]>([]);
  const [nextLevelXP, setNextLevelXP] = useState(1000);

  // Get XP token contract address from environment variables
  const xpTokenAddress = import.meta.env
    .VITE_XP_TOKEN_CONTRACT_ADDRESS as string;

  // Read user's XP balance
  const { data: balance, isLoading } = useContractRead({
    address: xpTokenAddress,
    abi: ASLExperienceToken__factory.abi,
    functionName: "balanceOf",
    args: [address],
    enabled: isConnected && !!address,
    watch: true,
  });

  // Format balance for display (convert from wei to token units)
  const formattedBalance = balance ? formatUnits(balance.toString(), 18) : "0";

  // Calculate current level based on XP (simple algorithm)
  const currentLevel = Math.floor(parseFloat(formattedBalance) / 1000) + 1;

  // Calculate progress to next level
  const progressToNextLevel = (parseFloat(formattedBalance) % 1000) / 10;

  // In a real app, you would fetch recent activity from an event listener or API
  useEffect(() => {
    // Simulate recent activity data for now
    // In production, you would query events from the blockchain or backend
    const mockActivity: XPActivity[] = [
      { amount: "50", timestamp: Date.now() - 3600000, activityType: "0" },
      { amount: "100", timestamp: Date.now() - 86400000, activityType: "1" },
      { amount: "20", timestamp: Date.now() - 172800000, activityType: "2" },
    ];

    setRecentActivity(mockActivity);
  }, [address]);

  if (!isConnected) {
    return (
      <div className="bg-zinc-100 p-6 rounded-lg text-center">
        Connect your wallet to view your XP
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-lg p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">Experience Points</h2>
        <div className="text-lg font-medium">{formattedBalance} XP</div>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span>Level {currentLevel}</span>
          <span>Level {currentLevel + 1}</span>
        </div>
        <Progress value={progressToNextLevel} className="h-2" />
      </div>

      <div className="mt-6">
        <h3 className="text-lg font-medium mb-2">Recent Activity</h3>
        <div className="space-y-2">
          {recentActivity.map((activity, index) => (
            <div
              key={index}
              className="flex justify-between py-2 border-b border-gray-100"
            >
              <span>
                {activityTypeToString(parseInt(activity.activityType))}
              </span>
              <span className="font-medium">+{activity.amount} XP</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

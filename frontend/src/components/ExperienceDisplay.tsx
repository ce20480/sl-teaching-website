import React, { useEffect, useState } from "react";
import { useAccount, useContractRead } from "wagmi";
import { formatUnits } from "ethers/lib/utils";
import { Progress } from "@/components/ui/progress";
import { ASLExperienceToken__factory } from "../types/contracts/types/factories/contracts/ASLExperienceToken__factory";
import { Award, Clock, Trophy } from "lucide-react";

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
      <div className="bg-blue-50 p-6 rounded-lg text-center text-blue-700 flex flex-col items-center">
        <Trophy className="h-12 w-12 mb-2 text-blue-400 opacity-50" />
        <p>Connect your wallet to view your XP</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 w-full">
      <div className="flex justify-between items-center bg-blue-50 p-4 rounded-lg">
        <div className="flex items-center">
          <Award className="h-6 w-6 text-blue-600 mr-2" />
          <h2 className="text-lg font-semibold text-blue-800">Experience</h2>
        </div>
        <div className="text-lg font-medium bg-white px-3 py-1 rounded-full text-blue-600 border border-blue-100">
          {parseFloat(formattedBalance).toLocaleString()} XP
        </div>
      </div>

      <div className="space-y-2 bg-white p-4 rounded-lg border border-slate-100">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium">Level {currentLevel}</span>
          <span className="text-sm text-slate-500">
            Level {currentLevel + 1}
          </span>
        </div>
        <Progress
          value={progressToNextLevel}
          className="h-2 bg-slate-100"
          indicatorClassName="bg-blue-500"
        />
        <div className="text-xs text-slate-500 text-right pt-1">
          {Math.round(progressToNextLevel * 10)} / 1000 XP
        </div>
      </div>

      <div className="mt-2 bg-white p-4 rounded-lg border border-slate-100">
        <h3 className="text-md font-medium mb-3 flex items-center text-blue-700">
          <Clock className="h-4 w-4 mr-2" />
          Recent Activity
        </h3>
        {recentActivity.length > 0 ? (
          <div className="space-y-2">
            {recentActivity.map((activity, index) => (
              <div
                key={index}
                className="flex justify-between py-2 border-b border-blue-50"
              >
                <span className="text-sm">
                  {activityTypeToString(parseInt(activity.activityType))}
                </span>
                <span className="font-medium text-sm text-green-600">
                  +{activity.amount} XP
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500 text-center py-2">
            No recent activity
          </p>
        )}
      </div>
    </div>
  );
}

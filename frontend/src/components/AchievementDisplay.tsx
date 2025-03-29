import React, { useEffect, useState } from 'react';
import { useAccount, useContractRead } from 'wagmi';
import { AchievementToken__factory } from '../contracts/types/factories/contracts/AchievementToken__factory';
import { ethers } from 'ethers';

interface Achievement {
  id: number;
  type: string;
  description: string;
  timestamp: number;
  ipfsHash: string;
}

export const AchievementDisplay: React.FC = () => {
  const { address, isConnected } = useAccount();
  const [achievements, setAchievements] = useState<Achievement[]>([]);

  // Contract address - should be moved to environment variables
  const contractAddress = process.env.REACT_APP_CONTRACT_ADDRESS || '';

  // Initialize contract
  const contract = AchievementToken__factory.connect(
    contractAddress,
    new ethers.providers.Web3Provider(window.ethereum).getSigner()
  );

  // Read user's achievement count
  const { data: achievementCount } = useContractRead({
    address: contractAddress as `0x${string}`,
    abi: AchievementToken__factory.abi,
    functionName: 'getUserAchievementCount',
    args: [address as `0x${string}`],
    enabled: isConnected && !!address,
  });

  // Read user's achievements
  const { data: achievementIds } = useContractRead({
    address: contractAddress as `0x${string}`,
    abi: AchievementToken__factory.abi,
    functionName: 'getUserAchievements',
    args: [address as `0x${string}`],
    enabled: isConnected && !!address,
  });

  // Fetch achievement details
  useEffect(() => {
    const fetchAchievements = async () => {
      if (!achievementIds || !contract) return;

      const achievementPromises = achievementIds.map(async (id: bigint) => {
        const achievement = await contract.getAchievement(Number(id));
        return {
          id: Number(id),
          type: String(achievement.achievementType),
          description: achievement.description,
          timestamp: achievement.timestamp.toNumber(),
          ipfsHash: achievement.ipfsHash,
        };
      });

      const results = await Promise.all(achievementPromises);
      setAchievements(results);
    };

    fetchAchievements();
  }, [achievementIds, contract]);

  if (!isConnected) {
    return <div>Please connect your wallet to view achievements</div>;
  }

  return (
    <div className="achievement-display">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Your Achievements</h2>
        <div className="text-lg font-semibold text-blue-600">
          Score: {achievementCount?.toString() || '0'}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {achievements.map((achievement) => (
          <div
            key={achievement.id}
            className="p-4 border rounded-lg shadow-md hover:shadow-lg transition-shadow"
          >
            <h3 className="text-xl font-semibold mb-2">
              {achievement.type}
            </h3>
            <p className="text-gray-600 mb-2">{achievement.description}</p>
            <p className="text-sm text-gray-500">
              Earned: {new Date(achievement.timestamp * 1000).toLocaleDateString()}
            </p>
            <a
              href={`https://ipfs.io/ipfs/${achievement.ipfsHash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-700 text-sm mt-2 inline-block"
            >
              View on IPFS
            </a>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AchievementDisplay; 
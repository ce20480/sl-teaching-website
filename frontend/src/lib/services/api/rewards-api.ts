import { apiClient } from "./api-client";

interface UserRewardsData {
  xp: number;
  level: number;
  achievements: Achievement[];
  contributions: number;
  wallet_address: string;
}

interface Achievement {
  id: string;
  name: string;
  description: string;
  image_url: string;
  acquired: boolean;
  acquired_at?: string;
  transaction_hash?: string;
}

interface LeaderboardEntry {
  wallet_address: string;
  xp: number;
  level: number;
  contributions: number;
  rank: number;
}

interface BlockchainStatus {
  success: boolean;
  connected: boolean;
  endpoint?: string;
  chain_id?: number;
  block_number?: number;
  gas_price_gwei?: number;
  account?: string;
  balance?: number;
  error?: string;
}

interface TransactionStatus {
  success: boolean;
  tx_hash: string;
  status: "pending" | "success" | "failed" | "not_found";
  confirmed: boolean;
  block_number?: number;
  block_timestamp?: number;
  gas_used?: number;
  effective_gas_price?: number;
  from?: string;
  to?: string;
  error?: string;
  message?: string;
}

export const rewardsApi = {
  /**
   * Get user rewards data
   * @param walletAddress The user's wallet address
   * @returns User rewards data including XP, level, and achievements
   */
  async getUserRewards(walletAddress: string): Promise<UserRewardsData> {
    const response = await apiClient.get(`/api/rewards/user/${walletAddress}`);
    return response.data;
  },

  /**
   * Award custom XP to a user
   * @param walletAddress The user's wallet address
   * @returns User rewards data including XP, level, and achievements
   */
  async awardCustomXP(
    walletAddress: string,
    amount: number
  ): Promise<UserRewardsData> {
    const response = await apiClient.get(
      `/api/rewards/xp/award-custom/${walletAddress}?amount=${amount}`
    );
    return response.data;
  },

  /**
   * Award XP to a user for a specific activity type
   * @param walletAddress The user's wallet address
   * @param amount The amount of XP to award
   * @param activityType The type of activity to award XP for
   * @returns User rewards data including XP, level, and achievements
   */
  async awardXP(
    walletAddress: string,
    activityType: string
  ): Promise<UserRewardsData> {
    const response = await apiClient.get(
      `/api/rewards/xp/award/${walletAddress}?activity_type=${activityType}`
    );
    return response.data;
  },

  /**
   * Get leaderboard
   * @param limit Optional number of entries to return (default 10)
   * @returns Leaderboard entries sorted by XP
   */
  async getLeaderboard(limit = 10): Promise<LeaderboardEntry[]> {
    const response = await apiClient.get(
      `/api/rewards/leaderboard?limit=${limit}`
    );
    return response.data;
  },

  /**
   * Get all achievements
   * @returns List of all possible achievements
   */
  async getAllAchievements(): Promise<Achievement[]> {
    const response = await apiClient.get("/api/rewards/achievements");
    return response.data;
  },

  /**
   * Get user's achievements
   * @param walletAddress The user's wallet address
   * @returns List of achievements for the user
   */
  async getUserAchievements(walletAddress: string): Promise<Achievement[]> {
    const response = await apiClient.get(
      `/api/rewards/achievements/${walletAddress}`
    );
    return response.data;
  },

  /**
   * Check the blockchain connection status
   */
  async checkBlockchainStatus(): Promise<BlockchainStatus> {
    try {
      const response = await apiClient.get("/api/rewards/blockchain/status");
      return response.data;
    } catch (error) {
      console.error("Error checking blockchain status:", error);
      throw error;
    }
  },

  /**
   * Check the status of a blockchain transaction
   * @param txHash The transaction hash to check
   * @returns Status of the transaction
   */
  async checkTransactionStatus(txHash: string): Promise<TransactionStatus> {
    try {
      const response = await apiClient.get(
        `/api/rewards/transactions/${txHash}`
      );
      return response.data;
    } catch (error) {
      console.error("Error checking transaction status:", error);
      return {
        success: false,
        tx_hash: txHash,
        status: "not_found",
        confirmed: false,
        error: error instanceof Error ? error.message : "Unknown error",
        message: "Failed to retrieve transaction status",
      };
    }
  },
};

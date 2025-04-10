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
};

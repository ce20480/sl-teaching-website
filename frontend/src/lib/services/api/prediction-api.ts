import { apiClient } from "./api-client";

interface PredictionResponse {
  letter: string;
  confidence: number;
  landmarks?: number[];
}

interface ContributionRequest {
  landmarks: number[];
  label: string;
  wallet_address?: string;
}

export const predictionApi = {
  /**
   * Send hand landmarks to the backend for sign language prediction
   * @param landmarks Flattened array of landmark coordinates [x1, y1, z1, x2, y2, z2, ...]
   * @returns Prediction response with letter and confidence
   */
  async predictSign(landmarks: number[]): Promise<PredictionResponse> {
    const response = await apiClient.post("/api/prediction/predict", {
      landmarks,
    });
    return response.data;
  },

  /**
   * Get the model's accuracy and statistics
   * @returns Model stats including accuracy, sample count, etc.
   */
  async getModelStats(): Promise<{
    accuracy: number;
    total_samples: number;
    last_trained: string;
    supported_signs: string[];
  }> {
    const response = await apiClient.get("/api/prediction/stats");
    return response.data;
  },

  /**
   * Contribute hand landmarks with label for training
   * @param landmarks Flattened array of landmark coordinates
   * @param label The sign language letter or label
   * @param walletAddress Optional wallet address for rewards
   * @returns Success status
   */
  async contributeData(
    landmarks: number[],
    label: string,
    walletAddress?: string
  ): Promise<{ success: boolean; task_id?: string }> {
    const payload: ContributionRequest = {
      landmarks,
      label,
    };

    if (walletAddress) {
      payload.wallet_address = walletAddress;
    }

    const response = await apiClient.post(
      "/api/prediction/contribute",
      payload
    );
    return response.data;
  },
};

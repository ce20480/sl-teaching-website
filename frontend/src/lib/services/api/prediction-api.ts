import { apiClient } from "./api-client";

interface PredictionResponse {
  letter: string;
  confidence: number;
  landmarks?: number[];
}

export const predictionApi = {
  /**
   * Send hand landmarks to the backend for sign language prediction
   * @param landmarks Flattened array of landmark coordinates [x1, y1, z1, x2, y2, z2, ...]
   * @returns Prediction response with letter and confidence
   */
  async predictSign(landmarks: number[]): Promise<PredictionResponse> {
    const response = await apiClient.post("/api/predict", { landmarks });
    return response.data;
  },

  /**
   * Contribute hand landmarks with label for training
   * @param landmarks Flattened array of landmark coordinates
   * @param label The sign language letter or label
   * @returns Success status
   */
  async contributeData(
    landmarks: number[],
    label: string
  ): Promise<{ success: boolean }> {
    const response = await apiClient.post("/api/contribute", {
      landmarks,
      label,
    });
    return response.data;
  },
};

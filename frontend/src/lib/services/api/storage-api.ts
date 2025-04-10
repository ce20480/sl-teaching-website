import { apiClient } from "./api-client";

interface FileMetadata {
  id: string;
  name: string;
  size: number;
  mimeType: string;
  url: string;
  createdAt: string;
}

interface UploadResponse {
  success: boolean;
  task_id?: string;
  message?: string;
  cid?: string;
}

interface EvaluationStatus {
  status: string;
  score?: number;
  message?: string;
  completed?: boolean;
  reward?: {
    xp?: {
      success: boolean;
      transaction_hash?: string;
    };
    achievement?: {
      success: boolean;
      transaction_hash?: string;
    };
  };
}

export const storageApi = {
  /**
   * Upload a file to storage with wallet address for rewards
   */
  async uploadFile(
    file: File,
    onProgress?: (progress: number) => void,
    walletAddress?: string
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    // Add wallet address if provided
    if (walletAddress) {
      formData.append("wallet_address", walletAddress);
    }

    const response = await apiClient.post("/api/storage/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(progress);
        }
      },
    });

    return response.data;
  },

  /**
   * Upload a file to storage with wallet address for rewards
   */
  async uploadContribution(
    file: File,
    onProgress?: (progress: number) => void,
    walletAddress?: string
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    // Add wallet address if provided
    if (walletAddress) {
      formData.append("user_address", walletAddress);
    }

    const response = await apiClient.post(
      "/api/storage/contribution",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(progress);
          }
        },
      }
    );

    return response.data;
  },

  /**
   * Check the evaluation status of an uploaded file
   */
  async checkEvaluationStatus(taskId: string): Promise<EvaluationStatus> {
    const response = await apiClient.get(`/api/evaluation/status/${taskId}`);
    return response.data;
  },

  /**
   * Get list of stored files
   */
  async getFiles(): Promise<FileMetadata[]> {
    const response = await apiClient.get("/api/storage/files");
    return response.data;
  },

  /**
   * Delete a file by ID
   */
  async deleteFile(fileId: string): Promise<{ success: boolean }> {
    const response = await apiClient.delete(`/api/storage/files/${fileId}`);
    return response.data;
  },
};

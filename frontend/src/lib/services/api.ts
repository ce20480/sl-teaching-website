export class ApiError extends Error {
  status: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status || 500;
  }
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface UploadResult {
  success: boolean;
  message: string;
  task_id?: string;
  upload_result?: any;
}

export interface EvaluationStatus {
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
  uploadFile: async (
    file: File,
    onProgress?: (progress: number) => void,
    userAddress?: string
  ): Promise<UploadResult> => {
    const formData = new FormData();
    formData.append("file", file);
    if (userAddress) {
      formData.append("user_address", userAddress);
    }

    try {
      // Use XMLHttpRequest for progress tracking
      return await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        // Track upload progress
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable && onProgress) {
            const progress = (event.loaded / event.total) * 100;
            onProgress(progress);
          }
        };

        // Handle response
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const response = JSON.parse(xhr.responseText);
              resolve(response);
            } catch {
              reject(new ApiError("Invalid response format"));
            }
          } else {
            try {
              const error = JSON.parse(xhr.responseText);
              reject(new ApiError(error.message || "Upload failed"));
            } catch {
              reject(new ApiError(`Upload failed with status ${xhr.status}`));
            }
          }
        };

        // Handle network errors
        xhr.onerror = () => {
          reject(new ApiError("Network error during upload"));
        };

        // Send the request
        xhr.open("POST", "/api/storage/upload");
        xhr.send(formData);
      });
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        error instanceof Error ? error.message : "Upload failed"
      );
    }
  },

  // Add new method for checking evaluation status
  checkEvaluationStatus: async (taskId: string): Promise<EvaluationStatus> => {
    try {
      const response = await fetch(`/api/contribution/status/${taskId}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new ApiError(
          errorData.message || "Failed to check status",
          response.status
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError("Failed to check evaluation status");
    }
  },

  // Add new method for getting reward history
  getUserRewards: async (userAddress: string): Promise<any> => {
    try {
      const response = await fetch(`/api/contribution/rewards/${userAddress}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new ApiError(
          errorData.message || "Failed to fetch rewards",
          response.status
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError("Failed to fetch reward history");
    }
  },
};

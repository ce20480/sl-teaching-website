import { apiClient } from "./api-client";
import { AxiosError } from "axios";
import {
  ContributionStatusResponse,
  EvaluationRequest,
  EvaluationResponse,
  RewardRequest,
  RewardResponse,
  UploadRequest,
  UploadResponse,
} from "@/types/contribution";

/**
 * API service for contribution workflow with staged evaluation, upload, and reward phases
 */
export const contributionApi = {
  /**
   * STAGE 1: Evaluate a contribution
   * Checks if the image is suitable (hand detection, blur detection)
   */
  async evaluateContribution(
    file: File,
    landmarks?: number[],
    walletAddress?: string,
    onProgress?: (progress: number) => void
  ): Promise<EvaluationResponse> {
    try {
      const formData = new FormData();
      formData.append("file", file);

      // Add wallet address
      if (walletAddress) {
        formData.append("user_address", walletAddress);
      }

      // Add landmarks if available
      if (landmarks && landmarks.length > 0) {
        formData.append("landmarks", JSON.stringify(landmarks));
      }

      console.log(
        `Evaluating file ${file.name} (${file.size} bytes) with address: ${walletAddress}`
      );

      const response = await apiClient.post("/api/storage/evaluate", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(progress);
            console.log(`Evaluation upload progress: ${progress}%`);
          }
        },
      });

      console.log("Evaluation response:", response.data);
      return response.data;
    } catch (error) {
      console.error("Evaluation error:", error);

      // Return a standardized error response
      return {
        success: false,
        task_id: "",
        message:
          error instanceof AxiosError
            ? error.response?.data?.error || error.message
            : error instanceof Error
            ? error.message
            : "Evaluation failed",
        status: "failed",
        error: String(error),
      };
    }
  },

  /**
   * STAGE 2: Upload an evaluated contribution
   * Uploads the file to permanent storage
   */
  async uploadContribution(
    file: File,
    taskId: string,
    contentHash: string,
    walletAddress: string,
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> {
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("content_hash", contentHash);
      formData.append("user_address", walletAddress);

      console.log(`Uploading file ${file.name} for task ${taskId}`);

      const response = await apiClient.post(
        `/api/storage/upload/${taskId}`,
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
              console.log(`Upload progress: ${progress}%`);
            }
          },
        }
      );

      console.log("Upload response:", response.data);
      return response.data;
    } catch (error) {
      console.error("Upload error:", error);

      // Check if error is specifically about duplicates
      const errorMessage =
        error instanceof AxiosError
          ? error.response?.data?.error || error.message
          : error instanceof Error
          ? error.message
          : "Upload failed";

      const isDuplicate = errorMessage.toLowerCase().includes("duplicate");

      return {
        success: false,
        task_id: taskId,
        message: errorMessage,
        status: isDuplicate ? "rejected" : "failed",
        error: String(error),
        duplicate: isDuplicate,
      };
    }
  },

  /**
   * STAGE 3: Process reward for an uploaded contribution
   * Initiates the reward process with retry logic
   */
  async processReward(
    taskId: string,
    walletAddress: string
  ): Promise<RewardResponse> {
    // Configure retry settings
    const maxRetries = 2;
    const baseDelay = 2000; // Start with 2 seconds
    let retryCount = 0;

    const attemptRewardProcessing = async (): Promise<RewardResponse> => {
      try {
        console.log(
          `Processing rewards for task ${taskId} (attempt ${retryCount + 1}/${
            maxRetries + 1
          })`
        );

        const response = await apiClient.post(
          `/api/storage/reward/${taskId}`,
          {
            user_address: walletAddress,
          },
          {
            // Set a longer timeout for reward processing
            timeout: 30000, // 30 seconds
          }
        );

        console.log("Reward response:", response.data);

        // If there's a transaction hash at the top level, make sure it's also in the reward.details
        if (response.data?.transaction_hash && response.data?.reward) {
          if (!response.data.reward.details) {
            response.data.reward.details = {};
          }
          response.data.reward.details.transaction_hash =
            response.data.transaction_hash;
        }

        return response.data;
      } catch (error) {
        // Check if this is a network error that might benefit from a retry
        const isNetworkError =
          error instanceof AxiosError &&
          (error.code === "ECONNABORTED" ||
            error.code === "ETIMEDOUT" ||
            error.code === "ECONNRESET" ||
            !error.response);

        // Check if this is a server error (5xx)
        const isServerError =
          error instanceof AxiosError &&
          error.response?.status &&
          error.response.status >= 500;

        // Determine if we should retry
        if ((isNetworkError || isServerError) && retryCount < maxRetries) {
          retryCount++;

          // Calculate delay with exponential backoff
          const delay = baseDelay * Math.pow(2, retryCount - 1);
          console.log(
            `Reward processing failed. Retrying in ${
              delay / 1000
            }s (Attempt ${retryCount}/${maxRetries})`
          );

          // Wait and retry
          await new Promise((resolve) => setTimeout(resolve, delay));
          return attemptRewardProcessing();
        }

        // If we've exhausted retries or it's not a retryable error
        console.error("Reward processing error:", error);

        // For connection errors, provide a more user-friendly message
        if (isNetworkError) {
          return {
            success: false,
            task_id: taskId,
            message:
              "The server is busy processing rewards. Your contribution has been received and rewards will be processed in the background.",
            status: "processing",
            reward: {
              status: "processing",
              success: false,
              error: "Reward processing queued",
            },
          };
        }

        // For other errors, return details from the server if available
        return {
          success: false,
          task_id: taskId,
          message:
            error instanceof AxiosError
              ? error.response?.data?.error ||
                error.response?.data?.message ||
                error.message
              : error instanceof Error
              ? error.message
              : "Reward processing failed",
          status: "failed",
          error: String(error),
        };
      }
    };

    // Start the reward process with retry logic
    return attemptRewardProcessing();
  },

  /**
   * Check status of a contribution
   * Optionally specify phase to get focused updates or provide transaction hash for direct blockchain status
   */
  async checkStatus(
    taskId: string,
    phase?: "evaluation" | "upload" | "reward",
    txHash?: string
  ): Promise<ContributionStatusResponse> {
    try {
      let url = `/api/storage/contribution/status/${taskId}`;

      // Build query parameters
      const params = new URLSearchParams();

      // Add phase parameter if specified
      if (phase) {
        params.append("phase", phase);
      }

      // Add transaction hash if provided
      if (txHash) {
        params.append("tx_hash", txHash);
        console.log(`Checking status with transaction hash: ${txHash}`);
      }

      // Add query parameters to URL if any exist
      const queryString = params.toString();
      if (queryString) {
        url += `?${queryString}`;
      }

      const response = await apiClient.get(url);
      return response.data;
    } catch (error) {
      console.error(`Error checking status for task ${taskId}:`, error);

      // Return a standardized error response
      return {
        task_id: taskId,
        status: "failed",
        message:
          error instanceof AxiosError
            ? error.response?.data?.error || error.message
            : error instanceof Error
            ? error.message
            : "Status check failed",
        completed: false,
      };
    }
  },

  /**
   * Set up event source for streaming status updates
   * Returns unsubscribe function
   */
  subscribeToStatusUpdates(
    taskId: string,
    onStatusUpdate: (status: ContributionStatusResponse) => void,
    phase?: "evaluation" | "upload" | "reward",
    txHash?: string
  ): () => void {
    // Build query parameters
    const params = new URLSearchParams();

    // Add phase parameter if specified
    if (phase) {
      params.append("phase", phase);
    }

    // Add transaction hash if provided
    if (txHash) {
      params.append("tx_hash", txHash);
    }

    // Create URL with base and query parameters
    const baseUrl = `${apiClient.defaults.baseURL}/api/storage/contribution/status/stream/${taskId}`;
    const url = params.toString() ? `${baseUrl}?${params.toString()}` : baseUrl;

    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onStatusUpdate(data);

        // Auto-close if completed
        if (data.completed) {
          eventSource.close();
        }
      } catch (e) {
        console.error("Error parsing SSE data:", e);
      }
    };

    eventSource.onerror = (error) => {
      console.error("SSE connection error:", error);
      eventSource.close();
    };

    // Return unsubscribe function
    return () => {
      eventSource.close();
    };
  },
};

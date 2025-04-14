import { apiClient } from "./api-client";
import { AxiosError } from "axios";
import { rewardsApi } from "./rewards-api";

// Import or redefine the TransactionStatus interface
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
  file_id?: string;
  message?: string;
  error?: string;
  duplicate?: boolean;
  details?: {
    error_type?: string;
    file_name?: string;
    file_type?: string;
    user_address?: string;
    [key: string]: string | number | boolean | undefined;
  };
}

interface PhaseDetails {
  [key: string]: string | number | boolean | null;
}

interface EvaluationPhase {
  status: "pending" | "processing" | "completed" | "failed";
  success: boolean;
  time?: number;
  details?: PhaseDetails;
  error?: string;
}

interface EvaluationResponse extends UploadResponse {
  status?:
    | "pending"
    | "processing"
    | "completed"
    | "approved"
    | "rejected"
    | "failed";
  content_hash?: string;
  file_info?: {
    filename: string;
    size: number;
    type: string;
  };
  evaluation?: EvaluationPhase;
}

interface UploadStatusResponse extends UploadResponse {
  status?:
    | "pending"
    | "processing"
    | "completed"
    | "approved"
    | "rejected"
    | "failed";
  upload?: EvaluationPhase;
  storage?: {
    cid?: string;
    bucket?: string;
    duplicate?: boolean;
  };
}

interface RewardResponse extends UploadResponse {
  status?:
    | "pending"
    | "processing"
    | "completed"
    | "approved"
    | "rejected"
    | "failed";
  phases?: {
    evaluation: EvaluationPhase;
    upload: EvaluationPhase;
    reward: EvaluationPhase;
  };
}

interface EvaluationStatus {
  task_id: string;
  status:
    | "pending"
    | "processing"
    | "completed"
    | "approved"
    | "rejected"
    | "failed";
  score?: number;
  message?: string;
  completed?: boolean;
  phases?: {
    evaluation: EvaluationPhase;
    upload: EvaluationPhase;
    reward: EvaluationPhase;
  };
  reward?: {
    xp?: {
      success: boolean;
      amount?: number;
      transaction_hash?: string;
    };
    achievement?: {
      success: boolean;
      token_id?: number;
      transaction_hash?: string;
    };
  };
  lastChecked: string;
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
    try {
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
    } catch (error: Error | AxiosError | unknown) {
      console.error("Upload file error:", error);
      return {
        success: false,
        message:
          error instanceof AxiosError
            ? error.response?.data?.error || error.message
            : error instanceof Error
            ? error.message
            : "Upload failed",
        error: String(error),
      };
    }
  },

  /**
   * LEGACY: Upload a file to storage with wallet address for rewards
   * Use the staged approach (evaluateContribution, uploadContribution, processReward) for better UX
   */
  async uploadContribution(
    file: File,
    onProgress?: (progress: number) => void,
    walletAddress?: string,
    landmarks?: number[]
  ): Promise<UploadResponse> {
    try {
      const formData = new FormData();
      formData.append("file", file);

      // Add wallet address if provided
      if (walletAddress) {
        formData.append("user_address", walletAddress);
      }

      // Add landmarks if provided
      if (landmarks && landmarks.length > 0) {
        formData.append("landmarks", JSON.stringify(landmarks));
      }

      console.log(
        `Uploading file ${file.name} (${file.size} bytes) with address: ${
          walletAddress || "none"
        }`
      );

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
              console.log(`Upload progress: ${progress}%`);
            }
          },
        }
      );

      console.log("Upload contribution response:", response.data);
      return response.data;
    } catch (error: Error | AxiosError | unknown) {
      console.error("Upload contribution error:", error);

      // Check for specific error responses
      if (error instanceof AxiosError && error.response?.data) {
        // Server returned an error response with details
        const errorData = error.response.data;
        console.log("Server error details:", errorData);

        // If this has a duplicate flag or specific message pattern
        if (
          errorData.duplicate ||
          (errorData.error && errorData.error.includes("already been uploaded"))
        ) {
          return {
            success: false,
            error: errorData.error || "This file has already been uploaded",
            duplicate: true,
            message: "File is a duplicate",
          };
        }

        // Return the server's error data with additional client info
        return {
          success: false,
          error: errorData.error || "Server error",
          message: errorData.message || error.message,
          ...errorData, // Preserve any other fields from the server response
        };
      }

      // Generic error case
      return {
        success: false,
        message:
          error instanceof Error ? error.message : "Unknown upload error",
        error: `Upload failed: ${
          error instanceof Error ? error.stack || error.message : String(error)
        }`,
      };
    }
  },

  /**
   * STAGE 1: Evaluate a contribution before uploading
   * Includes retry logic for rate limiting errors
   */
  async evaluateContribution(
    file: File,
    onProgress?: (progress: number) => void,
    walletAddress?: string,
    landmarks?: number[]
  ): Promise<EvaluationResponse> {
    // Configure retry settings
    const maxRetries = 3;
    const baseDelay = 2000; // Start with 2 seconds
    let retryCount = 0;

    // Define retry function
    const attemptEvaluation = async (): Promise<EvaluationResponse> => {
      try {
        const formData = new FormData();
        formData.append("file", file);

        // Add wallet address if provided
        if (walletAddress) {
          formData.append("user_address", walletAddress);
        }

        // Add landmarks if provided
        if (landmarks && landmarks.length > 0) {
          formData.append("landmarks", JSON.stringify(landmarks));
        }

        console.log(
          `Evaluating file ${file.name} (${file.size} bytes) with address: ${
            walletAddress || "none"
          } - Attempt ${retryCount + 1}/${maxRetries + 1}`
        );

        const response = await apiClient.post(
          "/api/storage/evaluate",
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
                console.log(`Evaluation upload progress: ${progress}%`);
              }
            },
          }
        );

        console.log("Evaluation response:", response.data);
        return response.data;
      } catch (error: Error | AxiosError | unknown) {
        // Check for rate limiting (429 Too Many Requests)
        if (error instanceof AxiosError && error.response?.status === 429) {
          retryCount++;
          if (retryCount <= maxRetries) {
            // Calculate delay with exponential backoff
            const delay = baseDelay * Math.pow(2, retryCount - 1);
            console.log(
              `Rate limited for evaluation. Retrying in ${
                delay / 1000
              }s (Attempt ${retryCount}/${maxRetries})`
            );

            // Tell the UI we're waiting for rate limiting to clear
            if (onProgress) {
              onProgress(0); // Reset progress
            }

            // Wait and retry
            await new Promise((resolve) => setTimeout(resolve, delay));
            return attemptEvaluation();
          }
        }

        // Handle other errors or if we've exhausted retries
        console.error("Evaluation error:", error);

        // Check for specific error responses
        if (error instanceof AxiosError && error.response?.data) {
          const errorData = error.response.data;
          console.log("Evaluation error details:", errorData);

          return {
            success: false,
            error: errorData.error || "Evaluation error",
            message: errorData.message || error.message,
            ...errorData,
          };
        }

        // Generic error case
        return {
          success: false,
          message: error instanceof Error ? error.message : "Unknown error",
          error: `Evaluation failed: ${
            error instanceof Error ? error.message : String(error)
          }`,
        };
      }
    };

    // Start the evaluation process with retry logic
    return attemptEvaluation();
  },

  /**
   * STAGE 2: Upload a contribution that has passed evaluation
   * Includes retry logic for rate limiting errors
   */
  async uploadEvaluatedContribution(
    file: File,
    taskId: string,
    contentHash: string,
    onProgress?: (progress: number) => void,
    walletAddress?: string
  ): Promise<UploadStatusResponse> {
    // Configure retry settings
    const maxRetries = 3;
    const baseDelay = 2000; // Start with 2 seconds
    let retryCount = 0;

    // Define retry function
    const attemptUpload = async (): Promise<UploadStatusResponse> => {
      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("content_hash", contentHash);

        // Add wallet address if provided
        if (walletAddress) {
          formData.append("user_address", walletAddress);
        }

        console.log(
          `Uploading evaluated file ${
            file.name
          } for task: ${taskId} - Attempt ${retryCount + 1}/${maxRetries + 1}`
        );

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

        // Check for duplicate indicators in successful response
        if (
          response.data.duplicate ||
          (response.data.error &&
            response.data.error.toLowerCase().includes("duplicate")) ||
          (response.data.message &&
            response.data.message.toLowerCase().includes("duplicate")) ||
          (response.data.status === "rejected" && response.data.duplicate)
        ) {
          console.log("Duplicate file detected in successful response");
          return {
            success: false,
            error: response.data.error || "This file has already been uploaded",
            message:
              response.data.message ||
              "Duplicate file detected. Please try a different image.",
            duplicate: true,
            status: "rejected",
            task_id: taskId,
          };
        }

        return response.data;
      } catch (error: Error | AxiosError | unknown) {
        // Check for rate limiting (429 Too Many Requests)
        if (error instanceof AxiosError && error.response?.status === 429) {
          retryCount++;
          if (retryCount <= maxRetries) {
            // Calculate delay with exponential backoff
            const delay = baseDelay * Math.pow(2, retryCount - 1);
            console.log(
              `Rate limited for upload. Retrying in ${
                delay / 1000
              }s (Attempt ${retryCount}/${maxRetries})`
            );

            // Tell the UI we're waiting for rate limiting to clear
            if (onProgress) {
              onProgress(0); // Reset progress
            }

            // Wait and retry
            await new Promise((resolve) => setTimeout(resolve, delay));
            return attemptUpload();
          }
        }

        console.error("Upload error:", error);

        // Check for specific error responses
        if (error instanceof AxiosError && error.response?.data) {
          const errorData = error.response.data;
          console.log("Upload error details:", errorData);

          // Check for duplicate indicators in error response
          if (
            errorData.duplicate ||
            (errorData.error &&
              errorData.error.toLowerCase().includes("duplicate")) ||
            (errorData.message &&
              errorData.message.toLowerCase().includes("duplicate")) ||
            (errorData.status === "rejected" && errorData.duplicate)
          ) {
            console.log("Duplicate file detected in error response");
            return {
              success: false,
              error: errorData.error || "This file has already been uploaded",
              message:
                errorData.message ||
                "Duplicate file detected. Please try a different image.",
              duplicate: true,
              status: "rejected",
              task_id: taskId,
            };
          }

          return {
            success: false,
            error: errorData.error || "Upload error",
            message: errorData.message || error.message,
            ...errorData,
          };
        }

        // Generic error case
        return {
          success: false,
          message: error instanceof Error ? error.message : "Unknown error",
          error: `Upload failed: ${
            error instanceof Error ? error.message : String(error)
          }`,
        };
      }
    };

    // Start the upload process with retry logic
    return attemptUpload();
  },

  /**
   * STAGE 3: Process rewards for a contribution that has been uploaded
   * This method triggers reward processing in the background and returns immediately
   */
  async processReward(
    taskId: string,
    walletAddress: string
  ): Promise<RewardResponse> {
    try {
      console.log(
        `Processing rewards for task: ${taskId} with address: ${walletAddress}`
      );

      // First check if this is a duplicate file by getting the status
      try {
        const status = await this.checkContributionStatus(taskId);

        // Detect duplicates and reject immediately without calling the backend
        const isDuplicate =
          status.status === "rejected" ||
          status.phases?.upload?.details?.duplicate === true ||
          (status.phases?.upload?.error &&
            status.phases.upload.error.toLowerCase().includes("duplicate")) ||
          (status.message &&
            status.message.toLowerCase().includes("duplicate"));

        if (isDuplicate) {
          console.log(
            `Rejecting reward for duplicate file, task ID: ${taskId}`
          );
          return {
            success: false,
            error: "Duplicate files are not eligible for rewards",
            message:
              "This file appears to be a duplicate. No rewards will be processed.",
            status: "rejected",
            duplicate: true,
            task_id: taskId,
            phases: {
              evaluation: status.phases?.evaluation || {
                status: "completed",
                success: true,
              },
              upload: status.phases?.upload || {
                status: "failed",
                success: false,
                details: { duplicate: true },
                error: "This file has already been uploaded.",
              },
              reward: {
                status: "failed",
                success: false,
                error: "Duplicate files are not eligible for rewards",
                details: { duplicate: true },
              },
            },
          };
        }
      } catch (error) {
        // If we can't check status, continue with the reward request
        console.warn(`Error checking status before rewards: ${error}`);
      }

      // Use a simple JSON payload
      const payload = {
        user_address: walletAddress,
      };

      console.log("Reward request payload:", payload);
      console.log("Reward request URL:", `/api/storage/reward/${taskId}`);

      // Use a shorter timeout since we only need to start the reward process,
      // not wait for it to complete
      const response = await apiClient.post(
        `/api/storage/reward/${taskId}`,
        payload,
        {
          headers: {
            "Content-Type": "application/json",
          },
          timeout: 10000, // 10 seconds timeout - just for initiating the process
        }
      );

      console.log("Reward response:", response.data);

      // If the response contains a transaction hash, start polling for status
      if (response.data?.reward?.xp?.transaction_hash) {
        this.pollTransactionStatus(
          response.data.reward.xp.transaction_hash,
          taskId,
          walletAddress
        );
      }

      return response.data;
    } catch (error: Error | AxiosError | unknown) {
      console.error("Reward processing error:", error);

      // Check if this is a timeout error
      if (error instanceof AxiosError && error.code === "ECONNABORTED") {
        console.log(
          "Request timed out, but reward processing may be continuing in the background"
        );
        // Return a more optimistic response for timeouts
        return {
          success: true,
          message:
            "Reward processing initiated but took longer than expected. Check status updates for confirmation.",
          task_id: taskId,
          status: "processing",
          phases: {
            reward: {
              status: "processing",
              success: false,
              message: "Reward processing started in background",
            } as unknown as EvaluationPhase,
            evaluation: {} as EvaluationPhase,
            upload: {} as EvaluationPhase,
          },
        };
      }

      // Check for specific error responses
      if (error instanceof AxiosError && error.response?.data) {
        const errorData = error.response.data;
        console.log("Reward error details:", errorData);
        console.log("Response status:", error.response.status);

        // Check for duplicate indicators in error response
        if (
          errorData.duplicate ||
          (errorData.error &&
            errorData.error.toLowerCase().includes("duplicate")) ||
          (errorData.message &&
            errorData.message.toLowerCase().includes("duplicate")) ||
          errorData.status === "rejected"
        ) {
          console.log("Duplicate file detected in reward response");
          return {
            success: false,
            error: errorData.error || "This file has already been uploaded",
            message:
              errorData.message ||
              "Duplicate file detected. Please try a different image.",
            duplicate: true,
            status: "rejected",
            task_id: taskId,
            phases: {
              reward: {
                status: "failed",
                success: false,
                error: "Duplicate files are not eligible for rewards",
                details: { duplicate: true },
              },
              // Add empty evaluation and upload phases to satisfy the type
              evaluation: {} as EvaluationPhase,
              upload: {} as EvaluationPhase,
            },
          };
        }

        return {
          success: false,
          error: errorData.error || "Reward processing error",
          message: errorData.message || error.message,
          ...errorData,
        };
      }

      // Generic error case
      return {
        success: false,
        message: error instanceof Error ? error.message : "Unknown error",
        error: `Reward processing failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      };
    }
  },

  /**
   * Poll for transaction status updates with exponential backoff
   * @param txHash The transaction hash to check
   * @param taskId Optional task ID for logging
   * @param walletAddress Optional wallet address for logging
   */
  async pollTransactionStatus(
    txHash: string,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _taskId?: string,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _walletAddress?: string
  ): Promise<void> {
    const maxAttempts = 12; // Maximum polling attempts
    const initialDelay = 15000; // Start with 15 seconds
    let attempt = 0;

    const checkStatus = async () => {
      try {
        // Stop if we've reached max attempts
        if (attempt >= maxAttempts) {
          console.log(
            `Stopped polling for transaction ${txHash} after ${maxAttempts} attempts`
          );
          return;
        }

        attempt++;
        console.log(
          `Checking transaction status (attempt ${attempt}/${maxAttempts}): ${txHash}`
        );

        // Use the rewards API to check status
        const status = await rewardsApi.checkTransactionStatus(txHash);
        console.log(`Transaction ${txHash} status:`, status);

        // If completed (success or failure), stop polling
        if (status.status === "success" || status.status === "failed") {
          console.log(
            `Transaction ${txHash} completed with status: ${status.status}`
          );

          // Optionally update UI or trigger other events here
          if (this.transactionStatusListeners[txHash]) {
            this.transactionStatusListeners[txHash].forEach((listener) =>
              listener(status)
            );
          }

          return;
        }

        // Calculate delay with exponential backoff, capped at 2 minutes
        const delay = Math.min(
          initialDelay * Math.pow(1.5, attempt - 1),
          120000
        );
        console.log(
          `Transaction ${txHash} still pending. Next check in ${
            delay / 1000
          } seconds`
        );

        // Schedule next check
        setTimeout(checkStatus, delay);
      } catch (error) {
        console.error(
          `Error checking transaction status for ${txHash}:`,
          error
        );

        // If there was an error, still retry but with exponential backoff
        const delay = Math.min(initialDelay * Math.pow(2, attempt - 1), 120000);
        console.log(
          `Error on attempt ${attempt}. Retrying in ${delay / 1000} seconds`
        );

        setTimeout(checkStatus, delay);
      }
    };

    // Start the first check after initialDelay
    setTimeout(checkStatus, initialDelay);
  },

  // Storage for transaction status update listeners
  transactionStatusListeners: {} as Record<
    string,
    Array<(status: TransactionStatus) => void>
  >,

  /**
   * Subscribe to transaction status updates
   * @param txHash The transaction hash to subscribe to
   * @param callback Function to call with status updates
   * @returns Unsubscribe function
   */
  subscribeToTransactionUpdates(
    txHash: string,
    callback: (status: TransactionStatus) => void
  ): () => void {
    if (!this.transactionStatusListeners[txHash]) {
      this.transactionStatusListeners[txHash] = [];
    }

    this.transactionStatusListeners[txHash].push(callback);

    return () => {
      this.transactionStatusListeners[txHash] = this.transactionStatusListeners[
        txHash
      ].filter((listener) => listener !== callback);
    };
  },

  /**
   * Check the contribution status of an uploaded file
   * Includes retry logic for rate limiting errors
   */
  async checkContributionStatus(taskId: string): Promise<EvaluationStatus> {
    // Configure retry settings
    const maxRetries = 2; // Fewer retries since this is called frequently
    const baseDelay = 1000; // Start with 1 second
    let retryCount = 0;

    // Define retry function
    const attemptStatusCheck = async (): Promise<EvaluationStatus> => {
      try {
        console.log(
          `Checking evaluation status for task: ${taskId} - Attempt ${
            retryCount + 1
          }/${maxRetries + 1}`
        );

        // First try the dedicated evaluation endpoint
        let response;
        try {
          response = await apiClient.get(
            `/api/storage/contribution/status/${taskId}`
          );
          console.log("Status response from primary endpoint:", response.data);
        } catch (error) {
          // Check if this was a rate limiting error
          if (error instanceof AxiosError && error.response?.status === 429) {
            retryCount++;
            if (retryCount <= maxRetries) {
              // Calculate delay with exponential backoff
              const delay = baseDelay * Math.pow(2, retryCount - 1);
              console.log(
                `Rate limited for status check. Retrying in ${
                  delay / 1000
                }s (Attempt ${retryCount}/${maxRetries})`
              );

              // Wait and retry
              await new Promise((resolve) => setTimeout(resolve, delay));
              return attemptStatusCheck();
            }
          }

          console.log(
            "Primary status endpoint failed, trying alternative path..."
          );
          console.error("Primary endpoint error:", error);
        }

        if (!response) {
          throw new Error("Empty response received from status endpoint");
        }

        // If the response doesn't have a task_id, add it
        if (!response.data) {
          console.error("Empty response received from status endpoint");
          throw new Error("Empty response from server");
        }

        if (!response.data.task_id) {
          console.log("Adding task_id to response data");
          response.data.task_id = taskId;
        }

        // Add timestamps for UI display if missing

        if (!response.data.lastChecked) {
          response.data.lastChecked = new Date().toISOString();
        }

        return response.data;
      } catch (error: Error | AxiosError | unknown) {
        console.error(`Error checking status for task ${taskId}:`, error);

        // Create a minimal status object for failed checks
        const errorStatus: EvaluationStatus = {
          task_id: taskId,
          status: "failed",
          message:
            error instanceof AxiosError
              ? error.response?.data?.error || error.message
              : error instanceof Error
              ? error.message
              : "Failed to check evaluation status",
          completed: false,
          lastChecked: new Date().toISOString(),
        };

        throw errorStatus;
      }
    };

    // Start the status check with retry logic
    return attemptStatusCheck();
  },

  /**
   * Subscribe to real-time status updates for a contribution using Server-Sent Events
   *
   * @param taskId The task ID to subscribe to
   * @param onStatusUpdate Callback function that receives status updates
   * @returns An unsubscribe function to stop listening for events
   */
  subscribeToStatusUpdates(
    taskId: string,
    onStatusUpdate: (status: EvaluationStatus) => void
  ): () => void {
    console.log(`Subscribing to status updates for task: ${taskId}`);

    const eventSource = new EventSource(
      `${apiClient.defaults.baseURL}/api/storage/evaluation/status/stream/${taskId}`
    );

    eventSource.onmessage = (event) => {
      try {
        const status = JSON.parse(event.data);
        console.log(`SSE status update for task ${taskId}:`, status);

        // Add timestamps for UI display if missing
        if (!status.lastChecked) {
          status.lastChecked = new Date().toISOString();
        }

        // Pass the updated status to the callback
        onStatusUpdate(status);

        // If we've reached a completed state, close the connection
        if (status.completed) {
          console.log(`Task ${taskId} completed, closing SSE connection`);
          eventSource.close();
        }
      } catch (error) {
        console.error(`Error parsing SSE data:`, error);
      }
    };

    eventSource.onerror = (error) => {
      console.error(`SSE connection error for task ${taskId}:`, error);

      // Retry logic is handled automatically by the browser
      // We just need to handle connection errors

      // If the connection is in a failed state, close it
      if (eventSource.readyState === EventSource.CLOSED) {
        console.log(`SSE connection closed for task ${taskId}`);
        eventSource.close();
      }
    };

    // Return an unsubscribe function
    return () => {
      console.log(`Unsubscribing from status updates for task ${taskId}`);
      eventSource.close();
    };
  },

  /**
   * Get list of stored files
   */
  async getFiles(): Promise<FileMetadata[]> {
    try {
      const response = await apiClient.get("/api/storage/files");
      return response.data.files || [];
    } catch (error: Error | AxiosError | unknown) {
      console.error("Error fetching files:", error);
      return [];
    }
  },

  /**
   * Delete a file by ID
   */
  async deleteFile(fileId: string): Promise<{ success: boolean }> {
    try {
      await apiClient.delete(`/api/storage/files/${fileId}`);
      return { success: true };
    } catch (error: Error | AxiosError | unknown) {
      console.error(`Error deleting file ${fileId}:`, error);
      return { success: false };
    }
  },
};

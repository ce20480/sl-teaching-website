export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export const storageApi = {
  uploadFile: async (
    file: File,
    onProgress?: (progress: number) => void,
    userAddress?: string
  ) => {
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
      throw new ApiError(error instanceof Error ? error.message : "Upload failed");
    }
  },

  checkEvaluationStatus: async (taskId: string) => {
    try {
      const response = await fetch(`/api/storage/evaluation/${taskId}`);
      if (!response.ok) {
        const error = await response.json();
        throw new ApiError(error.message || "Failed to check evaluation status");
      }
      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError("Network error while checking evaluation status");
    }
  }
}; 
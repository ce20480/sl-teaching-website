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
  file: FileMetadata;
  success: boolean;
}

export const storageApi = {
  /**
   * Upload a file to storage
   */
  async uploadFile(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

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

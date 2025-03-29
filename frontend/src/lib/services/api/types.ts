/**
 * API error type for handling error responses
 */
export class ApiError extends Error {
  statusCode: number;

  constructor(message: string, statusCode: number = 500) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
  }
}

/**
 * Generic API response with success flag
 */
export interface ApiResponse {
  success: boolean;
  message?: string;
}

// Add other common types here

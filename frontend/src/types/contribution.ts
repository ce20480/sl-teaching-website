// Types for the contribution stages

// Common status types
export type StatusType =
  | "pending"
  | "processing"
  | "completed"
  | "approved"
  | "rejected"
  | "failed";
export type PhaseStatusType = "pending" | "processing" | "completed" | "failed";

// Evaluation Stage
export interface EvaluationRequest {
  file: File;
  user_address: string;
  landmarks?: number[];
}

export interface EvaluationResponse {
  success: boolean;
  task_id: string;
  message: string;
  status: StatusType;
  content_hash?: string;
  error?: string;
  evaluation?: {
    status: PhaseStatusType;
    success: boolean;
    details?: {
      blur_score?: number;
      landmark_score?: number;
      detected_letter?: string;
    };
  };
}

// Upload Stage
export interface UploadRequest {
  file: File;
  task_id: string;
  content_hash: string;
  user_address: string;
}

export interface UploadResponse {
  success: boolean;
  task_id: string;
  message: string;
  status: StatusType;
  error?: string;
  duplicate?: boolean;
  upload?: {
    status: PhaseStatusType;
    success: boolean;
    details?: {
      cid?: string;
      bucket?: string;
      duplicate?: boolean;
    };
    error?: string;
  };
}

// Reward Stage
export interface RewardRequest {
  task_id: string;
  user_address: string;
}

export interface RewardResponse {
  success: boolean;
  task_id: string;
  message: string;
  status: StatusType;
  error?: string;
  transaction_hash?: string;
  is_rate_limited?: boolean;
  will_retry?: boolean;
  reward?: {
    status: PhaseStatusType;
    success: boolean;
    is_rate_limited?: boolean;
    will_retry?: boolean;
    details?: {
      amount?: number;
      transaction_hash?: string;
      is_rate_limited?: boolean;
    };
    error?: string;
  };
}

// Status check response - minimal for specific phase
export interface ContributionStatusResponse {
  task_id: string;
  status: StatusType;
  message: string;
  completed: boolean;
  phase_updated?: "evaluation" | "upload" | "reward";
  transaction_hash?: string;
  is_rate_limited?: boolean;
  will_retry?: boolean;

  // For backward compatibility with older response format
  phases?: {
    evaluation?: {
      status: PhaseStatusType;
      success: boolean;
      details?: {
        blur_score?: number;
        landmark_score?: number;
        detected_letter?: string;
        [key: string]: unknown;
      };
      error?: string;
    };
    upload?: {
      status: PhaseStatusType;
      success: boolean;
      details?: {
        cid?: string;
        bucket?: string;
        duplicate?: boolean;
        [key: string]: unknown;
      };
      error?: string;
    };
    reward?: {
      status: PhaseStatusType;
      success: boolean;
      details?: {
        amount?: number;
        transaction_hash?: string;
        block_number?: number;
        timestamp?: number;
        [key: string]: unknown;
      };
      error?: string;
      transaction_hash?: string;
      is_rate_limited?: boolean;
      will_retry?: boolean;
    };
  };

  // Only include relevant phase data based on phase_updated
  evaluation?: {
    status: PhaseStatusType;
    success: boolean;
    details?: {
      blur_score?: number;
      landmark_score?: number;
      detected_letter?: string;
    };
    error?: string;
  };

  upload?: {
    status: PhaseStatusType;
    success: boolean;
    details?: {
      cid?: string;
      bucket?: string;
      duplicate?: boolean;
    };
    error?: string;
  };

  reward?: {
    status: PhaseStatusType;
    success: boolean;
    is_rate_limited?: boolean;
    will_retry?: boolean;
    details?: {
      amount?: number;
      transaction_hash?: string;
      block_number?: number;
      timestamp?: number;
      is_rate_limited?: boolean;
    };
    error?: string;
  };
}

// Contribution tracker for managing the UI state
export interface ContributionState {
  taskId: string;
  fileName: string;
  status: StatusType;
  message: string;
  currentPhase: "evaluation" | "upload" | "reward" | "completed";
  completed: boolean;
  uploadTime: number;
  contentHash?: string;

  evaluation: {
    status: PhaseStatusType;
    success: boolean;
    details?: Record<string, unknown>;
    error?: string;
  };

  upload: {
    status: PhaseStatusType;
    success: boolean;
    details?: Record<string, unknown>;
    error?: string;
  };

  reward: {
    status: PhaseStatusType;
    success: boolean;
    details?: Record<string, unknown>;
    error?: string;
    transactionHash?: string;
    isRateLimited?: boolean;
    willRetry?: boolean;
  };

  lilypadJobId?: string;
  lilypadStatus?: "pending" | "processing" | "completed" | "failed" | "error";
}

export interface LilypadEvaluationResponse extends EvaluationResponse {
  job_id?: string; // Lilypad job ID for status tracking
  lilypad_status?: "pending" | "processing" | "completed" | "failed";
}

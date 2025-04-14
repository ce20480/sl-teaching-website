import { useState, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileUpload } from "@/components/features/upload/FileUpload";
import { HandDetectionPrevalidator } from "@/components/features/upload/HandDetectionPrevalidator";
import { storageApi } from "@/lib/services/api";
import { toast } from "sonner";
import { Progress } from "@/components/ui/progress";
import { useAccount } from "wagmi";
import { WalletConnect } from "@/components/features/wallet/WalletConnect";
import {
  Upload,
  Wallet,
  Loader2,
  FileType,
  Brain,
  Trophy,
  Settings,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

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
}

// Add this interface for tracking multiple contributions
interface ContributionTracker {
  taskId: string;
  fileName: string;
  status:
    | "pending"
    | "processing"
    | "completed"
    | "approved"
    | "rejected"
    | "failed";
  evaluationStatus: EvaluationStatus | null;
  uploadTime: number;
}

// Helper to get badge color based on status
const getStatusBadgeColor = (status: string) => {
  switch (status) {
    case "approved":
      return "bg-green-100 text-green-800";
    case "rejected":
      return "bg-red-100 text-red-800";
    case "failed":
      return "bg-red-100 text-red-800";
    case "processing":
      return "bg-blue-100 text-blue-800";
    case "pending":
      return "bg-gray-100 text-gray-800";
    case "completed":
      return "bg-green-100 text-green-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

export default function Contribute() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validatingFile, setValidatingFile] = useState(false);
  const [handLandmarks, setHandLandmarks] = useState<number[] | undefined>(
    undefined
  );
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [evaluationStatus, setEvaluationStatus] =
    useState<EvaluationStatus | null>(null);
  const [statusCheckErrors, setStatusCheckErrors] = useState(0);
  const [isPolling, setIsPolling] = useState(false);
  const { address, isConnected } = useAccount();

  // Track multiple contributions
  const [contributions, setContributions] = useState<ContributionTracker[]>([]);
  const [selectedContribution, setSelectedContribution] = useState<
    string | null
  >(null);

  // Add state to track reward polling
  const [rewardPollingTaskId, setRewardPollingTaskId] = useState<string | null>(
    null
  );
  const [rewardPollingInterval, setRewardPollingInterval] =
    useState<NodeJS.Timeout | null>(null);

  // Handle file selection
  const handleFileSelect = (file: File) => {
    // Verify that the file is an image before proceeding
    if (
      !file.type.startsWith("image/") &&
      !file.type.endsWith(".png") &&
      !file.type.endsWith(".jpg") &&
      !file.type.endsWith(".jpeg")
    ) {
      toast.error("Only image files are supported");
      return;
    }

    setSelectedFile(file);
    setValidatingFile(true);

    // Reset previous status for new uploads
    setTaskId(null);
    setEvaluationStatus(null);
    setStatusCheckErrors(0);
    setHandLandmarks(undefined);
  };

  // Handle validation result
  const handleValidationResult = (isValid: boolean, landmarks?: number[]) => {
    setValidatingFile(false);

    if (isValid && landmarks) {
      setHandLandmarks(landmarks);
      toast.success("Hand detected! Ready to upload.");
    } else {
      // If not valid, we'll keep the file selected but won't upload
      toast.error("Please try a different image with a clearly visible hand.");
    }
  };

  // Cancel validation
  const handleCancelValidation = () => {
    setValidatingFile(false);
    setSelectedFile(null);
  };

  // Handle file upload with new staged approach
  const handleUpload = async () => {
    if (!selectedFile || !address || !handLandmarks) {
      toast.error("Please select a valid file and connect your wallet");
      return;
    }

    try {
      // --- STAGE 1: EVALUATION ---
      setIsUploading(true);
      setUploadProgress(0);
      console.log("Stage 1: Evaluating file:", selectedFile.name);

      // First, evaluate the contribution
      const evaluationResult = await storageApi.evaluateContribution(
        selectedFile,
        (progress) => {
          setUploadProgress(progress);
        },
        address,
        handLandmarks
      );

      if (!evaluationResult.success) {
        console.error("Evaluation failed:", evaluationResult);
        toast.error(
          evaluationResult.message || "Evaluation failed. Please try again."
        );
        setIsUploading(false);
        return;
      }

      console.log("Evaluation result:", evaluationResult);

      // Get task ID for tracking
      const taskId = evaluationResult.task_id;
      if (!taskId) {
        console.error("No task ID in evaluation response");
        toast.error("Failed to create evaluation task");
        setIsUploading(false);
        return;
      }

      // Create a default evaluation status while waiting for next phase
      const initialStatus: EvaluationStatus = {
        task_id: taskId,
        status: evaluationResult.status || "processing",
        message: "Your contribution is being processed...",
        completed: false,
        phases: {
          evaluation: evaluationResult.evaluation || {
            status: "completed",
            success: true,
          },
          upload: { status: "pending", success: false },
          reward: { status: "pending", success: false },
        },
      };

      setTaskId(taskId);
      setEvaluationStatus(initialStatus);

      // Add to contributions history
      const newContribution: ContributionTracker = {
        taskId: taskId,
        fileName: selectedFile.name,
        status: initialStatus.status,
        evaluationStatus: initialStatus,
        uploadTime: Date.now(),
      };

      setContributions((prev) => [newContribution, ...prev]);

      // Show evaluation success message
      toast.success("Image evaluated successfully! Starting upload...");

      // --- STAGE 2: UPLOAD ---
      console.log("Stage 2: Uploading file:", selectedFile.name);

      // Upload the file with the original content hash
      const uploadResult = await storageApi.uploadEvaluatedContribution(
        selectedFile,
        taskId,
        evaluationResult.content_hash || "",
        (progress) => {
          setUploadProgress(progress);
        },
        address
      );

      // Check for upload failures, especially duplicates
      if (!uploadResult.success) {
        console.error("Upload failed:", uploadResult);

        // Handle duplicate file case
        if (
          uploadResult.duplicate ||
          (uploadResult.error && uploadResult.error.includes("duplicate")) ||
          (uploadResult.message &&
            uploadResult.message.includes("duplicate")) ||
          uploadResult.status === "rejected"
        ) {
          // Create a rejected status for duplicates
          const duplicateStatus: EvaluationStatus = {
            task_id: taskId,
            status: "rejected",
            message: "Duplicate file detected. Please try a different image.",
            completed: true,
            phases: {
              evaluation: initialStatus.phases?.evaluation || {
                status: "completed",
                success: true,
              },
              upload: {
                status: "failed",
                success: false,
                details: { duplicate: true },
                error: "This file has already been uploaded.",
              },
              reward: {
                status: "failed",
                success: false,
                error: "Duplicate files are not eligible for rewards",
              },
            },
          };

          setEvaluationStatus(duplicateStatus);

          // Update contribution in list
          setContributions((prev) =>
            prev.map((contrib) =>
              contrib.taskId === taskId
                ? {
                    ...contrib,
                    status: "rejected",
                    evaluationStatus: duplicateStatus,
                  }
                : contrib
            )
          );

          // Show an informative toast
          toast.error(
            "This file appears to be a duplicate. Please try a different image."
          );
          setIsUploading(false);
          return; // Exit early - don't process rewards for duplicates
        }

        // Handle other upload failures
        toast.error(
          uploadResult.message || "Failed to upload the file. Please try again."
        );
        setIsUploading(false);
        return;
      }

      // Also check if this is a duplicate but still reported success
      if (
        uploadResult.success &&
        (uploadResult.storage?.duplicate ||
          (uploadResult.message && uploadResult.message.includes("duplicate")))
      ) {
        console.log(
          "Upload was reported as successful but marked as duplicate"
        );

        const duplicateStatus: EvaluationStatus = {
          task_id: taskId,
          status: "rejected",
          message: "Duplicate file detected. Please try a different image.",
          completed: true,
          phases: {
            evaluation: initialStatus.phases?.evaluation || {
              status: "completed",
              success: true,
            },
            upload: {
              status: "failed",
              success: false,
              details: { duplicate: true },
              error: "This file has already been uploaded.",
            },
            reward: {
              status: "failed",
              success: false,
              error: "Duplicate files are not eligible for rewards",
            },
          },
        };

        setEvaluationStatus(duplicateStatus);

        // Update contribution in list
        setContributions((prev) =>
          prev.map((contrib) =>
            contrib.taskId === taskId
              ? {
                  ...contrib,
                  status: "rejected",
                  evaluationStatus: duplicateStatus,
                }
              : contrib
          )
        );

        // Show an informative toast
        toast.error(
          "This file appears to be a duplicate. Please try a different image."
        );
        setIsUploading(false);
        return; // Exit early - don't process rewards for duplicates
      }

      // Update status after upload phase
      const uploadStatus: EvaluationStatus = {
        ...initialStatus,
        status: uploadResult.status || "approved",
        phases: {
          evaluation: initialStatus.phases?.evaluation || {
            status: "completed",
            success: true,
          },
          upload: uploadResult.upload || { status: "completed", success: true },
          reward: initialStatus.phases?.reward || {
            status: "pending",
            success: false,
          },
        },
      };

      setEvaluationStatus(uploadStatus);

      // Update contribution in list
      setContributions((prev) =>
        prev.map((contrib) =>
          contrib.taskId === taskId
            ? {
                ...contrib,
                status: uploadStatus.status,
                evaluationStatus: uploadStatus,
              }
            : contrib
        )
      );

      // Show upload success message
      toast.success("File uploaded successfully! Processing rewards...");

      // --- STAGE 3: REWARDS (Background) ---
      console.log("Stage 3: Processing rewards in background");

      // Start reward processing
      const rewardResult = await storageApi.processReward(taskId, address);

      if (!rewardResult.success) {
        console.error("Reward processing failed:", rewardResult);

        // Check if this was rejected because it's a duplicate
        if (
          rewardResult.duplicate ||
          (rewardResult.error && rewardResult.error.includes("duplicate")) ||
          (rewardResult.message &&
            rewardResult.message.includes("duplicate")) ||
          rewardResult.status === "rejected"
        ) {
          // Update with duplicate rejection status
          const duplicateStatus: EvaluationStatus = {
            task_id: taskId,
            status: "rejected",
            message: "Duplicate file detected. Please try a different image.",
            completed: true,
            phases: {
              evaluation: initialStatus.phases?.evaluation || {
                status: "completed",
                success: true,
              },
              upload: {
                status: "failed",
                success: false,
                details: { duplicate: true },
                error: "This file has already been uploaded.",
              },
              reward: {
                status: "failed",
                success: false,
                error: "Duplicate files are not eligible for rewards",
              },
            },
          };

          setEvaluationStatus(duplicateStatus);

          // Update contribution in list
          setContributions((prev) =>
            prev.map((contrib) =>
              contrib.taskId === taskId
                ? {
                    ...contrib,
                    status: "rejected",
                    evaluationStatus: duplicateStatus,
                  }
                : contrib
            )
          );

          toast.error(
            "This file appears to be a duplicate. Please try a different image."
          );
        } else {
          toast.warning(
            "Reward processing has been queued but may take some time to complete."
          );
        }
      } else {
        console.log("Reward processing started:", rewardResult);
        toast.success(
          "Reward processing has started. You can track the status here."
        );
      }

      // Reset the file selection UI for next upload
      setSelectedFile(null);
      setHandLandmarks(undefined);
    } catch (error) {
      console.error("Upload process error:", error);
      toast.error(
        "An error occurred during the upload process. Please try again."
      );
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  // Reset the form when a duplicate is detected
  useEffect(() => {
    if (evaluationStatus?.phases?.upload?.details?.duplicate) {
      // Wait a bit before resetting to ensure the user sees the message
      const timer = setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
      }, 1000);

      return () => clearTimeout(timer);
    }
  }, [evaluationStatus]);

  // Poll for evaluation status - don't poll for reward status here anymore
  useEffect(() => {
    const checkStatus = async () => {
      if (!taskId) return;

      // Don't start general polling if we're specifically polling for rewards
      if (rewardPollingTaskId === taskId) {
        console.log(
          `Skipping general status polling for task ${taskId} - using reward-specific polling`
        );
        setIsPolling(false);
        return;
      }

      setIsPolling(true);

      try {
        // Initial check using the regular endpoint
        const status = await storageApi.checkContributionStatus(taskId);
        setStatusCheckErrors(0); // Reset error counter on success
        setEvaluationStatus(status);

        // Update the contribution in the list
        setContributions((prev) =>
          prev.map((contrib) =>
            contrib.taskId === taskId
              ? {
                  ...contrib,
                  status: status.status,
                  evaluationStatus: status,
                }
              : contrib
          )
        );

        // If already completed, just display the appropriate message
        handleCompletionStatus(status);

        // Check if we should start reward-specific polling instead
        if (
          status.status === "approved" &&
          status.phases?.upload?.success &&
          !status.phases?.reward?.success &&
          !status.reward?.xp?.transaction_hash
        ) {
          console.log(
            "Upload completed successfully, switching to reward-specific polling"
          );
          setIsPolling(false);
          startRewardStatusPolling(taskId);
          return;
        } else {
          setIsPolling(false);
        }
      } catch (error) {
        console.error("Error checking status:", error);
        setStatusCheckErrors((prev) => prev + 1);

        // Only show error toast after multiple failures to avoid overwhelming the user
        if (statusCheckErrors >= 3) {
          toast.error(
            "Failed to check evaluation status. The background task is still processing."
          );

          // After 10 consecutive errors, stop polling
          if (statusCheckErrors >= 10) {
            setIsPolling(false);
          }
        }
      }
    };

    // Helper function to handle completion status
    const handleCompletionStatus = (status: EvaluationStatus) => {
      // Check if this was a duplicate file
      const isDuplicate =
        status.status === "rejected" ||
        status.phases?.upload?.details?.duplicate === true ||
        (status.phases?.upload?.error &&
          status.phases.upload.error.toLowerCase().includes("duplicate")) ||
        (status.message && status.message.toLowerCase().includes("duplicate"));

      if (isDuplicate) {
        toast.error(
          "This file was already uploaded previously. Please try a different image."
        );
        return;
      }

      if (status.status === "approved") {
        if (
          status.phases?.reward?.error &&
          status.phases.reward.error.includes("rate limit")
        ) {
          toast.info(
            "Contribution approved! XP rewards will be processed later due to blockchain rate limits."
          );
        } else if (status.phases?.reward?.success) {
          toast.success("Contribution approved! XP tokens awarded.");
        } else if (status.phases?.reward?.status === "processing") {
          toast.info(
            "Contribution approved! XP rewards are being processed..."
          );
        } else {
          toast.success("Contribution approved! Processing rewards...");
        }
      } else if (status.status === "rejected") {
        // This should be unreachable with the isDuplicate check above
        // but keeping as a fallback
        toast.error(status.message || "Contribution was rejected.");
      } else if (status.status === "processing") {
        toast.info("Contribution is still being processed...");
      } else if (status.status === "failed") {
        toast.error(status.message || "Contribution processing failed.");
      }
    };

    if (taskId) {
      // Initial check
      checkStatus();
    }

    return () => {
      setIsPolling(false);
    };
  }, [taskId, statusCheckErrors, rewardPollingTaskId]);

  // Handle contribution selection for viewing details
  const handleContributionSelect = (taskId: string) => {
    setSelectedContribution(taskId);
    const contribution = contributions.find((c) => c.taskId === taskId);

    if (contribution) {
      setTaskId(taskId);
      setEvaluationStatus(contribution.evaluationStatus);
    }
  };

  // Render the phased evaluation status if available
  const renderPhasedStatus = () => {
    if (!evaluationStatus?.phases) return null;

    // Check if this is a duplicate file
    const isDuplicate = evaluationStatus.phases.upload?.details?.duplicate;

    // If it's a duplicate, show a special warning message
    if (isDuplicate) {
      return (
        <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start gap-3">
            <XCircle className="h-5 w-5 text-amber-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-amber-800">
                Duplicate File Detected
              </h3>
              <p className="text-amber-700 mt-1">
                This image has already been uploaded to our dataset. Please
                submit a different image.
              </p>
              <Button
                variant="outline"
                className="mt-3 text-amber-700 border-amber-300 hover:bg-amber-100"
                onClick={() => {
                  setSelectedFile(null);
                  setTaskId(null);
                  setEvaluationStatus(null);
                }}
              >
                Upload a Different Image
              </Button>
            </div>
          </div>
        </div>
      );
    }

    const phases = [
      {
        number: 1,
        key: "evaluation",
        title: "Evaluation",
        icon: <Brain className="h-4 w-4 text-blue-600" />,
        phase: evaluationStatus.phases.evaluation,
      },
      {
        number: 2,
        key: "upload",
        title: "Storage",
        icon: <Upload className="h-4 w-4 text-blue-600" />,
        phase: evaluationStatus.phases.upload,
      },
      {
        number: 3,
        key: "reward",
        title: "Rewards",
        icon: <Trophy className="h-4 w-4 text-blue-600" />,
        phase: evaluationStatus.phases.reward,
      },
    ];

    return (
      <div className="mt-4 grid grid-cols-3 gap-3">
        {phases.map((p) => (
          <div key={p.key} className="space-y-1">
            <div className="flex gap-2 items-center">
              <div
                className={cn(
                  "flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium",
                  p.phase.success
                    ? "bg-green-100 text-green-800"
                    : p.phase.status === "failed"
                    ? "bg-red-100 text-red-800"
                    : p.phase.status === "completed"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-gray-100 text-gray-800"
                )}
              >
                {p.number}
              </div>
              <h4 className="font-medium flex items-center gap-1">
                {p.title}
                {p.phase.status === "completed" && p.phase.success && (
                  <CheckCircle className="w-4 h-4 text-green-600" />
                )}
                {p.phase.status === "failed" ||
                (p.phase.status === "completed" && !p.phase.success) ? (
                  <XCircle className="w-4 h-4 text-red-600" />
                ) : p.phase.status === "processing" ? (
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                ) : null}
              </h4>
            </div>

            <div
              className={cn(
                "ml-8 text-sm",
                p.phase.success
                  ? "text-green-600"
                  : p.phase.status === "failed" ||
                    (p.phase.status === "completed" && !p.phase.success)
                  ? "text-red-600"
                  : "text-gray-500"
              )}
            >
              {p.phase.success
                ? "Completed successfully"
                : p.phase.status === "failed" ||
                  (p.phase.status === "completed" && !p.phase.success)
                ? p.key === "reward" && p.phase.error
                  ? `Failed: ${p.phase.error}`
                  : p.key === "upload" && p.phase.details?.duplicate
                  ? "Failed: Duplicate file detected"
                  : "Failed"
                : p.phase.status === "processing"
                ? "Processing..."
                : "Pending"}
            </div>

            {/* Show additional details if available */}
            {p.key === "evaluation" && p.phase.details && (
              <div className="mt-1 text-xs text-gray-500">
                {p.phase.details.blur_score !== undefined && (
                  <div>
                    Image quality:{" "}
                    {(Number(p.phase.details.blur_score) * 100).toFixed(0)}%
                  </div>
                )}
                {p.phase.details.landmark_score !== undefined && (
                  <div>
                    Hand detection:{" "}
                    {(Number(p.phase.details.landmark_score) * 100).toFixed(0)}%
                  </div>
                )}
                {p.phase.details.detected_letter && (
                  <div>Detected letter: {p.phase.details.detected_letter}</div>
                )}
              </div>
            )}

            {p.key === "upload" && p.phase.success && p.phase.details && (
              <div className="mt-1 text-xs text-gray-500">
                {p.phase.details.duplicate && (
                  <div className="text-amber-600 font-medium">
                    File already exists in storage
                  </div>
                )}
                {p.phase.details.cid &&
                  typeof p.phase.details.cid === "string" && (
                    <div className="truncate">
                      CID:{" "}
                      <span className="font-mono">
                        {p.phase.details.cid.substring(0, 10)}...
                      </span>
                    </div>
                  )}
              </div>
            )}

            {p.key === "reward" && p.phase.success && p.phase.details?.xp && (
              <div className="mt-1 text-xs text-green-600 font-medium">
                Earned: +
                {typeof p.phase.details.xp === "object"
                  ? (p.phase.details.xp as { amount?: number }).amount || 0
                  : 0}{" "}
                XP
              </div>
            )}

            {p.key === "reward" && p.phase.error && (
              <div className="mt-1 text-xs text-red-600 font-medium">
                Error: {p.phase.error}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  // Add a function to start polling for reward status
  const startRewardStatusPolling = (taskId: string) => {
    // Clear any existing polling
    if (rewardPollingInterval) {
      clearInterval(rewardPollingInterval);
      setRewardPollingInterval(null);
    }

    // Set the task ID we're polling for
    setRewardPollingTaskId(taskId);

    console.log(`Starting reward status polling for task ${taskId}`);

    // Initial polling interval and count to manage adaptive polling
    let pollCount = 0;
    const pollIntervals = [10000, 15000, 30000]; // 10s, 15s, 30s

    // Define the polling function
    const checkRewardStatus = async () => {
      try {
        pollCount++;
        console.log(
          `Checking reward status for task ${taskId} (poll #${pollCount})`
        );
        const status = await storageApi.checkContributionStatus(taskId);
        console.log("Reward status response:", status);

        // Update evaluation status and contribution list
        setEvaluationStatus(status);
        setContributions((prev) =>
          prev.map((contrib) =>
            contrib.taskId === taskId
              ? {
                  ...contrib,
                  status: status.status,
                  evaluationStatus: status,
                }
              : contrib
          )
        );

        // Check if the reward process is complete (success or failed)
        const rewardPhase = status.phases?.reward;
        const rewardStatus = rewardPhase?.status;
        const rewardSuccess = rewardPhase?.success;
        const hasTransactionHash = status.reward?.xp?.transaction_hash;

        console.log(
          `Reward phase status check: status=${rewardStatus}, success=${rewardSuccess}, hasHash=${!!hasTransactionHash}`
        );

        // If reward phase is completed or we have a transaction hash, stop polling
        if (
          rewardStatus === "completed" ||
          rewardSuccess === true ||
          hasTransactionHash
        ) {
          console.log(
            `Reward processing completed for task ${taskId} with status: ${
              rewardSuccess ? "success" : "failed"
            }`
          );

          // Display appropriate message
          if (rewardSuccess || hasTransactionHash) {
            toast.success(
              "Reward transaction completed successfully! XP has been awarded."
            );
          } else if (rewardPhase?.error) {
            toast.warning(`Reward processing failed: ${rewardPhase.error}`);
          }

          // Stop polling
          if (rewardPollingInterval) {
            clearInterval(rewardPollingInterval);
            setRewardPollingInterval(null);
          }
          setRewardPollingTaskId(null);

          console.log("Stopped reward polling interval");
          return;
        }

        // Adjust polling interval based on count
        if (rewardPollingInterval && (pollCount === 3 || pollCount === 8)) {
          // Clear current interval
          clearInterval(rewardPollingInterval);

          // Determine new interval
          const intervalIndex = pollCount === 3 ? 1 : 2; // 15s after 3 polls, 30s after 8 polls
          const newInterval = pollIntervals[intervalIndex];

          console.log(
            `Increasing polling interval to ${
              newInterval / 1000
            } seconds after ${pollCount} polls`
          );

          // Start new interval with updated time
          const newIntervalId = setInterval(checkRewardStatus, newInterval);
          setRewardPollingInterval(newIntervalId);
        }
      } catch (error) {
        console.error(
          `Error checking reward status for task ${taskId}:`,
          error
        );

        // After 5 consecutive errors, stop polling to avoid infinite errors
        setStatusCheckErrors((prev) => {
          if (prev >= 5) {
            console.log(
              "Too many errors checking reward status, stopping poll"
            );
            if (rewardPollingInterval) {
              clearInterval(rewardPollingInterval);
              setRewardPollingInterval(null);
            }
            setRewardPollingTaskId(null);
            return 0;
          }
          return prev + 1;
        });
      }
    };

    // Start initial polling
    const initialInterval = pollIntervals[0]; // Start with 10s
    const initialIntervalId = setInterval(checkRewardStatus, initialInterval);
    setRewardPollingInterval(initialIntervalId);
  };

  // Cleanup reward polling on component unmount
  useEffect(() => {
    return () => {
      if (rewardPollingInterval) {
        console.log(`Cleaning up reward polling interval`);
        clearInterval(rewardPollingInterval);
      }
    };
  }, [rewardPollingInterval]);

  return (
    <div className="container py-8 max-w-4xl mx-auto">
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center">
            <Upload className="h-6 w-6 text-blue-600 mr-2" />
            <div>
              <CardTitle>Upload Sign Language Data</CardTitle>
              <CardDescription>
                Upload images or videos of sign language gestures to help train
                our model
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Upload process step indicator */}
          {taskId && evaluationStatus && (
            <div
              className={`mb-6 p-4 rounded-lg ${
                evaluationStatus.status === "approved"
                  ? "bg-green-50 border border-green-100"
                  : evaluationStatus.status === "rejected" &&
                    evaluationStatus.phases?.upload?.details?.duplicate
                  ? "bg-amber-50 border border-amber-100"
                  : evaluationStatus.status === "rejected"
                  ? "bg-red-50 border border-red-100"
                  : "bg-blue-50 border border-blue-100"
              }`}
            >
              <h3
                className={`text-lg font-semibold ${
                  evaluationStatus.status === "approved"
                    ? "text-green-800"
                    : evaluationStatus.status === "rejected" &&
                      evaluationStatus.phases?.upload?.details?.duplicate
                    ? "text-amber-800"
                    : evaluationStatus.status === "rejected"
                    ? "text-red-800"
                    : "text-blue-800"
                }`}
              >
                {evaluationStatus.status === "approved"
                  ? "Contribution Approved!"
                  : evaluationStatus.status === "rejected" &&
                    evaluationStatus.phases?.upload?.details?.duplicate
                  ? "Duplicate File Detected"
                  : evaluationStatus.status === "rejected"
                  ? "Contribution Rejected"
                  : isPolling && !evaluationStatus.completed
                  ? "Processing Contribution..."
                  : "Contribution Status"}
                {isPolling && !evaluationStatus.completed && (
                  <Loader2 className="ml-2 h-4 w-4 inline animate-spin" />
                )}
              </h3>
              <p className="mt-2 text-sm">
                {evaluationStatus.status === "rejected" &&
                evaluationStatus.phases?.upload?.details?.duplicate
                  ? "This image has already been uploaded to our dataset. Please try a different image."
                  : evaluationStatus.message ||
                    "Your contribution is being processed."}
              </p>
              {renderPhasedStatus()}
            </div>
          )}

          {/* Connect wallet first */}
          {!isConnected ? (
            <div className="text-center py-8">
              <Wallet className="h-12 w-12 mx-auto text-blue-600 mb-4" />
              <h3 className="text-xl font-semibold mb-2">
                Connect Wallet to Contribute
              </h3>
              <p className="text-gray-600 mb-4">
                You'll need to connect your wallet to earn rewards for
                contributing data.
              </p>
              <WalletConnect />
            </div>
          ) : validatingFile && selectedFile ? (
            // Landmark validation step
            <HandDetectionPrevalidator
              file={selectedFile}
              onValidated={handleValidationResult}
              onCancel={handleCancelValidation}
            />
          ) : (
            <>
              {/* File upload */}
              <FileUpload
                onFileSelect={handleFileSelect}
                onRemove={() => setSelectedFile(null)}
                accept={{
                  "image/*": [".jpg", ".jpeg", ".png"],
                }}
              />

              {/* Upload button */}
              {selectedFile && (
                <div className="flex flex-col gap-2">
                  <div className="flex gap-2 mt-4">
                    <Button
                      onClick={handleUpload}
                      disabled={isUploading || !handLandmarks}
                      className="flex-1"
                    >
                      {isUploading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Uploading... {uploadProgress}%
                        </>
                      ) : (
                        <>
                          <Upload className="mr-2 h-4 w-4" />
                          Upload Contribution
                        </>
                      )}
                    </Button>
                    <Settings className="h-4 w-4" />
                  </div>
                </div>
              )}

              {/* Upload progress */}
              {isUploading && (
                <Progress
                  value={uploadProgress}
                  className="mt-2 h-2"
                  aria-label="Upload progress"
                />
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Contribution history section */}
      {contributions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Contributions</CardTitle>
            <CardDescription>
              Your recent sign language data contributions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-60 overflow-y-auto pr-2">
              {contributions.map((contribution) => (
                <div
                  key={contribution.taskId}
                  className={`p-3 rounded-lg border cursor-pointer transition-all 
                    ${
                      contribution.taskId === selectedContribution
                        ? "bg-blue-50 border-blue-300"
                        : "bg-white border-gray-200 hover:border-blue-200"
                    }`}
                  onClick={() => handleContributionSelect(contribution.taskId)}
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-2">
                      <FileType className="h-4 w-4 text-blue-600" />
                      <span className="font-medium truncate max-w-[180px]">
                        {contribution.fileName}
                      </span>
                    </div>
                    <div className="flex items-center">
                      <span
                        className={`text-xs px-2 py-1 rounded-full ${getStatusBadgeColor(
                          contribution.status
                        )}`}
                      >
                        {contribution.status}
                      </span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {new Date(contribution.uploadTime).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

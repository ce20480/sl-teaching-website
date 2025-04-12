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
import { Progress } from "@/components/ui/progress";
import { useAccount } from "wagmi";
import { WalletConnect } from "@/components/features/wallet/WalletConnect";
import {
  Upload,
  Wallet,
  Loader2,
  FileType,
  CheckCircle,
  XCircle,
  Cloud,
} from "lucide-react";
import { toast } from "sonner";
import {
  ContributionState,
  StatusType,
  PhaseStatusType,
} from "@/types/contribution";
import { contributionApi } from "@/lib/services/api/contribution-api";
import { cn } from "@/lib/utils";
import { useTransactionStatus } from "@/hooks/useTransactionStatus";

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

// Define Lilypad result interface
interface LilypadOutput {
  letter?: string;
  confidence?: number;
  status?: string;
}

interface LilypadResult {
  output?: LilypadOutput;
  message?: string;
  landmarks?: number[];
  status?: string;
}

export default function ContributeV2() {
  // File management state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validatingFile, setValidatingFile] = useState(false);
  const [handLandmarks, setHandLandmarks] = useState<number[] | undefined>(
    undefined
  );

  // Upload process state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);

  // Contribution status state
  const [contributions, setContributions] = useState<ContributionState[]>([]);
  const [selectedContribution, setSelectedContribution] = useState<
    string | null
  >(null);

  // Transaction tracking
  const [transactionHash, setTransactionHash] = useState<string | null>(null);
  const { status: txStatus, isPolling: isPollingTransaction } =
    useTransactionStatus(transactionHash);

  // Wallet connection
  const { address, isConnected } = useAccount();

  // Lilypad evaluation state
  const [isLilypadProcessing, setIsLilypadProcessing] = useState(false);
  const [lilypadResult, setLilypadResult] = useState<LilypadResult | null>(
    null
  );

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

    // Reset previous state for new uploads
    setHandLandmarks(undefined);
  };

  // Handle validation result
  const handleValidationResult = (isValid: boolean, landmarks?: number[]) => {
    setValidatingFile(false);

    if (isValid && landmarks) {
      setHandLandmarks(landmarks);
      toast.success("Hand detected! Ready to upload.");
    } else {
      toast.error("Please try a different image with a clearly visible hand.");
    }
  };

  // Cancel validation
  const handleCancelValidation = () => {
    setValidatingFile(false);
    setSelectedFile(null);
  };

  // Handle transaction status changes
  useEffect(() => {
    if (!txStatus || !transactionHash || !selectedContribution) return;

    console.log(
      `Transaction ${transactionHash.substring(
        0,
        8
      )}... status update: ${txStatus}`
    );

    if (txStatus === "success" || txStatus === "failed") {
      // Update contribution state based on transaction status
      setContributions((prev) => {
        return prev.map((contrib) => {
          if (contrib.taskId !== selectedContribution) return contrib;

          return {
            ...contrib,
            status: txStatus === "success" ? "completed" : "failed",
            currentPhase: txStatus === "success" ? "completed" : "reward",
            reward: {
              ...contrib.reward,
              status: txStatus === "success" ? "completed" : "failed",
              success: txStatus === "success",
              transactionHash,
            },
          };
        });
      });

      // Show notification
      if (txStatus === "success") {
        toast.success(
          `Reward transaction completed! XP has been awarded. TX: ${transactionHash.substring(
            0,
            8
          )}...`
        );
      } else {
        toast.error(
          `Reward transaction failed. TX: ${transactionHash.substring(0, 8)}...`
        );
      }

      // Clear transaction hash to stop polling
      setTransactionHash(null);
    }
  }, [txStatus, transactionHash, selectedContribution]);

  // After the transaction status effect
  // Add a cleanup effect for when the component unmounts
  useEffect(() => {
    return () => {
      // Clear transaction hash to stop any active polling when component unmounts
      setTransactionHash(null);
    };
  }, []);

  // Main contribution workflow handler
  const handleContribution = async () => {
    if (!selectedFile || !address || !handLandmarks) {
      // Provide informative message about what's missing
      if (!selectedFile) {
        toast.error("Please select a file to upload");
      } else if (!address) {
        toast.error("Please connect your wallet to upload");
      } else if (!handLandmarks) {
        toast.error("No hand landmarks detected. Please try another image.");
      }
      return;
    }

    // Pre-upload validation
    if (selectedFile.size > 10 * 1024 * 1024) {
      toast.error("File is too large. Maximum size is 10MB.");
      return;
    }

    try {
      // Set processing state
      setIsProcessing(true);
      setProgressPercent(0);

      // --- STAGE 1: EVALUATION ---
      console.log("Stage 1: Evaluating file");

      // Evaluate the contribution
      const evaluationResult = await contributionApi.evaluateContribution(
        selectedFile,
        handLandmarks,
        address,
        (progress) => setProgressPercent(progress)
      );

      if (!evaluationResult.success) {
        console.error("Evaluation failed:", evaluationResult);
        toast.error(
          evaluationResult.message || "Evaluation failed. Please try again."
        );
        setIsProcessing(false);
        return;
      }

      // Get task ID for tracking
      const taskId = evaluationResult.task_id;
      if (!taskId) {
        console.error("No task ID in evaluation response");
        toast.error("Failed to create evaluation task");
        setIsProcessing(false);
        return;
      }

      // Create initial contribution state
      const newContribution: ContributionState = {
        taskId,
        fileName: selectedFile.name,
        status: evaluationResult.status as StatusType,
        message: evaluationResult.message,
        currentPhase: "evaluation",
        completed: false,
        uploadTime: Date.now(),
        contentHash: evaluationResult.content_hash,

        evaluation: {
          status: (evaluationResult.evaluation?.status ||
            "completed") as PhaseStatusType,
          success: evaluationResult.evaluation?.success || true,
          details: evaluationResult.evaluation?.details,
        },

        upload: {
          status: "pending" as PhaseStatusType,
          success: false,
        },

        reward: {
          status: "pending" as PhaseStatusType,
          success: false,
        },
      };

      // Update state
      setContributions((prev) => [newContribution, ...prev]);
      setSelectedContribution(taskId);

      // Show success message
      toast.success("Image evaluated successfully! Starting upload...");

      // --- STAGE 2: UPLOAD ---
      if (evaluationResult.status === "approved") {
        console.log("Stage 2: Uploading to storage");
        setProgressPercent(0);

        // Upload the evaluated contribution
        const uploadResult = await contributionApi.uploadContribution(
          selectedFile,
          taskId,
          evaluationResult.content_hash || "",
          address,
          (progress) => setProgressPercent(progress)
        );

        // Check for upload failures, especially duplicates
        if (!uploadResult.success) {
          console.error("Upload failed:", uploadResult);

          // Update contribution state
          setContributions((prev) =>
            prev.map((contrib) =>
              contrib.taskId === taskId
                ? {
                    ...contrib,
                    status: uploadResult.status as StatusType,
                    message: uploadResult.message,
                    currentPhase: "upload",
                    upload: {
                      status: "failed" as PhaseStatusType,
                      success: false,
                      error: uploadResult.error,
                      details: { duplicate: uploadResult.duplicate },
                    },
                  }
                : contrib
            )
          );

          // Show error message
          if (uploadResult.duplicate) {
            toast.error(
              "This file appears to be a duplicate. Please try a different image."
            );
          } else {
            toast.error(
              uploadResult.message ||
                "Failed to upload the file. Please try again."
            );
          }

          setIsProcessing(false);
          setSelectedFile(null);
          setHandLandmarks(undefined);
          return;
        }

        // Update contribution state after successful upload
        setContributions((prev) =>
          prev.map((contrib) =>
            contrib.taskId === taskId
              ? {
                  ...contrib,
                  status: uploadResult.status as StatusType,
                  message: uploadResult.message,
                  currentPhase: "upload",
                  upload: {
                    status: (uploadResult.upload?.status ||
                      "completed") as PhaseStatusType,
                    success: uploadResult.upload?.success || true,
                    details: uploadResult.upload?.details,
                  },
                }
              : contrib
          )
        );

        // Show upload success message
        toast.success("File uploaded successfully! Processing rewards...");

        // --- STAGE 3: REWARDS ---
        console.log("Stage 3: Processing rewards");

        // Start reward processing
        const rewardResult = await contributionApi.processReward(
          taskId,
          address
        );

        // Update contribution state
        setContributions((prev) =>
          prev.map((contrib) => {
            if (contrib.taskId === taskId) {
              // Extract transaction hash from both possible locations
              const txHash =
                rewardResult.transaction_hash ||
                rewardResult.reward?.details?.transaction_hash;

              if (txHash) {
                console.log(`Transaction hash received: ${txHash}`);
              }

              return {
                ...contrib,
                status: rewardResult.status as StatusType,
                message: rewardResult.message,
                currentPhase: "reward",
                reward: {
                  status: (rewardResult.reward?.status ||
                    "processing") as PhaseStatusType,
                  success: rewardResult.reward?.success || false,
                  details: rewardResult.reward?.details,
                  transactionHash: txHash,
                  error: rewardResult.reward?.error,
                },
              };
            }
            return contrib;
          })
        );

        // Start blockchain polling for reward transaction
        startRewardStatusPolling(taskId);

        // Success message for reward process start
        toast.success(
          "Reward processing started. You can track the status here."
        );
      }

      // Reset form for next upload
      setSelectedFile(null);
      setHandLandmarks(undefined);
    } catch (error) {
      console.error("Contribution process error:", error);
      toast.error("An error occurred. Please try again.");
    } finally {
      setIsProcessing(false);
      setProgressPercent(0);
    }
  };

  // Start blockchain polling for reward transaction
  const startRewardStatusPolling = async (taskId: string) => {
    console.log(`Starting reward transaction monitoring for task ${taskId}`);

    // Get current contribution
    const currentContribution = contributions.find((c) => c.taskId === taskId);

    // Check if we already have a transaction hash
    if (currentContribution?.reward?.transactionHash) {
      console.log(
        `Using existing transaction hash: ${currentContribution.reward.transactionHash}`
      );
      setTransactionHash(currentContribution.reward.transactionHash);
      return;
    }

    // Make a single call to get the transaction hash
    try {
      console.log(`Fetching transaction hash for task ${taskId}`);
      const status = await contributionApi.checkStatus(taskId, "reward");

      // Extract transaction hash from different possible locations
      const txHash =
        status.transaction_hash ||
        status.reward?.details?.transaction_hash ||
        status.phases?.reward?.transaction_hash;

      if (txHash) {
        console.log(`Transaction hash found: ${txHash}`);

        // Update contribution with hash and latest status
        setContributions((prev) => {
          return prev.map((contrib) => {
            if (contrib.taskId !== taskId) return contrib;

            return {
              ...contrib,
              status: status.status as StatusType,
              message: status.message,
              currentPhase: "reward",
              reward: {
                ...contrib.reward,
                status: (status.reward?.status ||
                  "processing") as PhaseStatusType,
                success: status.reward?.success || false,
                details: status.reward?.details || contrib.reward.details,
                transactionHash: txHash,
                error: status.reward?.error,
              },
            };
          });
        });

        // Start blockchain polling
        setTransactionHash(txHash);
      } else {
        console.log(
          `No transaction hash found for task ${taskId}, will retry later`
        );

        // Schedule another check in 5 seconds
        setTimeout(() => startRewardStatusPolling(taskId), 5000);
      }
    } catch (error) {
      console.error(
        `Error fetching transaction hash for task ${taskId}:`,
        error
      );
      setTimeout(() => startRewardStatusPolling(taskId), 5000);
    }
  };

  // Handle contribution selection
  const handleContributionSelect = (taskId: string) => {
    setSelectedContribution(taskId);
    const contribution = contributions.find((c) => c.taskId === taskId);

    if (contribution) {
      // Start blockchain polling for reward transaction
      startRewardStatusPolling(taskId);
    }
  };

  // Handle Lilypad evaluation
  const handleLilypadEvaluation = async () => {
    if (!selectedFile || !address || !handLandmarks) {
      // Provide informative message about what's missing
      if (!selectedFile) {
        toast.error("Please select a file to upload");
      } else if (!address) {
        toast.error("Please connect your wallet to upload");
      } else if (!handLandmarks) {
        toast.error("No hand landmarks detected. Please try another image.");
      }
      return;
    }

    // Set processing state
    setIsLilypadProcessing(true);
    setProgressPercent(0);

    try {
      // Start Lilypad evaluation
      console.log("Starting Lilypad evaluation");
      const lilypadResponse = await contributionApi.evaluateLilypad(
        selectedFile,
        handLandmarks,
        address,
        (progress) => setProgressPercent(progress)
      );

      if (!lilypadResponse.success || !lilypadResponse.job_id) {
        console.error("Lilypad evaluation failed:", lilypadResponse);
        toast.error(
          lilypadResponse.message ||
            "Lilypad evaluation failed. Please try again."
        );
        setIsLilypadProcessing(false);
        return;
      }

      // Get job ID for polling
      const jobId = lilypadResponse.job_id;

      toast.success(
        `Lilypad evaluation started! Job ID: ${jobId.substring(0, 8)}...`
      );

      // Start polling for job status
      const toastId = toast.loading("Checking Lilypad evaluation status...");

      try {
        // Poll for status updates
        const statusResult = await contributionApi.pollLilypadJobStatus(
          jobId,
          (status) => {
            console.log("Lilypad status update:", status);
            // Update toast with current status
            toast.loading(`Lilypad evaluation ${status.status}...`, {
              id: toastId,
            });
          }
        );

        // Check if evaluation was successful
        if (statusResult.status === "completed" && statusResult.result) {
          toast.success("Lilypad evaluation completed successfully!", {
            id: toastId,
          });
          setLilypadResult(statusResult.result as LilypadResult);

          // Display the result
          const output = (statusResult.result?.output as LilypadOutput) || {};
          if (output.status === "success") {
            toast.success(
              `Detected sign: ${
                output.letter || "Unknown"
              } (confidence: ${Math.round((output.confidence || 0) * 100)}%)`
            );
          } else {
            toast.error("Lilypad evaluation did not return a valid result");
          }
        } else {
          // Handle error case
          toast.error(
            `Lilypad evaluation ${statusResult.status}: ${
              typeof statusResult.result?.message === "string"
                ? statusResult.result.message
                : "Unknown error"
            }`,
            { id: toastId }
          );
        }
      } catch (error) {
        console.error("Error polling Lilypad job status:", error);
        toast.error(
          `Lilypad status polling failed: ${
            error instanceof Error ? error.message : String(error)
          }`,
          { id: toastId }
        );
      }
    } catch (error) {
      console.error("Lilypad evaluation error:", error);
      toast.error(
        `Lilypad evaluation error: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    } finally {
      setIsLilypadProcessing(false);
    }
  };

  // Render contribution status information
  const renderContributionStatus = () => {
    const contribution = contributions.find(
      (c) => c.taskId === selectedContribution
    );
    if (!contribution) return null;

    // Determine color based on status
    const getStatusColor = () => {
      if (
        contribution.status === "approved" ||
        contribution.status === "completed"
      ) {
        return "bg-green-50 border-green-100";
      } else if (contribution.status === "rejected") {
        return contribution.upload.details?.duplicate
          ? "bg-amber-50 border-amber-100"
          : "bg-red-50 border-red-100";
      } else {
        return "bg-blue-50 border-blue-100";
      }
    };

    // Determine title based on status
    const getStatusTitle = () => {
      if (
        contribution.status === "approved" ||
        contribution.status === "completed"
      ) {
        return "Contribution Approved!";
      } else if (contribution.status === "rejected") {
        return contribution.upload.details?.duplicate
          ? "Duplicate File Detected"
          : "Contribution Rejected";
      } else if (contribution.status === "processing") {
        return "Processing Contribution...";
      } else {
        return "Contribution Status";
      }
    };

    // Determine title color based on status
    const getStatusTitleColor = () => {
      if (
        contribution.status === "approved" ||
        contribution.status === "completed"
      ) {
        return "text-green-800";
      } else if (contribution.status === "rejected") {
        return contribution.upload.details?.duplicate
          ? "text-amber-800"
          : "text-red-800";
      } else {
        return "text-blue-800";
      }
    };

    // Show transaction polling status if applicable
    const showTransactionPolling =
      isPollingTransaction &&
      contribution.reward?.transactionHash === transactionHash;

    return (
      <div className={`mb-6 p-4 rounded-lg ${getStatusColor()}`}>
        <h3 className={`text-lg font-semibold ${getStatusTitleColor()}`}>
          {getStatusTitle()}
          {(contribution.currentPhase !== "completed" &&
            contribution.status === "processing") ||
          showTransactionPolling ? (
            <Loader2 className="ml-2 h-4 w-4 inline animate-spin" />
          ) : null}
        </h3>
        <p className="mt-2 text-sm">{contribution.message}</p>

        {/* Render phases */}
        <div className="mt-4 grid grid-cols-3 gap-3">
          {/* Evaluation Phase */}
          <div className="space-y-1">
            <div className="flex gap-2 items-center">
              <div
                className={cn(
                  "flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium",
                  contribution.evaluation.success
                    ? "bg-green-100 text-green-800"
                    : contribution.evaluation.status === "failed"
                    ? "bg-red-100 text-red-800"
                    : contribution.evaluation.status === "completed"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-gray-100 text-gray-800"
                )}
              >
                1
              </div>
              <h4 className="font-medium flex items-center gap-1">
                Evaluation
                {contribution.evaluation.status === "completed" &&
                  contribution.evaluation.success && (
                    <CheckCircle className="w-4 h-4 text-green-600" />
                  )}
                {contribution.evaluation.status === "failed" ||
                (contribution.evaluation.status === "completed" &&
                  !contribution.evaluation.success) ? (
                  <XCircle className="w-4 h-4 text-red-600" />
                ) : contribution.evaluation.status === "processing" ? (
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                ) : null}
              </h4>
            </div>

            <div
              className={cn(
                "ml-8 text-sm",
                contribution.evaluation.success
                  ? "text-green-600"
                  : contribution.evaluation.status === "failed" ||
                    (contribution.evaluation.status === "completed" &&
                      !contribution.evaluation.success)
                  ? "text-red-600"
                  : "text-gray-500"
              )}
            >
              {contribution.evaluation.success
                ? "Completed successfully"
                : contribution.evaluation.status === "failed"
                ? "Failed"
                : contribution.evaluation.status === "processing"
                ? "Processing..."
                : "Pending"}
            </div>

            {/* Show evaluation details if available */}
            {contribution.evaluation.details && (
              <div className="mt-1 text-xs text-gray-500">
                {contribution.evaluation.details.blur_score !== undefined && (
                  <div>
                    Image quality:{" "}
                    {(
                      Number(contribution.evaluation.details.blur_score) * 100
                    ).toFixed(0)}
                    %
                  </div>
                )}
                {contribution.evaluation.details.landmark_score !==
                  undefined && (
                  <div>
                    Hand detection:{" "}
                    {(
                      Number(contribution.evaluation.details.landmark_score) *
                      100
                    ).toFixed(0)}
                    %
                  </div>
                )}
                {contribution.evaluation.details.detected_letter && (
                  <div>
                    Detected letter:{" "}
                    {contribution.evaluation.details.detected_letter as string}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Upload Phase */}
          <div className="space-y-1">
            <div className="flex gap-2 items-center">
              <div
                className={cn(
                  "flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium",
                  contribution.upload.success
                    ? "bg-green-100 text-green-800"
                    : contribution.upload.status === "failed"
                    ? "bg-red-100 text-red-800"
                    : contribution.upload.status === "completed"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-gray-100 text-gray-800"
                )}
              >
                2
              </div>
              <h4 className="font-medium flex items-center gap-1">
                Upload
                {contribution.upload.status === "completed" &&
                  contribution.upload.success && (
                    <CheckCircle className="w-4 h-4 text-green-600" />
                  )}
                {contribution.upload.status === "failed" ||
                (contribution.upload.status === "completed" &&
                  !contribution.upload.success) ? (
                  <XCircle className="w-4 h-4 text-red-600" />
                ) : contribution.upload.status === "processing" ? (
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                ) : null}
              </h4>
            </div>

            <div
              className={cn(
                "ml-8 text-sm",
                contribution.upload.success
                  ? "text-green-600"
                  : contribution.upload.status === "failed" ||
                    (contribution.upload.status === "completed" &&
                      !contribution.upload.success)
                  ? "text-red-600"
                  : "text-gray-500"
              )}
            >
              {contribution.upload.success
                ? "Completed successfully"
                : contribution.upload.status === "failed"
                ? contribution.upload.details?.duplicate
                  ? "Failed: Duplicate file detected"
                  : "Failed"
                : contribution.upload.status === "processing"
                ? "Processing..."
                : "Pending"}
            </div>

            {/* Show upload details if available */}
            {contribution.upload.details && (
              <div className="mt-1 text-xs text-gray-500">
                {contribution.upload.details.duplicate && (
                  <div className="text-amber-600 font-medium">
                    File already exists in storage
                  </div>
                )}
                {contribution.upload.details.cid && (
                  <div className="truncate">
                    CID:{" "}
                    <span className="font-mono">
                      {(contribution.upload.details.cid as string).substring(
                        0,
                        10
                      )}
                      ...
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Reward Phase */}
          <div className="space-y-1">
            <div className="flex gap-2 items-center">
              <div
                className={cn(
                  "flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium",
                  contribution.reward.success
                    ? "bg-green-100 text-green-800"
                    : contribution.reward.status === "failed"
                    ? "bg-red-100 text-red-800"
                    : contribution.reward.status === "completed"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-gray-100 text-gray-800"
                )}
              >
                3
              </div>
              <h4 className="font-medium flex items-center gap-1">
                Rewards
                {contribution.reward.status === "completed" &&
                  contribution.reward.success && (
                    <CheckCircle className="w-4 h-4 text-green-600" />
                  )}
                {contribution.reward.status === "failed" ||
                (contribution.reward.status === "completed" &&
                  !contribution.reward.success) ? (
                  <XCircle className="w-4 h-4 text-red-600" />
                ) : contribution.reward.status === "processing" ? (
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                ) : null}
              </h4>
            </div>

            <div
              className={cn(
                "ml-8 text-sm",
                contribution.reward.success
                  ? "text-green-600"
                  : contribution.reward.status === "failed" ||
                    (contribution.reward.status === "completed" &&
                      !contribution.reward.success)
                  ? "text-red-600"
                  : "text-gray-500"
              )}
            >
              {contribution.reward.success
                ? "Completed successfully"
                : contribution.reward.status === "failed"
                ? contribution.reward.error
                  ? `Failed: ${contribution.reward.error}`
                  : "Failed"
                : contribution.reward.status === "processing"
                ? "Processing..."
                : "Pending"}
            </div>

            {/* Show reward details if available */}
            {contribution.reward.details && (
              <div className="mt-1 text-xs text-green-600 font-medium">
                {contribution.reward.details.amount && (
                  <div>
                    Earned: +{contribution.reward.details.amount as number} XP
                  </div>
                )}
                {contribution.reward.transactionHash && (
                  <div className="truncate">
                    TX:{" "}
                    <a
                      href={`https://calibration.filfox.info/en/message/${contribution.reward.transactionHash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline hover:text-green-800 font-mono"
                    >
                      {(
                        contribution.reward.transactionHash as string
                      ).substring(0, 8)}
                      ...
                    </a>
                  </div>
                )}
              </div>
            )}

            {contribution.reward.error && (
              <div className="mt-1 text-xs text-red-600 font-medium">
                Error: {contribution.reward.error}
              </div>
            )}
          </div>
        </div>

        {showTransactionPolling && (
          <div className="mt-2 text-xs text-blue-600">
            <Loader2 className="h-3 w-3 inline-block mr-1 animate-spin" />
            Monitoring blockchain for transaction confirmation...
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="container py-8 max-w-4xl mx-auto">
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center">
            <Upload className="h-6 w-6 text-blue-600 mr-2" />
            <div>
              <CardTitle>Contribute (v2)</CardTitle>
              <CardDescription>
                Upload images of sign language gestures to help train our model
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Status indicator */}
          {selectedContribution && renderContributionStatus()}

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

              {/* Lilypad Upload Button */}
              <Button
                onClick={handleLilypadEvaluation}
                disabled={
                  isLilypadProcessing ||
                  isProcessing ||
                  !selectedFile ||
                  !handLandmarks ||
                  !isConnected
                }
                variant="outline"
                className="w-full flex gap-2 items-center"
              >
                {isLilypadProcessing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <Cloud className="h-4 w-4" />
                    <span>Lilypad Upload</span>
                  </>
                )}
              </Button>

              {/* Upload button */}
              {selectedFile && (
                <div className="flex flex-col gap-2">
                  <Button
                    onClick={handleContribution}
                    disabled={isProcessing || !handLandmarks}
                    className="mt-4"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing... {progressPercent}%
                      </>
                    ) : (
                      <>
                        <Upload className="mr-2 h-4 w-4" />
                        Upload Contribution
                      </>
                    )}
                  </Button>
                </div>
              )}

              {/* Upload progress */}
              {isProcessing && (
                <Progress
                  value={progressPercent}
                  className="mt-2 h-2"
                  aria-label="Upload progress"
                />
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Contribution history */}
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
                    {new Date(contribution.uploadTime).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Display Lilypad Results if available */}
      {lilypadResult && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle className="text-lg">Lilypad Evaluation Result</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {lilypadResult.output && (
                <div className="flex items-center gap-2">
                  <strong>Detected Sign:</strong>
                  <span className="text-lg font-semibold">
                    {lilypadResult.output.letter || "Unknown"}
                  </span>
                  {lilypadResult.output.status === "success" ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </div>
              )}

              {lilypadResult.output &&
                lilypadResult.output.confidence !== undefined && (
                  <div>
                    <strong>Confidence:</strong>{" "}
                    {Math.round((lilypadResult.output.confidence || 0) * 100)}%
                  </div>
                )}

              {lilypadResult.message && (
                <div className="text-sm text-muted-foreground">
                  {lilypadResult.message}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

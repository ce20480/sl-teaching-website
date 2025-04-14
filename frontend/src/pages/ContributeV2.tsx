import React, { useState, useEffect } from "react";
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
import { ImagePreview } from "@/components/features/upload/ImagePreview";

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
  message?: string;
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

        // Continue with reward phase
        await contributionApi.processReward(taskId, address);

        // Update UI to show we're now in the reward phase
        setContributions((prev) =>
          prev.map((contrib) =>
            contrib.taskId === taskId
              ? ({
                  ...contrib,
                  status: "processing",
                  message: "Processing reward transaction...",
                  currentPhase: "reward",
                  reward: {
                    ...contrib.reward,
                    status: "processing" as PhaseStatusType,
                  },
                } as ContributionState)
              : contrib
          )
        );

        // Update state with reward results and start polling
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

  // Handle the reward phase separately
  const handleRewardPhase = async (taskId: string) => {
    if (!address) return;

    try {
      // Update UI to show we're in the reward phase
      setContributions((prev) =>
        prev.map((contrib) =>
          contrib.taskId === taskId
            ? ({
                ...contrib,
                status: "processing" as StatusType,
                message: "Processing reward transaction...",
                currentPhase: "reward",
                reward: {
                  ...contrib.reward,
                  status: "processing" as PhaseStatusType,
                },
              } as ContributionState)
            : contrib
        )
      );

      // Start the reward process
      const rewardResult = await contributionApi.processReward(taskId, address);
      console.log("Reward process result:", rewardResult);

      // Extract transaction hash if available
      // Using this approach to avoid TypeScript errors
      let txHash: string | undefined;

      try {
        // Access transaction_hash if it exists in the response using type assertion
        interface RewardResponseWithHash {
          transaction_hash?: string;
          reward?: {
            details?: {
              transaction_hash?: string;
            };
          };
        }

        const result = rewardResult as unknown as RewardResponseWithHash;
        if (result.transaction_hash) {
          txHash = result.transaction_hash;
        } else if (result.reward?.details?.transaction_hash) {
          txHash = result.reward.details.transaction_hash;
        }

        if (txHash) {
          console.log(`Transaction hash found in reward response: ${txHash}`);

          // Update contribution with hash
          setContributions((prev) =>
            prev.map((contrib) =>
              contrib.taskId === taskId
                ? ({
                    ...contrib,
                    message:
                      "Reward transaction submitted. Tracking on blockchain...",
                    reward: {
                      ...contrib.reward,
                      transactionHash: txHash,
                    },
                  } as ContributionState)
                : contrib
            )
          );

          // Set transaction hash to trigger the web3 status polling hook
          setTransactionHash(txHash);
        } else {
          // If no hash found, call our polling method to get it
          console.log(
            "No transaction hash in initial response, starting polling"
          );
          startRewardStatusPolling(taskId);
        }
      } catch (err) {
        console.error("Error extracting transaction hash:", err);
        // Fall back to polling method
        startRewardStatusPolling(taskId);
      }

      // Show success message
      toast.success(
        "Reward processing started. You can track the status here."
      );
    } catch (error) {
      console.error("Reward phase error:", error);
      toast.error("Error during reward processing");

      // Update UI with error, but don't mark as completely failed since
      // the contribution itself was successful
      setContributions((prev) =>
        prev.map((contrib) =>
          contrib.taskId === taskId
            ? ({
                ...contrib,
                message: "Reward processing error, but contribution was saved",
                reward: {
                  ...contrib.reward,
                  status: "failed" as PhaseStatusType,
                  success: false,
                  error:
                    error instanceof Error ? error.message : "Unknown error",
                },
              } as ContributionState)
            : contrib
        )
      );
    }
  };

  // Start blockchain polling for reward transaction
  const startRewardStatusPolling = async (taskId: string) => {
    console.log(`Starting reward transaction monitoring for task ${taskId}`);

    // Get current contribution
    const currentContribution = contributions.find((c) => c.taskId === taskId);
    if (!currentContribution) {
      console.log(`No contribution found with task ID: ${taskId}`);

      // If no contribution is found, it might be because it was just created
      // Wait briefly and check again
      setTimeout(() => {
        const retryContribution = contributions.find(
          (c) => c.taskId === taskId
        );
        if (retryContribution) {
          console.log(`Found contribution after retry for task ID: ${taskId}`);
          startRewardStatusPolling(taskId);
        }
      }, 1000);

      return;
    }

    console.log(`Found contribution for ${taskId}:`, {
      status: currentContribution.status,
      phase: currentContribution.currentPhase,
      uploadSuccess: currentContribution.upload?.success,
    });

    // Check if this contribution is eligible for reward polling
    // If it was rejected or failed at the upload phase, we shouldn't poll for rewards
    if (
      currentContribution.status === "rejected" ||
      (currentContribution.upload && !currentContribution.upload.success) ||
      (currentContribution.currentPhase === "upload" &&
        currentContribution.status === "failed")
    ) {
      console.log(
        `Contribution ${taskId} is not eligible for reward polling due to status: ${currentContribution.status}`
      );
      return;
    }

    // Check if we already have a transaction hash
    if (currentContribution?.reward?.transactionHash) {
      console.log(
        `Using existing transaction hash: ${currentContribution.reward.transactionHash}`
      );
      // Set this hash to trigger the web3 polling via useTransactionStatus
      setTransactionHash(currentContribution.reward.transactionHash);
      return;
    }

    // If we don't have a hash yet, make just one call to get it
    try {
      console.log(`Fetching transaction hash for task ${taskId}`);
      const status = await contributionApi.checkStatus(taskId);
      console.log(`Status response for task ${taskId}:`, status);

      // Try to extract the transaction hash from all possible locations in the response
      let txHash: string | undefined;

      // Check all possible locations for the transaction hash
      if (typeof status === "object" && status !== null) {
        // Direct properties
        if (
          "transaction_hash" in status &&
          typeof status.transaction_hash === "string"
        ) {
          txHash = status.transaction_hash;
        }
        // Check phases.reward
        else if (status.phases?.reward?.details?.transaction_hash) {
          txHash = status.phases.reward.details.transaction_hash;
        }
        // Check reward
        else if (status.reward?.details?.transaction_hash) {
          txHash = status.reward.details.transaction_hash;
        }
      }

      if (txHash) {
        console.log(`Transaction hash found: ${txHash}`);

        // Update contribution with hash and latest status
        setContributions((prev) => {
          return prev.map((contrib) => {
            if (contrib.taskId !== taskId) return contrib;

            return {
              ...contrib,
              status: status.status as StatusType,
              message: status.message || "Reward transaction processing",
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

        // Start blockchain polling via the hook by setting transaction hash
        setTransactionHash(txHash);
      } else {
        // If no transaction hash is found yet, wait a bit and try once more
        console.log(
          `No transaction hash found for task ${taskId}, will retry once more in 5 seconds`
        );
        setTimeout(() => {
          const updatedContribution = contributions.find(
            (c) => c.taskId === taskId
          );
          if (updatedContribution?.reward?.transactionHash) {
            // If we now have a hash, use it
            console.log(
              `Found transaction hash on retry: ${updatedContribution.reward.transactionHash}`
            );
            setTransactionHash(updatedContribution.reward.transactionHash);
          } else {
            console.log(
              `Still no transaction hash found for task ${taskId}, will not retry further`
            );
            // Update the contribution to show that we're waiting
            setContributions((prev) => {
              return prev.map((contrib) => {
                if (contrib.taskId !== taskId) return contrib;
                return {
                  ...contrib,
                  message:
                    "Transaction submitted. Waiting for blockchain confirmation...",
                  reward: {
                    ...contrib.reward,
                    status: "processing" as PhaseStatusType,
                  },
                };
              });
            });
          }
        }, 5000);
      }
    } catch (error) {
      console.error(
        `Error fetching transaction hash for task ${taskId}:`,
        error
      );
    }
  };

  // Handle contribution selection
  const handleContributionSelect = (taskId: string) => {
    setSelectedContribution(taskId);
    const contribution = contributions.find((c) => c.taskId === taskId);

    if (contribution) {
      // Only start reward polling if the contribution is in a valid state
      const isEligibleForRewardPolling =
        contribution.status !== "rejected" &&
        !(contribution.upload && !contribution.upload.success) &&
        !(
          contribution.currentPhase === "upload" &&
          contribution.status === "failed"
        );

      if (
        isEligibleForRewardPolling &&
        (contribution.currentPhase === "reward" ||
          contribution.status === "approved" ||
          contribution.status === "processing")
      ) {
        // Start blockchain polling for reward transaction
        startRewardStatusPolling(taskId);
      } else {
        console.log(
          `Contribution ${taskId} selected but not eligible for reward polling (${contribution.status})`
        );
      }
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
      // Start Lilypad sign language evaluation
      console.log("Starting Lilypad sign language detection evaluation");
      toast.info("Starting sign language detection...");

      // Send the Lilypad sign language evaluation request
      const lilypadResponse = await contributionApi.evaluateLilypad(
        selectedFile,
        handLandmarks,
        address,
        (progress) => setProgressPercent(progress)
      );

      // Check if evaluation failed immediately
      if (!lilypadResponse.success || !lilypadResponse.job_id) {
        console.error(
          "Sign language Lilypad evaluation failed:",
          lilypadResponse
        );
        toast.error(
          lilypadResponse.message ||
            "Sign language evaluation failed. Please try again."
        );
        setIsLilypadProcessing(false);
        return;
      }

      // Get the task and job IDs
      const taskId = lilypadResponse.task_id ?? "";
      const jobId = lilypadResponse.job_id ?? "";

      toast.success("Evaluation job started! Processing your image...");

      // Create initial contribution state immediately after getting the response
      const newContribution: ContributionState = {
        taskId,
        fileName: selectedFile.name,
        status: "processing" as StatusType,
        message: "Processing sign language detection...",
        currentPhase: "evaluation",
        completed: false,
        uploadTime: Date.now(),
        contentHash: lilypadResponse.content_hash ?? "",
        lilypadJobId: jobId,
        lilypadStatus: "processing",

        evaluation: {
          status: "processing" as PhaseStatusType,
          success: true,
          details: lilypadResponse.evaluation?.details || {},
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

      // Update state and select this contribution immediately
      setContributions((prev) => [newContribution, ...prev]);
      setSelectedContribution(taskId);

      // Start polling for Lilypad status updates separately
      // This allows the UI to continue updating while the evaluation is in progress
      const pollLilypadStatus = async () => {
        try {
          // Poll Lilypad status and provide a callback for incremental updates
          const signLangResult = await contributionApi.pollLilypadJobStatus(
            jobId,
            (status) => {
              // Update contribution with latest Lilypad status in real-time
              setContributions((prev) =>
                prev.map((contrib) =>
                  contrib.taskId === taskId
                    ? ({
                        ...contrib,
                        lilypadStatus: status.status,
                        message:
                          status.status === "processing"
                            ? "Processing sign language detection..."
                            : status.status === "completed"
                            ? "Sign language detection completed!"
                            : "Waiting for results...",
                      } as ContributionState)
                    : contrib
                )
              );
            }
          );

          // After Lilypad evaluation completes, update UI with results
          if (signLangResult.status === "completed" && signLangResult.result) {
            const signOutput =
              (signLangResult.result?.output as LilypadOutput) || {};

            // Update contribution with Lilypad results
            setContributions((prev) =>
              prev.map((contrib) =>
                contrib.taskId === taskId
                  ? ({
                      ...contrib,
                      lilypadStatus: "completed",
                      status: "approved" as StatusType,
                      message: "Evaluation completed successfully!",
                      evaluation: {
                        ...contrib.evaluation,
                        status: "completed" as PhaseStatusType,
                        success: true,
                        details: {
                          ...contrib.evaluation.details,
                          detected_letter: signOutput.letter,
                          confidence: signOutput.confidence,
                        },
                      },
                    } as ContributionState)
                  : contrib
              )
            );

            // Store the Lilypad result for display
            setLilypadResult({
              output: signOutput,
              message:
                typeof signLangResult.result === "object" &&
                "message" in signLangResult.result
                  ? String(signLangResult.result.message)
                  : "",
              landmarks: handLandmarks,
              status: "success",
            });

            // Show success message with detected letter
            toast.success(`Detected sign: ${signOutput.letter || "Unknown"}`);

            // Move to upload phase immediately
            handleUploadPhase(
              taskId,
              selectedFile,
              lilypadResponse.content_hash || ""
            );
          }
          // Handle Lilypad error or failure
          else if (
            signLangResult.status === "error" ||
            signLangResult.status === "failed"
          ) {
            const errorMessage =
              signLangResult.error ||
              (signLangResult.result &&
              typeof signLangResult.result === "object" &&
              "output" in signLangResult.result &&
              typeof signLangResult.result.output === "object" &&
              signLangResult.result.output &&
              "message" in signLangResult.result.output
                ? String(signLangResult.result.output.message)
                : "") ||
              "Sign language detection failed";

            // Update contribution with error status
            setContributions((prev) =>
              prev.map((contrib) =>
                contrib.taskId === taskId
                  ? ({
                      ...contrib,
                      lilypadStatus: "failed",
                      status: "failed" as StatusType,
                      message: errorMessage,
                      evaluation: {
                        ...contrib.evaluation,
                        status: "failed" as PhaseStatusType,
                        success: false,
                        error: errorMessage,
                      },
                    } as ContributionState)
                  : contrib
              )
            );

            // Store and display error
            setLilypadResult({
              output: {
                status: "error",
                message: errorMessage,
              } as LilypadOutput,
              message: errorMessage,
              landmarks: handLandmarks,
              status: "error",
            });

            toast.error(`Sign language detection failed: ${errorMessage}`);
          }
        } catch (error) {
          console.error("Error polling Lilypad status:", error);
          toast.error("Failed to get sign language detection results");

          // Update the contribution status to reflect the error
          setContributions((prev) =>
            prev.map((contrib) =>
              contrib.taskId === taskId
                ? ({
                    ...contrib,
                    lilypadStatus: "failed",
                    status: "failed" as StatusType,
                    message:
                      error instanceof Error ? error.message : "Unknown error",
                    evaluation: {
                      ...contrib.evaluation,
                      status: "failed" as PhaseStatusType,
                      success: false,
                      error:
                        error instanceof Error
                          ? error.message
                          : "Unknown error",
                    },
                  } as ContributionState)
                : contrib
            )
          );
        }
      };

      // Start the polling process in the background
      pollLilypadStatus();

      // Clear the file selection form
      setSelectedFile(null);
      setHandLandmarks(undefined);
    } catch (error) {
      console.error("Lilypad evaluation error:", error);
      toast.error(
        `Lilypad evaluation error: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    } finally {
      setIsLilypadProcessing(false);
      setProgressPercent(0);
    }
  };

  // Handle the upload phase separately
  const handleUploadPhase = async (
    taskId: string,
    file: File,
    contentHash: string
  ) => {
    if (!address) return;

    try {
      // Update UI to show we're in the upload phase
      setContributions((prev) =>
        prev.map((contrib) =>
          contrib.taskId === taskId
            ? ({
                ...contrib,
                currentPhase: "upload",
                message: "Uploading to permanent storage...",
                upload: {
                  ...contrib.upload,
                  status: "processing" as PhaseStatusType,
                },
              } as ContributionState)
            : contrib
        )
      );

      // Start the upload process
      const uploadResult = await contributionApi.uploadContribution(
        file,
        taskId,
        contentHash,
        address,
        (progress) => setProgressPercent(progress)
      );

      // Update state with upload results
      if (uploadResult.success) {
        // Update contribution state to reflect successful upload
        setContributions((prev) =>
          prev.map((contrib) =>
            contrib.taskId === taskId
              ? ({
                  ...contrib,
                  status: uploadResult.status as StatusType,
                  message:
                    uploadResult.message || "File uploaded successfully!",
                  currentPhase: "upload",
                  upload: {
                    status: "completed" as PhaseStatusType,
                    success: true,
                    details: uploadResult.upload?.details || {
                      cid: uploadResult.upload?.details?.cid,
                    },
                  },
                } as ContributionState)
              : contrib
          )
        );

        toast.success("File uploaded successfully! Processing rewards...");

        // Move to reward phase immediately
        handleRewardPhase(taskId);
      } else {
        // Handle upload failure
        setContributions((prev) =>
          prev.map((contrib) =>
            contrib.taskId === taskId
              ? ({
                  ...contrib,
                  status: "failed" as StatusType,
                  message: uploadResult.message || "Upload failed",
                  currentPhase: "upload",
                  upload: {
                    status: "failed" as PhaseStatusType,
                    success: false,
                    error: uploadResult.error,
                    details: uploadResult.duplicate
                      ? { duplicate: true }
                      : undefined,
                  },
                } as ContributionState)
              : contrib
          )
        );

        toast.error(uploadResult.message || "Upload failed");
      }
    } catch (error) {
      console.error("Upload phase error:", error);
      toast.error("Error during upload phase");

      // Update UI to reflect upload error
      setContributions((prev) =>
        prev.map((contrib) =>
          contrib.taskId === taskId
            ? ({
                ...contrib,
                status: "failed" as StatusType,
                message: "Upload failed",
                currentPhase: "upload",
                upload: {
                  status: "failed" as PhaseStatusType,
                  success: false,
                  error:
                    error instanceof Error ? error.message : "Unknown error",
                },
              } as ContributionState)
            : contrib
        )
      );
    }
  };

  // Render the contribution status card
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

            <div className="ml-8 text-sm">
              {contribution.evaluation.success
                ? contribution.lilypadStatus === "processing"
                  ? "Evaluating sign language detection..."
                  : "Completed successfully"
                : contribution.evaluation.status === "failed"
                ? "Failed"
                : contribution.evaluation.status === "processing"
                ? "Processing..."
                : "Pending"}

              {contribution.lilypadStatus === "processing" && (
                <div className="mt-1 flex items-center">
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                  <span className="text-xs">Lilypad module running...</span>
                </div>
              )}
            </div>

            {/* Show evaluation details if available */}
            {contribution.evaluation.details && (
              <div className="mt-1 text-xs text-gray-500">
                {contribution.evaluation.details &&
                  "blur_score" in contribution.evaluation.details && (
                    <div>
                      Image quality:{" "}
                      {(
                        Number(contribution.evaluation.details.blur_score) * 100
                      ).toFixed(0)}
                      %
                    </div>
                  )}
                {contribution.evaluation.details &&
                  "landmark_score" in contribution.evaluation.details && (
                    <div>
                      Hand detection:{" "}
                      {(
                        Number(contribution.evaluation.details.landmark_score) *
                        100
                      ).toFixed(0)}
                      %
                    </div>
                  )}
                {contribution.evaluation.details &&
                  "detected_letter" in contribution.evaluation.details && (
                    <div>
                      Detected letter:{" "}
                      {String(contribution.evaluation.details.detected_letter)}
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
                ? typeof contribution.upload.details === "object" &&
                  contribution.upload.details !== null &&
                  "duplicate" in contribution.upload.details &&
                  Boolean(contribution.upload.details.duplicate)
                  ? "Failed: Duplicate file detected"
                  : "Failed"
                : contribution.upload.status === "processing"
                ? "Processing..."
                : "Pending"}
            </div>

            {/* Show upload details if available */}
            {contribution.upload.details && (
              <div className="mt-1 text-xs text-gray-500">
                {contribution.upload.details &&
                  "duplicate" in contribution.upload.details &&
                  Boolean(contribution.upload.details.duplicate) && (
                    <div className="text-amber-600 font-medium">
                      File already exists in storage
                    </div>
                  )}
                {contribution.upload.details &&
                  "cid" in contribution.upload.details &&
                  typeof contribution.upload.details.cid === "string" && (
                    <div>
                      <a
                        href={`http://explorer.akave.ai/address/0x54F26e68C2c60cb81BE26b45D013153d769a2565/?tab=txs`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline flex items-center"
                      >
                        <Cloud className="h-3 w-3 mr-1" />
                        <span>View in storage explorer</span>
                      </a>
                      <div className="text-xs text-gray-500 mt-1 font-mono truncate">
                        CID:{" "}
                        {typeof contribution.upload.details === "object" &&
                        contribution.upload.details !== null &&
                        "cid" in contribution.upload.details &&
                        typeof contribution.upload.details.cid === "string"
                          ? String(contribution.upload.details.cid).substring(
                              0,
                              16
                            ) + "..."
                          : "Processing..."}
                      </div>
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
                {<div>Earned: +100 XP</div>}
              </div>
            )}

            {/* Transaction hash section */}
            {contribution.reward.transactionHash && (
              <div className="mt-1 text-xs">
                <a
                  href={`https://calibration.filfox.info/en/message/${
                    contribution.reward.transactionHash.startsWith("0x")
                      ? (contribution.reward.transactionHash as string)
                      : `0x${contribution.reward.transactionHash as string}`
                  }`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline flex items-center"
                >
                  <FileType className="h-3 w-3 mr-1" />
                  <span>View transaction in blockchain explorer</span>
                </a>
                <div className="text-xs text-gray-500 mt-1 font-mono truncate">
                  TX:{" "}
                  {(contribution.reward.transactionHash as string).substring(
                    0,
                    16
                  )}
                  ...
                </div>
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
              {/* Information guide for new users */}
              {!selectedFile && (
                <div className="mb-8 bg-blue-50 p-4 rounded-lg border border-blue-100">
                  <h3 className="text-lg font-semibold text-blue-800 mb-3 flex items-center">
                    <Upload className="h-5 w-5 mr-2 text-blue-600" />
                    How to Contribute Sign Language Images
                  </h3>

                  <div className="space-y-4">
                    <div className="grid grid-cols-12 gap-2 items-start">
                      <div className="col-span-1 flex justify-center">
                        <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-medium">
                          1
                        </div>
                      </div>
                      <div className="col-span-11">
                        <p className="text-blue-800 font-medium">
                          Select an image
                        </p>
                        <p className="text-sm text-blue-700">
                          Upload a photo showing a clear hand sign. Good
                          lighting and a clear background will help with
                          detection.
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-12 gap-2 items-start">
                      <div className="col-span-1 flex justify-center">
                        <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-medium">
                          2
                        </div>
                      </div>
                      <div className="col-span-11">
                        <p className="text-blue-800 font-medium">
                          Hand detection
                        </p>
                        <p className="text-sm text-blue-700">
                          Our system will validate that your image contains a
                          visible hand. This step is necessary for quality
                          control.
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-12 gap-2 items-start">
                      <div className="col-span-1 flex justify-center">
                        <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-medium">
                          3
                        </div>
                      </div>
                      <div className="col-span-11">
                        <p className="text-blue-800 font-medium">
                          Choose upload method
                        </p>
                        <p className="text-sm text-blue-700">
                          <span className="block mt-1 mb-2">
                            You'll have two options after hand detection:
                          </span>
                          <span className="flex items-center text-green-700 mb-1">
                            <Cloud className="h-4 w-4 mr-1 text-green-600" />
                            <strong>Decentralized Compute (Lilypad):</strong>
                            Uses AI to analyze with decentralized compute!!
                          </span>
                          <span className="flex items-center text-gray-700">
                            <Upload className="h-4 w-4 mr-1 text-blue-600" />
                            <strong>Standard Upload:</strong> Uses AI to analyze
                            without decentralized compute
                          </span>
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-12 gap-2 items-start">
                      <div className="col-span-1 flex justify-center">
                        <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-medium">
                          4
                        </div>
                      </div>
                      <div className="col-span-11">
                        <p className="text-blue-800 font-medium">
                          Get rewarded
                        </p>
                        <p className="text-sm text-blue-700">
                          After successful verification and upload, you'll
                          receive XP tokens as a reward for your contribution.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* File upload section */}
              {selectedFile ? (
                <>
                  {validatingFile ? (
                    <HandDetectionPrevalidator
                      file={selectedFile}
                      onValidated={handleValidationResult}
                      onCancel={handleCancelValidation}
                    />
                  ) : (
                    <>
                      <ImagePreview
                        file={selectedFile}
                        onRemove={() => {
                          setSelectedFile(null);
                          setHandLandmarks(undefined);
                        }}
                        className="mb-4"
                        landmarks={handLandmarks}
                      />
                      {handLandmarks ? (
                        <div className="bg-green-50 p-3 rounded-lg border border-green-100 mb-6 flex items-center">
                          <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                          <span className="text-green-800 text-sm">
                            Hand detected successfully! Ready to upload.
                          </span>
                        </div>
                      ) : (
                        <div className="bg-blue-50 p-3 rounded-lg border border-blue-100 mb-6 flex items-center">
                          <Loader2 className="h-5 w-5 text-blue-500 mr-2 animate-spin" />
                          <span className="text-blue-800 text-sm">
                            Analyzing image for hand detection...
                          </span>
                        </div>
                      )}
                    </>
                  )}
                </>
              ) : (
                <FileUpload
                  onFileSelect={handleFileSelect}
                  onRemove={() => setSelectedFile(null)}
                  accept={{
                    "image/*": [".jpg", ".jpeg", ".png"],
                  }}
                />
              )}

              {/* Only show buttons when file is selected and landmarks are detected */}
              {selectedFile && handLandmarks && (
                <div className="flex flex-col gap-4 mt-6">
                  {/* Lilypad Upload Button */}
                  <Button
                    onClick={handleLilypadEvaluation}
                    disabled={
                      isLilypadProcessing || isProcessing || !isConnected
                    }
                    variant="default"
                    className="w-full flex gap-2 items-center bg-green-600 hover:bg-green-700 text-white"
                  >
                    {isLilypadProcessing ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Processing Lilypad Detection...</span>
                      </>
                    ) : (
                      <>
                        <Cloud className="h-4 w-4" />
                        <span>
                          Upload & Evaluate with decentralized compute(Lilypad!)
                        </span>
                      </>
                    )}
                  </Button>

                  {/* Regular Upload button */}
                  <Button
                    onClick={handleContribution}
                    disabled={isProcessing}
                    className="w-full"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing... {progressPercent}%
                      </>
                    ) : (
                      <>
                        <Upload className="mr-2 h-4 w-4" />
                        Standard Upload & Verification
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
        <Card className="mt-4 overflow-hidden">
          <CardHeader
            className={`${
              lilypadResult.status === "success"
                ? "bg-green-50 border-b border-green-100"
                : lilypadResult.status === "error"
                ? "bg-red-50 border-b border-red-100"
                : "bg-blue-50 border-b border-blue-100"
            }`}
          >
            <div className="flex items-center">
              {lilypadResult.status === "success" ? (
                <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
              ) : lilypadResult.status === "error" ? (
                <XCircle className="h-5 w-5 text-red-600 mr-2" />
              ) : (
                <Cloud className="h-5 w-5 text-blue-600 mr-2" />
              )}
              <CardTitle
                className={`text-lg ${
                  lilypadResult.status === "success"
                    ? "text-green-800"
                    : lilypadResult.status === "error"
                    ? "text-red-800"
                    : "text-blue-800"
                }`}
              >
                Sign Language Detection Result
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="space-y-3">
              {lilypadResult.output && (
                <div className="flex items-center gap-2 bg-gray-50 p-3 rounded-md">
                  <div className="font-semibold text-gray-700">
                    Detected Sign:
                  </div>
                  <div className="text-xl font-bold flex items-center gap-2">
                    <span
                      className={
                        lilypadResult.output.status === "success"
                          ? "text-green-600"
                          : "text-gray-700"
                      }
                    >
                      {lilypadResult.output.letter || "Unknown"}
                    </span>
                    {lilypadResult.output.status === "success" ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                </div>
              )}

              {lilypadResult.output &&
                lilypadResult.output.confidence !== undefined && (
                  <div className="flex items-center gap-2 mb-2">
                    <div className="font-semibold text-gray-700">
                      Confidence:
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-20 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500"
                          style={{
                            width: `${Math.round(
                              (lilypadResult.output.confidence || 0) * 100
                            )}%`,
                          }}
                        ></div>
                      </div>
                      <span className="text-sm font-medium">
                        {Math.round(
                          (lilypadResult.output.confidence || 0) * 100
                        )}
                        %
                      </span>
                    </div>
                  </div>
                )}

              {lilypadResult.message && (
                <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-md">
                  <div className="font-semibold mb-1">Details:</div>
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

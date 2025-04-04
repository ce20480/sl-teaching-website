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
import { storageApi, ApiError } from "@/lib/services/api";
import { toast } from "sonner";
import { Progress } from "@/components/ui/progress";
import { useAccount } from "wagmi";
import { ExperienceDisplay } from "@/components/ExperienceDisplay";
import { WalletConnect } from "@/components/features/wallet/WalletConnect";

interface EvaluationStatus {
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

export default function Contribute() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [evaluationStatus, setEvaluationStatus] =
    useState<EvaluationStatus | null>(null);
  const { address, isConnected } = useAccount();

  // Handle file selection
  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    // Reset previous status
    setTaskId(null);
    setEvaluationStatus(null);
  };

  // Handle file upload
  const handleUpload = async () => {
    if (!selectedFile || !address) return;

    try {
      setIsUploading(true);
      setUploadProgress(0);

      const result = await storageApi.uploadFile(
        selectedFile,
        (progress) => {
          setUploadProgress(progress);
        },
        address // Pass the user's wallet address
      );

      console.log("Upload successful:", result);
      toast.success("File successfully uploaded and submitted for evaluation!");

      if (result.task_id) {
        setTaskId(result.task_id);
      }

      setSelectedFile(null);
    } catch (error) {
      console.error("Upload error details:", error);

      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Unexpected error during upload");
      }
    } finally {
      setIsUploading(false);
    }
  };

  // Poll for evaluation status
  useEffect(() => {
    let intervalId: number;

    const checkStatus = async () => {
      if (!taskId) return;

      try {
        const status = await storageApi.checkEvaluationStatus(taskId);
        setEvaluationStatus(status);

        // Stop polling when evaluation is complete
        if (status.completed) {
          if (status.status === "approved") {
            toast.success("Contribution approved! XP tokens awarded.");

            // Show achievement toast if one was granted
            if (status.reward?.achievement?.success) {
              toast.success("Achievement unlocked! NFT minted to your wallet.");
            }
          } else if (status.status === "rejected") {
            toast.error(
              "Contribution rejected. Please try again with a different image."
            );
          }

          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Error checking status:", error);
        clearInterval(intervalId);
      }
    };

    if (taskId) {
      // Initial check
      checkStatus();

      // Poll every 3 seconds
      intervalId = window.setInterval(checkStatus, 3000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [taskId]);

  return (
    <div className="max-w-3xl mx-auto space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Contribute</h1>
        <p className="text-muted-foreground mt-2">
          Help improve sign language recognition by contributing your signs
        </p>
      </div>

      {!isConnected && (
        <Card>
          <CardContent className="pt-6">
            <WalletConnect />
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Upload Sign Language Data</CardTitle>
            <CardDescription>
              Upload images or videos of sign language gestures to help train
              our model and earn XP tokens
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <FileUpload
              onFileSelect={handleFileSelect}
              onRemove={() => setSelectedFile(null)}
              accept={{
                "image/*": [".png", ".jpg", ".jpeg", ".gif"],
                "video/*": [".mp4", ".webm", ".mov"],
              }}
              maxSize={10 * 1024 * 1024} // 10MB
            />

            {selectedFile && (
              <div className="space-y-4">
                {isUploading && (
                  <Progress value={uploadProgress} className="w-full" />
                )}
                <Button
                  onClick={handleUpload}
                  disabled={isUploading || !address}
                  className="w-full"
                >
                  {!address
                    ? "Connect wallet to upload"
                    : isUploading
                    ? "Uploading to Filecoin..."
                    : "Upload to Filecoin"}
                </Button>
              </div>
            )}

            {evaluationStatus && (
              <div
                className={`mt-4 p-4 rounded-md ${
                  evaluationStatus.status === "approved"
                    ? "bg-green-50 text-green-800"
                    : evaluationStatus.status === "rejected"
                    ? "bg-red-50 text-red-800"
                    : "bg-blue-50 text-blue-800"
                }`}
              >
                <h3 className="font-semibold">
                  {evaluationStatus.status === "approved"
                    ? "Contribution Approved!"
                    : evaluationStatus.status === "rejected"
                    ? "Contribution Rejected"
                    : "Evaluating Contribution..."}
                </h3>
                <p className="text-sm mt-1">
                  {evaluationStatus.message ||
                    "Processing your contribution..."}
                </p>
                {evaluationStatus.score !== undefined && (
                  <p className="text-sm mt-1">
                    Quality Score: {evaluationStatus.score.toFixed(2)}
                  </p>
                )}
                {evaluationStatus.reward?.xp?.transaction_hash && (
                  <p className="text-sm mt-1">
                    <a
                      href={`https://calibration.filfox.info/en/tx/${evaluationStatus.reward.xp.transaction_hash}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      View XP Transaction
                    </a>
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {isConnected && (
          <Card>
            <CardHeader>
              <CardTitle>Your Experience</CardTitle>
              <CardDescription>Track your progress and rewards</CardDescription>
            </CardHeader>
            <CardContent>
              <ExperienceDisplay />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

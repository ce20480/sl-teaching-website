import { useState, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileUpload } from "@/components/features/upload/FileUpload";
import { storageApi, ApiError } from "@/lib/services/api";
import { toast } from "sonner";
import { Progress } from "@/components/ui/progress";
import { useAccount } from "wagmi";
import { ExperienceDisplay } from "@/components/ExperienceDisplay";
import { WalletConnect } from "@/components/features/wallet/WalletConnect";
import { InfoIcon, Upload, Brain, Trophy, Wallet } from "lucide-react";

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

      // const result = await storageApi.uploadFile(
      //   selectedFile,
      //   (progress) => {
      //     setUploadProgress(progress);
      //   },
      //   address // Pass the user's wallet address
      // );

      const result = await storageApi.uploadContribution(
        selectedFile,
        (progress) => {
          setUploadProgress(progress);
        },
        address // Pass the user's wallet address
      );

      if (result && result.status) {
        toast.success("File successfully uploaded and submitted for evaluation!");
      } else {
        toast.error("Failed to upload file");
      }

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
        <Card className="mb-6 bg-blue-50 border-blue-100">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center text-blue-700">
              <Wallet className="mr-2 h-5 w-5" />
              Connect Wallet
            </CardTitle>
            <CardDescription>
              Connect your wallet to earn rewards for your contributions
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="flex justify-center py-2 max-w-md mx-auto">
              <WalletConnect />
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Upload className="mr-2 h-5 w-5 text-blue-600" />
              Upload Sign Language Data
            </CardTitle>
            <CardDescription>
              Upload images or videos of sign language gestures to help train
              our model
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
          <Card className="border-blue-100">
            <CardHeader className="bg-blue-50 rounded-t-lg">
              <CardTitle className="flex items-center">
                <Trophy className="mr-2 h-5 w-5 text-blue-600" />
                Your Experience
              </CardTitle>
              <CardDescription>Track your progress and rewards</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <ExperienceDisplay />
            </CardContent>
            <CardFooter className="bg-slate-50 border-t py-3 px-6 text-xs text-slate-500 flex items-center gap-2">
              <InfoIcon className="h-4 w-4" />
              <span>Earn XP for each approved contribution</span>
            </CardFooter>
          </Card>
        )}
      </div>
      
      <Card className="border-blue-100">
        <CardHeader className="pb-3 bg-blue-50 rounded-t-lg">
          <CardTitle className="flex items-center">
            <Brain className="mr-2 h-5 w-5 text-blue-600" />
            How it Works
          </CardTitle>
          <CardDescription>
            Your contributions help improve our sign language recognition model
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 grid-cols-1 sm:grid-cols-3 pt-6">
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
            <div className="font-medium mb-1 text-blue-700">1. Upload</div>
            <p className="text-sm text-slate-600">
              Upload images or videos of sign language gestures
            </p>
          </div>
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
            <div className="font-medium mb-1 text-blue-700">2. Processing</div>
            <p className="text-sm text-slate-600">
              Our system evaluates your contribution
            </p>
          </div>
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
            <div className="font-medium mb-1 text-blue-700">3. Rewards</div>
            <p className="text-sm text-slate-600">
              Earn XP and special achievement NFTs
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, X } from "lucide-react";
import { useAccount } from "wagmi";
import { toast } from "sonner";

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  onRemove: () => void;
  accept?: Record<string, string[]>;
  maxSize?: number;
}

interface EvaluationStatus {
  status: "pending" | "processing" | "approved" | "rejected";
  score?: number;
  feedback?: string;
}

export function FileUpload({
  onFileSelect,
  onRemove,
  accept,
  maxSize = 5 * 1024 * 1024, // 5MB default
}: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [evaluationStatus, setEvaluationStatus] = useState<EvaluationStatus | null>(null);
  const { address } = useAccount();

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (file) {
        setSelectedFile(file);
        onFileSelect(file);
        setEvaluationStatus(null);
      }
    },
    [onFileSelect]
  );

  const handleRemove = () => {
    setSelectedFile(null);
    setEvaluationStatus(null);
    onRemove();
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxSize,
    multiple: false,
  });

  const checkEvaluationStatus = async (taskId: string) => {
    try {
      const response = await fetch(`/api/storage/evaluation/${taskId}`);
      if (response.ok) {
        const data = await response.json();
        setEvaluationStatus({
          status: data.status,
          score: data.score,
          feedback: data.feedback,
        });

        if (data.status === "approved") {
          toast.success("Contribution approved! Achievement token awarded.");
        }
      }
    } catch (error) {
      console.error("Error checking evaluation status:", error);
    }
  };

  // Helper function to format accept types for display
  const formatAcceptedTypes = () => {
    if (!accept) return null;
    return Object.entries(accept)
      .map(([mimeType]) => mimeType.split('/')[1].toUpperCase())
      .join(', ');
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
          ${
            isDragActive
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25 hover:border-primary"
          }`}
      >
        <input {...getInputProps()} />
        {selectedFile ? (
          <div className="flex items-center justify-between">
            <span className="text-sm">{selectedFile.name}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleRemove();
              }}
              className="p-1 hover:bg-destructive/10 rounded-full"
            >
              <X className="h-4 w-4 text-destructive" />
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Drag and drop a file, or click to select
            </p>
            {accept && (
              <p className="text-xs text-muted-foreground">
                Accepted formats: {formatAcceptedTypes()}
              </p>
            )}
            {maxSize && (
              <p className="text-xs text-muted-foreground">
                Max size: {Math.round(maxSize / 1024 / 1024)}MB
              </p>
            )}
          </div>
        )}
      </div>

      {evaluationStatus && (
        <div className={`p-4 rounded-lg ${
          evaluationStatus.status === "approved" 
            ? "bg-green-50 text-green-700" 
            : evaluationStatus.status === "rejected"
            ? "bg-red-50 text-red-700"
            : "bg-blue-50 text-blue-700"
        }`}>
          <p className="font-medium">
            Status: {evaluationStatus.status.charAt(0).toUpperCase() + evaluationStatus.status.slice(1)}
          </p>
          {evaluationStatus.score && (
            <p className="text-sm">Quality Score: {evaluationStatus.score}</p>
          )}
          {evaluationStatus.feedback && (
            <p className="text-sm mt-1">{evaluationStatus.feedback}</p>
          )}
        </div>
      )}
    </div>
  );
}

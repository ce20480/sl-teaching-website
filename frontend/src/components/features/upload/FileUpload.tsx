import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, X, FileType } from "lucide-react";

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
  const [evaluationStatus, setEvaluationStatus] =
    useState<EvaluationStatus | null>(null);

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

  // Helper function to format accept types for display
  const formatAcceptedTypes = () => {
    if (!accept) return null;
    return Object.entries(accept)
      .map(([mimeType]) => mimeType.split("/")[1].toUpperCase())
      .join(", ");
  };

  return (
    <div className="space-y-4 w-full">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
          ${
            isDragActive
              ? "border-blue-500 bg-blue-50"
              : "border-slate-200 hover:border-blue-500 hover:bg-blue-50/30"
          }`}
      >
        <input {...getInputProps()} />
        {selectedFile ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <FileType className="h-5 w-5 text-blue-600 mr-2" />
              <span className="text-sm font-medium">{selectedFile.name}</span>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleRemove();
              }}
              className="p-1 hover:bg-red-100 rounded-full"
            >
              <X className="h-4 w-4 text-red-500" />
            </button>
          </div>
        ) : (
          <div className="space-y-3 py-4">
            <Upload className="h-10 w-10 mx-auto text-blue-500" />
            <p className="text-sm font-medium text-slate-700">
              Drag and drop a file, or click to select
            </p>
            {accept && (
              <p className="text-xs text-slate-500">
                Accepted formats: {formatAcceptedTypes()}
              </p>
            )}
            {maxSize && (
              <p className="text-xs text-slate-500">
                Max size: {Math.round(maxSize / 1024 / 1024)}MB
              </p>
            )}
          </div>
        )}
      </div>

      {evaluationStatus && (
        <div
          className={`p-4 rounded-lg ${
            evaluationStatus.status === "approved"
              ? "bg-green-50 text-green-700"
              : evaluationStatus.status === "rejected"
              ? "bg-red-50 text-red-700"
              : "bg-blue-50 text-blue-700"
          }`}
        >
          <p className="font-medium">
            Status:{" "}
            {evaluationStatus.status.charAt(0).toUpperCase() +
              evaluationStatus.status.slice(1)}
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

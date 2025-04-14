import React, { useState, useEffect } from "react";
import { ImageHandDetector } from "../hands/ImageHandDetector";
import { HandLandmarkerResult } from "@mediapipe/tasks-vision";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { CheckCircle, XCircle, Loader2, Upload } from "lucide-react";
import { ImagePreview } from "./ImagePreview";

interface HandDetectionPrevalidatorProps {
  file: File;
  onValidated: (isValid: boolean, landmarks?: number[]) => void;
  onCancel: () => void;
}

export function HandDetectionPrevalidator({
  file,
  onValidated,
  onCancel,
}: HandDetectionPrevalidatorProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(true);
  const [validationResult, setValidationResult] = useState<{
    isValid: boolean;
    message: string;
    landmarks?: number[];
  } | null>(null);

  // Create object URL for the image file
  useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file);
      setImageUrl(url);

      // Clean up the URL when component unmounts
      return () => {
        URL.revokeObjectURL(url);
      };
    }
  }, [file]);

  // Handle detection results from MediaPipe
  const handleHandsDetected = (
    results: HandLandmarkerResult,
    rawLandmarks?: number[]
  ) => {
    setIsValidating(false);

    const hasHands = results.landmarks && results.landmarks.length > 0;

    if (hasHands) {
      setValidationResult({
        isValid: true,
        message: "Hand detected! You can proceed with the upload.",
        landmarks: rawLandmarks,
      });
    } else {
      setValidationResult({
        isValid: false,
        message:
          "No hand detected in the image. Please try another image with a clearly visible hand.",
      });
    }
  };

  // Submit validation result to parent
  const handleSubmit = () => {
    if (validationResult) {
      onValidated(validationResult.isValid, validationResult.landmarks);
    }
  };

  return (
    <div className="space-y-4">
      <div className="relative">
        {/* Loading indicator */}
        {isValidating && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/20 z-10 rounded-md">
            <div className="bg-white rounded-lg p-3 flex items-center space-x-2">
              <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
              <span>Validating image...</span>
            </div>
          </div>
        )}

        {/* Two-part display:
            1. Invisible hand detection component for processing
            2. Visible ImagePreview component for user interaction */}
        <div className="relative">
          {/* Hidden hand detector (processes the image) */}
          {imageUrl && (
            <div className="absolute inset-0 opacity-0 pointer-events-none">
              <ImageHandDetector
                imageUrl={imageUrl}
                onHandsDetected={handleHandsDetected}
              />
            </div>
          )}

          {/* Visible image preview with controls */}
          <ImagePreview
            file={file}
            onRemove={onCancel}
            className="mb-4"
            landmarks={validationResult?.landmarks}
          />
        </div>
      </div>

      {/* Validation result message */}
      {validationResult && (
        <Alert
          className={
            validationResult.isValid
              ? "border-green-200 bg-green-50"
              : "border-red-200 bg-red-50"
          }
        >
          <div className="flex items-start">
            {validationResult.isValid ? (
              <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 mr-2" />
            ) : (
              <XCircle className="h-5 w-5 text-red-600 mt-0.5 mr-2" />
            )}
            <div>
              <AlertTitle
                className={
                  validationResult.isValid ? "text-green-800" : "text-red-800"
                }
              >
                {validationResult.isValid ? "Valid Image" : "Invalid Image"}
              </AlertTitle>
              <AlertDescription
                className={
                  validationResult.isValid ? "text-green-700" : "text-red-700"
                }
              >
                {validationResult.message}
              </AlertDescription>
            </div>
          </div>
        </Alert>
      )}

      {/* Action buttons */}
      <div className="flex space-x-2 justify-end">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>

        {validationResult?.isValid ? (
          <Button
            onClick={handleSubmit}
            variant="default"
            disabled={isValidating}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Upload className="mr-2 h-4 w-4" />
            Proceed with Upload
          </Button>
        ) : (
          <Button variant="outline" onClick={onCancel} disabled={isValidating}>
            Try Another Image
          </Button>
        )}
      </div>
    </div>
  );
}

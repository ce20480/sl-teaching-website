import React, { useState, useCallback, useRef, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { WebcamManager } from "./WebcamManager";
import { HandLandmarkVisualizer } from "./HandLandmarkVisualizer";
import { GenericHandDetector } from "./GenericHandDetector";
import { HandLandmarkerResult } from "@mediapipe/tasks-vision";

interface WebcamHandDetectorProps {
  onHandsDetected?: (
    results: HandLandmarkerResult,
    rawLandmarks?: number[]
  ) => void;
  className?: string;
  isActive: boolean;
}

export function WebcamHandDetector({
  onHandsDetected,
  className = "",
  isActive,
}: WebcamHandDetectorProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<HandLandmarkerResult | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Add debug console log
  useEffect(() => {
    console.log("WebcamHandDetector isActive changed:", isActive);
  }, [isActive]);

  const handleStreamReady = useCallback((video: HTMLVideoElement) => {
    console.log("Stream ready, video element received");
    videoRef.current = video;
    setIsLoading(false);
  }, []);

  const handleDetectionResults = useCallback(
    (detectionResults: HandLandmarkerResult) => {
      setResults(detectionResults);

      // Extract flat landmarks for potential backend processing
      const flatLandmarks = detectionResults.landmarks?.[0]
        ? detectionResults.landmarks[0].map((lm) => [lm.x, lm.y, lm.z]).flat()
        : undefined;

      if (onHandsDetected) {
        onHandsDetected(detectionResults, flatLandmarks);
      }
    },
    [onHandsDetected]
  );

  // Reset when component becomes inactive
  useEffect(() => {
    if (!isActive) {
      console.log("Resetting WebcamHandDetector state");
      setResults(null);
      setIsLoading(true); // Reset loading state for next activation
      videoRef.current = null;
    }
  }, [isActive]);

  // Handle errors from child components
  const handleError = useCallback((errorMessage: string) => {
    console.error("WebcamHandDetector error:", errorMessage);
    setError(errorMessage);
    setIsLoading(false);
  }, []);

  return (
    <div className={`relative ${className}`}>
      {isActive && (
        <WebcamManager
          onStreamReady={handleStreamReady}
          isActive={isActive}
          onError={handleError}
        />
      )}

      {videoRef.current && !isLoading && isActive && (
        <GenericHandDetector
          mediaElement={videoRef.current}
          mode="VIDEO"
          isActive={isActive}
          onHandsDetected={handleDetectionResults}
          onError={handleError}
        />
      )}

      {results && videoRef.current && isActive && (
        <HandLandmarkVisualizer
          results={results}
          width={videoRef.current.videoWidth}
          height={videoRef.current.videoHeight}
        />
      )}

      {isLoading && isActive && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <div className="flex flex-col items-center">
            <Loader2 className="w-8 h-8 animate-spin text-white mb-2" />
            <p className="text-white text-sm">Starting camera...</p>
          </div>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <div className="bg-white p-4 rounded-md max-w-md">
            <p className="text-red-500 font-medium">Camera Error</p>
            <p className="text-sm mt-1">{error}</p>
            <p className="text-xs mt-2">
              Please make sure you've granted camera permissions and try again.
            </p>
          </div>
        </div>
      )}

      {!isActive && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-muted-foreground">
            Start camera to begin translation
          </p>
        </div>
      )}
    </div>
  );
}

import React, { useState, useRef } from "react";
import { HandLandmarkVisualizer } from "./HandLandmarkVisualizer";
import { GenericHandDetector } from "./GenericHandDetector";
import { HandLandmarkerResult } from "@mediapipe/tasks-vision";

interface ImageHandDetectorProps {
  imageUrl: string;
  onHandsDetected?: (
    results: HandLandmarkerResult,
    rawLandmarks?: number[]
  ) => void;
  onError?: (error: string) => void;
  className?: string;
}

export function ImageHandDetector({
  imageUrl,
  onHandsDetected,
  onError,
  className = "",
}: ImageHandDetectorProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [results, setResults] = useState<HandLandmarkerResult | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const handleImageLoad = () => {
    setIsLoaded(true);
  };

  const handleDetectionResults = (detectionResults: HandLandmarkerResult) => {
    setResults(detectionResults);

    // Extract flat landmarks for potential backend processing
    let flatLandmarks = undefined;

    if (detectionResults.landmarks?.[0]?.length > 0) {
      try {
        // Convert landmarks to a flat array of coordinates
        flatLandmarks = detectionResults.landmarks[0]
          .map((lm) => [lm.x, lm.y, lm.z])
          .flat();

        // Ensure we have the correct number of elements (21 landmarks x 3 coords = 63 values)
        if (flatLandmarks.length !== 63) {
          console.warn(
            `Unexpected landmark data length: ${flatLandmarks.length} (expected 63)`
          );
        }
      } catch (error) {
        console.error("Error flattening landmarks:", error);
      }
    }

    if (onHandsDetected) {
      onHandsDetected(detectionResults, flatLandmarks);
    }
  };

  return (
    <div className={`relative ${className}`}>
      <img
        ref={imgRef}
        src={imageUrl}
        onLoad={handleImageLoad}
        className="w-full h-auto"
        alt="Hand detection image"
      />

      {imgRef.current && isLoaded && (
        <GenericHandDetector
          mediaElement={imgRef.current}
          mode="IMAGE"
          isActive={true}
          onHandsDetected={handleDetectionResults}
          onError={onError}
        />
      )}

      {results && imgRef.current && (
        <HandLandmarkVisualizer
          results={results}
          width={imgRef.current.naturalWidth}
          height={imgRef.current.naturalHeight}
        />
      )}
    </div>
  );
}

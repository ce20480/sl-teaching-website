import React, { useState, useRef, useEffect } from "react";
import { HandLandmarkVisualizer } from "./HandLandmarkVisualizer";
import { GenericHandDetector } from "./GenericHandDetector";
import { HandLandmarkerResult } from "@mediapipe/tasks-vision";

interface ImageHandDetectorProps {
  imageUrl: string;
  onHandsDetected?: (
    results: HandLandmarkerResult,
    rawLandmarks?: number[]
  ) => void;
  className?: string;
}

export function ImageHandDetector({
  imageUrl,
  onHandsDetected,
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
    const flatLandmarks = detectionResults.landmarks?.[0]
      ? detectionResults.landmarks[0].map((lm) => [lm.x, lm.y, lm.z]).flat()
      : undefined;

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

import React, { useState, useCallback } from "react";
import { HandLandmarkerResult } from "@mediapipe/tasks-vision";
import { predictionApi } from "@/lib/services/api/prediction-api";

interface SignLanguagePredictorProps {
  children: React.ReactNode;
  onPrediction?: (prediction: {
    letter: string;
    confidence: number;
    landmarks?: number[];
  }) => void;
  autoPredict?: boolean;
  minConfidence?: number;
}

export function SignLanguagePredictor({
  children,
  onPrediction,
  autoPredict = true,
  minConfidence = 0.7,
}: SignLanguagePredictorProps) {
  const [isPredicting, setIsPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleHandsDetected = useCallback(
    async (results: HandLandmarkerResult, landmarks?: number[]) => {
      // Only process if landmarks are available and we're not already predicting
      if (
        !landmarks ||
        landmarks.length === 0 ||
        !autoPredict ||
        isPredicting
      ) {
        return;
      }

      try {
        setIsPredicting(true);

        // Send landmarks to backend for prediction
        const prediction = await predictionApi.predictSign(landmarks);

        // Only handle predictions with sufficient confidence
        if (prediction.confidence >= minConfidence) {
          onPrediction?.(prediction);
        }
      } catch (err) {
        setError((err as Error).message);
        console.error("Prediction error:", err);
      } finally {
        setIsPredicting(false);
      }
    },
    [onPrediction, autoPredict, isPredicting, minConfidence]
  );

  // Create a clone of the child elements with the additional handleHandsDetected prop
  const childrenWithProps = React.Children.map(children, (child) => {
    if (React.isValidElement(child)) {
      return React.cloneElement(child, {
        onHandsDetected: handleHandsDetected,
      });
    }
    return child;
  });

  return (
    <div className="relative">
      {childrenWithProps}
      {error && <div className="text-red-500 text-sm mt-2">{error}</div>}
      {isPredicting && (
        <div className="absolute top-2 right-2 bg-amber-500 text-white text-xs px-2 py-1 rounded-full">
          Predicting...
        </div>
      )}
    </div>
  );
}

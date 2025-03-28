import React, { useEffect, useRef, useState } from "react";
import { HandDetectionService } from "@/lib/services/hand-detection";
import { HandLandmarkerResult, HandLandmarker } from "@mediapipe/tasks-vision";

interface GenericHandDetectorProps {
  mediaElement: HTMLVideoElement | HTMLImageElement | HTMLCanvasElement;
  mode: "IMAGE" | "VIDEO";
  isActive: boolean;
  onHandsDetected?: (results: HandLandmarkerResult) => void;
  onError?: (error: string) => void;
  className?: string;
}

export function GenericHandDetector({
  mediaElement,
  mode,
  isActive,
  onHandsDetected,
  onError,
}: GenericHandDetectorProps) {
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const handLandmarkerRef = useRef<HandLandmarker | null>(null);
  const animationRef = useRef<number | null>(null);
  const lastVideoTimeRef = useRef<number>(-1);

  // Report errors to parent component
  useEffect(() => {
    if (error && onError) {
      onError(error);
    }
  }, [error, onError]);

  // Initialize hand detection service
  useEffect(() => {
    const initialize = async () => {
      try {
        const handDetectionService = HandDetectionService.getInstance();
        handLandmarkerRef.current = await handDetectionService.initialize();
        await handDetectionService.setRunningMode(mode);
        setIsInitialized(true);
      } catch (err) {
        setError((err as Error).message);
      }
    };

    if (isActive && !isInitialized) {
      initialize();
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [isActive, mode, isInitialized]);

  // Handle detection based on mode
  useEffect(() => {
    if (!isInitialized || !isActive) return;

    const handDetectionService = HandDetectionService.getInstance();

    if (mode === "IMAGE") {
      // For image mode, just detect once
      try {
        const results = handDetectionService.detectHandsFromImage(
          mediaElement as HTMLImageElement
        );
        if (onHandsDetected) {
          onHandsDetected(results);
        }
      } catch (err) {
        setError((err as Error).message);
      }
    } else if (mode === "VIDEO") {
      // For video mode, set up continuous detection
      const detectFrame = async () => {
        const video = mediaElement as HTMLVideoElement;

        // Only process if video is playing and ready
        if (video.readyState === 4 && !video.paused && !video.ended) {
          if (lastVideoTimeRef.current !== video.currentTime) {
            lastVideoTimeRef.current = video.currentTime;
            const startTimeMs = performance.now();

            try {
              const results = await handDetectionService.detectHands(
                video,
                startTimeMs
              );
              if (onHandsDetected && isActive) {
                onHandsDetected(results);
              }
            } catch (err) {
              setError((err as Error).message);
            }
          }

          if (isActive) {
            animationRef.current = requestAnimationFrame(detectFrame);
          }
        } else if (isActive) {
          // If video isn't ready yet, check again soon
          animationRef.current = requestAnimationFrame(detectFrame);
        }
      };

      detectFrame();
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [isInitialized, isActive, mediaElement, mode, onHandsDetected]);

  // Make sure we cleanup properly when component becomes inactive
  useEffect(() => {
    if (!isActive && animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
  }, [isActive]);

  return <>{error && <div className="text-red-500">Error: {error}</div>}</>;
}

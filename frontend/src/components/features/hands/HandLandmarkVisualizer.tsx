import React, { useEffect, useRef } from "react";
import { HandLandmarkerResult } from "@mediapipe/tasks-vision";
import { HandDetectionService } from "@/lib/services/hand-detection";

interface HandLandmarkVisualizerProps {
  results: HandLandmarkerResult;
  width: number;
  height: number;
  className?: string;
}

export function HandLandmarkVisualizer({
  results,
  width,
  height,
  className = "",
}: HandLandmarkVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Make sure canvas dimensions match the video exactly
    canvas.width = width;
    canvas.height = height;

    // Save the current canvas state
    ctx.save();

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw landmarks using the static method
    if (results.landmarks) {
      HandDetectionService.drawResults(ctx, results);
    }

    // Restore the canvas state
    ctx.restore();
  }, [results, width, height]);

  return (
    <canvas
      ref={canvasRef}
      className={`absolute top-0 left-0 pointer-events-none ${className}`}
      style={{
        width: "100%",
        height: "100%",
        objectFit: "contain",
      }}
    />
  );
}

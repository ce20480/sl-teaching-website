import React, { useEffect, useRef } from "react";

interface WebcamManagerProps {
  onStreamReady: (video: HTMLVideoElement) => void;
  isActive: boolean;
  className?: string;
}

export function WebcamManager({
  onStreamReady,
  isActive,
  className = "",
}: WebcamManagerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    let isMounted = true;

    const setupWebcam = async () => {
      if (!videoRef.current) return;

      try {
        // If we already have a stream, close it first
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        if (isActive) {
          // Get new stream
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 },
          });

          // Save reference to stream for cleanup
          streamRef.current = stream;

          if (isMounted && videoRef.current) {
            videoRef.current.srcObject = stream;
            await videoRef.current.play();
            onStreamReady(videoRef.current);
          } else if (stream) {
            // If component unmounted during async operation, clean up
            stream.getTracks().forEach((track) => track.stop());
          }
        }
      } catch (err) {
        console.error("Error accessing webcam:", err);
      }
    };

    setupWebcam();

    // Cleanup function
    return () => {
      isMounted = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }

      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [isActive, onStreamReady]);

  // Also make sure we clean up when isActive changes to false
  useEffect(() => {
    if (!isActive && streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;

      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    }
  }, [isActive]);

  return (
    <video
      ref={videoRef}
      className={`w-full h-full object-cover ${className}`}
      playsInline
    />
  );
}

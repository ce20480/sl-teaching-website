import React, { useEffect, useRef } from "react";

interface WebcamManagerProps {
  onStreamReady: (video: HTMLVideoElement) => void;
  isActive: boolean;
  className?: string;
  onError?: (error: string) => void;
}

export function WebcamManager({
  onStreamReady,
  isActive,
  className = "",
  onError,
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
          console.log("WebcamManager: Setting up webcam");
          // Get new stream
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 },
          });

          // Save reference to stream for cleanup
          streamRef.current = stream;

          if (isMounted && videoRef.current) {
            videoRef.current.srcObject = stream;

            // Wait for video to be ready before notifying parent
            videoRef.current.onloadedmetadata = () => {
              if (videoRef.current) {
                console.log("Video metadata loaded, playing video");
                videoRef.current
                  .play()
                  .then(() => {
                    console.log("Video playback started successfully");
                    onStreamReady(videoRef.current!);
                  })
                  .catch((err) => {
                    console.error("Error starting video playback:", err);
                    onError?.("Failed to start video playback: " + err.message);
                  });
              }
            };
          } else if (stream) {
            // If component unmounted during async operation, clean up
            stream.getTracks().forEach((track) => track.stop());
          }
        }
      } catch (err) {
        console.error("Error accessing webcam:", err);

        // Provide more user-friendly error messages
        if (err instanceof DOMException) {
          if (err.name === "NotAllowedError") {
            onError?.(
              "Camera access denied. Please allow camera permissions in your browser settings."
            );
          } else if (err.name === "NotFoundError") {
            onError?.(
              "No camera detected. Please connect a camera and try again."
            );
          } else if (err.name === "NotReadableError") {
            onError?.(
              "Camera is in use by another application. Please close other programs using the camera."
            );
          } else {
            onError?.(`Camera error: ${err.message}`);
          }
        } else {
          onError?.(`Failed to start camera: ${(err as Error).message}`);
        }
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
  }, [isActive, onStreamReady, onError]);

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

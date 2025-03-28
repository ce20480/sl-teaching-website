import { Camera, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useState, useEffect } from "react";
import { WebcamHandDetector } from "@/components/features/hands/WebcamHandDetector";
import { HandLandmarkerResult } from "@mediapipe/tasks-vision";

const Translate = () => {
  const [isActive, setIsActive] = useState(false);
  const [prediction, setPrediction] = useState<string>("");

  const handleHandsDetected = (
    results: HandLandmarkerResult,
    landmarks?: number[]
  ) => {
    // Only process if hands were actually detected
    if (results.landmarks && results.landmarks.length > 0) {
      // For now just log the landmarks
      console.log("Hand landmarks detected:", landmarks);

      // In the future, send landmarks to the backend for prediction
      // For now, we could display some basic data about the detection
      if (results.handednesses && results.handednesses.length > 0) {
        const handedness = results.handednesses[0][0];
        setPrediction(
          `Detected ${
            handedness.categoryName
          } hand with ${handedness.score.toFixed(2)} confidence`
        );
      }
    } else {
      setPrediction("No hands detected");
    }
  };

  const toggleCamera = () => {
    // If we're turning off the camera, clear prediction
    if (isActive) {
      setPrediction("");
    }
    setIsActive(!isActive);
  };

  // Clear prediction when component unmounts
  useEffect(() => {
    return () => {
      // Force stop any webcam that might be running when navigating away
      navigator.mediaDevices
        .getUserMedia({ video: true })
        .then((stream) => {
          stream.getTracks().forEach((track) => track.stop());
        })
        .catch(() => {
          // Ignore errors here, we're just trying to clean up
        });
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Sign Language Translator
          </h1>
          <p className="text-muted-foreground mt-2">
            Use your camera to translate sign language in real-time
          </p>
        </div>
        <Button variant="outline" size="icon">
          <Settings className="h-4 w-4" />
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Camera Feed</CardTitle>
            <Button
              onClick={toggleCamera}
              variant={isActive ? "destructive" : "default"}
              size="sm"
            >
              <Camera className="mr-2 h-4 w-4" />
              {isActive ? "Stop Camera" : "Start Camera"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="relative aspect-video w-full rounded-lg overflow-hidden bg-muted">
            <WebcamHandDetector
              onHandsDetected={handleHandsDetected}
              className="w-full h-full"
              isActive={isActive}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Translation Results</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-32 flex items-center justify-center text-muted-foreground">
            {prediction || "Translation results will appear here in real-time"}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Translate;

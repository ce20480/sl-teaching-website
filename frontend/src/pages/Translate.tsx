import { Camera, Settings, History } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { useState, useEffect } from "react";
import { WebcamHandDetector } from "@/components/features/hands/WebcamHandDetector";
import { SignLanguagePredictor } from "@/components/features/prediction/SignLanguagePredictor";

const Translate = () => {
  const [isActive, setIsActive] = useState(false);
  const [prediction, setPrediction] = useState<{
    letter: string;
    confidence: number;
  } | null>(null);

  // Keep track of recent predictions
  const [recentPredictions, setRecentPredictions] = useState<string[]>([]);

  const handlePrediction = (result: { letter: string; confidence: number }) => {
    setPrediction(result);

    // Add to recent predictions (keep only last 10)
    setRecentPredictions((prev) => {
      const updated = [result.letter, ...prev];
      return updated.slice(0, 10);
    });
  };

  const toggleCamera = () => {
    if (isActive) {
      setPrediction(null);
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
    <div className="container mx-auto py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">ASL Translator</h1>
      <p className="text-gray-600 mb-8">
        Use your camera to translate American Sign Language in real-time.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main content - Camera feed (takes up 2/3 on medium screens) */}
        <div className="md:col-span-2">
          <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div>
                <CardTitle className="text-xl">Camera Feed</CardTitle>
                <CardDescription>
                  Position your hand clearly in the frame
                </CardDescription>
              </div>
              <Button
                onClick={toggleCamera}
                className={isActive ? "bg-red-500 hover:bg-red-600" : ""}
                variant={isActive ? "destructive" : "default"}
              >
                <Camera className="mr-2 h-4 w-4" />
                {isActive ? "Stop Camera" : "Start Camera"}
              </Button>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="relative bg-slate-50 rounded-lg overflow-hidden aspect-video w-full flex items-center justify-center">
                {isActive ? (
                  <SignLanguagePredictor onPrediction={handlePrediction}>
                    <WebcamHandDetector
                      isActive={isActive}
                      className="w-full h-full"
                    />
                  </SignLanguagePredictor>
                ) : (
                  <div className="text-center p-8 text-slate-500">
                    <Camera className="mx-auto h-12 w-12 mb-4 text-slate-400" />
                    <p className="text-lg font-medium mb-2">
                      Start camera to begin translation
                    </p>
                    <p className="text-sm">
                      Make sure your hand is visible and well-lit
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - Results and history (takes up 1/3 on medium screens) */}
        <div>
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="text-xl">Translation Results</CardTitle>
              <CardDescription>Current detection and history</CardDescription>
            </CardHeader>
            <CardContent>
              {/* Current prediction */}
              <div className="bg-slate-50 rounded-lg p-6 mb-6 flex flex-col items-center justify-center min-h-[160px]">
                {prediction ? (
                  <>
                    <div className="text-5xl font-bold mb-2">
                      {prediction.letter}
                    </div>
                    <div className="text-sm text-slate-500">
                      Confidence: {(prediction.confidence * 100).toFixed(0)}%
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2.5 mt-4">
                      <div
                        className="bg-blue-600 h-2.5 rounded-full"
                        style={{ width: `${prediction.confidence * 100}%` }}
                      ></div>
                    </div>
                  </>
                ) : (
                  <div className="text-center text-slate-500">
                    {isActive
                      ? "Waiting for hand gestures..."
                      : "Translation results will appear here"}
                  </div>
                )}
              </div>

              {/* Recent history */}
              <div>
                <h3 className="flex items-center text-sm font-medium mb-3 text-slate-500">
                  <History className="mr-2 h-4 w-4" />
                  Recent Detections
                </h3>

                {recentPredictions.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {recentPredictions.map((letter, index) => (
                      <span
                        key={index}
                        className="inline-block bg-slate-100 text-slate-800 px-3 py-1 rounded-md text-sm"
                      >
                        {letter}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">No recent detections</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Additional settings or instructions */}
      <Card className="mt-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center">
            <Settings className="h-5 w-5 mr-2" />
            Tips for Better Results
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc pl-5 text-sm text-slate-600 space-y-2">
            <li>Make sure your hand is clearly visible and well-lit</li>
            <li>Keep your hand within the camera frame</li>
            <li>Make distinct hand shapes for better recognition</li>
            <li>Face your palm towards the camera when possible</li>
            <li>Avoid rapid movements for better detection accuracy</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};

export default Translate;

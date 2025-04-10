import {
  HandLandmarker,
  FilesetResolver,
  HandLandmarkerResult,
  DrawingUtils,
} from "@mediapipe/tasks-vision";

export class HandDetectionService {
  private static instance: HandDetectionService;
  private handLandmarker: HandLandmarker | undefined;
  private runningMode: "IMAGE" | "VIDEO" = "VIDEO";
  private isInitializing = false;
  private initError: Error | null = null;

  private constructor() {}

  static getInstance(): HandDetectionService {
    if (!HandDetectionService.instance) {
      HandDetectionService.instance = new HandDetectionService();
    }
    return HandDetectionService.instance;
  }

  async initialize() {
    // Prevent multiple simultaneous initializations
    if (this.isInitializing) {
      console.log("HandDetectionService already initializing, waiting...");
      // Wait for initialization to complete
      await new Promise<void>((resolve) => {
        const checkInit = () => {
          if (!this.isInitializing) {
            resolve();
          } else {
            setTimeout(checkInit, 100);
          }
        };
        checkInit();
      });

      if (this.initError) {
        throw this.initError;
      }

      if (this.handLandmarker) {
        return this.handLandmarker;
      }
    }

    // If already initialized, return the existing instance
    if (this.handLandmarker) {
      return this.handLandmarker;
    }

    try {
      this.isInitializing = true;
      console.log("Starting HandDetectionService initialization");

      const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
      );

      console.log("FilesetResolver completed, creating HandLandmarker");

      this.handLandmarker = await HandLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`,
          delegate: "GPU",
        },
        runningMode: this.runningMode,
        numHands: 2,
        minHandDetectionConfidence: 0.5,
        minHandPresenceConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });

      console.log("HandLandmarker created successfully");
      return this.handLandmarker;
    } catch (error) {
      console.error("Error initializing HandDetectionService:", error);
      this.initError =
        error instanceof Error ? error : new Error(String(error));
      throw this.initError;
    } finally {
      this.isInitializing = false;
    }
  }

  async setRunningMode(mode: "IMAGE" | "VIDEO") {
    if (this.runningMode !== mode) {
      console.log(`Changing running mode from ${this.runningMode} to ${mode}`);
      this.runningMode = mode;
      if (this.handLandmarker) {
        await this.handLandmarker.setOptions({ runningMode: mode });
      }
    }
  }

  async detectHands(
    video: HTMLVideoElement,
    timestamp: number
  ): Promise<HandLandmarkerResult> {
    if (!this.handLandmarker) {
      console.log("HandLandmarker not initialized, initializing now...");
      await this.initialize();

      if (!this.handLandmarker) {
        throw new Error("Failed to initialize HandLandmarker");
      }
    }

    if (this.runningMode !== "VIDEO") {
      await this.setRunningMode("VIDEO");
    }

    // Make sure video is ready
    if (video.readyState < 2) {
      console.warn("Video not ready yet, returning empty result");
      return {
        landmarks: [],
        worldLandmarks: [],
        handednesses: [],
        handedness: [],
      };
    }

    return this.handLandmarker.detectForVideo(video, timestamp);
  }

  detectHandsFromImage(
    image: HTMLImageElement | HTMLCanvasElement
  ): HandLandmarkerResult {
    if (!this.handLandmarker) throw new Error("HandLandmarker not initialized");
    if (this.runningMode !== "IMAGE") {
      this.runningMode = "IMAGE";
      this.handLandmarker.setOptions({ runningMode: "IMAGE" });
    }
    return this.handLandmarker.detect(image);
  }

  static drawResults(
    ctx: CanvasRenderingContext2D,
    results: HandLandmarkerResult
  ) {
    if (!results.landmarks) return;

    const drawingUtils = new DrawingUtils(ctx);

    for (const landmarks of results.landmarks) {
      // Draw connections with a nicer color
      drawingUtils.drawConnectors(landmarks, HandLandmarker.HAND_CONNECTIONS, {
        color: "#4A90E2", // Nicer blue color
        lineWidth: 3,
      });

      // Draw landmarks with different colors for different types of points
      for (let i = 0; i < landmarks.length; i++) {
        let color;
        let size;

        // Fingertips get a different color (indices 4, 8, 12, 16, 20)
        if ([4, 8, 12, 16, 20].includes(i)) {
          color = "#FF5252"; // Red for fingertips
          size = 6;
        } else if (i === 0) {
          color = "#FFC107"; // Yellow for wrist
          size = 8;
        } else {
          color = "#69F0AE"; // Green for other landmarks
          size = 4;
        }

        drawingUtils.drawLandmarks([landmarks[i]], {
          color: color,
          lineWidth: 2,
          radius: size,
        });
      }
    }
  }
}

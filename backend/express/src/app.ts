import express from "express";
import cors from "cors";
import { config } from "@/config";
import { uploadLimiter, inferenceLimiter } from "@/middleware/rateLimiter";
import { validateRequest } from "@/middleware/validation";
import { authMiddleware } from "@/middleware/auth";
import {
  validateFileType,
  validateFileSize,
} from "@/middleware/fileValidation";
import storageRoutes from "@/routes/storage/upload";
import predictionRoutes from "@/routes/prediction";
import contributionRoutes from "@/routes/storage/contribution";
import evaluationRoutes from "@/routes/evaluation";

const app = express();

app.use(
  cors({
    origin: config.corsOrigins,
    credentials: true,
  })
);

app.use(express.json());
app.use(validateRequest);
app.use(authMiddleware);

// Routes with specific middleware
app.use(
  "/api/storage",
  uploadLimiter,
  validateFileSize(10 * 1024 * 1024), // 10MB limit
  validateFileType,
  storageRoutes
);

app.use("/api", predictionRoutes);
app.use("/api/contribution", contributionRoutes);
app.use("/api/evaluation", evaluationRoutes);
// Health check
app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

// Error handling
app.use(
  (
    err: Error,
    req: express.Request,
    res: express.Response,
    next: express.NextFunction
  ) => {
    console.error("Server error:", err);
    res.status(500).json({
      message: err.message || "Internal server error",
    });
  }
);

export default app;

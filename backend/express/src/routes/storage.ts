import express, { Request, Response, NextFunction } from "express";
import axios from "axios";
import { config } from "@/config";
import { authenticateJWT } from "../middleware/auth";
import { handleErrors } from "../middleware/errorHandler";
import { logRequest } from "../middleware/logger";
import {
  streamingLimiter,
  apiLimiter,
  statusLimiter,
  uploadLimiter,
} from "../middleware/rateLimiter";
import multer from "multer";
import FormData from "form-data";

const router = express.Router();

// Configuration for Python backend
const PYTHON_SERVICE_URL = config.pythonApiUrl;

// Configure axios with higher timeouts and no rate limiting for large uploads
// const pythonClient = axios.create({
//   timeout: 60000, // 60 seconds
//   maxContentLength: Infinity,
//   maxBodyLength: Infinity,
// });

// Configure multer for temporary storage
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 100 * 1024 * 1024, // 100MB limit (matching Python backend)
  },
});

// Enhanced logging for file uploads
const logFileUpload = (
  req: Request,
  file: Express.Multer.File,
  address?: string,
  context?: string
) => {
  console.log(`[Express] File upload received:
    - Filename: ${file.originalname}
    - Size: ${file.size} bytes
    - MIME type: ${file.mimetype}
    - User address: ${address || "Not provided"}
    - Context: ${context || "Not provided"}`);
};

// Helper function to proxy storage requests to Python backend
const proxyStorageRequest = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const url = `${PYTHON_SERVICE_URL}/storage${req.path}`;
    const method = req.method.toLowerCase();
    console.log(
      `[Express] Proxying ${method.toUpperCase()} request to: ${url}`
    );

    let requestConfig: any = {
      method,
      url,
      headers: {
        "Content-Type": "application/json",
        ...(req.headers.authorization && {
          Authorization: req.headers.authorization,
        }),
      },
    };

    // Handle request data based on method
    if (method === "get" || method === "delete") {
      requestConfig.params = req.query;
    } else {
      requestConfig.data = req.body;
    }

    const response = await axios(requestConfig);
    console.log(
      `[Express] Proxy response received with status: ${response.status}`
    );
    return res.status(response.status).json(response.data);
  } catch (error: any) {
    console.error(
      `[Express] Error proxying to Python storage endpoint: ${error.message}`,
      error.response?.data || ""
    );
    return res.status(error.response?.status || 500).json({
      success: false,
      error:
        error.response?.data?.detail ||
        error.response?.data?.error ||
        error.message ||
        "Failed to process storage request",
    });
  }
};

// Basic file upload route
router.post(
  "/upload",
  logRequest,
  authenticateJWT,
  upload.single("file"),
  async (req: Request, res: Response) => {
    try {
      if (!req.file) {
        console.error("[Express] Upload error: No file provided");
        return res.status(400).json({
          success: false,
          error: "No file provided",
        });
      }

      logFileUpload(req, req.file, req.body.wallet_address);

      // Create form data to send to Python backend
      const formData = new FormData();
      formData.append("file", req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      });

      // Add wallet address if provided
      if (req.body.wallet_address) {
        formData.append("wallet_address", req.body.wallet_address);
      }

      console.log(`[Express] Forwarding upload to Python backend`);

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/storage/upload`,
        formData,
        {
          headers: {
            ...formData.getHeaders(),
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      console.log(
        `[Express] Upload response received with status: ${response.status}`
      );
      return res.status(response.status).json({
        success: true,
        ...response.data,
      });
    } catch (error: any) {
      console.error(`[Express] Upload error: ${error.message}`);
      console.error(error.response?.data || error);

      return res.status(error.response?.status || 500).json({
        success: false,
        error:
          error.response?.data?.detail ||
          error.response?.data?.error ||
          error.message ||
          "Failed to upload file",
      });
    }
  }
);

// Staged contribution upload - Phase 1: Evaluate
router.post(
  "/evaluate",
  logRequest,
  authenticateJWT,
  uploadLimiter,
  upload.single("file"),
  async (req: Request, res: Response) => {
    try {
      if (!req.file) {
        console.error("[Express] Evaluation error: No file uploaded");
        return res.status(400).json({
          success: false,
          error: "No file uploaded",
        });
      }

      const user_address = req.body.user_address;
      if (!user_address) {
        console.error("[Express] Evaluation error: No user address provided");
        return res.status(400).json({
          success: false,
          error: "User address is required",
        });
      }

      logFileUpload(req, req.file, user_address, "evaluation");

      // Check for landmarks from client-side detection
      const landmarks = req.body.landmarks;
      if (landmarks) {
        console.log(
          `[Express] Received hand landmarks from client-side detection`
        );
      }

      // Create form data to send to Python backend
      const formData = new FormData();
      formData.append("file", req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      });
      formData.append("user_address", user_address);

      // Add landmarks if provided
      if (landmarks) {
        formData.append("landmarks", landmarks);
      }

      console.log(
        `[Express] Forwarding contribution to Python evaluation endpoint`
      );

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/storage/evaluate`,
        formData,
        {
          headers: {
            ...formData.getHeaders(),
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      console.log(`[Express] Evaluation response received:`, response.data);

      // Ensure response has success field
      if (response.data && !response.data.hasOwnProperty("success")) {
        response.data.success = true;
      }

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(`[Express] Evaluation error: ${error.message}`);
      console.error(error.response?.data || error);

      return res.status(error.response?.status || 500).json({
        success: false,
        error:
          error.response?.data?.detail ||
          error.response?.data?.error ||
          error.message ||
          "Failed to evaluate contribution",
      });
    }
  }
);

// Staged contribution upload - Phase 2: Upload
router.post(
  "/upload/:taskId",
  logRequest,
  authenticateJWT,
  uploadLimiter,
  upload.single("file"),
  async (req: Request, res: Response) => {
    try {
      const taskId = req.params.taskId;

      if (!req.file) {
        console.error("[Express] Upload error: No file uploaded");
        return res.status(400).json({
          success: false,
          error: "No file uploaded",
        });
      }

      const user_address = req.body.user_address;
      if (!user_address) {
        console.error("[Express] Upload error: No user address provided");
        return res.status(400).json({
          success: false,
          error: "User address is required",
        });
      }

      const content_hash = req.body.content_hash;
      if (!content_hash) {
        console.error("[Express] Upload error: No content hash provided");
        return res.status(400).json({
          success: false,
          error: "Content hash is required to verify file integrity",
        });
      }

      logFileUpload(req, req.file, user_address, "upload");

      // Create form data to send to Python backend
      const formData = new FormData();
      formData.append("file", req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      });
      formData.append("user_address", user_address);
      formData.append("content_hash", content_hash);

      console.log(
        `[Express] Forwarding file to Python upload endpoint for task ${taskId}`
      );

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/storage/upload/${taskId}`,
        formData,
        {
          headers: {
            ...formData.getHeaders(),
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      console.log(`[Express] Upload response received:`, response.data);

      // Check for duplicate files
      if (
        response.data?.duplicate ||
        (response.data?.error && response.data.error.includes("duplicate")) ||
        (response.data?.status === "rejected" &&
          response.data?.message?.includes("duplicate"))
      ) {
        console.log(`[Express] Duplicate file detected for task ${taskId}`);

        return res.status(200).json({
          success: false,
          error:
            "This file has already been uploaded. Please try a different image.",
          duplicate: true,
          message: "Duplicate file detected. Please try a different image.",
          status: "rejected",
        });
      }

      // Ensure response has success field
      if (response.data && !response.data.hasOwnProperty("success")) {
        response.data.success = true;
      }

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(`[Express] Upload error: ${error.message}`);
      console.error(error.response?.data || error);

      // Check for duplicate file indicators in error response
      const errorData = error.response?.data;
      if (
        errorData?.duplicate ||
        (errorData?.error && errorData.error.includes("duplicate")) ||
        (errorData?.message && errorData.message.includes("duplicate"))
      ) {
        return res.status(200).json({
          success: false,
          error:
            "This file has already been uploaded. Please try a different image.",
          duplicate: true,
          message: "Duplicate file detected. Please try a different image.",
          status: "rejected",
        });
      }

      return res.status(error.response?.status || 500).json({
        success: false,
        error:
          error.response?.data?.detail ||
          error.response?.data?.error ||
          error.message ||
          "Failed to upload contribution",
      });
    }
  }
);

// Process rewards for a contribution - Phase 3: Rewards
router.post(
  "/reward/:taskId",
  logRequest,
  authenticateJWT,
  apiLimiter,
  async (req: Request, res: Response) => {
    try {
      const taskId = req.params.taskId;
      const userAddress =
        req.body.user_address || req.body.wallet_address || req.body.address;

      console.log(`[Express] Processing rewards for task: ${taskId}`);
      console.log(`[Express] User address: ${userAddress}`);

      // Forward the request to the backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/storage/reward/${taskId}`,
        {
          user_address: userAddress,
        },
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: req.headers.authorization,
          },
        }
      );

      console.log(
        `[Express] Reward response for task ${taskId}:`,
        response.data
      );

      // Return the backend response
      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(
        `[Express] Error processing reward for task ${req.params.taskId}:`,
        error
      );

      // Return error response
      return res.status(error.response?.status || 500).json({
        success: false,
        error: error.response?.data?.error || error.message,
        message: error.response?.data?.message || "Failed to process reward",
      });
    }
  }
);

// Get evaluation status
router.get(
  "/contribution/status/:taskId",
  logRequest,
  authenticateJWT,
  statusLimiter,
  async (req: Request, res: Response) => {
    try {
      const taskId = req.params.taskId;
      console.log(`[Express] Fetching evaluation status for task: ${taskId}`);

      // Forward to Python backend
      const response = await axios.get(
        `${PYTHON_SERVICE_URL}/storage/contribution/status/${taskId}`,
        {
          headers: {
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      console.log(
        `[Express] Evaluation status received for task ${taskId}:`,
        response.data.status || "unknown status"
      );

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(
        `[Express] Error getting evaluation status: ${error.message}`
      );
      console.error(error.response?.data || error);

      return res.status(error.response?.status || 500).json({
        success: false,
        error:
          error.response?.data?.detail ||
          error.response?.data?.error ||
          error.message ||
          "Failed to get evaluation status",
      });
    }
  }
);

// Server-Sent Events for evaluation status
router.get(
  "/evaluation/status/stream/:task_id",
  logRequest,
  authenticateJWT,
  streamingLimiter,
  async (req: Request, res: Response) => {
    const { task_id } = req.params;

    if (!task_id) {
      return res.status(400).json({
        success: false,
        error: "Task ID is required",
      });
    }

    console.log(`[Express] Starting SSE stream for task: ${task_id}`);

    // Set up SSE headers
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.flushHeaders();

    // Create proxy request to Python backend
    const forwardSSE = async () => {
      try {
        // Get status from Python backend
        const response = await axios.get(
          `${PYTHON_SERVICE_URL}/storage/evaluation/status/${task_id}`,
          {
            headers: {
              ...(req.headers.authorization && {
                Authorization: req.headers.authorization,
              }),
            },
          }
        );

        // Format and send as SSE
        const data = JSON.stringify(response.data);
        res.write(`data: ${data}\n\n`);

        // If the task is completed, end the stream
        if (response.data.completed) {
          console.log(`[Express] Task ${task_id} completed, ending SSE stream`);
          clearInterval(intervalId);
          res.end();
          return;
        }
      } catch (error: any) {
        console.error(
          `[Express] SSE error for task ${task_id}: ${error.message}`
        );

        // Send error as SSE
        const errorData = {
          task_id,
          status: "error",
          message: "Error fetching evaluation status",
          error: error.message,
          completed: false,
        };

        res.write(`data: ${JSON.stringify(errorData)}\n\n`);

        // Don't end the stream on error, let it retry
      }
    };

    // Send initial status
    await forwardSSE();

    // Poll for updates every second
    const intervalId = setInterval(forwardSSE, 1000);

    // Handle client disconnect
    req.on("close", () => {
      console.log(
        `[Express] Client disconnected from SSE stream for task: ${task_id}`
      );
      clearInterval(intervalId);
    });
  }
);

router.get(
  "/files",
  logRequest,
  authenticateJWT,
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      console.log(`[Express] Listing files`);
      await proxyStorageRequest(req, res, next);
    } catch (error) {
      next(error);
    }
  }
);

// Lilypad evaluation endpoint
router.post(
  "/evaluate_lilypad",
  logRequest,
  authenticateJWT,
  uploadLimiter,
  upload.single("file"),
  async (req: Request, res: Response) => {
    try {
      if (!req.file) {
        console.error("[Express] Lilypad evaluation error: No file uploaded");
        return res.status(400).json({
          success: false,
          error: "No file uploaded",
        });
      }

      const user_address = req.body.user_address;
      if (!user_address) {
        console.error(
          "[Express] Lilypad evaluation error: No user address provided"
        );
        return res.status(400).json({
          success: false,
          error: "User address is required",
        });
      }

      logFileUpload(req, req.file, user_address, "lilypad-evaluation");

      // Check for landmarks
      const landmarks = req.body.landmarks;
      if (!landmarks) {
        console.error(
          "[Express] Lilypad evaluation error: No landmarks provided"
        );
        return res.status(400).json({
          success: false,
          error: "Landmarks are required for Lilypad evaluation",
        });
      }

      // Create form data to send to Python backend
      const formData = new FormData();
      formData.append("file", req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      });
      formData.append("user_address", user_address);
      formData.append("landmarks", landmarks);

      console.log(`[Express] Forwarding to Python Lilypad evaluation endpoint`);

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/storage/evaluate_lilypad`,
        formData,
        {
          headers: {
            ...formData.getHeaders(),
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      console.log(
        `[Express] Lilypad evaluation response received:`,
        response.data
      );

      // Ensure response has success field
      if (response.data && !response.data.hasOwnProperty("success")) {
        response.data.success = true;
      }

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(`[Express] Lilypad evaluation error: ${error.message}`);
      console.error(error.response?.data || error);

      return res.status(error.response?.status || 500).json({
        success: false,
        error:
          error.response?.data?.detail ||
          error.response?.data?.error ||
          error.message ||
          "Failed to process Lilypad evaluation",
      });
    }
  }
);

// Lilypad focus evaluation endpoint
router.post(
  "/evaluate_lilypad_focus",
  logRequest,
  authenticateJWT,
  uploadLimiter,
  upload.single("file"),
  async (req: Request, res: Response) => {
    try {
      if (!req.file) {
        console.error(
          "[Express] Lilypad focus evaluation error: No file uploaded"
        );
        return res.status(400).json({
          success: false,
          error: "No file uploaded",
        });
      }

      const user_address = req.body.user_address;
      if (!user_address) {
        console.error(
          "[Express] Lilypad focus evaluation error: No user address provided"
        );
        return res.status(400).json({
          success: false,
          error: "User address is required",
        });
      }

      logFileUpload(req, req.file, user_address, "lilypad-focus-evaluation");

      // Check for landmarks
      const landmarks = req.body.landmarks;
      if (!landmarks) {
        console.error(
          "[Express] Lilypad focus evaluation error: No landmarks provided"
        );
        return res.status(400).json({
          success: false,
          error: "Landmarks are required for Lilypad focus evaluation",
        });
      }

      // Create form data to send to Python backend
      const formData = new FormData();
      formData.append("file", req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      });
      formData.append("user_address", user_address);
      formData.append("landmarks", landmarks);

      console.log(
        `[Express] Forwarding to Python Lilypad focus evaluation endpoint`
      );

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/storage/evaluate_lilypad_focus`,
        formData,
        {
          headers: {
            ...formData.getHeaders(),
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      console.log(
        `[Express] Lilypad focus evaluation response received:`,
        response.data
      );

      // Ensure response has success field
      if (response.data && !response.data.hasOwnProperty("success")) {
        response.data.success = true;
      }

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(
        `[Express] Lilypad focus evaluation error: ${error.message}`
      );
      console.error(error.response?.data || error);

      return res.status(error.response?.status || 500).json({
        success: false,
        error:
          error.response?.data?.detail ||
          error.response?.data?.error ||
          error.message ||
          "Failed to process Lilypad focus evaluation",
      });
    }
  }
);

// Lilypad job status endpoint
router.get(
  "/lilypad/status/:jobId",
  logRequest,
  statusLimiter,
  async (req: Request, res: Response) => {
    try {
      const jobId = req.params.jobId;
      console.log(`[Express] Checking Lilypad job status for: ${jobId}`);

      // Forward to Python backend
      const response = await axios.get(
        `${PYTHON_SERVICE_URL}/storage/lilypad/status/${jobId}`,
        {
          headers: {
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      console.log(
        `[Express] Lilypad job status response received with status: ${response.status}`
      );
      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(`[Express] Lilypad job status error: ${error.message}`);

      // Special handling for 404 Not Found errors
      if (error.response?.status === 404) {
        return res.status(404).json({
          success: false,
          error: "Job not found",
        });
      }

      return res.status(error.response?.status || 500).json({
        success: false,
        error:
          error.response?.data?.detail ||
          error.response?.data?.error ||
          error.message ||
          "Failed to get Lilypad job status",
      });
    }
  }
);

// Error handler specific to storage routes
router.use((err: any, req: Request, res: Response, next: NextFunction) => {
  console.error(`[Express] Storage route error:`, err);
  res.status(err.status || 500).json({
    success: false,
    error: err.message || "An unexpected error occurred",
  });
});

// Proxy any other routes to Python backend with general API limiter
router.all(
  "/*",
  logRequest,
  authenticateJWT,
  apiLimiter,
  handleErrors(proxyStorageRequest)
);

export default router;

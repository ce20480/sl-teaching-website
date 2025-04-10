import express, { Request, Response, NextFunction } from "express";
import axios from "axios";
import { config } from "@/config";
import { authenticateJWT } from "../middleware/auth";
import { handleErrors } from "../middleware/errorHandler";
import { logRequest } from "../middleware/logger";
import multer from "multer";
import FormData from "form-data";

const router = express.Router();

// Configuration for Python backend
const PYTHON_SERVICE_URL = config.pythonApiUrl;

// Configure multer for temporary storage
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 100 * 1024 * 1024, // 100MB limit (matching Python backend)
  },
});

// Helper function to proxy storage requests to Python backend
const proxyStorageRequest = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const url = `${PYTHON_SERVICE_URL}/storage${req.path}`;
    const method = req.method.toLowerCase();

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
    return res.status(response.status).json(response.data);
  } catch (error: any) {
    console.error(
      `Error proxying to Python storage endpoint: ${error.message}`
    );
    return res.status(error.response?.status || 500).json({
      error: error.response?.data || "Failed to process storage request",
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
        return res.status(400).json({ error: "No file provided" });
      }

      console.log(
        `Received file: ${req.file.originalname}, forwarding to Python backend`
      );

      // Create form data to send to Python backend
      const formData = new FormData();
      formData.append("file", req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      });

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
          maxContentLength: Infinity,
          maxBodyLength: Infinity,
        }
      );

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(`Error uploading file: ${error.message}`);
      return res.status(error.response?.status || 500).json({
        error: error.response?.data || "Failed to upload file",
      });
    }
  }
);

// Contribution upload route
router.post(
  "/contribution",
  logRequest,
  authenticateJWT,
  upload.single("file"),
  async (req: Request, res: Response) => {
    try {
      if (!req.file) {
        return res.status(400).json({ error: "No file uploaded" });
      }

      const user_address = req.body.user_address;
      if (!user_address) {
        return res.status(400).json({ error: "User address is required" });
      }

      console.log(`Processing contribution from user: ${user_address}`);

      // Create form data to send to Python backend
      const formData = new FormData();
      formData.append("file", req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype,
      });
      formData.append("user_address", user_address);

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/storage/contribution`,
        formData,
        {
          headers: {
            ...formData.getHeaders(),
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
          maxContentLength: Infinity,
          maxBodyLength: Infinity,
        }
      );

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(`Error uploading contribution: ${error.message}`);
      return res.status(error.response?.status || 500).json({
        error: error.response?.data || "Failed to upload contribution",
      });
    }
  }
);

// Get evaluation status
router.get(
  "/evaluation/:taskId",
  logRequest,
  authenticateJWT,
  async (req: Request, res: Response) => {
    try {
      const taskId = req.params.taskId;

      // Forward to Python backend
      const response = await axios.get(
        `${PYTHON_SERVICE_URL}/storage/evaluation/${taskId}`,
        {
          headers: {
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(`Error getting evaluation status: ${error.message}`);
      return res.status(error.response?.status || 500).json({
        error: error.response?.data || "Failed to get evaluation status",
      });
    }
  }
);

// List files
router.get(
  "/files",
  logRequest,
  authenticateJWT,
  handleErrors(proxyStorageRequest)
);

// Proxy any other routes to Python backend
router.all(
  "/*",
  logRequest,
  authenticateJWT,
  handleErrors(proxyStorageRequest)
);

export default router;

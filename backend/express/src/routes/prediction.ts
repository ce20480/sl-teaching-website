import express, { Request, Response, NextFunction } from "express";
import { config } from "@/config";
import axios from "axios";
import { logRequest } from "../middleware/logger";
import { handleErrors } from "../middleware/errorHandler";
import { authenticateJWT } from "../middleware/auth";
import { validateRequestSchema } from "../middleware/validation";

// Prediction API router 
const router = express.Router();

// Configuration for Python backend
const PYTHON_SERVICE_URL = config.pythonApiUrl;

// Helper function to proxy prediction requests to Python backend
const proxyPredictionRequest = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const url = `${PYTHON_SERVICE_URL}/prediction${req.path}`;
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
      `Error proxying to Python prediction endpoint: ${error.message}`
    );
    return res.status(error.response?.status || 500).json({
      error: error.response?.data?.detail || "Failed to process prediction request",
    });
  }
};

/**
 * Route that receives landmarks from frontend and forwards to Python backend
 * POST /api/predict
 */
router.post(
  "/predict",
  logRequest,
  async (req: Request, res: Response) => {
    try {
      const { landmarks } = req.body;

      if (!landmarks || !Array.isArray(landmarks)) {
        return res.status(400).json({
          error: "Invalid landmarks data. Expected an array of coordinates.",
        });
      }

      console.log(
        "Received landmarks for prediction, forwarding to Python backend"
      );

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/prediction/predict`,
        { landmarks },
        {
          headers: {
            "Content-Type": "application/json",
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      return res.json(response.data);
    } catch (error: any) {
      console.error("Prediction error:", error.response?.data || error);
      return res.status(error.response?.status || 500).json({
        error: error.response?.data?.detail || "Failed to process prediction",
      });
    }
  }
);

/**
 * Route that receives labeled landmarks from frontend for training
 * POST /api/contribute
 */
router.post(
  "/contribute",
  logRequest,
  authenticateJWT,
  validateRequestSchema("contribution"),
  async (req: Request, res: Response) => {
    try {
      const { landmarks, label } = req.body;

      if (!landmarks || !Array.isArray(landmarks) || !label) {
        return res.status(400).json({
          error: "Invalid contribution data. Expected landmarks array and label.",
        });
      }

      console.log(
        `Received contribution for label '${label}', forwarding to Python backend`
      );

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/prediction/contribute`,
        { landmarks, label },
        {
          headers: {
            "Content-Type": "application/json",
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      return res.json(response.data);
    } catch (error: any) {
      console.error("Contribution error:", error.response?.data || error);
      return res.status(error.response?.status || 500).json({
        error: error.response?.data?.detail || "Failed to store contribution",
      });
    }
  }
);

// Proxy any other routes to Python backend
router.all(
  "/*",
  logRequest,
  authenticateJWT,
  handleErrors(proxyPredictionRequest)
);

export default router;

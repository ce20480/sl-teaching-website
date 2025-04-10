import express, { Request, Response, NextFunction } from "express";
import axios from "axios";
import { config } from "@/config";
import { authenticateJWT } from "../middleware/auth";
import { validateRequestSchema } from "../middleware/validation";
import { handleErrors } from "../middleware/errorHandler";
import { logRequest } from "../middleware/logger";

const router = express.Router();

// Configuration for Python backend
const PYTHON_SERVICE_URL = config.pythonApiUrl;

// Helper function to proxy evaluation requests to Python backend
const proxyEvaluationRequest = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    // Make sure the endpoint is correct
    const url = `${PYTHON_SERVICE_URL}/evaluation${req.path}`;
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
      `Error proxying to Python evaluation endpoint: ${error.message}`
    );
    return res.status(error.response?.status || 500).json({
      error: error.response?.data || "Failed to process evaluation request",
    });
  }
};

// Evaluation endpoints
// Apply middleware in the order: logging → authentication → validation → error handling

// GET /api/evaluation - Get all evaluations
router.get(
  "/",
  logRequest,
  authenticateJWT,
  express.json(),
  handleErrors(proxyEvaluationRequest)
);

// GET /api/evaluation/:id - Get a specific evaluation
router.get(
  "/:id",
  logRequest,
  authenticateJWT,
  express.json(),
  handleErrors(proxyEvaluationRequest)
);

// POST /api/evaluation - Create a new evaluation
router.post(
  "/",
  logRequest,
  authenticateJWT,
  express.json(),
  validateRequestSchema("evaluation"),
  handleErrors(proxyEvaluationRequest)
);

// PUT /api/evaluation/:id - Update an evaluation
router.put(
  "/:id",
  logRequest,
  authenticateJWT,
  express.json(),
  validateRequestSchema("evaluation"),
  handleErrors(proxyEvaluationRequest)
);

// DELETE /api/evaluation/:id - Delete an evaluation
router.delete(
  "/:id",
  logRequest,
  authenticateJWT,
  express.json(),
  handleErrors(proxyEvaluationRequest)
);

// Submit a solution for evaluation
router.post(
  "/:id/submit",
  logRequest,
  authenticateJWT,
  express.json(),
  validateRequestSchema("submission"),
  handleErrors(proxyEvaluationRequest)
);

// Get evaluation results
router.get(
  "/:id/results",
  logRequest,
  authenticateJWT,
  express.json(),
  handleErrors(proxyEvaluationRequest)
);

export default router;

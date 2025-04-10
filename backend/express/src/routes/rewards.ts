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

// Helper function to proxy rewards requests to Python backend
const proxyRewardsRequest = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    // Make sure the path is correct
    const url = `${PYTHON_SERVICE_URL}/rewards${req.path}`;
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
      `Error proxying to Python rewards endpoint: ${error.message}`
    );
    return res.status(error.response?.status || 500).json({
      error: error.response?.data || "Failed to process rewards request",
    });
  }
};

// XP Reward Endpoints

// Award XP
router.post(
  "/xp/award/:address",
  logRequest,
  authenticateJWT,
  express.json(),
  async (req: Request, res: Response) => {
    try {
      const { address } = req.params;
      const { activity_type = "DATASET_CONTRIBUTION" } = req.query;

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/rewards/xp/award/${address}`,
        {}, // Empty object as body
        {
          params: { activity_type },
          headers: {
            "Content-Type": "application/json",
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(`Error awarding XP: ${error.message}`);
      return res.status(error.response?.status || 500).json({
        error: error.response?.data || "Failed to award XP",
      });
    }
  }
);

// Award Custom XP
router.post(
  "/xp/award-custom/:address",
  logRequest,
  authenticateJWT,
  express.json(),
  async (req: Request, res: Response) => {
    try {
      const { address } = req.params;
      const { amount, activity_type = "DATASET_CONTRIBUTION" } = req.query;

      if (!amount || isNaN(Number(amount))) {
        return res.status(400).json({
          status: "error",
          message: "Amount must be a valid number",
          address,
        });
      }

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/rewards/xp/award-custom/${address}`,
        {}, // Empty object as body
        {
          params: { amount, activity_type },
          headers: {
            "Content-Type": "application/json",
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(`Error awarding custom XP: ${error.message}`);
      return res.status(error.response?.status || 500).json({
        error: error.response?.data || "Failed to award custom XP",
      });
    }
  }
);

// Get XP Balance
router.get(
  "/xp/balance/:address",
  logRequest,
  authenticateJWT,
  handleErrors(proxyRewardsRequest)
);

// Get Transaction Status
router.get(
  "/transactions/:txHash",
  logRequest,
  authenticateJWT,
  handleErrors(proxyRewardsRequest)
);

// Achievement Endpoints

// Mint Achievement
router.post(
  "/achievements/mint/:address",
  logRequest,
  authenticateJWT,
  express.json(),
  async (req: Request, res: Response) => {
    try {
      const { address } = req.params;
      const { achievement_type, ipfs_hash = "", description = "" } = req.query;

      if (!achievement_type) {
        return res.status(400).json({
          status: "error",
          message: "Achievement type is required",
          address,
        });
      }

      // Forward to Python backend
      const response = await axios.post(
        `${PYTHON_SERVICE_URL}/rewards/achievements/mint/${address}`,
        {}, // Empty object as body
        {
          params: { achievement_type, ipfs_hash, description },
          headers: {
            "Content-Type": "application/json",
            ...(req.headers.authorization && {
              Authorization: req.headers.authorization,
            }),
          },
        }
      );

      return res.status(response.status).json(response.data);
    } catch (error: any) {
      console.error(`Error minting achievement: ${error.message}`);
      return res.status(error.response?.status || 500).json({
        error: error.response?.data || "Failed to mint achievement",
      });
    }
  }
);

// Get User Achievements
router.get(
  "/achievements/user/:address",
  logRequest,
  authenticateJWT,
  handleErrors(proxyRewardsRequest)
);

// Get Achievement by Token ID
router.get(
  "/achievements/:tokenId",
  logRequest,
  authenticateJWT,
  handleErrors(proxyRewardsRequest)
);

// Proxy any other routes to Python backend
router.all(
  "/*",
  logRequest,
  authenticateJWT,
  express.json(),
  handleErrors(proxyRewardsRequest)
);

export default router;

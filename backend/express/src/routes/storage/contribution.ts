import express from "express";
import multer from "multer";
import axios from "axios";
import FormData from "form-data";
import { config } from "@/config";
import { validateWalletAddress } from "@/middleware/walletValidation";

const router = express.Router();

// Configure multer for temporary storage
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit
  },
});

// Handle contribution uploads
router.post(
  "/upload",
  upload.single("file"),
  validateWalletAddress,
  async (req, res) => {
    console.log("Request received:", {
      body: req.body,
      file: req.file
        ? {
            filename: req.file.originalname,
            mimetype: req.file.mimetype,
            size: req.file.size,
          }
        : null,
    });

    try {
      const { file } = req;
      const { user_address } = req.body;

      if (!file) {
        return res.status(400).json({
          success: false,
          message: "No file uploaded",
        });
      }

      // Create form data to forward to Python backend
      const formData = new FormData();
      formData.append("file", file.buffer, {
        filename: file.originalname,
        contentType: file.mimetype,
      });
      formData.append("user_address", user_address);

      // Forward to Python backend with proper headers
      const pythonResponse = await axios.post(
        `${config.pythonApiUrl}/storage/upload`,
        formData,
        {
          headers: {
            ...formData.getHeaders(),
            "Content-Length": formData.getLengthSync(),
          },
          // Stream the response for progress tracking
          onUploadProgress: (progressEvent) => {
            console.log(
              `Upload progress: ${Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              )}%`
            );
          },
        }
      );

      // Return the Python backend response
      return res.status(200).json(pythonResponse.data);
    } catch (error) {
      console.error("Upload processing error:", error);

      // Handle different error types
      if (error.response) {
        // Python backend returned an error
        return res.status(error.response.status).json({
          success: false,
          message: error.response.data.detail || "Error processing upload",
          error: error.response.data,
        });
      } else if (error.request) {
        // No response received
        return res.status(503).json({
          success: false,
          message: "Python backend service unavailable",
        });
      } else {
        // Other error
        return res.status(500).json({
          success: false,
          message: error.message || "Unknown error occurred",
        });
      }
    }
  }
);

// Check evaluation status
router.get("/status/:taskId", async (req, res) => {
  try {
    const { taskId } = req.params;

    const response = await axios.get(
      `${config.pythonApiUrl}/storage/evaluation/${taskId}`
    );
    return res.status(200).json(response.data);
  } catch (error) {
    console.error("Status check error:", error);

    if (error.response) {
      return res.status(error.response.status).json({
        success: false,
        message: error.response.data.detail || "Error checking status",
        error: error.response.data,
      });
    } else {
      return res.status(500).json({
        success: false,
        message: error.message || "Unknown error occurred",
      });
    }
  }
});

// Get user rewards history
router.get("/rewards/:userAddress", async (req, res) => {
  try {
    const { userAddress } = req.params;

    // Use utils from the middleware for validation or import separately
    // For now, let's import it just for this function
    const { utils } = require("ethers");

    // Validate address
    if (!utils.isAddress(userAddress)) {
      return res.status(400).json({
        success: false,
        message: "Invalid wallet address format",
      });
    }

    // Also fix this line - it's using an undefined variable
    // const [achievementsResponse, xpResponse] = await Promise.all([
    //   axios.get(`${PYTHON_API_URL}/rewards/achievements/${userAddress}`),
    //   axios.get(`${PYTHON_API_URL}/rewards/xp/${userAddress}`),
    // ]);

    // Change to:
    const [achievementsResponse, xpResponse] = await Promise.all([
      axios.get(`${config.pythonApiUrl}/rewards/achievements/${userAddress}`),
      axios.get(`${config.pythonApiUrl}/rewards/xp/${userAddress}`),
    ]);

    return res.status(200).json({
      achievements: achievementsResponse.data,
      xp: xpResponse.data,
    });
  } catch (error) {
    console.error("Rewards history error:", error);

    if (error.response) {
      return res.status(error.response.status).json({
        success: false,
        message: error.response.data.detail || "Error fetching rewards",
        error: error.response.data,
      });
    } else {
      return res.status(500).json({
        success: false,
        message: error.message || "Unknown error occurred",
      });
    }
  }
});

router.get("/test", (req, res) => {
  res.json({ message: "Contribution route is working" });
});

export default router;

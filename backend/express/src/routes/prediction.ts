import express from "express";
import { config } from "@/config";
import axios from "axios";

const router = express.Router();

/**
 * Route that receives landmarks from frontend and forwards to Python backend
 * POST /api/predict
 */
router.post("/predict", async (req, res) => {
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
      `${config.pythonApiUrl}/api/prediction/predict`,
      { landmarks },
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    console.log("Python response:", response.data);
    res.json(response.data);
  } catch (error) {
    console.error("Prediction error:", error.response?.data || error);
    res.status(error.response?.status || 500).json({
      message: error.response?.data?.detail || "Failed to process prediction",
    });
  }
});

/**
 * Route that receives labeled landmarks from frontend for training
 * POST /api/contribute
 */
router.post("/contribute", async (req, res) => {
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
      `${config.pythonApiUrl}/api/prediction/contribute`,
      { landmarks, label },
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    console.log("Python response:", response.data);
    res.json(response.data);
  } catch (error) {
    console.error("Contribution error:", error.response?.data || error);
    res.status(error.response?.status || 500).json({
      message: error.response?.data?.detail || "Failed to store contribution",
    });
  }
});

export default router;

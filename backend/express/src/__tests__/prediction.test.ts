import request from "supertest";
import axios from "axios";
import app from "../app";

// Mock axios
jest.mock("axios");
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe("Prediction Routes", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("POST /api/predict", () => {
    it("should forward landmarks to Python backend and return prediction", async () => {
      // Test landmarks data
      const landmarksData = {
        landmarks: [0.1, 0.2, 0.3, 0.4, 0.5],
      };

      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          letter: "A",
          confidence: 0.95,
          landmarks: landmarksData.landmarks,
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app)
        .post("/api/predict")
        .send(landmarksData);

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining("/prediction/predict"),
        landmarksData,
        expect.any(Object)
      );
    });

    it("should return 400 when landmarks data is invalid", async () => {
      // Invalid landmarks data (not an array)
      const invalidData = {
        landmarks: "not an array",
      };

      // Make request to Express endpoint
      const response = await request(app)
        .post("/api/predict")
        .send(invalidData);

      // Assertions
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty(
        "error",
        "Invalid landmarks data. Expected an array of coordinates."
      );
      // Should not have called the Python backend
      expect(mockedAxios.post).not.toHaveBeenCalled();
    });

    it("should handle errors from the Python backend", async () => {
      // Test landmarks data
      const landmarksData = {
        landmarks: [0.1, 0.2, 0.3, 0.4, 0.5],
      };

      // Mock error response
      mockedAxios.post.mockRejectedValueOnce({
        response: {
          status: 500,
          data: { detail: "Internal server error" },
        },
      });

      // Make request to Express endpoint
      const response = await request(app)
        .post("/api/predict")
        .send(landmarksData);

      // Assertions
      expect(response.status).toBe(500);
      expect(response.body).toHaveProperty("error");
    });
  });

  describe("POST /api/contribute", () => {
    it("should forward labeled landmarks to Python backend", async () => {
      // Test contribution data
      const contributionData = {
        landmarks: [[0.1, 0.2, 0.3, 0.4, 0.5]],
        label: "A",
      };

      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          success: true,
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app)
        .post("/api/contribute")
        .send(contributionData);

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining("/prediction/contribute"),
        contributionData,
        expect.any(Object)
      );
    });

    it("should return 400 when contribution data is invalid", async () => {
      // Invalid contribution data (missing label)
      const invalidData = {
        landmarks: [[0.1, 0.2, 0.3]],
        // No label provided
      };

      // Make request to Express endpoint
      const response = await request(app)
        .post("/api/contribute")
        .send(invalidData);

      // Assertions
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty(
        "error",
        "Invalid contribution data. Expected landmarks array and label."
      );
      // Should not have called the Python backend
      expect(mockedAxios.post).not.toHaveBeenCalled();
    });

    it("should handle errors from the Python backend", async () => {
      // Test contribution data
      const contributionData = {
        landmarks: [[0.1, 0.2, 0.3]],
        label: "A",
      };

      // Mock error response
      mockedAxios.post.mockRejectedValueOnce({
        response: {
          status: 500,
          data: { detail: "Failed to store contribution" },
        },
      });

      // Make request to Express endpoint
      const response = await request(app)
        .post("/api/contribute")
        .send(contributionData);

      // Assertions
      expect(response.status).toBe(500);
      expect(response.body).toHaveProperty("error");
    });
  });
});

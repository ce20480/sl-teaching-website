import request from "supertest";
import axios from "axios";
import app from "../app";

// Mock axios
jest.mock("axios");
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe("Evaluation Routes", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("GET /api/evaluation", () => {
    it("should proxy the request to the Python backend and return the response", async () => {
      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          evaluations: [
            { id: "123", status: "completed", score: 0.95 },
            { id: "456", status: "pending", score: 0 },
          ],
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app).get("/api/evaluation");

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining("/api/evaluation"),
        expect.any(Object)
      );
    });

    it("should handle errors from the Python backend", async () => {
      // Mock error response
      mockedAxios.get.mockRejectedValueOnce({
        response: {
          status: 500,
          data: { detail: "Internal server error" },
        },
      });

      // Make request to Express endpoint
      const response = await request(app).get("/api/evaluation");

      // Assertions
      expect(response.status).toBe(500);
      expect(response.body).toHaveProperty("error");
    });
  });

  describe("GET /api/evaluation/:id", () => {
    it("should get a specific evaluation", async () => {
      const evaluationId = "123";

      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          id: evaluationId,
          status: "completed",
          score: 0.95,
          feedback: "Great job!",
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app).get(
        `/api/evaluation/${evaluationId}`
      );

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining(`/api/evaluation/${evaluationId}`),
        expect.any(Object)
      );
    });
  });

  describe("POST /api/evaluation", () => {
    it("should create a new evaluation", async () => {
      const evaluationData = {
        name: "Test Evaluation",
        description: "This is a test evaluation",
        criteria: { accuracy: 0.7, completeness: 0.3 },
      };

      // Mock successful response from Python backend
      const mockResponse = {
        status: 201,
        data: {
          id: "789",
          ...evaluationData,
          created_at: "2023-06-15T10:30:00Z",
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app)
        .post("/api/evaluation")
        .send(evaluationData);

      // Assertions
      expect(response.status).toBe(201);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining("/api/evaluation"),
        evaluationData,
        expect.any(Object)
      );
    });
  });

  describe("POST /api/evaluation/:id/submit", () => {
    it("should submit a solution for evaluation", async () => {
      const evaluationId = "123";
      const submissionData = {
        solution: "Test solution",
        user_id: "user123",
      };

      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          id: "sub456",
          evaluation_id: evaluationId,
          ...submissionData,
          status: "submitted",
          created_at: "2023-06-15T10:30:00Z",
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app)
        .post(`/api/evaluation/${evaluationId}/submit`)
        .send(submissionData);

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining(`/api/evaluation/${evaluationId}/submit`),
        submissionData,
        expect.any(Object)
      );
    });
  });
});

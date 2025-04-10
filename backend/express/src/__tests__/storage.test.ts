import request from "supertest";
import axios from "axios";
import app from "../app";

// Mock axios
jest.mock("axios");
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe("Storage Routes", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("GET /api/storage/files", () => {
    it("should proxy the request to the Python backend and return the response", async () => {
      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          files: [
            { id: "123", name: "test.jpg", size: 1024 },
            { id: "456", name: "image.png", size: 2048 },
          ],
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app).get("/api/storage/files");

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining("/storage/files"),
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
      const response = await request(app).get("/api/storage/files");

      // Assertions
      expect(response.status).toBe(500);
      expect(response.body).toHaveProperty("error");
    });
  });

  describe("POST /api/storage/upload", () => {
    it("should handle file uploads and proxy to Python backend", async () => {
      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          message: "File uploaded successfully",
          filename: "test.jpg",
          size: 1024,
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint with file
      const response = await request(app)
        .post("/api/storage/upload")
        .attach("file", Buffer.from("test file content"), "test.jpg");

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining("/storage/upload"),
        expect.any(Object), // FormData object
        expect.any(Object) // Config object
      );
    });

    it("should return 400 when no file is provided", async () => {
      // Make request without file
      const response = await request(app).post("/api/storage/upload");

      // Assertions
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty("error", "No file provided");
    });
  });

  describe("POST /api/storage/contribution/upload", () => {
    it("should handle contribution uploads with user address", async () => {
      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          success: true,
          message: "File uploaded and submitted for evaluation",
          task_id: "123e4567-e89b-12d3-a456-426614174000",
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint with file and user_address
      const response = await request(app)
        .post("/api/storage/contribution/upload")
        .field("user_address", "0x123456789abcdef")
        .attach("file", Buffer.from("test contribution"), "contrib.jpg");

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining("/storage/contribution/upload"),
        expect.any(Object), // FormData object
        expect.any(Object) // Config object
      );
    });

    it("should return 400 when no user_address is provided", async () => {
      // Make request without user_address
      const response = await request(app)
        .post("/api/storage/contribution/upload")
        .attach("file", Buffer.from("test contribution"), "contrib.jpg");

      // Assertions
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty(
        "error",
        "User address is required for contribution uploads"
      );
    });
  });

  describe("GET /api/storage/evaluation/:taskId", () => {
    it("should get evaluation status for a task", async () => {
      const taskId = "123e4567-e89b-12d3-a456-426614174000";

      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          task_id: taskId,
          status: "completed",
          score: 0.95,
          feedback: "Great submission!",
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app).get(
        `/api/storage/evaluation/${taskId}`
      );

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining(`/storage/evaluation/${taskId}`),
        expect.any(Object)
      );
    });
  });
});

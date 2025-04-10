import request from "supertest";
import axios from "axios";
import app from "../app";

// Mock axios
jest.mock("axios");
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe("Rewards Routes", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("POST /api/rewards/xp/award/:address", () => {
    it("should award XP to a user", async () => {
      const address = "0x123456789abcdef";
      const activityType = "DATASET_CONTRIBUTION";

      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          status: "processing",
          message:
            "XP award initiated - check transaction status endpoint for confirmation",
          address,
          activity_type: activityType,
          transaction_status: "pending",
          tx_hash: "0xabcdef1234567890",
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app)
        .post(`/api/rewards/xp/award/${address}`)
        .query({ activity_type: activityType });

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining(`/rewards/xp/award/${address}`),
        null,
        expect.objectContaining({
          params: { activity_type: activityType },
        })
      );
    });

    it("should handle errors from the Python backend", async () => {
      const address = "0x123456789abcdef";

      // Mock error response
      mockedAxios.post.mockRejectedValueOnce({
        response: {
          status: 500,
          data: { error: "Failed to award XP" },
        },
      });

      // Make request to Express endpoint
      const response = await request(app).post(
        `/api/rewards/xp/award/${address}`
      );

      // Assertions
      expect(response.status).toBe(500);
      expect(response.body).toHaveProperty("error");
    });
  });

  describe("POST /api/rewards/xp/award-custom/:address", () => {
    it("should award custom XP amount to a user", async () => {
      const address = "0x123456789abcdef";
      const amount = 100;

      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          status: "processing",
          message: "Custom XP award initiated",
          address,
          amount,
          tx_hash: "0xabcdef1234567890",
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app)
        .post(`/api/rewards/xp/award-custom/${address}`)
        .query({ amount });

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining(`/rewards/xp/award-custom/${address}`),
        null,
        expect.objectContaining({
          params: { amount, activity_type: "DATASET_CONTRIBUTION" },
        })
      );
    });

    it("should validate amount parameter", async () => {
      const address = "0x123456789abcdef";

      // Make request with invalid amount
      const response = await request(app)
        .post(`/api/rewards/xp/award-custom/${address}`)
        .query({ amount: "invalid" });

      // Assertions
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty("status", "error");
      expect(response.body).toHaveProperty(
        "message",
        "Amount must be a valid number"
      );
    });
  });

  describe("GET /api/rewards/xp/balance/:address", () => {
    it("should get XP balance for a user", async () => {
      const address = "0x123456789abcdef";

      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          address,
          balance: 500,
          last_updated: "2023-06-15T10:30:00Z",
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app).get(
        `/api/rewards/xp/balance/${address}`
      );

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining(`/rewards/xp/balance/${address}`),
        expect.any(Object)
      );
    });
  });

  describe("GET /api/rewards/achievements/user/:address", () => {
    it("should get achievements for a user", async () => {
      const address = "0x123456789abcdef";

      // Mock successful response from Python backend
      const mockResponse = {
        status: 200,
        data: {
          address,
          achievements: [
            {
              id: 1,
              type: "FIRST_CONTRIBUTION",
              awarded_at: "2023-05-10T14:30:00Z",
            },
            {
              id: 2,
              type: "TEN_CONTRIBUTIONS",
              awarded_at: "2023-06-01T09:15:00Z",
            },
          ],
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      // Make request to Express endpoint
      const response = await request(app).get(
        `/api/rewards/achievements/user/${address}`
      );

      // Assertions
      expect(response.status).toBe(200);
      expect(response.body).toEqual(mockResponse.data);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining(`/rewards/achievements/user/${address}`),
        expect.any(Object)
      );
    });
  });
});

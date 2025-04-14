import rateLimit from "express-rate-limit";
import { Request, Response } from "express";

// Use a more permissive rate limiter for the contribution workflow
export const uploadLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 30, // Limit each IP to 30 uploads per window
  message: "Too many uploads from this IP, please try again later",
  standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
  legacyHeaders: false, // Disable the `X-RateLimit-*` headers
});

// Higher limit for inference to accommodate client-side hand detection
export const inferenceLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 50, // Limit each IP to 50 inference requests per minute
  message: "Too many inference requests, please try again later",
  standardHeaders: true,
  legacyHeaders: false,
});

// More restrictive limiter for Server-Sent Events
export const streamingLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 5, // Limit each IP to 5 SSE connections per minute
  message: {
    success: false,
    error: "Too many SSE connections. Please try again later.",
  },
  standardHeaders: true, // Return rate limit info in the RateLimit-* headers
  legacyHeaders: false,
  keyGenerator: (req: Request) => {
    const taskId = req.params.task_id || "unknown";
    return `${req.ip}-sse-${taskId}`;
  },
  handler: (req: Request, res: Response) => {
    console.log(
      `[Express] Rate limit exceeded for SSE stream by IP: ${req.ip}`
    );
    res.status(429).json({
      success: false,
      error: "Too many SSE connections. Please try again later.",
    });
  },
});

// General API rate limiter
export const apiLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 30, // Limit each IP to 30 requests per minute
  message: {
    success: false,
    error: "Too many requests. Please try again later.",
  },
  standardHeaders: true,
  legacyHeaders: false,
  handler: (req: Request, res: Response) => {
    console.log(
      `[Express] Rate limit exceeded for API by IP: ${req.ip}, path: ${req.path}`
    );
    res.status(429).json({
      success: false,
      error: "Too many requests. Please try again later.",
    });
  },
});

// Status endpoint specific limiter with higher limits
export const statusLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 60, // Allow more status checks (60 per minute)
  message: {
    success: false,
    error: "Too many status checks. Please try again later.",
  },
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req: Request) => {
    const taskId = req.params.taskId || "unknown";
    return `${req.ip}-status-${taskId}`;
  },
  handler: (req: Request, res: Response) => {
    console.log(
      `[Express] Rate limit exceeded for status checks by IP: ${req.ip}, task: ${req.params.taskId}`
    );
    res.status(429).json({
      success: false,
      error: "Too many status checks. Please try again later.",
    });
  },
});

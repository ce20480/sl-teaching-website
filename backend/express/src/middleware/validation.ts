import { Request, Response, NextFunction } from "express";

// Basic middleware for all requests
export const validateRequest = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  // Basic request validation - can be expanded based on needs
  if (req.method === "POST" && !req.headers["content-type"]) {
    return res.status(400).json({ error: "Content-Type header is required" });
  }
  next();
};

// Schema-specific validation for routes
export const validateRequestSchema = (schema: string) => {
  return (req: Request, res: Response, next: NextFunction) => {
    // TODO: Implement schema validation logic
    console.log(`Validating request against schema: ${schema}`);
    next();
  };
};

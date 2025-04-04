import { Request, Response, NextFunction } from "express";
import { utils } from "ethers";

/**
 * Middleware to validate Ethereum wallet addresses
 */
export const validateWalletAddress = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const { user_address } = req.body;

  if (!user_address) {
    return res.status(400).json({
      success: false,
      message: "Wallet address is required",
    });
  }

  // Basic validation - check if it's a valid Ethereum address format
  if (!utils.isAddress(user_address)) {
    return res.status(400).json({
      success: false,
      message: "Invalid wallet address format",
    });
  }

  next();
};

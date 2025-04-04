import { execSync } from "child_process";
import { mkdirSync, existsSync } from "fs";
import { join } from "path";

// Ensure contracts are compiled with Hardhat
console.log("Compiling contracts...");
execSync("npx hardhat compile", { stdio: "inherit" });

// Create frontend/src/contracts/types directory if it doesn't exist
const typesDir = join(__dirname, "../frontend/src/contracts/types");
if (!existsSync(typesDir)) {
  console.log("Creating types directory...");
  mkdirSync(typesDir, { recursive: true });
}

// Copy generated types to frontend
console.log("Copying types to frontend...");
execSync("cp -r typechain-types/* frontend/src/contracts/types/", {
  stdio: "inherit",
});

console.log("Types generation complete!");

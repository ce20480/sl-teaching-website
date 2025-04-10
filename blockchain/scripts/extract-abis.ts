import fs from "fs";
import path from "path";

// Paths
const artifactsDir = path.join(__dirname, "../artifacts/contracts");
const abiDir = path.join(__dirname, "../contracts");

// Ensure ABI directory exists
if (!fs.existsSync(abiDir)) {
  fs.mkdirSync(abiDir, { recursive: true });
}

// Extract ABI for AchievementToken
const achievementTokenPath = path.join(
  artifactsDir,
  "AchievementToken.sol/AchievementToken.json"
);
if (fs.existsSync(achievementTokenPath)) {
  const artifact = JSON.parse(fs.readFileSync(achievementTokenPath, "utf8"));
  fs.writeFileSync(
    path.join(abiDir, "AchievementToken.json"),
    JSON.stringify({ abi: artifact.abi }, null, 2)
  );
  console.log("Extracted AchievementToken ABI");
}

// Extract ABI for ASLExperienceToken
const xpTokenPath = path.join(
  artifactsDir,
  "ASLExperienceToken.sol/ASLExperienceToken.json"
);
if (fs.existsSync(xpTokenPath)) {
  const artifact = JSON.parse(fs.readFileSync(xpTokenPath, "utf8"));
  fs.writeFileSync(
    path.join(abiDir, "ASLExperienceToken.json"),
    JSON.stringify({ abi: artifact.abi }, null, 2)
  );
  console.log("Extracted ASLExperienceToken ABI");
}

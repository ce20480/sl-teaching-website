import { ethers } from "hardhat";
import dotenv from "dotenv";

dotenv.config();

async function main() {
  console.log("Getting deployer account...");
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);

  console.log("Deploying AchievementToken contract...");
  const AchievementToken = await ethers.getContractFactory("AchievementToken");
  const achievementToken = await AchievementToken.deploy();

  await achievementToken.deployed();
  console.log("AchievementToken deployed to:", achievementToken.address);
  console.log("Transaction hash:", achievementToken.deployTransaction.hash);

  // Wait for just 1 confirmation for local testing
  await achievementToken.deployTransaction.wait(1);
  console.log("Achievement contract confirmed on network");

  console.log("Deploying XP Token contract...");
  const XPToken = await ethers.getContractFactory("ASLExperienceToken");
  const xpToken = await XPToken.deploy();

  await xpToken.deployed();
  console.log(`XP Token deployed to: ${xpToken.address}`);

  // If needed, set up the contracts to interact with each other
  console.log("Setting up contract permissions...");
  const minterRole = await xpToken.MINTER_ROLE();
  const tx = await xpToken.grantRole(minterRole, achievementToken.address);
  await tx.wait(1); // Again, just 1 confirmation for local

  console.log("Deployment complete!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

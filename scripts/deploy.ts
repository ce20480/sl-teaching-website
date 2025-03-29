import { ethers } from "hardhat";
import { config } from "dotenv";

config();

async function main() {
  console.log("Deploying AchievementToken contract...");

  const AchievementToken = await ethers.getContractFactory("AchievementToken");
  const achievementToken = await AchievementToken.deploy();

  await achievementToken.deployed();

  console.log("AchievementToken deployed to:", achievementToken.address);
  console.log("Transaction hash:", achievementToken.deployTransaction.hash);

  // Wait for a few block confirmations
  await achievementToken.deployTransaction.wait(5);
  console.log("Contract confirmed on network");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  }); 
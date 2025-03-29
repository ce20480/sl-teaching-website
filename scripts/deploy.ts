import { ethers } from "hardhat";
import { config } from "dotenv";

config();

async function main() {
  console.log("Deploying ASL Achievement Token...");

  // Get the contract factory
  const ASLAchievementToken = await ethers.getContractFactory("ASLAchievementToken");
  
  // Deploy the contract
  const achievementToken = await ASLAchievementToken.deploy();
  
  // Wait for deployment to complete
  await achievementToken.deployed();
  
  console.log("ASL Achievement Token deployed to:", achievementToken.address);
  
  // Set initial metadata URIs for achievement types
  const metadataURIs = {
    CONTRIBUTOR: "ipfs://Qm...", // Replace with actual IPFS URI
    EXPERT: "ipfs://Qm...",
    COMMUNITY: "ipfs://Qm...",
    INNOVATOR: "ipfs://Qm..."
  };

  // Update metadata URIs
  for (const [type, uri] of Object.entries(metadataURIs)) {
    await achievementToken.updateAchievementMetadata(
      type,
      uri
    );
    console.log(`Updated metadata URI for ${type}`);
  }

  // Grant minter role to the backend service
  const backendAddress = process.env.BACKEND_ADDRESS;
  if (backendAddress) {
    await achievementToken.grantMinterRole(backendAddress);
    console.log(`Granted minter role to backend at ${backendAddress}`);
  }
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
}); 
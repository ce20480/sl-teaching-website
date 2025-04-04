import { expect } from "chai";
import { ethers } from "hardhat";
import { SignerWithAddress } from "@nomiclabs/hardhat-ethers/signers";
import { AchievementToken, ASLExperienceToken } from "../typechain-types";

describe("ASL Token Integration", function () {
  let achievementToken: AchievementToken;
  let xpToken: ASLExperienceToken;
  let owner: SignerWithAddress;
  let user: SignerWithAddress;

  beforeEach(async function () {
    [owner, user] = await ethers.getSigners();

    // Deploy contracts
    const AchievementFactory = await ethers.getContractFactory(
      "AchievementToken"
    );
    achievementToken = await AchievementFactory.deploy();
    await achievementToken.deployed();

    const XPFactory = await ethers.getContractFactory("ASLExperienceToken");
    xpToken = await XPFactory.deploy();
    await xpToken.deployed();

    // Grant minter role to the achievement contract
    const minterRole = await xpToken.MINTER_ROLE();
    await xpToken.grantRole(minterRole, achievementToken.address);
  });

  it("Should award XP tokens for contributions", async function () {
    // Grant minter role to owner for testing
    const minterRole = await achievementToken.MINTER_ROLE();
    await achievementToken.grantRole(minterRole, owner.address);

    // Mint achievement (0 = BEGINNER type)
    await achievementToken.mintAchievement(
      user.address,
      0, // Achievement type
      "ipfs://test-hash",
      "Test achievement"
    );

    // Check if user has the achievement
    const achievements = await achievementToken.getUserAchievements(
      user.address
    );
    expect(achievements.length).to.equal(1);

    // Award XP directly (for testing purposes)
    await xpToken.awardXP(user.address, 1); // 1 = DATASET_CONTRIBUTION

    // Check if user has XP balance - Fixed to work with BigNumber
    const balance = await xpToken.balanceOf(user.address);
    expect(balance.gt(0)).to.be.true;
  });
});

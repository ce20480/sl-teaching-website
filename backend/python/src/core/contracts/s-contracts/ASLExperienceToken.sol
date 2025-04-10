// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title ASLExperienceToken
 * @dev ERC20 token for rewarding users learning ASL and contributing to the dataset
 */
contract ASLExperienceToken is ERC20, ERC20Burnable, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    
    // Different activities that earn XP
    enum ActivityType {
        LESSON_COMPLETION,
        DATASET_CONTRIBUTION,
        DAILY_PRACTICE,
        QUIZ_COMPLETION,
        ACHIEVEMENT_EARNED
    }
    
    // Mapping to store XP rates for different activities
    mapping(ActivityType => uint256) public activityRewards;
    
    // Event emitted when XP is awarded
    event ExperienceEarned(address indexed user, uint256 amount, ActivityType activityType);
    
    // Event emitted when reward rates are updated
    event RewardRateUpdated(ActivityType activityType, uint256 newRate);

    constructor() ERC20("ASL Experience Points", "ASLXP") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        
        // Set initial XP reward rates
        activityRewards[ActivityType.LESSON_COMPLETION] = 50 * 10**decimals();
        activityRewards[ActivityType.DATASET_CONTRIBUTION] = 100 * 10**decimals();
        activityRewards[ActivityType.DAILY_PRACTICE] = 20 * 10**decimals();
        activityRewards[ActivityType.QUIZ_COMPLETION] = 30 * 10**decimals();
        activityRewards[ActivityType.ACHIEVEMENT_EARNED] = 200 * 10**decimals();
    }
    
    /**
     * @dev Awards XP to a user for completing an activity
     * @param to The user being awarded XP
     * @param activityType The type of activity completed
     */
    function awardXP(address to, ActivityType activityType) external onlyRole(MINTER_ROLE) {
        uint256 rewardAmount = activityRewards[activityType];
        _mint(to, rewardAmount);
        emit ExperienceEarned(to, rewardAmount, activityType);
    }
    
    /**
     * @dev Awards a custom amount of XP to a user
     * @param to The user being awarded XP
     * @param amount The amount of XP to award
     * @param activityType The type of activity completed
     */
    function awardCustomXP(address to, uint256 amount, ActivityType activityType) 
        external 
        onlyRole(MINTER_ROLE) 
    {
        _mint(to, amount);
        emit ExperienceEarned(to, amount, activityType);
    }
    
    /**
     * @dev Updates the reward rate for an activity type
     * @param activityType The activity type to update
     * @param newRate The new reward rate
     */
    function updateRewardRate(ActivityType activityType, uint256 newRate) 
        external 
        onlyRole(ADMIN_ROLE) 
    {
        activityRewards[activityType] = newRate;
        emit RewardRateUpdated(activityType, newRate);
    }
    
    /**
     * @dev Burns XP from a user (for potential future use cases)
     * @param from The user to burn XP from
     * @param amount The amount to burn
     */
    function burnFrom(address from, uint256 amount) 
        public 
        override 
        onlyRole(MINTER_ROLE) 
    {
        super.burnFrom(from, amount);
    }
    
    // Overrides required by Solidity
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
} 
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/utils/Strings.sol";
import "@openzeppelin/contracts/utils/Base64.sol";

/**
 * @title ASLAchievementToken
 * @dev Implementation of ERC4973 (Soulbound Token) for ASL achievements
 */
contract ASLAchievementToken is ERC721, AccessControl {
    using Counters for Counters.Counter;
    using Strings for uint256;

    // Role definitions
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");

    // Achievement types
    enum AchievementType {
        CONTRIBUTOR,    // Basic contribution
        EXPERT,         // High quality contributions
        COMMUNITY,      // Community engagement
        INNOVATOR       // Novel contributions
    }

    // Achievement metadata structure
    struct Achievement {
        AchievementType achievementType;
        uint256 timestamp;
        string metadataURI;
        string description;
    }

    // Token counter
    Counters.Counter private _tokenIds;

    // Mapping from token ID to Achievement
    mapping(uint256 => Achievement) public achievements;
    
    // Mapping from user address to their achievement count
    mapping(address => uint256) public userAchievementCount;
    
    // Mapping from user address to array of their token IDs
    mapping(address => uint256[]) public userTokens;
    
    // Mapping from achievement type to IPFS metadata URI
    mapping(AchievementType => string) public achievementMetadataURIs;

    // Events
    event AchievementMinted(
        address indexed to,
        uint256 indexed tokenId,
        AchievementType achievementType
    );
    event AchievementMetadataUpdated(
        AchievementType indexed achievementType,
        string newMetadataURI
    );
    event AdminRoleGranted(address indexed account);
    event MinterRoleGranted(address indexed account);

    constructor() ERC721("ASL Achievement Token", "ASL") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
    }

    /**
     * @dev Mints a new achievement token
     * @param to The address to receive the token
     * @param achievementType The type of achievement
     * @param description Description of the achievement
     */
    function mintAchievement(
        address to,
        AchievementType achievementType,
        string memory description
    ) external onlyRole(MINTER_ROLE) returns (uint256) {
        require(to != address(0), "Invalid recipient address");
        
        _tokenIds.increment();
        uint256 newTokenId = _tokenIds.current();

        // Create achievement metadata
        Achievement memory achievement = Achievement({
            achievementType: achievementType,
            timestamp: block.timestamp,
            metadataURI: achievementMetadataURIs[achievementType],
            description: description
        });

        // Store achievement data
        achievements[newTokenId] = achievement;
        
        // Update user mappings
        userAchievementCount[to]++;
        userTokens[to].push(newTokenId);

        // Mint the token
        _safeMint(to, newTokenId);

        emit AchievementMinted(to, newTokenId, achievementType);
        return newTokenId;
    }

    /**
     * @dev Updates metadata URI for an achievement type
     * @param achievementType The type of achievement
     * @param newMetadataURI New IPFS metadata URI
     */
    function updateAchievementMetadata(
        AchievementType achievementType,
        string memory newMetadataURI
    ) external onlyRole(ADMIN_ROLE) {
        achievementMetadataURIs[achievementType] = newMetadataURI;
        emit AchievementMetadataUpdated(achievementType, newMetadataURI);
    }

    /**
     * @dev Returns all achievements for a user
     * @param user The user address
     * @return Array of token IDs
     */
    function getUserAchievements(address user) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return userTokens[user];
    }

    /**
     * @dev Returns achievement count for a user
     * @param user The user address
     * @return Number of achievements
     */
    function getUserAchievementCount(address user) 
        external 
        view 
        returns (uint256) 
    {
        return userAchievementCount[user];
    }

    /**
     * @dev Returns achievement details for a token
     * @param tokenId The token ID
     * @return Achievement struct
     */
    function getAchievement(uint256 tokenId) 
        external 
        view 
        returns (Achievement memory) 
    {
        require(_exists(tokenId), "Token does not exist");
        return achievements[tokenId];
    }

    /**
     * @dev Override transfer functions to make token soulbound
     */
    function transferFrom(
        address from,
        address to,
        uint256 tokenId
    ) public virtual override {
        revert("Soulbound token cannot be transferred");
    }

    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId
    ) public virtual override {
        revert("Soulbound token cannot be transferred");
    }

    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId,
        bytes memory data
    ) public virtual override {
        revert("Soulbound token cannot be transferred");
    }

    /**
     * @dev Returns the token URI with metadata
     * @param tokenId The token ID
     * @return Token URI
     */
    function tokenURI(uint256 tokenId) 
        public 
        view 
        override 
        returns (string memory) 
    {
        require(_exists(tokenId), "Token does not exist");
        
        Achievement memory achievement = achievements[tokenId];
        
        // Create metadata JSON
        string memory json = Base64.encode(
            bytes(
                string(
                    abi.encodePacked(
                        '{"name": "ASL Achievement #',
                        tokenId.toString(),
                        '","description": "',
                        achievement.description,
                        '","type": "',
                        _getAchievementTypeString(achievement.achievementType),
                        '","timestamp": ',
                        achievement.timestamp.toString(),
                        ',"image": "',
                        achievement.metadataURI,
                        '"}'
                    )
                )
            )
        );
        
        return string(abi.encodePacked("data:application/json;base64,", json));
    }

    /**
     * @dev Helper function to convert AchievementType to string
     */
    function _getAchievementTypeString(AchievementType _type) 
        internal 
        pure 
        returns (string memory) 
    {
        if (_type == AchievementType.CONTRIBUTOR) return "Contributor";
        if (_type == AchievementType.EXPERT) return "Expert";
        if (_type == AchievementType.COMMUNITY) return "Community";
        if (_type == AchievementType.INNOVATOR) return "Innovator";
        return "Unknown";
    }

    /**
     * @dev Grant admin role
     * @param account The account to grant the role to
     */
    function grantAdminRole(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _grantRole(ADMIN_ROLE, account);
        emit AdminRoleGranted(account);
    }

    /**
     * @dev Grant minter role
     * @param account The account to grant the role to
     */
    function grantMinterRole(address account) external onlyRole(ADMIN_ROLE) {
        _grantRole(MINTER_ROLE, account);
        emit MinterRoleGranted(account);
    }
} 
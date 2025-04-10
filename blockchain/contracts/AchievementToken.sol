// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title AchievementToken
 * @dev Implementation of the ERC4973 Soulbound Token for ASL achievements
 */
contract AchievementToken is ERC721, AccessControl {
    using Counters for Counters.Counter;
    using Strings for uint256;

    // Role definitions
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");

    // Achievement types
    enum AchievementType {
        BEGINNER,
        INTERMEDIATE,
        ADVANCED,
        EXPERT,
        MASTER
    }

    // Achievement struct
    struct Achievement {
        AchievementType achievementType;
        string ipfsHash;  // IPFS hash for metadata
        uint256 timestamp;
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

    // Events
    event AchievementMinted(
        address indexed to,
        uint256 indexed tokenId,
        AchievementType achievementType,
        string ipfsHash
    );
    
    event AchievementMetadataUpdated(
        uint256 indexed tokenId,
        string newIpfsHash
    );

    constructor() ERC721("ASL Achievement Token", "ASL") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
    }

    /**
     * @dev Mints a new achievement token
     * @param to Address to receive the token
     * @param achievementType Type of achievement
     * @param ipfsHash IPFS hash containing metadata
     * @param description Description of the achievement
     */
    function mintAchievement(
        address to,
        AchievementType achievementType,
        string memory ipfsHash,
        string memory description
    ) external onlyRole(MINTER_ROLE) returns (uint256) {
        _tokenIds.increment();
        uint256 newTokenId = _tokenIds.current();

        _safeMint(to, newTokenId);

        achievements[newTokenId] = Achievement({
            achievementType: achievementType,
            ipfsHash: ipfsHash,
            timestamp: block.timestamp,
            description: description
        });

        userAchievementCount[to]++;
        userTokens[to].push(newTokenId);

        emit AchievementMinted(to, newTokenId, achievementType, ipfsHash);

        return newTokenId;
    }

    /**
     * @dev Updates the IPFS hash for a token's metadata
     * @param tokenId ID of the token
     * @param newIpfsHash New IPFS hash
     */
    function updateMetadata(
        uint256 tokenId,
        string memory newIpfsHash
    ) external onlyRole(ADMIN_ROLE) {
        require(_exists(tokenId), "Token does not exist");
        achievements[tokenId].ipfsHash = newIpfsHash;
        emit AchievementMetadataUpdated(tokenId, newIpfsHash);
    }

    /**
     * @dev Returns all achievements for a user
     * @param user Address of the user
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
     * @dev Returns achievement details for a specific token
     * @param tokenId ID of the token
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
     * @dev Returns the total number of achievements for a user
     * @param user Address of the user
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
     * @dev Returns the token URI for a given token ID
     */
    function tokenURI(uint256 tokenId) 
        public 
        view 
        override 
        returns (string memory) 
    {
        require(_exists(tokenId), "Token does not exist");
        return string(abi.encodePacked("ipfs://", achievements[tokenId].ipfsHash));
    }

    /**
     * @dev Required override for ERC721
     */
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
} 
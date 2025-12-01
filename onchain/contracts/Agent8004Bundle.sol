// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/token/ERC721/extensions/ERC721URIStorageUpgradeable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import "@openzeppelin/contracts/interfaces/IERC1271.sol";

// ---------- Proxy Wrapper ----------
contract ERC1967ProxyWrapper is ERC1967Proxy {
    constructor(address implementation, bytes memory _data) ERC1967Proxy(implementation, _data) {}
}

// ---------- IdentityRegistryUpgradeable ----------
contract IdentityRegistryUpgradeable is
    Initializable,
    ERC721URIStorageUpgradeable,
    OwnableUpgradeable,
    UUPSUpgradeable
{
    // agentId => key => value
    mapping(uint256 => mapping(string => bytes)) private _metadata;

    uint256 private _lastId;
    struct MetadataEntry {
        string key;
        bytes value;
    }

    event Registered(uint256 indexed agentId, string tokenURI, address indexed owner);
    event MetadataSet(uint256 indexed agentId, string indexed indexedKey, string key, bytes value);
    event UriUpdated(uint256 indexed agentId, string newUri, address indexed updatedBy);

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize() public initializer {
        __ERC721_init("AgentIdentity", "AID");
        __ERC721URIStorage_init();
        __Ownable_init(msg.sender);
        __UUPSUpgradeable_init();
        _lastId = 0;
    }

    function register() external returns (uint256 agentId) {
        agentId = _lastId++;
        _safeMint(msg.sender, agentId);
        emit Registered(agentId, "", msg.sender);
    }

    function register(string memory tokenUri) external returns (uint256 agentId) {
        agentId = _lastId++;
        _safeMint(msg.sender, agentId);
        _setTokenURI(agentId, tokenUri);
        emit Registered(agentId, tokenUri, msg.sender);
    }

    function register(string memory tokenUri, MetadataEntry[] memory metadata) external returns (uint256 agentId) {
        agentId = _lastId++;
        _safeMint(msg.sender, agentId);
        _setTokenURI(agentId, tokenUri);
        emit Registered(agentId, tokenUri, msg.sender);

        for (uint256 i = 0; i < metadata.length; i++) {
            _metadata[agentId][metadata[i].key] = metadata[i].value;
            emit MetadataSet(agentId, metadata[i].key, metadata[i].key, metadata[i].value);
        }
    }

    function getMetadata(uint256 agentId, string memory key) external view returns (bytes memory) {
        return _metadata[agentId][key];
    }

    function setMetadata(uint256 agentId, string memory key, bytes memory value) external {
        require(
            msg.sender == _ownerOf(agentId) ||
            isApprovedForAll(_ownerOf(agentId), msg.sender) ||
            msg.sender == getApproved(agentId),
            "Not authorized"
        );
        _metadata[agentId][key] = value;
        emit MetadataSet(agentId, key, key, value);
    }

    function setAgentUri(uint256 agentId, string calldata newUri) external {
        address owner = ownerOf(agentId);
        require(
            msg.sender == owner ||
            isApprovedForAll(owner, msg.sender) ||
            msg.sender == getApproved(agentId),
            "Not authorized"
        );
        _setTokenURI(agentId, newUri);
        emit UriUpdated(agentId, newUri, msg.sender);
    }

    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}

    function getVersion() external pure returns (string memory) {
        return "1.0.0";
    }
}

// ---------- ReputationRegistryUpgradeable ----------
interface IIdentityRegistry {
    function ownerOf(uint256 tokenId) external view returns (address);
    function isApprovedForAll(address owner, address operator) external view returns (bool);
    function getApproved(uint256 tokenId) external view returns (address);
}

contract ReputationRegistryUpgradeable is Initializable, OwnableUpgradeable, UUPSUpgradeable {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    address private identityRegistry;

    event NewFeedback(
        uint256 indexed agentId,
        address indexed clientAddress,
        uint8 score,
        bytes32 indexed tag1,
        bytes32 tag2,
        string feedbackUri,
        bytes32 feedbackHash
    );

    event FeedbackRevoked(
        uint256 indexed agentId,
        address indexed clientAddress,
        uint64 indexed feedbackIndex
    );

    event ResponseAppended(
        uint256 indexed agentId,
        address indexed clientAddress,
        uint64 feedbackIndex,
        address indexed responder,
        string responseUri,
        bytes32 responseHash
    );

    struct Feedback {
        uint8 score;
        bytes32 tag1;
        bytes32 tag2;
        bool isRevoked;
    }

    struct FeedbackAuth {
        uint256 agentId;
        address clientAddress;
        uint64 indexLimit;
        uint256 expiry;
        uint256 chainId;
        address identityRegistry;
        address signerAddress;
    }

    // agentId => clientAddress => feedbackIndex => Feedback (1-indexed)
    mapping(uint256 => mapping(address => mapping(uint64 => Feedback))) private _feedback;

    // agentId => clientAddress => last feedback index
    mapping(uint256 => mapping(address => uint64)) private _lastIndex;

    // agentId => clientAddress => feedbackIndex => responder => response count
    mapping(uint256 => mapping(address => mapping(uint64 => mapping(address => uint64)))) private _responseCount;

    // Track all unique responders for each feedback
    mapping(uint256 => mapping(address => mapping(uint64 => address[]))) private _responders;
    mapping(uint256 => mapping(address => mapping(uint64 => mapping(address => bool)))) private _responderExists;

    // Track all unique clients that have given feedback for each agent
    mapping(uint256 => mapping(address => bool)) private _clientExists;
    mapping(uint256 => address[]) private _clients;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(address _identityRegistry) public initializer {
        require(_identityRegistry != address(0), "bad identity");
        __Ownable_init(msg.sender);
        __UUPSUpgradeable_init();
        identityRegistry = _identityRegistry;
    }

    function getIdentityRegistry() external view returns (address) {
        return identityRegistry;
    }

    function giveFeedback(
        uint256 agentId,
        uint8 score,
        bytes32 tag1,
        bytes32 tag2,
        string calldata feedbackUri,
        bytes32 feedbackHash,
        bytes calldata feedbackAuth
    ) external {
        require(score <= 100, "score>100");

        // Verify agent exists
        require(_agentExists(agentId), "Agent does not exist");

        // Get agent owner
        IIdentityRegistry registry = IIdentityRegistry(identityRegistry);
        address agentOwner = registry.ownerOf(agentId);

        // SECURITY: Prevent self-feedback from owner and operators
        require(
            msg.sender != agentOwner &&
            !registry.isApprovedForAll(agentOwner, msg.sender) &&
            registry.getApproved(agentId) != msg.sender,
            "Self-feedback not allowed"
        );

        // Verify feedbackAuth signature
        _verifyFeedbackAuth(agentId, msg.sender, feedbackAuth);

        // Get current index for this client-agent pair (1-indexed)
        uint64 currentIndex = _lastIndex[agentId][msg.sender] + 1;

        // Store feedback at 1-indexed position
        _feedback[agentId][msg.sender][currentIndex] = Feedback({
            score: score,
            tag1: tag1,
            tag2: tag2,
            isRevoked: false
        });

        // Update last index
        _lastIndex[agentId][msg.sender] = currentIndex;

        // track new client
        if (!_clientExists[agentId][msg.sender]) {
            _clients[agentId].push(msg.sender);
            _clientExists[agentId][msg.sender] = true;
        }

        emit NewFeedback(agentId, msg.sender, score, tag1, tag2, feedbackUri, feedbackHash);
    }

    function _verifyFeedbackAuth(
        uint256 agentId,
        address clientAddress,
        bytes calldata feedbackAuth
    ) internal view {
        require(
            IIdentityRegistry(identityRegistry).ownerOf(agentId) != address(0),
            "Unregistered agent"
        );
        require(feedbackAuth.length >= 289, "Invalid auth length");

        // Decode the first 224 bytes into struct
        FeedbackAuth memory auth;
        (
            auth.agentId,
            auth.clientAddress,
            auth.indexLimit,
            auth.expiry,
            auth.chainId,
            auth.identityRegistry,
            auth.signerAddress
        ) = abi.decode(feedbackAuth[:224], (uint256, address, uint64, uint256, uint256, address, address));

        // Verify parameters
        require(auth.agentId == agentId, "AgentId mismatch");
        require(auth.clientAddress == clientAddress, "Client mismatch");
        require(block.timestamp < auth.expiry, "Auth expired");
        require(auth.chainId == block.chainid, "ChainId mismatch");
        require(auth.identityRegistry == identityRegistry, "Registry mismatch");
        require(auth.indexLimit >= _lastIndex[agentId][clientAddress] + 1, "IndexLimit exceeded");

        // Verify signature
        _verifySignature(auth, feedbackAuth[224:]);
    }

    function _verifySignature(
        FeedbackAuth memory auth,
        bytes calldata signature
    ) internal view {
        // Construct message hash
        bytes32 messageHash = keccak256(
            abi.encode(
                auth.agentId,
                auth.clientAddress,
                auth.indexLimit,
                auth.expiry,
                auth.chainId,
                auth.identityRegistry,
                auth.signerAddress
            )
        ).toEthSignedMessageHash();

        // verify signature: EOA or ERC-1271 contract
        address recoveredSigner = messageHash.recover(signature);
        if (recoveredSigner != auth.signerAddress) {
            if (auth.signerAddress.code.length == 0) {
                revert("Invalid signature");
            }
            require(
                IERC1271(auth.signerAddress).isValidSignature(messageHash, signature) == IERC1271.isValidSignature.selector,
                "Bad 1271 signature"
            );
        }

        // Verify signerAddress is owner or operator
        IIdentityRegistry registry = IIdentityRegistry(identityRegistry);
        address owner = registry.ownerOf(auth.agentId);
        require(
            auth.signerAddress == owner ||
            registry.isApprovedForAll(owner, auth.signerAddress) ||
            registry.getApproved(auth.agentId) == auth.signerAddress,
            "Signer not authorized"
        );
    }

    function revokeFeedback(uint256 agentId, uint64 feedbackIndex) external {
        require(feedbackIndex > 0, "index must be > 0");
        require(feedbackIndex <= _lastIndex[agentId][msg.sender], "index out of bounds");
        require(!_feedback[agentId][msg.sender][feedbackIndex].isRevoked, "Already revoked");

        _feedback[agentId][msg.sender][feedbackIndex].isRevoked = true;
        emit FeedbackRevoked(agentId, msg.sender, feedbackIndex);
    }

    function appendResponse(
        uint256 agentId,
        address clientAddress,
        uint64 feedbackIndex,
        string calldata responseUri,
        bytes32 responseHash
    ) external {
        require(feedbackIndex > 0, "index must be > 0");
        require(feedbackIndex <= _lastIndex[agentId][clientAddress], "index out of bounds");
        require(bytes(responseUri).length > 0, "Empty URI");

        // Track new responder
        if (!_responderExists[agentId][clientAddress][feedbackIndex][msg.sender]) {
            _responders[agentId][clientAddress][feedbackIndex].push(msg.sender);
            _responderExists[agentId][clientAddress][feedbackIndex][msg.sender] = true;
        }

        // Increment response count for this responder
        _responseCount[agentId][clientAddress][feedbackIndex][msg.sender]++;

        emit ResponseAppended(agentId, clientAddress, feedbackIndex, msg.sender, responseUri, responseHash);
    }

    function getLastIndex(uint256 agentId, address clientAddress) external view returns (uint64) {
        return _lastIndex[agentId][clientAddress];
    }

    function readFeedback(uint256 agentId, address clientAddress, uint64 index)
        external
        view
        returns (uint8 score, bytes32 tag1, bytes32 tag2, bool isRevoked)
    {
        require(index > 0, "index must be > 0");
        require(index <= _lastIndex[agentId][clientAddress], "index out of bounds");
        Feedback storage f = _feedback[agentId][clientAddress][index];
        return (f.score, f.tag1, f.tag2, f.isRevoked);
    }

    function getSummary(
        uint256 agentId,
        address[] calldata clientAddresses,
        bytes32 tag1,
        bytes32 tag2
    ) external view returns (uint64 count, uint8 averageScore) {
        address[] memory clientList;
        if (clientAddresses.length > 0) {
            clientList = clientAddresses;
        } else {
            clientList = _clients[agentId];
        }

        uint256 totalScore = 0;
        count = 0;

        for (uint256 i = 0; i < clientList.length; i++) {
            uint64 lastIdx = _lastIndex[agentId][clientList[i]];
            for (uint64 j = 1; j <= lastIdx; j++) {
                Feedback storage fb = _feedback[agentId][clientList[i]][j];
                if (fb.isRevoked) continue;
                if (tag1 != bytes32(0) && fb.tag1 != tag1) continue;
                if (tag2 != bytes32(0) && fb.tag2 != tag2) continue;

                totalScore += fb.score;
                count++;
            }
        }

        averageScore = count > 0 ? uint8(totalScore / count) : 0;
    }

    function readAllFeedback(
        uint256 agentId,
        address[] calldata clientAddresses,
        bytes32 tag1,
        bytes32 tag2,
        bool includeRevoked
    ) external view returns (
        address[] memory clients,
        uint8[] memory scores,
        bytes32[] memory tag1s,
        bytes32[] memory tag2s,
        bool[] memory revokedStatuses
    ) {
        address[] memory clientList;
        if (clientAddresses.length > 0) {
            clientList = clientAddresses;
        } else {
            clientList = _clients[agentId];
        }

        // First pass: count matching feedback
        uint256 totalCount = 0;
        for (uint256 i = 0; i < clientList.length; i++) {
            uint64 lastIdx = _lastIndex[agentId][clientList[i]];
            for (uint64 j = 1; j <= lastIdx; j++) {
                Feedback storage fb = _feedback[agentId][clientList[i]][j];
                if (!includeRevoked && fb.isRevoked) continue;
                if (tag1 != bytes32(0) && fb.tag1 != tag1) continue;
                if (tag2 != bytes32(0) && fb.tag2 != tag2) continue;
                totalCount++;
            }
        }

        // Initialize arrays
        clients = new address[](totalCount);
        scores = new uint8[](totalCount);
        tag1s = new bytes32[](totalCount);
        tag2s = new bytes32[](totalCount);
        revokedStatuses = new bool[](totalCount);

        // Second pass: populate arrays
        uint256 idx = 0;
        for (uint256 i = 0; i < clientList.length; i++) {
            uint64 lastIdx = _lastIndex[agentId][clientList[i]];
            for (uint64 j = 1; j <= lastIdx; j++) {
                Feedback storage fb = _feedback[agentId][clientList[i]][j];
                if (!includeRevoked && fb.isRevoked) continue;
                if (tag1 != bytes32(0) && fb.tag1 != tag1) continue;
                if (tag2 != bytes32(0) && fb.tag2 != tag2) continue;

                clients[idx] = clientList[i];
                scores[idx] = fb.score;
                tag1s[idx] = fb.tag1;
                tag2s[idx] = fb.tag2;
                revokedStatuses[idx] = fb.isRevoked;
                idx++;
            }
        }
    }

    function getResponseCount(
        uint256 agentId,
        address clientAddress,
        uint64 feedbackIndex,
        address[] calldata responders
    ) external view returns (uint64 count) {
        if (clientAddress == address(0)) {
            // Count all responses for all clients
            address[] memory clients = _clients[agentId];
            for (uint256 i = 0; i < clients.length; i++) {
                uint64 lastIdx = _lastIndex[agentId][clients[i]];
                for (uint64 j = 1; j <= lastIdx; j++) {
                    count += _countResponses(agentId, clients[i], j, responders);
                }
            }
        } else if (feedbackIndex == 0) {
            // Count all responses for specific clientAddress
            uint64 lastIdx = _lastIndex[agentId][clientAddress];
            for (uint64 j = 1; j <= lastIdx; j++) {
                count += _countResponses(agentId, clientAddress, j, responders);
            }
        } else {
            // Count responses for specific clientAddress and feedbackIndex
            count = _countResponses(agentId, clientAddress, feedbackIndex, responders);
        }
    }

    function _countResponses(
        uint256 agentId,
        address clientAddress,
        uint64 feedbackIndex,
        address[] calldata responders
    ) internal view returns (uint64 count) {
        if (responders.length == 0) {
            // Count from all responders
            address[] memory allResponders = _responders[agentId][clientAddress][feedbackIndex];
            for (uint256 k = 0; k < allResponders.length; k++) {
                count += _responseCount[agentId][clientAddress][feedbackIndex][allResponders[k]];
            }
        } else {
            // Count from specified responders
            for (uint256 k = 0; k < responders.length; k++) {
                count += _responseCount[agentId][clientAddress][feedbackIndex][responders[k]];
            }
        }
    }

    function getClients(uint256 agentId) external view returns (address[] memory) {
        return _clients[agentId];
    }

    function _agentExists(uint256 agentId) internal view returns (bool) {
        try IIdentityRegistry(identityRegistry).ownerOf(agentId) returns (address owner) {
            return owner != address(0);
        } catch {
            return false;
        }
    }

    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}

    function getVersion() external pure returns (string memory) {
        return "1.0.0";
    }
}

// ---------- ValidationRegistryUpgradeable ----------
contract ValidationRegistryUpgradeable is Initializable, OwnableUpgradeable, UUPSUpgradeable {
    address private identityRegistry;

    event ValidationRequest(
        address indexed validatorAddress,
        uint256 indexed agentId,
        string requestUri,
        bytes32 indexed requestHash
    );

    event ValidationResponse(
        address indexed validatorAddress,
        uint256 indexed agentId,
        bytes32 indexed requestHash,
        uint8 response,
        string responseUri,
        bytes32 responseHash,
        bytes32 tag
    );

    struct ValidationStatus {
        address validatorAddress;
        uint256 agentId;
        uint8 response;       // 0..100
        bytes32 responseHash;
        bytes32 tag;
        uint256 lastUpdate;
    }

    // agentId => list of requestHashes
    mapping(uint256 => bytes32[]) private _agentValidations;

    // requestHash => validation status
    mapping(bytes32 => ValidationStatus) public validations;

    // validatorAddress => list of requestHashes
    mapping(address => bytes32[]) private _validatorRequests;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(address _identityRegistry) public initializer {
        require(_identityRegistry != address(0), "bad identity");
        __Ownable_init(msg.sender);
        __UUPSUpgradeable_init();
        identityRegistry = _identityRegistry;
    }

    function getIdentityRegistry() external view returns (address) {
        return identityRegistry;
    }

    function validationRequest(
        address validatorAddress,
        uint256 agentId,
        string calldata requestUri,
        bytes32 requestHash
    ) external {
        require(validatorAddress != address(0), "bad validator");
        require(validations[requestHash].validatorAddress == address(0), "exists");

        // Check permission: caller must be owner or approved operator
        IIdentityRegistry registry = IIdentityRegistry(identityRegistry);
        address owner = registry.ownerOf(agentId);
        require(
            msg.sender == owner || registry.isApprovedForAll(owner, msg.sender),
            "Not authorized"
        );

        validations[requestHash] = ValidationStatus({
            validatorAddress: validatorAddress,
            agentId: agentId,
            response: 0,
            responseHash: bytes32(0),
            tag: bytes32(0),
            lastUpdate: block.timestamp
        });

        // Track for lookups
        _agentValidations[agentId].push(requestHash);
        _validatorRequests[validatorAddress].push(requestHash);

        emit ValidationRequest(validatorAddress, agentId, requestUri, requestHash);
    }

    function validationResponse(
        bytes32 requestHash,
        uint8 response,
        string calldata responseUri,
        bytes32 responseHash,
        bytes32 tag
    ) external {
        ValidationStatus storage s = validations[requestHash];
        require(s.validatorAddress != address(0), "unknown");
        require(msg.sender == s.validatorAddress, "not validator");
        require(response <= 100, "resp>100");
        s.response = response;
        s.responseHash = responseHash;
        s.tag = tag;
        s.lastUpdate = block.timestamp;
        emit ValidationResponse(s.validatorAddress, s.agentId, requestHash, response, responseUri, responseHash, tag);
    }

    function getValidationStatus(bytes32 requestHash)
        external
        view
        returns (address validatorAddress, uint256 agentId, uint8 response, bytes32 responseHash, bytes32 tag, uint256 lastUpdate)
    {
        ValidationStatus memory s = validations[requestHash];
        require(s.validatorAddress != address(0), "unknown");
        return (s.validatorAddress, s.agentId, s.response, s.responseHash, s.tag, s.lastUpdate);
    }

    function getSummary(
        uint256 agentId,
        address[] calldata validatorAddresses,
        bytes32 tag
    ) external view returns (uint64 count, uint8 avgResponse) {
        uint256 totalResponse = 0;
        count = 0;

        bytes32[] storage requestHashes = _agentValidations[agentId];

        for (uint256 i = 0; i < requestHashes.length; i++) {
            ValidationStatus storage s = validations[requestHashes[i]];

            // Filter by validator if specified
            bool matchValidator = (validatorAddresses.length == 0);
            if (!matchValidator) {
                for (uint256 j = 0; j < validatorAddresses.length; j++) {
                    if (s.validatorAddress == validatorAddresses[j]) {
                        matchValidator = true;
                        break;
                    }
                }
            }

            // Filter by tag (0x0 means no filter)
            bool matchTag = (tag == bytes32(0)) || (s.tag == tag);

            if (matchValidator && matchTag && s.response >= 0) {
                totalResponse += s.response;
                count++;
            }
        }

        avgResponse = count > 0 ? uint8(totalResponse / count) : 0;
    }

    function getAgentValidations(uint256 agentId) external view returns (bytes32[] memory) {
        return _agentValidations[agentId];
    }

    function getValidatorRequests(address validatorAddress) external view returns (bytes32[] memory) {
        return _validatorRequests[validatorAddress];
    }

    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}

    function getVersion() external pure returns (string memory) {
        return "1.0.0";
    }
}

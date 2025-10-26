// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @title AttuarioVaultV2_Adaptive – Wave Rotation con resilienza
/// @notice Rotazione dinamica del pool; su 3 rotazioni consecutive in crisi → exit & pausa.
/// @dev Owner = EOA/bot che decide. Il contratto non gestisce LP/DEX; esegue segnali e custodisce fondi.

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
}

contract AttuarioVaultV2_Adaptive {
    /* ========== STORAGE ========== */
    address public owner;

    bool public active = true;
    uint256 public executionInterval = 3600;
    uint256 public lastExecuted;
    uint256 public totalExecutions;

    string public activePool;
    uint8 public rotationCount;
    bool public inCrisis;

    event StrategyExecuted(uint256 timestamp, string pool, uint256 apyBps, uint256 capitalUnits);
    event PoolRotated(string oldPool, string newPool, uint256 timestamp, bool crisis);
    event CrisisTriggered(string lastPool, uint256 timestamp);
    event Paused(address indexed by);
    event Resumed(address indexed by);
    event IntervalChanged(uint256 oldInterval, uint256 newInterval);
    event EmergencyExit(address to, uint256 ethAmount);
    event ERC20Swept(address token, address to, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    constructor(string memory initialPool, uint256 initialInterval) {
        owner = msg.sender;
        activePool = initialPool;
        if (initialInterval > 0) {
            require(initialInterval >= 300, "Interval too low");
            executionInterval = initialInterval;
        }
    }

    receive() external payable {}

    function setExecutionInterval(uint256 newInterval) external onlyOwner {
        require(newInterval >= 300, "Interval too low");
        uint256 old = executionInterval;
        executionInterval = newInterval;
        emit IntervalChanged(old, newInterval);
    }

    function pauseVault() external onlyOwner {
        active = false;
        emit Paused(msg.sender);
    }

    function resumeVault() external onlyOwner {
        active = true;
        inCrisis = false;
        rotationCount = 0;
        emit Resumed(msg.sender);
    }

    function setActivePool(string calldata newPool, bool crisis) external onlyOwner {
        if (keccak256(bytes(activePool)) != keccak256(bytes(newPool))) {
            emit PoolRotated(activePool, newPool, block.timestamp, crisis);
            activePool = newPool;
            if (crisis) {
                unchecked {
                    rotationCount += 1;
                }
            } else {
                rotationCount = 0;
            }
        } else {
            if (!crisis) {
                rotationCount = 0;
            }
        }

        inCrisis = crisis;

        if (inCrisis && rotationCount >= 3) {
            emit CrisisTriggered(activePool, block.timestamp);
            _emergencyExit(payable(owner));
            active = false;
        }
    }

    function executeStrategy(string calldata pool, uint256 apyBps, uint256 capitalUnits) external onlyOwner {
        require(active, "Vault paused");
        require(block.timestamp >= lastExecuted + executionInterval, "Execution interval not met");

        lastExecuted = block.timestamp;
        totalExecutions += 1;

        emit StrategyExecuted(block.timestamp, pool, apyBps, capitalUnits);
    }

    function emergencyWithdraw(address to) external onlyOwner {
        _emergencyExit(payable(to));
    }

    function _emergencyExit(address payable to) internal {
        uint256 bal = address(this).balance;
        if (bal > 0) {
            (bool ok, ) = to.call{value: bal}("");
            require(ok, "ETH transfer failed");
            emit EmergencyExit(to, bal);
        } else {
            emit EmergencyExit(to, 0);
        }
        inCrisis = false;
        rotationCount = 0;
    }

    function sweepERC20(address token, address to) external onlyOwner {
        uint256 amt = IERC20(token).balanceOf(address(this));
        require(amt > 0, "No balance");
        require(IERC20(token).transfer(to, amt), "Transfer failed");
        emit ERC20Swept(token, to, amt);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Zero address");
        owner = newOwner;
    }
}

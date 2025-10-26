// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title AttuarioVault - Wave Rotation logger
/// @notice riceve i dati giornalieri della strategia e li registra on-chain
contract AttuarioVault {
    struct Execution {
        string pool;
        uint256 apyBps;
        uint256 capital;
        uint256 timestamp;
    }

    address public owner;
    address public gelatoExecutor;
    uint256 public lastExecuted;
    uint256 public totalExecutions;
    uint256 public executionInterval = 1 days;
    Execution private _latest;

    event StrategyExecuted(
        uint256 indexed timestamp,
        string pool,
        uint256 apyBps,
        uint256 capital,
        address indexed executor
    );
    event GelatoExecutorUpdated(address indexed previousExecutor, address indexed newExecutor);
    event ExecutionIntervalUpdated(uint256 previousInterval, uint256 newInterval);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    modifier onlyExecutor() {
        require(msg.sender == owner || msg.sender == gelatoExecutor, "Executor not authorized");
        _;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid owner");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function latestExecution() external view returns (Execution memory) {
        return _latest;
    }

    function setGelatoExecutor(address newExecutor) external onlyOwner {
        emit GelatoExecutorUpdated(gelatoExecutor, newExecutor);
        gelatoExecutor = newExecutor;
    }

    function setExecutionInterval(uint256 newInterval) external onlyOwner {
        require(newInterval >= 1 hours, "Interval too short");
        emit ExecutionIntervalUpdated(executionInterval, newInterval);
        executionInterval = newInterval;
    }

    function executeStrategy(
        string calldata pool,
        uint256 apyBps,
        uint256 capital
    ) external onlyExecutor {
        require(bytes(pool).length > 0, "Pool required");
        require(block.timestamp >= lastExecuted + executionInterval, "Execution interval not met");

        lastExecuted = block.timestamp;
        totalExecutions += 1;
        _latest = Execution({pool: pool, apyBps: apyBps, capital: capital, timestamp: block.timestamp});

        emit StrategyExecuted(block.timestamp, pool, apyBps, capital, msg.sender);
    }
}

# Trade Engine

A production-grade, strategy-agnostic Trade Engine for algorithmic trading platforms.

## Overview

The Trade Engine is the final gate between trading signals and real capital. It enforces risk controls, manages order execution, and provides full auditability without containing any strategy logic.

## Architecture

### Core Principles

- **Strategy-Agnostic**: No alpha logic, indicators, or predictions
- **Stateless Per Request**: All authoritative state is externalized
- **Deterministic**: Same inputs produce same outputs
- **Idempotent**: Safe to retry signal processing
- **Auditable**: Every decision is logged

### Components

#### API Layer (`api/`)
- `signal_ingest.py`: Receives and validates trading signals
- `health.py`: Health check endpoints
- `kill_switch.py`: Emergency circuit breaker controls

#### Execution Layer (`execution/`)
- `order_router.py`: Routes orders to appropriate broker adapters
- `order_state.py`: Manages order lifecycle state machine
- `fills.py`: Processes and validates trade fills

#### Risk Management (`risk/`)
- `pre_trade.py`: Pre-trade risk checks orchestration
- `exposure.py`: Position and exposure calculations
- `loss_limits.py`: Daily loss and drawdown limits
- `throttles.py`: Rate limiting per strategy

#### Broker Adapters (`brokers/`)
- `base.py`: Abstract broker interface
- `paper.py`: Paper trading implementation
- `ibkr_stub.py`: Interactive Brokers stub (for integration)

#### Portfolio (`portfolio/`)
- `client.py`: External portfolio state management

#### Audit (`audit/`)
- `trade_log.py`: Trade execution logging
- `decision_log.py`: Risk decision audit trail

#### Configuration (`config/`)
- `limits.py`: Risk limit definitions and validation

## Signal Contract

```json
{
  "strategy_id": "string",
  "symbol": "string",
  "side": "BUY | SELL",
  "confidence": number,
  "target_exposure": number,
  "time_horizon": "INTRADAY | SWING | LONG",
  "constraints": {
    "max_slippage_bps": number,
    "max_notional": number
  }
}
```

## Risk Rules

The engine enforces:

- Maximum position size per symbol
- Maximum asset exposure (concentration limits)
- Maximum daily loss limits
- Maximum order notional
- Per-strategy rate limits (throttling)

## Usage

```bash
# Install dependencies
pip install -e .

# Run the engine
python -m trade_engine.main

# Run tests
pytest
```

## Safety Guarantees

1. **Kill Switch**: Global circuit breaker can halt all trading
2. **Pre-Trade Checks**: All orders validated before execution
3. **Idempotency**: Duplicate signals are safely handled
4. **Audit Trail**: Every decision is logged with full context
5. **Broker Abstraction**: Risk logic independent of execution venue

## State Management

All state is externalized to:
- Redis: Kill switch, rate limits, daily loss tracking
- Portfolio Service: Position and exposure data
- Audit Logs: Immutable decision and trade records

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format code
black trade_engine/

# Type check
mypy trade_engine/

# Lint
ruff check trade_engine/
```

## License

Proprietary - Internal use only


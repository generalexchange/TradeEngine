# Options Trading Extension

This document describes the options trading extension added to the Trade Engine.

## Overview

The options extension adds support for:
- Single-leg option orders
- Multi-leg option spreads (atomic execution)
- Option contract validation
- Assignment and exercise event handling
- Broker-agnostic option execution

**Key Design Principles:**
- No strategy logic (no Greeks, no position tracking)
- No portfolio mutation (assignment/exercise events are emitted, not executed)
- Broker-agnostic design
- Atomic spread execution (all legs fill together or none do)

## New Modules

### Execution Layer

#### `option_orders.py`
- **OptionLeg**: Represents a single option contract leg
- **OptionOrder**: Single-leg option order with lifecycle tracking
- **OptionSpreadOrder**: Multi-leg spread order with atomic execution guarantee

#### `option_validation.py`
- **OptionContractValidator**: Validates option contracts before execution
  - Expiration date validation
  - Strike price validation
  - Contract multiplier enforcement
  - Spread consistency checks

#### `option_fills.py`
- **OptionFill**: Represents an option fill from a broker
- **OptionFillProcessor**: Processes and validates option fills
- **AssignmentEvent**: Emitted when an option is assigned (no portfolio mutation)
- **ExerciseEvent**: Emitted when an option is exercised (no portfolio mutation)

#### `option_router.py`
- **OptionOrderRouter**: Routes option orders to broker adapters
  - Single-leg order routing
  - Spread order routing (atomic execution)
  - Order cancellation

### Broker Extensions

#### `brokers/base.py`
Extended `BrokerAdapter` with:
- `submit_option_order()`: Submit single-leg option orders
- `submit_option_spread()`: Submit multi-leg spreads (atomic execution)

#### `brokers/paper.py`
Implemented option support in paper broker:
- Mock option premium calculation
- Single-leg option execution simulation
- Atomic spread execution simulation

## Usage Examples

### Single-Leg Option Order

```python
from trade_engine.execution.option_orders import OptionLeg, OptionOrder, OptionType
from trade_engine.execution.option_router import OptionOrderRouter
from trade_engine.brokers.paper import PaperBroker

# Create option leg
leg = OptionLeg(
    symbol="AAPL",
    option_type=OptionType.CALL,
    strike=175.0,
    expiration="2024-12-20",
    side="BUY",
    quantity=10,
)

# Create order
order = OptionOrder(
    strategy_id="momentum_strategy",
    leg=leg,
    limit_price=2.50,  # $2.50 per contract
)

# Submit via router
broker = PaperBroker()
router = OptionOrderRouter(default_broker=broker)
updated_order, error = await router.submit_option_order(order)
```

### Multi-Leg Spread Order

```python
from trade_engine.execution.option_orders import OptionSpreadOrder

# Create spread (vertical call spread)
leg1 = OptionLeg(
    symbol="AAPL",
    option_type=OptionType.CALL,
    strike=175.0,
    expiration="2024-12-20",
    side="BUY",
    quantity=10,
)

leg2 = OptionLeg(
    symbol="AAPL",
    option_type=OptionType.CALL,
    strike=180.0,
    expiration="2024-12-20",
    side="SELL",
    quantity=10,
)

# Create spread order (atomic execution)
spread = OptionSpreadOrder(
    strategy_id="spread_strategy",
    legs=[leg1, leg2],
    limit_price=1.50,  # Net debit
)

# Submit via router
updated_spread, error = await router.submit_spread_order(spread)
```

## Contract Validation

All option orders are validated before execution:

1. **Expiration Validation**: Expiration must be in the future
2. **Strike Validation**: Strike price must be positive
3. **Quantity Validation**: Quantity must be positive integer
4. **Contract Multiplier**: Enforced (typically 100 for US options)
5. **Spread Consistency**: All legs must have same underlying and expiration (for simplicity)

## Atomic Execution

Spread orders guarantee atomic execution:
- All legs fill together, or none do
- Partial fills are tracked per leg
- Order status reflects overall spread state

## Assignment and Exercise Events

The engine emits assignment and exercise events but does not mutate portfolios:

```python
from trade_engine.execution.option_fills import AssignmentEvent, ExerciseEvent

# Assignment event (short option was assigned)
assignment = AssignmentEvent(
    contract_symbol="AAPL_241220_C_175000",
    quantity=10,
    assignment_price=175.0,
    timestamp=datetime.now().isoformat(),
)

# Exercise event (long option was exercised)
exercise = ExerciseEvent(
    contract_symbol="AAPL_241220_P_170000",
    quantity=10,
    exercise_price=170.0,
    timestamp=datetime.now().isoformat(),
)
```

## Testing

Comprehensive tests are provided:

- `test_option_orders.py`: Order model and validation tests
- `test_option_execution.py`: Execution and fill processing tests

Run tests with:
```bash
pytest tests/test_option_orders.py -v
pytest tests/test_option_execution.py -v
```

## Integration Notes

- **Equity execution unchanged**: All existing equity order processing remains intact
- **Broker abstraction**: New option methods are optional (default to `NotImplementedError`)
- **No refactoring**: Existing code was not modified, only extended

## Future Enhancements

Potential future additions (not included per requirements):
- Calendar spreads (different expirations)
- Different underlying spreads
- Greeks calculation (strategy logic - excluded)
- Position tracking (excluded per requirements)
- Margin modeling (beyond basic validation - excluded)


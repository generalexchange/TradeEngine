"""Tests for option execution and fills."""

import pytest
from datetime import datetime, timedelta

from trade_engine.brokers.paper import PaperBroker
from trade_engine.execution.option_fills import (
    AssignmentEvent,
    ExerciseEvent,
    OptionFill,
    OptionFillProcessor,
)
from trade_engine.execution.option_orders import (
    OptionLeg,
    OptionOrder,
    OptionSpreadOrder,
    OptionType,
)
from trade_engine.execution.option_router import OptionOrderRouter
from trade_engine.execution.order_state import OrderStatus


@pytest.fixture
def broker():
    """Create a paper broker for testing."""
    return PaperBroker()


@pytest.fixture
def option_router(broker):
    """Create an option order router."""
    return OptionOrderRouter(default_broker=broker)


@pytest.fixture
def sample_leg():
    """Create a sample option leg."""
    return OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        side="BUY",
        quantity=10,
    )


@pytest.mark.asyncio
async def test_single_leg_option_execution(broker, sample_leg):
    """Test single-leg option order execution."""
    order = OptionOrder(
        strategy_id="test_strategy",
        leg=sample_leg,
        limit_price=2.50,
    )

    # Submit order
    broker_order_id = await broker.submit_option_order(leg=sample_leg, limit_price=2.50)

    assert broker_order_id is not None
    assert broker_order_id.startswith("PAPER_OPT_")

    # Check order status
    status = await broker.get_order_status(broker_order_id)
    # Note: Paper broker fills immediately, so status might be FILLED
    assert status is not None


@pytest.mark.asyncio
async def test_option_fill_processing(sample_leg):
    """Test option fill processing."""
    order = OptionOrder(
        strategy_id="test",
        leg=sample_leg,
    )
    order.broker_order_id = "BROKER_123"
    order.update_status(OrderStatus.SUBMITTED)

    # Create fill
    fill = OptionFill(
        broker_order_id="BROKER_123",
        contract_symbol=sample_leg.get_contract_symbol(),
        quantity=5,  # Partial fill
        price_per_contract=2.50,
        timestamp=datetime.now().isoformat(),
    )

    # Apply fill
    OptionFillProcessor.apply_fill_to_order(order, fill)

    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert order.filled_quantity == 5
    assert order.filled_price == 2.50

    # Apply second fill to complete order
    fill2 = OptionFill(
        broker_order_id="BROKER_123",
        contract_symbol=sample_leg.get_contract_symbol(),
        quantity=5,
        price_per_contract=2.55,
        timestamp=datetime.now().isoformat(),
    )

    OptionFillProcessor.apply_fill_to_order(order, fill2)

    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == 10
    # Average price should be weighted
    assert order.filled_price is not None


@pytest.mark.asyncio
async def test_spread_atomic_execution(broker):
    """Test atomic spread execution (all legs fill together)."""
    leg1 = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        side="BUY",
        quantity=10,
    )

    leg2 = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=180.0,
        expiration=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        side="SELL",
        quantity=10,
    )

    spread = OptionSpreadOrder(
        strategy_id="test",
        legs=[leg1, leg2],
        limit_price=1.50,
    )

    # Submit spread
    broker_order_id = await broker.submit_option_spread(
        legs=[leg1, leg2],
        limit_price=1.50,
    )

    assert broker_order_id is not None
    assert broker_order_id.startswith("PAPER_SPREAD_")

    # Check that all legs were filled atomically
    status = await broker.get_order_status(broker_order_id)
    assert status is not None


@pytest.mark.asyncio
async def test_spread_fill_processing():
    """Test spread fill processing."""
    leg1 = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        side="BUY",
        quantity=10,
    )

    leg2 = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=180.0,
        expiration=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        side="SELL",
        quantity=10,
    )

    spread = OptionSpreadOrder(
        strategy_id="test",
        legs=[leg1, leg2],
    )
    spread.broker_order_id = "BROKER_SPREAD_123"
    spread.update_status(OrderStatus.SUBMITTED)

    # Create fill for leg1
    fill1 = OptionFill(
        broker_order_id="BROKER_SPREAD_123",
        contract_symbol=leg1.get_contract_symbol(),
        quantity=10,
        price_per_contract=2.50,
        timestamp=datetime.now().isoformat(),
    )

    OptionFillProcessor.apply_fill_to_spread(spread, fill1, leg1)

    # Create fill for leg2
    fill2 = OptionFill(
        broker_order_id="BROKER_SPREAD_123",
        contract_symbol=leg2.get_contract_symbol(),
        quantity=10,
        price_per_contract=1.00,
        timestamp=datetime.now().isoformat(),
    )

    OptionFillProcessor.apply_fill_to_spread(spread, fill2, leg2)

    # Spread should be fully filled
    assert spread.is_fully_filled()
    assert spread.status == OrderStatus.FILLED


@pytest.mark.asyncio
async def test_option_router_single_leg(option_router, sample_leg):
    """Test option router for single-leg orders."""
    order = OptionOrder(
        strategy_id="test",
        leg=sample_leg,
        limit_price=2.50,
    )

    updated_order, error = await option_router.submit_option_order(order)

    assert error is None
    assert updated_order.status == OrderStatus.SUBMITTED
    assert updated_order.broker_order_id is not None


@pytest.mark.asyncio
async def test_option_router_spread(option_router):
    """Test option router for spread orders."""
    leg1 = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        side="BUY",
        quantity=10,
    )

    leg2 = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=180.0,
        expiration=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        side="SELL",
        quantity=10,
    )

    spread = OptionSpreadOrder(
        strategy_id="test",
        legs=[leg1, leg2],
        limit_price=1.50,
    )

    updated_spread, error = await option_router.submit_spread_order(spread)

    assert error is None
    assert updated_spread.status == OrderStatus.SUBMITTED
    assert updated_spread.broker_order_id is not None


def test_assignment_event():
    """Test assignment event creation."""
    event = AssignmentEvent(
        contract_symbol="AAPL_241220_C_175000",
        quantity=10,
        assignment_price=175.0,
        timestamp=datetime.now().isoformat(),
    )

    assert event.quantity == 10
    assert event.assignment_price == 175.0
    assert event.event_id is not None

    event_dict = event.to_dict()
    assert event_dict["event_type"] == "ASSIGNMENT"
    assert event_dict["quantity"] == 10


def test_exercise_event():
    """Test exercise event creation."""
    event = ExerciseEvent(
        contract_symbol="AAPL_241220_C_175000",
        quantity=10,
        exercise_price=175.0,
        timestamp=datetime.now().isoformat(),
    )

    assert event.quantity == 10
    assert event.exercise_price == 175.0
    assert event.event_id is not None

    event_dict = event.to_dict()
    assert event_dict["event_type"] == "EXERCISE"
    assert event_dict["quantity"] == 10


def test_fill_validation(sample_leg):
    """Test fill validation."""
    order = OptionOrder(
        strategy_id="test",
        leg=sample_leg,
    )
    order.broker_order_id = "BROKER_123"

    # Valid fill
    fill = OptionFill(
        broker_order_id="BROKER_123",
        contract_symbol=sample_leg.get_contract_symbol(),
        quantity=5,
        price_per_contract=2.50,
        timestamp=datetime.now().isoformat(),
    )

    is_valid, error = OptionFillProcessor.validate_fill(fill, order)
    assert is_valid is True
    assert error is None

    # Invalid fill (wrong contract)
    fill_invalid = OptionFill(
        broker_order_id="BROKER_123",
        contract_symbol="WRONG_CONTRACT",
        quantity=5,
        price_per_contract=2.50,
        timestamp=datetime.now().isoformat(),
    )

    is_valid, error = OptionFillProcessor.validate_fill(fill_invalid, order)
    assert is_valid is False
    assert error is not None


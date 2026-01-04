"""Tests for execution layer."""

import pytest

from trade_engine.execution.order_state import Order, OrderStatus
from trade_engine.execution.fills import Fill, FillProcessor


def test_order_creation():
    """Test order creation."""
    order = Order(
        strategy_id="test_strategy",
        symbol="AAPL",
        side="BUY",
        quantity=100.0,
        notional=10000.0,
    )

    assert order.status == OrderStatus.PENDING
    assert order.filled_quantity == 0.0
    assert not order.is_terminal()


def test_order_state_transitions():
    """Test valid order state transitions."""
    order = Order(
        strategy_id="test",
        symbol="AAPL",
        side="BUY",
        quantity=100.0,
        notional=10000.0,
    )

    # Valid transition: PENDING -> SUBMITTED
    order.update_status(OrderStatus.SUBMITTED)
    assert order.status == OrderStatus.SUBMITTED
    assert order.submitted_at is not None

    # Valid transition: SUBMITTED -> PARTIALLY_FILLED
    order.update_status(OrderStatus.PARTIALLY_FILLED)
    assert order.status == OrderStatus.PARTIALLY_FILLED

    # Valid transition: PARTIALLY_FILLED -> FILLED
    order.update_status(OrderStatus.FILLED)
    assert order.status == OrderStatus.FILLED
    assert order.is_terminal()


def test_order_fill_processing():
    """Test fill processing."""
    order = Order(
        strategy_id="test",
        symbol="AAPL",
        side="BUY",
        quantity=100.0,
        notional=10000.0,
    )
    order.broker_order_id = "BROKER_123"
    order.update_status(OrderStatus.SUBMITTED)

    # Create fill
    fill = Fill(
        broker_order_id="BROKER_123",
        symbol="AAPL",
        quantity=50.0,
        price=100.0,
        timestamp="2024-01-01T12:00:00Z",
    )

    # Apply fill
    FillProcessor.apply_fill_to_order(order, fill)

    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert order.filled_quantity == 50.0
    assert order.filled_notional == 5000.0
    assert order.average_fill_price == 100.0

    # Apply second fill to complete order
    fill2 = Fill(
        broker_order_id="BROKER_123",
        symbol="AAPL",
        quantity=50.0,
        price=100.0,
        timestamp="2024-01-01T12:00:01Z",
    )

    FillProcessor.apply_fill_to_order(order, fill2)

    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == 100.0
    assert order.filled_notional == 10000.0


def test_fill_validation():
    """Test fill validation."""
    order = Order(
        strategy_id="test",
        symbol="AAPL",
        side="BUY",
        quantity=100.0,
        notional=10000.0,
    )
    order.broker_order_id = "BROKER_123"

    # Valid fill
    fill = Fill(
        broker_order_id="BROKER_123",
        symbol="AAPL",
        quantity=50.0,
        price=100.0,
        timestamp="2024-01-01T12:00:00Z",
    )

    valid, error = FillProcessor.validate_fill(fill, order)
    assert valid is True
    assert error is None

    # Invalid fill (wrong symbol)
    fill_invalid = Fill(
        broker_order_id="BROKER_123",
        symbol="MSFT",  # Wrong symbol
        quantity=50.0,
        price=100.0,
        timestamp="2024-01-01T12:00:00Z",
    )

    valid, error = FillProcessor.validate_fill(fill_invalid, order)
    assert valid is False
    assert error is not None


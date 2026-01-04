"""Tests for option order models and validation."""

import pytest
from datetime import datetime, timedelta

from trade_engine.execution.option_orders import (
    OptionLeg,
    OptionOrder,
    OptionSpreadOrder,
    OptionType,
)
from trade_engine.execution.option_validation import OptionContractValidator
from trade_engine.execution.order_state import OrderStatus


def test_option_leg_creation():
    """Test option leg creation."""
    leg = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration="2024-12-20",
        side="BUY",
        quantity=10,
    )

    assert leg.symbol == "AAPL"
    assert leg.option_type == OptionType.CALL
    assert leg.strike == 175.0
    assert leg.quantity == 10
    assert leg.contract_multiplier == 100  # Default


def test_option_leg_contract_symbol():
    """Test contract symbol generation."""
    leg = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration="2024-12-20",
        side="BUY",
        quantity=10,
    )

    contract_symbol = leg.get_contract_symbol()
    assert "AAPL" in contract_symbol
    assert "C" in contract_symbol  # Call indicator


def test_option_leg_notional():
    """Test notional calculation."""
    leg = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration="2024-12-20",
        side="BUY",
        quantity=10,
        contract_multiplier=100,
    )

    # Premium of $2.50 per contract
    notional = leg.get_notional(2.50)
    assert notional == 2.50 * 10 * 100  # $2,500


def test_option_order_creation():
    """Test single-leg option order creation."""
    leg = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration="2024-12-20",
        side="BUY",
        quantity=10,
    )

    order = OptionOrder(
        strategy_id="test_strategy",
        leg=leg,
        limit_price=2.50,
    )

    assert order.leg == leg
    assert order.limit_price == 2.50
    assert order.status == OrderStatus.PENDING
    assert order.filled_quantity == 0


def test_option_order_state_transitions():
    """Test option order state transitions."""
    leg = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration="2024-12-20",
        side="BUY",
        quantity=10,
    )

    order = OptionOrder(strategy_id="test", leg=leg)

    # Valid transition: PENDING -> SUBMITTED
    order.update_status(OrderStatus.SUBMITTED)
    assert order.status == OrderStatus.SUBMITTED
    assert order.submitted_at is not None

    # Valid transition: SUBMITTED -> FILLED
    order.update_status(OrderStatus.FILLED)
    assert order.status == OrderStatus.FILLED
    assert order.is_terminal()


def test_spread_order_creation():
    """Test multi-leg spread order creation."""
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

    spread = OptionSpreadOrder(
        strategy_id="test_strategy",
        legs=[leg1, leg2],
        limit_price=1.50,  # Net debit
    )

    assert len(spread.legs) == 2
    assert spread.limit_price == 1.50
    assert not spread.is_fully_filled()


def test_spread_order_validation():
    """Test spread order validation."""
    # Spread must have at least 2 legs
    with pytest.raises(Exception):
        OptionSpreadOrder(
            strategy_id="test",
            legs=[
                OptionLeg(
                    symbol="AAPL",
                    option_type=OptionType.CALL,
                    strike=175.0,
                    expiration="2024-12-20",
                    side="BUY",
                    quantity=10,
                )
            ],
        )


def test_option_leg_validation():
    """Test option leg validation."""
    # Valid leg
    leg = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        side="BUY",
        quantity=10,
    )

    is_valid, error = OptionContractValidator.validate_leg(leg)
    assert is_valid is True
    assert error is None

    # Invalid expiration (past date)
    leg_invalid = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration="2020-01-01",  # Past date
        side="BUY",
        quantity=10,
    )

    is_valid, error = OptionContractValidator.validate_leg(leg_invalid)
    assert is_valid is False
    assert "future" in error.lower()


def test_option_order_validation():
    """Test option order validation."""
    leg = OptionLeg(
        symbol="AAPL",
        option_type=OptionType.CALL,
        strike=175.0,
        expiration=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        side="BUY",
        quantity=10,
    )

    order = OptionOrder(strategy_id="test", leg=leg, limit_price=2.50)

    is_valid, error = OptionContractValidator.validate_option_order(order)
    assert is_valid is True
    assert error is None


def test_spread_order_validation():
    """Test spread order validation."""
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

    is_valid, error = OptionContractValidator.validate_spread_order(spread)
    assert is_valid is True
    assert error is None

    # Invalid: different underlyings
    leg3 = OptionLeg(
        symbol="MSFT",  # Different underlying
        option_type=OptionType.CALL,
        strike=180.0,
        expiration=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        side="SELL",
        quantity=10,
    )

    spread_invalid = OptionSpreadOrder(
        strategy_id="test",
        legs=[leg1, leg3],
        limit_price=1.50,
    )

    is_valid, error = OptionContractValidator.validate_spread_order(spread_invalid)
    assert is_valid is False
    assert "underlying" in error.lower()


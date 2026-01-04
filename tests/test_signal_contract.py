"""Tests for signal contract validation."""

import pytest

from trade_engine.config.signal_contract import SignalConstraints, TradingSignal, Side, TimeHorizon


def test_valid_signal():
    """Test valid signal creation."""
    signal = TradingSignal(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=Side.BUY,
        confidence=0.85,
        target_exposure=10000.0,
        time_horizon=TimeHorizon.INTRADAY,
        constraints=SignalConstraints(max_slippage_bps=25, max_notional=15000.0),
    )

    assert signal.strategy_id == "test_strategy"
    assert signal.symbol == "AAPL"
    assert signal.side == Side.BUY
    assert signal.get_order_notional() == 10000.0  # min(target_exposure, max_notional)


def test_signal_validation():
    """Test signal validation rules."""
    # Invalid confidence (out of range)
    with pytest.raises(Exception):
        TradingSignal(
            strategy_id="test",
            symbol="AAPL",
            side=Side.BUY,
            confidence=1.5,  # Invalid: > 1.0
            target_exposure=1000.0,
            time_horizon=TimeHorizon.INTRADAY,
            constraints=SignalConstraints(max_slippage_bps=25),
        )

    # Invalid target exposure (negative)
    with pytest.raises(Exception):
        TradingSignal(
            strategy_id="test",
            symbol="AAPL",
            side=Side.BUY,
            confidence=0.8,
            target_exposure=-1000.0,  # Invalid: negative
            time_horizon=TimeHorizon.INTRADAY,
            constraints=SignalConstraints(max_slippage_bps=25),
        )


def test_signal_notional_calculation():
    """Test order notional calculation."""
    # Without max_notional constraint
    signal1 = TradingSignal(
        strategy_id="test",
        symbol="AAPL",
        side=Side.BUY,
        confidence=0.8,
        target_exposure=10000.0,
        time_horizon=TimeHorizon.INTRADAY,
        constraints=SignalConstraints(max_slippage_bps=25),
    )
    assert signal1.get_order_notional() == 10000.0

    # With max_notional constraint (should use minimum)
    signal2 = TradingSignal(
        strategy_id="test",
        symbol="AAPL",
        side=Side.BUY,
        confidence=0.8,
        target_exposure=10000.0,
        time_horizon=TimeHorizon.INTRADAY,
        constraints=SignalConstraints(max_slippage_bps=25, max_notional=5000.0),
    )
    assert signal2.get_order_notional() == 5000.0


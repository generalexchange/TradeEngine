"""Tests for risk management checks."""

import pytest

from trade_engine.config.limits import RiskLimits
from trade_engine.config.signal_contract import SignalConstraints, TradingSignal, Side, TimeHorizon
from trade_engine.portfolio.client import PortfolioClient
from trade_engine.risk.exposure import ExposureCalculator
from trade_engine.risk.loss_limits import LossLimitChecker
from trade_engine.risk.pre_trade import PreTradeRiskChecker
from trade_engine.risk.throttles import ThrottleChecker


@pytest.fixture
def portfolio_client():
    """Create a test portfolio client."""
    client = PortfolioClient()
    client.set_mock_portfolio_value(1_000_000.0)  # $1M portfolio
    return client


@pytest.fixture
def limits():
    """Create test risk limits."""
    return RiskLimits(
        max_position_size_usd=100_000.0,
        max_total_exposure_usd=500_000.0,
        max_order_notional_usd=50_000.0,
        min_order_notional_usd=1_000.0,
        max_daily_loss_usd=10_000.0,
    )


@pytest.fixture
def risk_checker(portfolio_client, limits):
    """Create a pre-trade risk checker."""
    exposure_calc = ExposureCalculator(portfolio_client)
    loss_checker = LossLimitChecker(portfolio_client)
    throttle_checker = ThrottleChecker()  # No Redis for testing

    return PreTradeRiskChecker(
        exposure_calculator=exposure_calc,
        loss_limit_checker=loss_checker,
        throttle_checker=throttle_checker,
        limits=limits,
    )


@pytest.mark.asyncio
async def test_order_notional_check(risk_checker):
    """Test order notional limits."""
    # Valid order
    signal = TradingSignal(
        strategy_id="test",
        symbol="AAPL",
        side=Side.BUY,
        confidence=0.8,
        target_exposure=10_000.0,
        time_horizon=TimeHorizon.INTRADAY,
        constraints=SignalConstraints(max_slippage_bps=25),
    )

    valid, error = await risk_checker.check_order_notional(signal)
    assert valid is True
    assert error is None

    # Order too large
    signal_large = TradingSignal(
        strategy_id="test",
        symbol="AAPL",
        side=Side.BUY,
        confidence=0.8,
        target_exposure=100_000.0,  # Exceeds max_order_notional
        time_horizon=TimeHorizon.INTRADAY,
        constraints=SignalConstraints(max_slippage_bps=25),
    )

    valid, error = await risk_checker.check_order_notional(signal_large)
    assert valid is False
    assert error is not None

    # Order too small
    signal_small = TradingSignal(
        strategy_id="test",
        symbol="AAPL",
        side=Side.BUY,
        confidence=0.8,
        target_exposure=500.0,  # Below min_order_notional
        time_horizon=TimeHorizon.INTRADAY,
        constraints=SignalConstraints(max_slippage_bps=25),
    )

    valid, error = await risk_checker.check_order_notional(signal_small)
    assert valid is False
    assert error is not None


@pytest.mark.asyncio
async def test_position_limit_check(portfolio_client, limits):
    """Test position size limits."""
    exposure_calc = ExposureCalculator(portfolio_client)

    # Set existing position
    portfolio_client.set_mock_position("AAPL", 50_000.0)

    signal = TradingSignal(
        strategy_id="test",
        symbol="AAPL",
        side=Side.BUY,
        confidence=0.8,
        target_exposure=60_000.0,  # Would exceed max_position_size_usd
        time_horizon=TimeHorizon.INTRADAY,
        constraints=SignalConstraints(max_slippage_bps=25),
    )

    valid, error = await exposure_calc.check_position_limit(signal, limits)
    assert valid is False
    assert "Position limit exceeded" in error


@pytest.mark.asyncio
async def test_all_risk_checks(risk_checker, portfolio_client):
    """Test full risk check suite."""
    # Valid signal
    signal = TradingSignal(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=Side.BUY,
        confidence=0.8,
        target_exposure=10_000.0,
        time_horizon=TimeHorizon.INTRADAY,
        constraints=SignalConstraints(max_slippage_bps=25),
    )

    is_valid, errors, check_results = await risk_checker.run_all_checks(signal)

    # Should pass all checks (assuming no existing positions/losses)
    assert is_valid is True
    assert len(errors) == 0
    assert all(result["valid"] for result in check_results.values())


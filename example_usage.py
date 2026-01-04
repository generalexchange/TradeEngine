"""Example usage of the Trade Engine.

This script demonstrates how to use the Trade Engine to process trading signals.
"""

import asyncio

from trade_engine.api.kill_switch import KillSwitch
from trade_engine.api.signal_ingest import SignalIngestionService, set_service
from trade_engine.audit.decision_log import DecisionLogger
from trade_engine.audit.trade_log import TradeLogger
from trade_engine.brokers.paper import PaperBroker
from trade_engine.config.limits import DEFAULT_LIMITS
from trade_engine.config.signal_contract import SignalConstraints, TradingSignal, Side, TimeHorizon
from trade_engine.execution.order_router import OrderRouter
from trade_engine.portfolio.client import PortfolioClient
from trade_engine.risk.exposure import ExposureCalculator
from trade_engine.risk.loss_limits import LossLimitChecker
from trade_engine.risk.pre_trade import PreTradeRiskChecker
from trade_engine.risk.throttles import ThrottleChecker


async def main():
    """Example: Process a trading signal through the Trade Engine."""
    print("=== Trade Engine Example ===\n")

    # Initialize components
    portfolio_client = PortfolioClient()
    portfolio_client.set_mock_portfolio_value(1_000_000.0)  # $1M portfolio
    portfolio_client.set_mock_position("AAPL", 50_000.0)  # Existing $50k position

    kill_switch = KillSwitch()
    broker = PaperBroker(slippage_bps=5)
    order_router = OrderRouter(default_broker=broker)

    # Initialize risk checkers
    exposure_calculator = ExposureCalculator(portfolio_client)
    loss_limit_checker = LossLimitChecker(portfolio_client)
    throttle_checker = ThrottleChecker()

    risk_checker = PreTradeRiskChecker(
        exposure_calculator=exposure_calculator,
        loss_limit_checker=loss_limit_checker,
        throttle_checker=throttle_checker,
        limits=DEFAULT_LIMITS,
    )

    # Initialize audit loggers
    decision_logger = DecisionLogger()
    trade_logger = TradeLogger()

    # Initialize signal ingestion service
    signal_service = SignalIngestionService(
        risk_checker=risk_checker,
        order_router=order_router,
        kill_switch=kill_switch,
        decision_logger=decision_logger,
        trade_logger=trade_logger,
        limits=DEFAULT_LIMITS,
    )

    # Create a trading signal
    signal = TradingSignal(
        strategy_id="momentum_strategy_v1",
        symbol="AAPL",
        side=Side.BUY,
        confidence=0.85,
        target_exposure=10_000.0,  # $10k order
        time_horizon=TimeHorizon.INTRADAY,
        constraints=SignalConstraints(max_slippage_bps=25, max_notional=15_000.0),
    )

    print(f"Processing signal: {signal.symbol} {signal.side} ${signal.target_exposure:,.2f}")
    print(f"Strategy: {signal.strategy_id}")
    print(f"Confidence: {signal.confidence:.2%}\n")

    # Process the signal
    response = await signal_service.process_signal(signal)

    print(f"Signal ID: {response.signal_id}")
    print(f"Status: {response.status}")
    print(f"Message: {response.message}")

    if response.order_id:
        print(f"Order ID: {response.order_id}")

    if response.errors:
        print(f"Errors: {response.errors}")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())


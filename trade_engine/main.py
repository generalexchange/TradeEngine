"""Main entry point for Trade Engine.

Initializes all components and starts the FastAPI server.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from trade_engine.api.health import router as health_router
from trade_engine.api.kill_switch import KillSwitch
from trade_engine.api.signal_ingest import SignalIngestionService, router as signal_router, set_service
from trade_engine.audit.decision_log import DecisionLogger
from trade_engine.audit.trade_log import TradeLogger
from trade_engine.brokers.paper import PaperBroker
from trade_engine.config.limits import DEFAULT_LIMITS
from trade_engine.execution.order_router import OrderRouter
from trade_engine.portfolio.client import PortfolioClient
from trade_engine.risk.exposure import ExposureCalculator
from trade_engine.risk.loss_limits import LossLimitChecker
from trade_engine.risk.pre_trade import PreTradeRiskChecker
from trade_engine.risk.throttles import ThrottleChecker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - initializes and cleans up resources."""
    # Initialize components
    redis_client = None  # In production, initialize Redis client

    # Initialize portfolio client
    portfolio_url = os.getenv("PORTFOLIO_SERVICE_URL")
    portfolio_client = PortfolioClient(portfolio_service_url=portfolio_url)

    # Initialize kill switch
    kill_switch = KillSwitch(redis_client=redis_client)

    # Initialize broker
    broker = PaperBroker(slippage_bps=5)
    order_router = OrderRouter(default_broker=broker)

    # Initialize risk checkers
    exposure_calculator = ExposureCalculator(portfolio_client)
    loss_limit_checker = LossLimitChecker(portfolio_client)
    throttle_checker = ThrottleChecker(redis_client=redis_client)

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
    set_service(signal_service)

    # Store components in app state for API endpoints
    app.state.kill_switch = kill_switch
    app.state.portfolio_client = portfolio_client
    app.state.broker = broker

    yield  # Application runs here

    # Cleanup (if needed)
    # In production, close connections, etc.


# Create FastAPI app
app = FastAPI(
    title="Trade Engine",
    description="Production-grade Trade Engine for algorithmic trading",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(health_router, tags=["health"])
app.include_router(
    signal_router,
    prefix="/api/v1",
    tags=["signals"],
)

# Kill switch endpoints
@app.post("/api/v1/kill-switch/activate")
async def activate_kill_switch(reason: str = "Manual activation"):
    """Activate kill switch."""
    kill_switch = app.state.kill_switch
    await kill_switch.activate(reason)
    return {"status": "activated", "reason": reason}


@app.post("/api/v1/kill-switch/deactivate")
async def deactivate_kill_switch(reason: str = "Manual deactivation"):
    """Deactivate kill switch."""
    kill_switch = app.state.kill_switch
    await kill_switch.deactivate(reason)
    return {"status": "deactivated", "reason": reason}


@app.get("/api/v1/kill-switch/status")
async def get_kill_switch_status():
    """Get kill switch status."""
    kill_switch = app.state.kill_switch
    return await kill_switch.get_status()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


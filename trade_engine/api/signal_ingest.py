"""Signal ingestion endpoint.

Receives trading signals and processes them through the Trade Engine.
"""

from typing import Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from trade_engine.api.kill_switch import KillSwitch
from trade_engine.audit.decision_log import DecisionLogger
from trade_engine.audit.trade_log import TradeLogger
from trade_engine.config.limits import DEFAULT_LIMITS, RiskLimits
from trade_engine.config.signal_contract import TradingSignal
from trade_engine.execution.order_router import OrderRouter
from trade_engine.execution.order_state import Order, OrderStatus
from trade_engine.risk.pre_trade import PreTradeRiskChecker

router = APIRouter()


class SignalResponse(BaseModel):
    """Response model for signal ingestion."""

    signal_id: str
    order_id: Optional[str] = None
    status: str  # APPROVED, REJECTED, PENDING
    message: str
    errors: list[str] = []


class SignalIngestionService:
    """Service for processing trading signals.

    This is the main orchestration point for signal processing.
    """

    def __init__(
        self,
        risk_checker: PreTradeRiskChecker,
        order_router: OrderRouter,
        kill_switch: KillSwitch,
        decision_logger: DecisionLogger,
        trade_logger: TradeLogger,
        limits: RiskLimits = DEFAULT_LIMITS,
    ):
        """Initialize signal ingestion service.

        Args:
            risk_checker: Pre-trade risk checker
            order_router: Order router
            kill_switch: Kill switch
            decision_logger: Decision logger
            trade_logger: Trade logger
            limits: Risk limits
        """
        self.risk_checker = risk_checker
        self.order_router = order_router
        self.kill_switch = kill_switch
        self.decision_logger = decision_logger
        self.trade_logger = trade_logger
        self.limits = limits

    async def process_signal(self, signal: TradingSignal) -> SignalResponse:
        """Process a trading signal through the Trade Engine.

        This is the main entry point for signal processing.
        All steps are logged for full auditability.

        Args:
            signal: Trading signal

        Returns:
            Signal response with status and order ID (if approved)
        """
        signal_id = str(uuid4())

        # 1. Check kill switch (highest priority)
        if await self.kill_switch.is_active():
            error_msg = "Kill switch is active - trading halted"
            self.decision_logger.log_risk_decision(
                signal_id=signal_id,
                strategy_id=signal.strategy_id,
                symbol=signal.symbol,
                decision="REJECTED",
                check_results={"kill_switch": {"valid": False, "error": error_msg}},
                errors=[error_msg],
            )
            return SignalResponse(
                signal_id=signal_id,
                status="REJECTED",
                message=error_msg,
                errors=[error_msg],
            )

        # 2. Run all risk checks
        is_valid, errors, check_results = await self.risk_checker.run_all_checks(signal)

        # 3. Log decision
        decision = "APPROVED" if is_valid else "REJECTED"
        self.decision_logger.log_risk_decision(
            signal_id=signal_id,
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            decision=decision,
            check_results=check_results,
            errors=errors,
        )

        if not is_valid:
            return SignalResponse(
                signal_id=signal_id,
                status="REJECTED",
                message="Signal rejected by risk checks",
                errors=errors,
            )

        # 4. Create order
        order = Order(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=signal.side.value,
            quantity=signal.target_exposure,  # Simplified - in production, convert to shares
            notional=signal.get_order_notional(),
        )

        self.trade_logger.log_order_created(order, signal.to_dict())

        # 5. Submit order to broker
        order, submit_error = await self.order_router.submit_order(order, signal)

        if submit_error:
            order.update_status(OrderStatus.REJECTED, rejection_reason=submit_error)
            self.trade_logger.log_order_rejected(order, submit_error)
            return SignalResponse(
                signal_id=signal_id,
                order_id=order.order_id,
                status="REJECTED",
                message=f"Order submission failed: {submit_error}",
                errors=[submit_error],
            )

        self.trade_logger.log_order_submitted(order, order.broker_order_id or "")

        return SignalResponse(
            signal_id=signal_id,
            order_id=order.order_id,
            status="APPROVED",
            message="Signal processed and order submitted",
            errors=[],
        )


# Global service instance (in production, use dependency injection)
_service: Optional[SignalIngestionService] = None


def set_service(service: SignalIngestionService):
    """Set the global signal ingestion service."""
    global _service
    _service = service


@router.post("/signals", response_model=SignalResponse)
async def ingest_signal(signal: TradingSignal) -> SignalResponse:
    """Ingest a trading signal.

    This endpoint receives trading signals and processes them through
    the full Trade Engine pipeline: validation, risk checks, and execution.

    Args:
        signal: Trading signal

    Returns:
        Signal response with processing result

    Raises:
        HTTPException: If service is not initialized or processing fails
    """
    if _service is None:
        raise HTTPException(
            status_code=503, detail="Signal ingestion service not initialized"
        )

    try:
        return await _service.process_signal(signal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signal processing failed: {str(e)}")


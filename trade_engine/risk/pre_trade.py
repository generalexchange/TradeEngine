"""Pre-trade risk checks orchestration.

This module coordinates all risk checks before order execution.
All checks must pass for an order to proceed.
"""

from typing import Optional

from trade_engine.config.limits import RiskLimits
from trade_engine.config.signal_contract import TradingSignal
from trade_engine.risk.exposure import ExposureCalculator
from trade_engine.risk.loss_limits import LossLimitChecker
from trade_engine.risk.throttles import ThrottleChecker


class PreTradeRiskChecker:
    """Orchestrates all pre-trade risk checks.

    This is the main entry point for risk validation.
    All checks are deterministic and stateless per request.
    """

    def __init__(
        self,
        exposure_calculator: ExposureCalculator,
        loss_limit_checker: LossLimitChecker,
        throttle_checker: ThrottleChecker,
        limits: RiskLimits,
    ):
        """Initialize with all risk checkers and limits."""
        self.exposure_calculator = exposure_calculator
        self.loss_limit_checker = loss_limit_checker
        self.throttle_checker = throttle_checker
        self.limits = limits

    async def check_order_notional(
        self, signal: TradingSignal
    ) -> tuple[bool, Optional[str]]:
        """Check if order notional is within limits.

        Returns:
            (is_valid, error_message)
        """
        notional = signal.get_order_notional()

        if notional > self.limits.max_order_notional_usd:
            return (
                False,
                f"Order notional exceeds limit: ${notional:.2f} > ${self.limits.max_order_notional_usd:.2f}",
            )

        if notional < self.limits.min_order_notional_usd:
            return (
                False,
                f"Order notional below minimum: ${notional:.2f} < ${self.limits.min_order_notional_usd:.2f}",
            )

        return True, None

    async def check_slippage_limit(
        self, signal: TradingSignal
    ) -> tuple[bool, Optional[str]]:
        """Check if requested slippage is within limits.

        Returns:
            (is_valid, error_message)
        """
        if signal.constraints.max_slippage_bps > self.limits.max_slippage_bps:
            return (
                False,
                f"Slippage limit exceeded: {signal.constraints.max_slippage_bps} bps > {self.limits.max_slippage_bps} bps",
            )

        return True, None

    async def run_all_checks(
        self, signal: TradingSignal
    ) -> tuple[bool, list[str], dict]:
        """Run all pre-trade risk checks.

        Args:
            signal: Trading signal to validate

        Returns:
            (is_valid, error_messages, check_results)
            check_results: Dictionary of individual check results for audit
        """
        errors: list[str] = []
        check_results: dict = {}

        # 1. Order notional check
        valid, error = await self.check_order_notional(signal)
        check_results["order_notional"] = {"valid": valid, "error": error}
        if not valid:
            errors.append(error)

        # 2. Slippage limit check
        valid, error = await self.check_slippage_limit(signal)
        check_results["slippage"] = {"valid": valid, "error": error}
        if not valid:
            errors.append(error)

        # 3. Position size limit
        valid, error = await self.exposure_calculator.check_position_limit(
            signal, self.limits
        )
        check_results["position_limit"] = {"valid": valid, "error": error}
        if not valid:
            errors.append(error)

        # 4. Total exposure limit
        valid, error = await self.exposure_calculator.check_total_exposure_limit(
            signal, self.limits
        )
        check_results["total_exposure"] = {"valid": valid, "error": error}
        if not valid:
            errors.append(error)

        # 5. Single asset concentration limit
        portfolio_value = await self.exposure_calculator.portfolio_client.get_portfolio_value()
        valid, error = await self.exposure_calculator.check_single_asset_exposure_limit(
            signal, self.limits, portfolio_value or 0.0
        )
        check_results["single_asset_exposure"] = {"valid": valid, "error": error}
        if not valid:
            errors.append(error)

        # 6. Daily loss limit (strategy-specific)
        valid, error = await self.loss_limit_checker.check_daily_loss_limit(
            signal.strategy_id, self.limits
        )
        check_results["strategy_daily_loss"] = {"valid": valid, "error": error}
        if not valid:
            errors.append(error)

        # 7. Total daily loss limit
        valid, error = await self.loss_limit_checker.check_total_daily_loss_limit(
            self.limits
        )
        check_results["total_daily_loss"] = {"valid": valid, "error": error}
        if not valid:
            errors.append(error)

        # 8. Rate limiting
        valid, error, _ = await self.throttle_checker.check_rate_limit(
            signal.strategy_id, self.limits
        )
        check_results["rate_limit"] = {"valid": valid, "error": error}
        if not valid:
            errors.append(error)

        is_valid = len(errors) == 0
        return is_valid, errors, check_results


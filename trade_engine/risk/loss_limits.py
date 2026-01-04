"""Daily loss limits and drawdown controls.

This module enforces daily loss limits to prevent catastrophic drawdowns.
State is maintained in external storage (Redis/DB).
"""

from datetime import datetime, timezone
from typing import Optional

from trade_engine.config.limits import RiskLimits


class LossLimitChecker:
    """Checks daily loss limits against current P&L.

    This class is stateless - all P&L data comes from external sources.
    """

    def __init__(self, portfolio_client: "PortfolioClient"):
        """Initialize with portfolio client for P&L data."""
        self.portfolio_client = portfolio_client

    async def get_daily_pnl(self, strategy_id: Optional[str] = None) -> float:
        """Get daily P&L for a strategy or all strategies.

        Args:
            strategy_id: Optional strategy ID to filter by

        Returns:
            Daily P&L in USD (negative for losses)
        """
        # Get start of day timestamp
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        if strategy_id:
            return await self.portfolio_client.get_strategy_daily_pnl(
                strategy_id, since=today_start
            )
        else:
            return await self.portfolio_client.get_total_daily_pnl(since=today_start)

    async def check_daily_loss_limit(
        self, strategy_id: str, limits: RiskLimits
    ) -> tuple[bool, Optional[str]]:
        """Check if strategy has exceeded daily loss limit.

        Returns:
            (is_valid, error_message)
        """
        daily_pnl = await self.get_daily_pnl(strategy_id)

        # Check absolute loss limit
        if daily_pnl < -limits.max_daily_loss_usd:
            return (
                False,
                f"Daily loss limit exceeded: ${abs(daily_pnl):.2f} > ${limits.max_daily_loss_usd:.2f}",
            )

        # Check percentage loss limit (if portfolio value available)
        portfolio_value = await self.portfolio_client.get_portfolio_value()
        if portfolio_value and portfolio_value > 0:
            loss_pct = abs(daily_pnl) / portfolio_value
            if loss_pct > limits.max_daily_loss_pct:
                return (
                    False,
                    f"Daily loss percentage limit exceeded: {loss_pct:.2%} > {limits.max_daily_loss_pct:.2%}",
                )

        return True, None

    async def check_total_daily_loss_limit(
        self, limits: RiskLimits
    ) -> tuple[bool, Optional[str]]:
        """Check if total portfolio has exceeded daily loss limit.

        Returns:
            (is_valid, error_message)
        """
        total_daily_pnl = await self.get_daily_pnl()

        if total_daily_pnl < -limits.max_daily_loss_usd:
            return (
                False,
                f"Total daily loss limit exceeded: ${abs(total_daily_pnl):.2f} > ${limits.max_daily_loss_usd:.2f}",
            )

        return True, None


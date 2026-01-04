"""Position and exposure calculations.

This module calculates current positions and exposures for risk checks.
All state is fetched from external portfolio service.
"""

from typing import Dict, Optional

from trade_engine.config.limits import RiskLimits
from trade_engine.config.signal_contract import TradingSignal


class ExposureCalculator:
    """Calculates portfolio exposure for risk checks.

    This class is stateless - all position data comes from external sources.
    """

    def __init__(self, portfolio_client: "PortfolioClient"):
        """Initialize with portfolio client for position data."""
        self.portfolio_client = portfolio_client

    async def get_current_position(self, symbol: str) -> float:
        """Get current position size for a symbol in USD.

        Returns:
            Position size in USD (positive for long, negative for short)
        """
        return await self.portfolio_client.get_position(symbol)

    async def get_total_exposure(self) -> float:
        """Get total portfolio exposure in USD (sum of absolute positions)."""
        positions = await self.portfolio_client.get_all_positions()
        return sum(abs(pos) for pos in positions.values())

    async def get_asset_exposure(self, symbol: str) -> float:
        """Get exposure for a specific asset in USD (absolute value)."""
        position = await self.get_current_position(symbol)
        return abs(position)

    async def calculate_new_exposure(
        self, signal: TradingSignal, current_position: float
    ) -> float:
        """Calculate what the new exposure would be after executing the signal.

        Args:
            signal: Trading signal
            current_position: Current position in USD

        Returns:
            New exposure after signal execution (absolute value)
        """
        if signal.side == "BUY":
            new_position = current_position + signal.target_exposure
        else:  # SELL
            new_position = current_position - signal.target_exposure

        return abs(new_position)

    async def check_position_limit(
        self, signal: TradingSignal, limits: RiskLimits
    ) -> tuple[bool, Optional[str]]:
        """Check if signal would violate position size limits.

        Returns:
            (is_valid, error_message)
        """
        current_position = await self.get_current_position(signal.symbol)
        new_exposure = await self.calculate_new_exposure(signal, current_position)

        if new_exposure > limits.max_position_size_usd:
            return (
                False,
                f"Position limit exceeded: {new_exposure:.2f} > {limits.max_position_size_usd:.2f}",
            )

        return True, None

    async def check_total_exposure_limit(
        self, signal: TradingSignal, limits: RiskLimits
    ) -> tuple[bool, Optional[str]]:
        """Check if signal would violate total portfolio exposure limits.

        Returns:
            (is_valid, error_message)
        """
        current_total = await self.get_total_exposure()
        current_asset = await self.get_asset_exposure(signal.symbol)
        new_asset = await self.calculate_new_exposure(
            signal, await self.get_current_position(signal.symbol)
        )

        # Calculate new total exposure
        new_total = current_total - current_asset + new_asset

        if new_total > limits.max_total_exposure_usd:
            return (
                False,
                f"Total exposure limit exceeded: {new_total:.2f} > {limits.max_total_exposure_usd:.2f}",
            )

        return True, None

    async def check_single_asset_exposure_limit(
        self, signal: TradingSignal, limits: RiskLimits, total_portfolio_value: float
    ) -> tuple[bool, Optional[str]]:
        """Check if signal would violate single asset concentration limit.

        Args:
            signal: Trading signal
            limits: Risk limits
            total_portfolio_value: Total portfolio value in USD

        Returns:
            (is_valid, error_message)
        """
        if total_portfolio_value <= 0:
            return True, None  # Skip check if portfolio value unknown

        new_exposure = await self.calculate_new_exposure(
            signal, await self.get_current_position(signal.symbol)
        )
        exposure_pct = new_exposure / total_portfolio_value

        if exposure_pct > limits.max_single_asset_exposure_pct:
            return (
                False,
                f"Single asset exposure limit exceeded: {exposure_pct:.2%} > {limits.max_single_asset_exposure_pct:.2%}",
            )

        return True, None


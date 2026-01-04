"""Portfolio client for externalized state management.

This client interfaces with an external portfolio service to fetch
position, exposure, and P&L data. All state is externalized.
"""

from datetime import datetime
from typing import Dict, Optional


class PortfolioClient:
    """Client for fetching portfolio state from external service.

    This is a stateless client - all data comes from external sources.
    In production, this would connect to a portfolio service API or database.
    """

    def __init__(self, portfolio_service_url: Optional[str] = None):
        """Initialize portfolio client.

        Args:
            portfolio_service_url: URL of portfolio service (optional for testing)
        """
        self.portfolio_service_url = portfolio_service_url
        # For testing/development, we can use in-memory state
        self._mock_positions: Dict[str, float] = {}
        self._mock_portfolio_value: Optional[float] = None
        self._mock_pnl_history: list[dict] = []

    async def get_position(self, symbol: str) -> float:
        """Get current position for a symbol in USD.

        Args:
            symbol: Trading symbol

        Returns:
            Position size in USD (positive for long, negative for short)
        """
        # In production, this would make an API call
        # For now, return mock data
        return self._mock_positions.get(symbol, 0.0)

    async def get_all_positions(self) -> Dict[str, float]:
        """Get all current positions.

        Returns:
            Dictionary mapping symbol to position size in USD
        """
        # In production, this would make an API call
        return self._mock_positions.copy()

    async def get_portfolio_value(self) -> Optional[float]:
        """Get total portfolio value in USD.

        Returns:
            Portfolio value or None if unavailable
        """
        # In production, this would make an API call
        return self._mock_portfolio_value

    async def get_strategy_daily_pnl(
        self, strategy_id: str, since: datetime
    ) -> float:
        """Get daily P&L for a specific strategy since a timestamp.

        Args:
            strategy_id: Strategy identifier
            since: Start timestamp

        Returns:
            P&L in USD (negative for losses)
        """
        # In production, this would query the portfolio service
        # For now, sum mock P&L history
        total = 0.0
        for entry in self._mock_pnl_history:
            if (
                entry.get("strategy_id") == strategy_id
                and entry.get("timestamp", datetime.min) >= since
            ):
                total += entry.get("pnl", 0.0)
        return total

    async def get_total_daily_pnl(self, since: datetime) -> float:
        """Get total daily P&L across all strategies.

        Args:
            since: Start timestamp

        Returns:
            Total P&L in USD
        """
        # In production, this would query the portfolio service
        total = 0.0
        for entry in self._mock_pnl_history:
            if entry.get("timestamp", datetime.min) >= since:
                total += entry.get("pnl", 0.0)
        return total

    # Mock methods for testing (not used in production)
    def set_mock_position(self, symbol: str, position: float):
        """Set mock position for testing."""
        self._mock_positions[symbol] = position

    def set_mock_portfolio_value(self, value: float):
        """Set mock portfolio value for testing."""
        self._mock_portfolio_value = value

    def add_mock_pnl(self, strategy_id: str, pnl: float, timestamp: Optional[datetime] = None):
        """Add mock P&L entry for testing."""
        if timestamp is None:
            timestamp = datetime.now()
        self._mock_pnl_history.append(
            {"strategy_id": strategy_id, "pnl": pnl, "timestamp": timestamp}
        )


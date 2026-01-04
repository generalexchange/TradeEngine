"""Base broker adapter interface.

All broker implementations must inherit from this abstract class.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BrokerAdapter(ABC):
    """Abstract base class for broker adapters.

    This provides a broker-agnostic interface for order execution.
    All broker-specific logic is encapsulated in implementations.
    """

    @abstractmethod
    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        **kwargs,
    ) -> str:
        """Submit an order to the broker.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            order_type: Order type (MARKET, LIMIT, etc.)
            **kwargs: Additional broker-specific parameters

        Returns:
            Broker order ID

        Raises:
            BrokerError: If order submission fails
        """
        pass

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order.

        Args:
            broker_order_id: Broker's order ID

        Returns:
            True if cancellation successful

        Raises:
            BrokerError: If cancellation fails
        """
        pass

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> dict:
        """Get current status of an order.

        Args:
            broker_order_id: Broker's order ID

        Returns:
            Order status dictionary

        Raises:
            BrokerError: If status check fails
        """
        pass

    @abstractmethod
    async def get_fills(self, broker_order_id: str) -> list[dict]:
        """Get fills for an order.

        Args:
            broker_order_id: Broker's order ID

        Returns:
            List of fill dictionaries

        Raises:
            BrokerError: If fill retrieval fails
        """
        pass

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return broker name/identifier."""
        pass


class BrokerError(Exception):
    """Base exception for broker-related errors."""

    pass


class BrokerConnectionError(BrokerError):
    """Raised when broker connection fails."""

    pass


class BrokerOrderError(BrokerError):
    """Raised when order submission/management fails."""

    pass


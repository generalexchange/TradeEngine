"""Base broker adapter interface.

All broker implementations must inherit from this abstract class.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from trade_engine.execution.option_orders import OptionLeg


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

    async def submit_option_order(
        self,
        leg: "OptionLeg",
        limit_price: Optional[float] = None,
        **kwargs,
    ) -> str:
        """Submit a single-leg option order to the broker.

        Args:
            leg: Option leg to execute
            limit_price: Optional limit price per contract
            **kwargs: Additional broker-specific parameters

        Returns:
            Broker order ID

        Raises:
            BrokerError: If order submission fails

        Note:
            Default implementation raises NotImplementedError.
            Brokers should override this method.
        """
        raise NotImplementedError("Option orders not supported by this broker")

    async def submit_option_spread(
        self,
        legs: list["OptionLeg"],
        limit_price: Optional[float] = None,
        **kwargs,
    ) -> str:
        """Submit a multi-leg option spread order (atomic execution).

        Args:
            legs: List of option legs in the spread
            limit_price: Optional net limit price for the spread
            **kwargs: Additional broker-specific parameters

        Returns:
            Broker order ID

        Raises:
            BrokerError: If order submission fails

        Note:
            Default implementation raises NotImplementedError.
            Brokers should override this method.
        """
        raise NotImplementedError("Option spreads not supported by this broker")


class BrokerError(Exception):
    """Base exception for broker-related errors."""

    pass


class BrokerConnectionError(BrokerError):
    """Raised when broker connection fails."""

    pass


class BrokerOrderError(BrokerError):
    """Raised when order submission/management fails."""

    pass


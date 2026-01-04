"""Paper trading broker adapter.

Simulates order execution without real capital at risk.
Useful for testing and development.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from trade_engine.brokers.base import BrokerAdapter, BrokerError


class PaperBroker(BrokerAdapter):
    """Paper trading broker - simulates execution without real capital.

    This broker simulates realistic execution with:
    - Instant fills (market orders)
    - Simulated slippage
    - Order state tracking
    """

    def __init__(self, slippage_bps: int = 5):
        """Initialize paper broker.

        Args:
            slippage_bps: Simulated slippage in basis points
        """
        self.slippage_bps = slippage_bps
        self._orders: dict[str, dict] = {}
        self._fills: dict[str, list[dict]] = {}
        self._option_orders: dict[str, dict] = {}
        self._option_fills: dict[str, list[dict]] = {}

    @property
    def broker_name(self) -> str:
        """Return broker name."""
        return "PAPER"

    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        **kwargs,
    ) -> str:
        """Submit order (simulated).

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            order_type: Order type (only MARKET supported for paper)
            **kwargs: Additional parameters

        Returns:
            Broker order ID
        """
        if order_type != "MARKET":
            raise BrokerError(f"Paper broker only supports MARKET orders, got {order_type}")

        broker_order_id = f"PAPER_{uuid4().hex[:8]}"

        # Simulate order submission delay
        await asyncio.sleep(0.01)

        # Store order
        self._orders[broker_order_id] = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "status": "SUBMITTED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # For paper trading, immediately fill market orders
        await self._simulate_fill(broker_order_id, symbol, side, quantity)

        return broker_order_id

    async def _simulate_fill(
        self, broker_order_id: str, symbol: str, side: str, quantity: float
    ):
        """Simulate order fill with slippage.

        Args:
            broker_order_id: Broker order ID
            symbol: Trading symbol
            side: Order side
            quantity: Order quantity
        """
        # Simulate execution delay
        await asyncio.sleep(0.05)

        # Get mock price (in production, would fetch from market data)
        base_price = self._get_mock_price(symbol)

        # Apply slippage
        slippage_multiplier = 1 + (self.slippage_bps / 10000) * (1 if side == "BUY" else -1)
        fill_price = base_price * slippage_multiplier

        # Create fill
        fill = {
            "fill_id": f"fill_{uuid4().hex[:8]}",
            "broker_order_id": broker_order_id,
            "symbol": symbol,
            "quantity": quantity,
            "price": fill_price,
            "notional": quantity * fill_price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Store fill
        if broker_order_id not in self._fills:
            self._fills[broker_order_id] = []
        self._fills[broker_order_id].append(fill)

        # Update order status
        if broker_order_id in self._orders:
            self._orders[broker_order_id]["status"] = "FILLED"
            self._orders[broker_order_id]["filled_at"] = fill["timestamp"]

    def _get_mock_price(self, symbol: str) -> float:
        """Get mock price for a symbol (for testing).

        In production, this would fetch real market data.

        Args:
            symbol: Trading symbol

        Returns:
            Mock price
        """
        # Simple hash-based mock price for consistency
        mock_prices = {
            "AAPL": 175.50,
            "MSFT": 380.25,
            "GOOGL": 140.75,
            "TSLA": 250.00,
        }
        return mock_prices.get(symbol, 100.0)

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order.

        Args:
            broker_order_id: Broker order ID

        Returns:
            True if cancellation successful
        """
        if broker_order_id not in self._orders:
            raise BrokerError(f"Order not found: {broker_order_id}")

        order = self._orders[broker_order_id]
        if order["status"] in ("FILLED", "CANCELLED"):
            return False

        order["status"] = "CANCELLED"
        order["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        return True

    async def get_order_status(self, broker_order_id: str) -> dict:
        """Get order status.

        Args:
            broker_order_id: Broker order ID

        Returns:
            Order status dictionary
        """
        if broker_order_id not in self._orders:
            raise BrokerError(f"Order not found: {broker_order_id}")

        return self._orders[broker_order_id].copy()

    async def get_fills(self, broker_order_id: str) -> list[dict]:
        """Get fills for an order.

        Args:
            broker_order_id: Broker order ID

        Returns:
            List of fill dictionaries
        """
        return self._fills.get(broker_order_id, []).copy()

    async def submit_option_order(
        self,
        leg: "OptionLeg",
        limit_price: Optional[float] = None,
        **kwargs,
    ) -> str:
        """Submit a single-leg option order (simulated).

        Args:
            leg: Option leg to execute
            limit_price: Optional limit price per contract
            **kwargs: Additional parameters

        Returns:
            Broker order ID
        """
        from trade_engine.execution.option_orders import OptionLeg

        broker_order_id = f"PAPER_OPT_{uuid4().hex[:8]}"

        # Simulate order submission delay
        await asyncio.sleep(0.01)

        # Store order
        contract_symbol = leg.get_contract_symbol()
        self._option_orders[broker_order_id] = {
            "contract_symbol": contract_symbol,
            "leg": leg,
            "status": "SUBMITTED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # For paper trading, immediately fill option orders
        await self._simulate_option_fill(broker_order_id, leg, limit_price)

        return broker_order_id

    async def _simulate_option_fill(
        self, broker_order_id: str, leg: "OptionLeg", limit_price: Optional[float]
    ):
        """Simulate option fill with mock premium.

        Args:
            broker_order_id: Broker order ID
            leg: Option leg
            limit_price: Optional limit price
        """
        from trade_engine.execution.option_orders import OptionLeg

        # Simulate execution delay
        await asyncio.sleep(0.05)

        # Get mock option premium (simplified - in production, use real market data)
        base_premium = self._get_mock_option_premium(leg)

        # Use limit price if provided, otherwise use mock premium
        fill_price = limit_price if limit_price else base_premium

        # Create fill
        fill = {
            "fill_id": f"option_fill_{uuid4().hex[:8]}",
            "broker_order_id": broker_order_id,
            "contract_symbol": leg.get_contract_symbol(),
            "quantity": leg.quantity,
            "price_per_contract": fill_price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Store fill
        if broker_order_id not in self._option_fills:
            self._option_fills[broker_order_id] = []
        self._option_fills[broker_order_id].append(fill)

        # Update order status
        if broker_order_id in self._option_orders:
            self._option_orders[broker_order_id]["status"] = "FILLED"
            self._option_orders[broker_order_id]["filled_at"] = fill["timestamp"]

    def _get_mock_option_premium(self, leg: "OptionLeg") -> float:
        """Get mock option premium (for testing).

        Args:
            leg: Option leg

        Returns:
            Mock premium per contract
        """
        # Simplified mock premium calculation
        # In production, this would fetch real option chain data
        base_price = self._get_mock_price(leg.symbol)
        strike = leg.strike

        # Simple intrinsic value + time value approximation
        if leg.option_type.value == "CALL":
            intrinsic = max(0, base_price - strike)
        else:  # PUT
            intrinsic = max(0, strike - base_price)

        # Add mock time value (simplified)
        time_value = base_price * 0.02  # 2% of underlying as time value

        return max(0.01, intrinsic + time_value)  # Minimum $0.01

    async def submit_option_spread(
        self,
        legs: list["OptionLeg"],
        limit_price: Optional[float] = None,
        **kwargs,
    ) -> str:
        """Submit a multi-leg option spread (atomic execution, simulated).

        Args:
            legs: List of option legs
            limit_price: Optional net limit price for the spread
            **kwargs: Additional parameters

        Returns:
            Broker order ID
        """
        from trade_engine.execution.option_orders import OptionLeg

        broker_order_id = f"PAPER_SPREAD_{uuid4().hex[:8]}"

        # Simulate order submission delay
        await asyncio.sleep(0.01)

        # Store spread order
        self._option_orders[broker_order_id] = {
            "legs": legs,
            "status": "SUBMITTED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_spread": True,
        }

        # For paper trading, immediately fill all legs atomically
        await self._simulate_spread_fill(broker_order_id, legs, limit_price)

        return broker_order_id

    async def _simulate_spread_fill(
        self,
        broker_order_id: str,
        legs: list["OptionLeg"],
        limit_price: Optional[float],
    ):
        """Simulate atomic spread fill (all legs fill together).

        Args:
            broker_order_id: Broker order ID
            legs: Option legs in the spread
            limit_price: Optional net limit price
        """
        from trade_engine.execution.option_orders import OptionLeg

        # Simulate execution delay
        await asyncio.sleep(0.05)

        # Calculate individual leg prices if limit_price provided
        # Otherwise, use mock premiums
        if limit_price:
            # Distribute net price across legs (simplified)
            leg_prices = [limit_price / len(legs)] * len(legs)
        else:
            leg_prices = [self._get_mock_option_premium(leg) for leg in legs]

        # Create fills for all legs (atomic execution)
        fills = []
        for leg, price in zip(legs, leg_prices):
            fill = {
                "fill_id": f"spread_fill_{uuid4().hex[:8]}",
                "broker_order_id": broker_order_id,
                "contract_symbol": leg.get_contract_symbol(),
                "quantity": leg.quantity,
                "price_per_contract": price,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            fills.append(fill)

        # Store all fills
        self._option_fills[broker_order_id] = fills

        # Update order status
        if broker_order_id in self._option_orders:
            self._option_orders[broker_order_id]["status"] = "FILLED"
            self._option_orders[broker_order_id]["filled_at"] = fills[0]["timestamp"]


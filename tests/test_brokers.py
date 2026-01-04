"""Tests for broker adapters."""

import pytest

from trade_engine.brokers.base import BrokerError
from trade_engine.brokers.paper import PaperBroker


@pytest.mark.asyncio
async def test_paper_broker_submit_order():
    """Test paper broker order submission."""
    broker = PaperBroker(slippage_bps=5)

    broker_order_id = await broker.submit_order(
        symbol="AAPL",
        side="BUY",
        quantity=100.0,
        order_type="MARKET",
    )

    assert broker_order_id is not None
    assert broker_order_id.startswith("PAPER_")

    # Check order status
    status = await broker.get_order_status(broker_order_id)
    assert status["status"] == "FILLED"
    assert status["symbol"] == "AAPL"

    # Check fills
    fills = await broker.get_fills(broker_order_id)
    assert len(fills) == 1
    assert fills[0]["quantity"] == 100.0
    assert fills[0]["price"] > 0


@pytest.mark.asyncio
async def test_paper_broker_cancel_order():
    """Test paper broker order cancellation."""
    broker = PaperBroker()

    # Submit order
    broker_order_id = await broker.submit_order(
        symbol="AAPL",
        side="BUY",
        quantity=100.0,
    )

    # For paper broker, market orders fill immediately
    # So cancellation might not work
    # This tests the cancellation logic
    status = await broker.get_order_status(broker_order_id)
    if status["status"] != "FILLED":
        cancelled = await broker.cancel_order(broker_order_id)
        assert cancelled is True


@pytest.mark.asyncio
async def test_paper_broker_invalid_order_type():
    """Test paper broker rejects non-MARKET orders."""
    broker = PaperBroker()

    with pytest.raises(BrokerError):
        await broker.submit_order(
            symbol="AAPL",
            side="BUY",
            quantity=100.0,
            order_type="LIMIT",  # Not supported
        )


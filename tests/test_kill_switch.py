"""Tests for kill switch functionality."""

import pytest

from trade_engine.api.kill_switch import KillSwitch


@pytest.mark.asyncio
async def test_kill_switch_activation():
    """Test kill switch activation and deactivation."""
    kill_switch = KillSwitch()  # No Redis for testing

    # Initially inactive
    assert await kill_switch.is_active() is False

    # Activate
    await kill_switch.activate("Test activation")
    assert await kill_switch.is_active() is True

    # Deactivate
    await kill_switch.deactivate("Test deactivation")
    assert await kill_switch.is_active() is False


@pytest.mark.asyncio
async def test_kill_switch_status():
    """Test kill switch status retrieval."""
    kill_switch = KillSwitch()

    status = await kill_switch.get_status()
    assert "active" in status
    assert status["active"] is False

    await kill_switch.activate("Test")
    status = await kill_switch.get_status()
    assert status["active"] is True


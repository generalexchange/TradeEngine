"""Rate limiting and throttling per strategy.

Prevents order spam and ensures fair resource allocation.
State is maintained in external storage (Redis).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from trade_engine.config.limits import RiskLimits


class ThrottleChecker:
    """Checks rate limits for strategy order submission.

    This class is stateless - all throttle state is in external storage.
    """

    def __init__(self, redis_client: Optional["Redis"] = None):
        """Initialize with Redis client for throttle state.

        Args:
            redis_client: Redis client for rate limit tracking
                          If None, uses in-memory fallback (not production-ready)
        """
        self.redis_client = redis_client
        self._memory_cache: dict[str, list[datetime]] = {}  # Fallback for testing

    async def _get_order_timestamps(
        self, strategy_id: str, window_minutes: int
    ) -> list[datetime]:
        """Get order timestamps for a strategy within a time window.

        Args:
            strategy_id: Strategy identifier
            window_minutes: Time window in minutes

        Returns:
            List of order timestamps
        """
        if self.redis_client:
            # Use Redis sorted set for efficient time-window queries
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
            cutoff_timestamp = cutoff.timestamp()

            # Get all orders in window (using sorted set)
            key = f"throttle:{strategy_id}:orders"
            timestamps = await self.redis_client.zrangebyscore(
                key, cutoff_timestamp, "+inf"
            )
            return [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in timestamps]
        else:
            # Fallback: in-memory cache (for testing only)
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
            if strategy_id not in self._memory_cache:
                return []
            return [
                ts
                for ts in self._memory_cache[strategy_id]
                if ts >= cutoff
            ]

    async def _record_order(self, strategy_id: str):
        """Record an order submission for rate limiting.

        Args:
            strategy_id: Strategy identifier
        """
        now = datetime.now(timezone.utc)

        if self.redis_client:
            # Add to Redis sorted set with timestamp as score
            key = f"throttle:{strategy_id}:orders"
            await self.redis_client.zadd(key, {str(now.timestamp()): now.timestamp()})
            # Expire old entries (keep last 24 hours)
            await self.redis_client.expire(key, 86400)
        else:
            # Fallback: in-memory cache
            if strategy_id not in self._memory_cache:
                self._memory_cache[strategy_id] = []
            self._memory_cache[strategy_id].append(now)

    async def check_rate_limit(
        self, strategy_id: str, limits: RiskLimits
    ) -> tuple[bool, Optional[str], bool]:
        """Check if strategy has exceeded rate limits.

        Returns:
            (is_valid, error_message, should_record)
            should_record: Whether to record this check (for idempotency)
        """
        # Check per-minute limit
        recent_orders = await self._get_order_timestamps(strategy_id, window_minutes=1)
        if len(recent_orders) >= limits.max_orders_per_strategy_per_minute:
            return (
                False,
                f"Rate limit exceeded: {len(recent_orders)} orders in last minute (max: {limits.max_orders_per_strategy_per_minute})",
                False,
            )

        # Check per-hour limit
        recent_orders = await self._get_order_timestamps(strategy_id, window_minutes=60)
        if len(recent_orders) >= limits.max_orders_per_strategy_per_hour:
            return (
                False,
                f"Rate limit exceeded: {len(recent_orders)} orders in last hour (max: {limits.max_orders_per_strategy_per_hour})",
                False,
            )

        # If passed, record this order (for future checks)
        await self._record_order(strategy_id)

        return True, None, True


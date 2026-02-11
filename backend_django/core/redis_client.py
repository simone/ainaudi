"""
Redis client singleton per email service e PDF caching.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_redis_client = None
_connection_tested = False


def get_redis_client():
    """
    Get Redis client singleton.

    Returns:
        Redis client instance or None if not available
    """
    global _redis_client, _connection_tested

    if _redis_client is not None:
        return _redis_client

    if _connection_tested:
        # Already tried and failed
        return None

    try:
        import redis

        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        _redis_client = redis.from_url(redis_url, decode_responses=True)

        # Test connection
        _redis_client.ping()

        logger.info(f"✅ Redis connected: {redis_url}")
        _connection_tested = True

        return _redis_client

    except ImportError:
        logger.warning("⚠️  Redis module not installed - install with: pip install redis")
        _connection_tested = True
        return None

    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e}")
        _connection_tested = True
        return None


def reset_redis_client():
    """Reset Redis client (useful for testing)."""
    global _redis_client, _connection_tested
    _redis_client = None
    _connection_tested = False

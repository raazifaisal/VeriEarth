"""
Redis caching service for VeriEarth backend.
Provides caching utilities with automatic JSON serialization and TTL management.
"""
import json
import hashlib
from typing import Optional, Any, Dict
import redis
from config import REDIS_URL
import logging

logger = logging.getLogger(__name__)

# Global Redis connection pool
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client connection."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            # Test connection
            _redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    return _redis_client


def make_cache_key(prefix: str, org_id: str, *args, **kwargs) -> str:
    """
    Generate a cache key from prefix, org_id, and optional parameters.
    
    Args:
        prefix: Cache key prefix (e.g., 'gds', 'dashboard', 'prefixspan')
        org_id: Organization ID
        *args: Positional arguments to include in hash
        **kwargs: Keyword arguments to include in hash
    
    Returns:
        Cache key string
    """
    parts = [prefix, org_id]
    if args:
        parts.append(str(args))
    if kwargs:
        # Sort kwargs for consistent hashing
        sorted_kwargs = sorted(kwargs.items())
        parts.append(str(sorted_kwargs))
    
    key_str = ":".join(parts)
    if len(key_str) > 200:
        # Hash long keys
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{prefix}:{org_id}:{key_hash}"
    return key_str.replace(' ', '').replace("'", "").replace('"', '')


def cache_get(key: str, default: Any = None) -> Optional[Any]:
    """Get value from cache, deserializing JSON if needed."""
    try:
        client = get_redis_client()
        value = client.get(key)
        if value is None:
            return default
        # Try to parse as JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    except Exception as e:
        logger.warning(f"Cache get failed for key {key}: {e}")
        return default


def cache_set(key: str, value: Any, ttl: int = 900) -> bool:
    """
    Set value in cache with TTL.
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time to live in seconds (default 15 minutes)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        # Serialize to JSON if it's a dict/list
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value)
        else:
            serialized = str(value)
        client.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.warning(f"Cache set failed for key {key}: {e}")
        return False


def cache_delete(key: str) -> bool:
    """Delete a single key from cache."""
    try:
        client = get_redis_client()
        client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete failed for key {key}: {e}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching a pattern.
    
    Args:
        pattern: Redis key pattern (e.g., 'gds:org_id:*')
    
    Returns:
        Number of keys deleted
    """
    try:
        client = get_redis_client()
        keys = list(client.scan_iter(match=pattern))
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache delete pattern failed for {pattern}: {e}")
        return 0


def invalidate_org_cache(org_id: str, prefixes: list[str]) -> int:
    """
    Invalidate all cache keys for an organization matching given prefixes.
    
    Args:
        org_id: Organization ID
        prefixes: List of cache key prefixes to invalidate (e.g., ['gds', 'dashboard', 'prefixspan'])
    
    Returns:
        Number of keys deleted
    """
    total = 0
    for prefix in prefixes:
        pattern = f"{prefix}:{org_id}:*"
        deleted = cache_delete_pattern(pattern)
        total += deleted
        if deleted > 0:
            logger.info(f"Invalidated {deleted} cache keys for pattern {pattern}")
    return total


def cache_decorator(prefix: str, ttl: int = 900, key_params: Optional[list] = None):
    """
    Decorator for caching function results.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_params: List of parameter names to include in cache key (if None, uses all kwargs)
    
    Example:
        @cache_decorator('gds', ttl=900, key_params=['limit'])
        def get_betweenness(org_id: str, limit: int = 15):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract org_id from args/kwargs (usually first arg or 'org_id' kwarg)
            org_id = None
            if args and len(args) > 0:
                org_id = args[0]
            elif 'org_id' in kwargs:
                org_id = kwargs['org_id']
            
            if not org_id:
                # No org_id, skip caching
                return func(*args, **kwargs)
            
            # Build cache key
            key_kwargs = {}
            if key_params:
                for param in key_params:
                    if param in kwargs:
                        key_kwargs[param] = kwargs[param]
            else:
                # Include all kwargs except org_id
                key_kwargs = {k: v for k, v in kwargs.items() if k != 'org_id'}
            
            cache_key = make_cache_key(prefix, org_id, **key_kwargs)
            
            # Try cache
            cached = cache_get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached
            
            # Cache miss, execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache_set(cache_key, result, ttl)
            logger.debug(f"Cache set: {cache_key}")
            
            return result
        return wrapper
    return decorator


"""Sliding-window-log rate limiting, backed by Redis.

Each rate-limited key (one per caller per limited action) is a Redis sorted
set: one member per request, scored by the millisecond timestamp it arrived.
On every call we drop members older than the window, count what's left, and
either admit the request (adding its own timestamp) or reject it — all in a
single Lua script, so the count-then-add is atomic and two concurrent
requests can't both slip through when only one slot is left.

Fails open: if Redis can't be reached, the request is allowed rather than
the endpoint going down. Matches this project's existing degradation
pattern for the cache backend (config/settings.py CACHES, IGNORE_EXCEPTIONS)
and Celery enqueueing (notifications.tasks) — a down Redis should degrade
abuse protection, not take the API with it.
"""

import functools
import logging
import math
import uuid

from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

# KEYS[1] = rate limit key
# ARGV[1] = window length in milliseconds
# ARGV[2] = limit (max requests allowed within the window)
# ARGV[3] = unique id for this request, used as the sorted set member so two
#           requests landing in the same millisecond don't collide and
#           silently undercount (their scores would tie, but members must
#           be distinct or ZADD just overwrites the same entry)
_SCRIPT_SRC = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local member = ARGV[3]

-- Redis's own clock, not the caller's: keeps the window correct even if
-- multiple app servers' local clocks have drifted relative to each other.
local time = redis.call('TIME')
local now = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, member)
    redis.call('PEXPIRE', key, window)
    return {1, 0}
end

local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local retry_after_ms = window - (now - tonumber(oldest[2]))
if retry_after_ms < 0 then
    retry_after_ms = 0
end
return {0, retry_after_ms}
"""

_script = None


def _get_script(client):
    global _script
    if _script is None:
        # register_script only computes the SHA locally and doesn't touch
        # the network — the real EVALSHA (with automatic fallback to a full
        # EVAL if Redis doesn't recognize the hash, e.g. after a restart)
        # happens on each call below.
        _script = client.register_script(_SCRIPT_SRC)
    return _script


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _identity(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return f"user:{user.id}"
    return f"ip:{_client_ip(request)}"


def _check(scope, request, limit, window_seconds):
    """Returns (allowed, retry_after_ms). Fails open on any Redis error."""
    try:
        client = get_redis_connection("default")
        script = _get_script(client)
        key = f"ratelimit:{scope}:{_identity(request)}"
        allowed, retry_after_ms = script(
            keys=[key],
            args=[window_seconds * 1000, limit, uuid.uuid4().hex],
            client=client,
        )
        return bool(allowed), retry_after_ms
    except Exception:
        logger.warning("rate_limit: Redis unavailable, failing open", exc_info=True)
        return True, 0


def rate_limit(limit, window=60, scope=None):
    """Decorator: allow at most `limit` requests per `window` seconds per
    caller (authenticated user id, else client IP).

    Works on both plain view functions (`request` is the first positional
    arg) and DRF viewset methods (`self` is first, `request` is second) —
    it tells them apart by duck-typing `.META`, which only a real
    request object has.
    """

    def decorator(view_func):
        limit_scope = scope or view_func.__qualname__

        @functools.wraps(view_func)
        def wrapped(*args, **kwargs):
            request = args[0] if hasattr(args[0], "META") else args[1]

            allowed, retry_after_ms = _check(limit_scope, request, limit, window)
            if not allowed:
                retry_after = max(1, math.ceil(retry_after_ms / 1000))
                return Response(
                    {"detail": "Request was throttled. Try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(retry_after)},
                )
            return view_func(*args, **kwargs)

        return wrapped

    return decorator

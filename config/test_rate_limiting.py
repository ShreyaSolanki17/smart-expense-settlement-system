import time
from unittest.mock import patch

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase, override_settings
from django_redis import get_redis_connection
from redis.exceptions import RedisError
from rest_framework.test import APITestCase

from config.rate_limiting import rate_limit
from groups.models import Group

# Isolated from the app's normal db 0 so these tests can freely flushdb()
# without touching dev data, same real-backend-over-mock approach
# groups/tests.py uses for cache invalidation — a real Redis is the only
# thing that actually exercises the Lua script.
TEST_CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/15",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "CONNECTION_POOL_KWARGS": {"socket_connect_timeout": 1, "socket_timeout": 1},
        },
    }
}


def _request_from(user):
    request = HttpRequest()
    request.META["REMOTE_ADDR"] = "127.0.0.1"
    request.user = user
    return request


def _skip_unless_redis_reachable(test_case):
    # These tests exercise the real Lua script against a real Redis, so
    # unlike the rest of the suite they can't run against sqlite alone.
    # Skip (not fail) when Redis isn't up, so `pytest` still works out of
    # the box per the README's "no Postgres/Redis required" local setup —
    # the CI workflow runs a redis service so they execute for real there.
    try:
        get_redis_connection("default").ping()
    except RedisError:
        test_case.skipTest("Redis not reachable on localhost:6379 - start it to run these tests")


@override_settings(CACHES=TEST_CACHES)
class RateLimitDecoratorTests(TestCase):
    """Unit-level tests against the decorator itself, with tiny windows so
    the reset case doesn't need a real 60s sleep. expenses/views.py's use
    of the real 20/min limit is covered separately below.
    """

    def setUp(self):
        _skip_unless_redis_reachable(self)
        get_redis_connection("default").flushdb()
        self.user = User.objects.create_user("alice", password="x")

    def test_requests_under_the_limit_succeed(self):
        @rate_limit(limit=3, window=60)
        def view(request):
            return "ok"

        request = _request_from(self.user)
        for _ in range(3):
            self.assertEqual(view(request), "ok")

    def test_requests_over_the_limit_are_rejected(self):
        @rate_limit(limit=3, window=60)
        def view(request):
            return "ok"

        request = _request_from(self.user)
        for _ in range(3):
            view(request)

        response = view(request)

        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)

    def test_limit_resets_after_the_window(self):
        @rate_limit(limit=1, window=1)
        def view(request):
            return "ok"

        request = _request_from(self.user)
        self.assertEqual(view(request), "ok")
        self.assertEqual(view(request).status_code, 429)

        time.sleep(1.1)

        self.assertEqual(view(request), "ok")

    def test_limit_is_tracked_per_caller(self):
        other = User.objects.create_user("bob", password="x")

        @rate_limit(limit=1, window=60)
        def view(request):
            return "ok"

        self.assertEqual(view(_request_from(self.user)), "ok")
        self.assertEqual(view(_request_from(self.user)).status_code, 429)
        # bob has never called this view — alice using up her limit doesn't
        # touch his.
        self.assertEqual(view(_request_from(other)), "ok")

    def test_fails_open_when_redis_is_unreachable(self):
        @rate_limit(limit=1, window=60)
        def view(request):
            return "ok"

        request = _request_from(self.user)
        self.assertEqual(view(request), "ok")  # uses up the only allowed slot

        with patch("config.rate_limiting.get_redis_connection", side_effect=ConnectionError("down")):
            # would be a 429 if Redis were reachable; instead falls open
            self.assertEqual(view(request), "ok")


class ExpenseCreateRateLimitTests(APITestCase):
    """Confirms the decorator is actually wired onto the real endpoint —
    the decorator's own behavior is covered above.
    """

    @override_settings(CACHES=TEST_CACHES)
    def test_expense_creation_is_rate_limited_at_twenty_per_minute(self):
        _skip_unless_redis_reachable(self)
        get_redis_connection("default").flushdb()
        user = User.objects.create_user("alice", password="x")
        group = Group.objects.create(name="trip")
        group.members.add(user)
        self.client.force_authenticate(user)

        def create(i):
            return self.client.post(
                "/api/expenses/",
                {"group": group.id, "description": f"item{i}", "amount": "1.00", "paid_by": user.id},
            )

        for i in range(20):
            response = create(i)
            self.assertEqual(response.status_code, 201, f"request {i} should be within the 20/min limit")

        response = create(20)

        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)

"""
Django settings for config project.
"""

from pathlib import Path

import environ
from kombu import Exchange, Queue

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-key-change-me")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "graphene_django",
    "groups",
    "expenses",
    "settlements",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "config.middleware.TokenAuthMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

GRAPHENE = {
    "SCHEMA": "config.schema.schema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Smart Expense Settlement System API",
    "DESCRIPTION": "Splitwise-style expense splitting and settlement API.",
    "VERSION": "1.0.0",
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
# Any localhost/127.0.0.1 port: Vite bumps ports when one's taken, and no
# remote origin can spoof a browser into sending Origin: http://localhost:*.
CORS_ALLOWED_ORIGIN_REGEXES = [r"^http://(localhost|127\.0\.0\.1):\d+$"]

# Redis: cache only now (see RABBITMQ_URL below for the task queue).
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

# RabbitMQ: Celery's broker. Split from Redis so task delivery gets AMQP's
# guarantees (durable queues, per-message ack, dead-lettering) instead of
# Redis's at-most-once list-based queue.
RABBITMQ_URL = env("RABBITMQ_URL", default="amqp://guest:guest@localhost:5672//")

CELERY_BROKER_URL = RABBITMQ_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
# ponytail: fail fast (no retry backoff, short connect timeout) when
# *publishing* a task — notify_members is fire-and-forget, so a hung
# retry/timeout loop in the request/response cycle is pure waste.
# broker_connection_retry stays True (the default) since it also gates the
# worker's own startup retry — disabling it made the worker give up and
# exit instead of waiting for RabbitMQ to come up.
CELERY_TASK_PUBLISH_RETRY = False
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_TIMEOUT = 1
# read_timeout/write_timeout are pyamqp's equivalent of the old Redis
# transport's socket_timeout — the Redis-specific socket_connect_timeout/
# socket_timeout keys are silently ignored by the amqp transport, so they'd
# have quietly stopped doing anything if left in place.
CELERY_BROKER_TRANSPORT_OPTIONS = {"read_timeout": 1, "write_timeout": 1}

# notify_members is the only task today, but giving it an explicit
# exchange/queue (instead of Celery's implicit default "celery" queue)
# gives us a named place to hang per-queue behavior — ack semantics and,
# below, a dead-letter queue.
#
# Direct exchange: a message's routing key must match a bound queue's
# binding key *exactly* for that queue to get it — simple point-to-point
# delivery. That's the right fit: one task type, one intended consumer
# queue. It would be different if this fanned out to independent consumers
# each wanting their own full copy of the same event (e.g. a separate
# email service and a separate push service both reacting to "member
# notified") — that's what a fanout exchange is for, broadcasting to every
# bound queue regardless of routing key. Or if we had a family of related
# routing keys consumers subscribe to slices of via wildcards — that's a
# topic exchange. Neither applies: notify_members has exactly one task
# type and one consumer (the worker pool), so direct is the simplest thing
# that's still correct.
notifications_exchange = Exchange("notifications", type="direct")

CELERY_TASK_QUEUES = (
    Queue(
        "notifications",
        exchange=notifications_exchange,
        routing_key="notification.notify_members",
    ),
)
CELERY_TASK_ROUTES = {
    "notifications.tasks.notify_members": {
        "queue": "notifications",
        "routing_key": "notification.notify_members",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # ponytail: Redis may not be running in dev/CI; degrade to a
            # no-op cache instead of 500ing (or hanging) every request that
            # touches it.
            "IGNORE_EXCEPTIONS": True,
            "CONNECTION_POOL_KWARGS": {"socket_connect_timeout": 1, "socket_timeout": 1},
        },
    }
}

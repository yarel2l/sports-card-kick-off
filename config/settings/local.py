"""
Local settings
"""

import os
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# ✅ NUEVO: Middleware para detectar N+1 queries (solo en desarrollo local)
MIDDLEWARE += [
    "config.middleware.query_optimization.QueryOptimizationMiddleware",
]

# ✅ HABILITAR: Logging de queries para el middleware de optimización
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "config.middleware.query_optimization": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


# Allow all host headers. UPDATE in production
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",")]
)

# Password validation is enabled by default from base.py
# Do not disable AUTH_PASSWORD_VALIDATORS in development to ensure proper testing

INTERNAL_IPS = ["127.0.0.1"]

CELERYD_FORCE_EXECV = True

GRAPH_MODELS = {"all_applications": True, "group_models": True}

# CORS configuration for local development
CORS_ALLOW_ALL_ORIGINS = True  # Enable all origins for development
CORS_ALLOW_CREDENTIALS = True

# Additional CORS headers for React development
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-tenant-schema',
    'cache-control',
    'pragma',
]

# Development email configuration - Console backend for local testing
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Optional: Use SES in development (uncomment to test with real emails)
# EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"
# ANYMAIL = {
#     "AMAZON_SES_SESSION_PARAMS": {
#         "aws_access_key_id": config("AWS_SES_ACCESS_KEY_ID", default=None),
#         "aws_secret_access_key": config("AWS_SES_SECRET_ACCESS_KEY", default=None),
#         "region_name": config("AWS_SES_REGION", default="us-east-1"),
#     },
#     "AMAZON_SES_AUTO_CONFIRM_SNS_SUBSCRIPTIONS": True,
# }

# Default FROM email for development
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@sportscardkickoff.com")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Legacy SendGrid configuration (commented out)
# EMAIL_BACKEND = "anymail.backends.sendgrid.EmailBackend"
# ANYMAIL = {
#     "SENDGRID_API_KEY": config("ANYMAIL_SENDGRID_API_KEY", default=None),
#     "SENDGRID_MERGE_FIELD_FORMAT": "-{}-",
#     "WEBHOOK_SECRET": None
# }


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB"),
        "USER": config("POSTGRES_USER"),
        "PASSWORD": config("POSTGRES_PASSWORD"),
        "HOST": config("POSTGRES_HOST"),
        "PORT": config("POSTGRES_PORT"),
        # ✅ Reduced CONN_MAX_AGE to prevent connection pool exhaustion
        # Setting to 0 (None) closes connections after each request
        # This is crucial for django-tenants which switches schemas frequently
        "CONN_MAX_AGE": 0,  # Close connections after each request
        "OPTIONS": {
            "connect_timeout": 10,  # 10 segundos de timeout de conexión
            "options": "-c statement_timeout=30000",  # 30 segundos de timeout para comandos
        },
        # ✅ Disable persistent connections for django-tenants
        "DISABLE_SERVER_SIDE_CURSORS": True,
        # Test database configuration
        "TEST": {
            "NAME": "test_sportcards_db",
        },
    },
}

PGCRYPTO_KEY = config("PGCRYPTO_KEY")



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media/")

FILE_UPLOAD_PERMISSIONS = 0o644
DATA_UPLOAD_MAX_MEMORY_SIZE = 200 * 1024 * 1024  # 200 MB


CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://10.0.0.3:8000",
]


# import sentry_sdk

# # from sentry_sdk.integrations.django import DjangoIntegration

# sentry_sdk.init(
#     dsn="https://e9197d4a1f2135ce6671d9854fc4395c@o1353781.ingest.us.sentry.io/4508645704204288",
#     enable_tracing=True,
#     # integrations=[DjangoIntegration()],
#     # Set traces_sample_rate to 1.0 to capture 100%
#     # of transactions for performance monitoring.
#     # We recommend adjusting this value in production,
#     traces_sample_rate=1.0,
#     # If you wish to associate users to errors (assuming you are using
#     # django.contrib.auth) you may enable sending PII data.
#     send_default_pii=True,
#     # By default the SDK will try to use the SENTRY_RELEASE
#     # environment variable, or infer a git commit
#     # SHA as release, however you may want to set
#     # something more human-readable.
#     # release="myapp@1.0.0",
#     _experiments={
#         # Set continuous_profiling_auto_start to True
#         # to automatically start the profiler on when
#         # possible.
#         "continuous_profiling_auto_start": True,
#     },
# )

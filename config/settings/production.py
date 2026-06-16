"""
Production settings
"""

from decouple import config

# from sentry_sdk.integrations.django import DjangoIntegration

from .base import *

DEBUG = False

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default=".sportscardkickoff.com",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# Never allow all origins in production. Provide the trusted frontend domains
# via the CORS_ALLOWED_ORIGINS environment variable (comma separated).
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="https://sportscardkickoff.com,https://www.sportscardkickoff.com",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)
CSRF_TRUSTED_ORIGINS = ["https://*.sportscardkickoff.com"]

# Cookie/SSL security. TLS terminates at the ALB and SECURE_PROXY_SSL_HEADER
# (set above) lets Django detect HTTPS, so cookies must be marked secure.
# SECURE_SSL_REDIRECT stays opt-in to avoid redirect loops behind the proxy.
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# SECURE_HSTS_SECONDS = 15552000 # 6 months
# SECURE_HSTS_SECONDS = 31536000 # 1 year
# SECURE_HSTS_INCLUDE_SUBDOMAINS = False
# SECURE_HSTS_PRELOAD = False


# Amazon SES Email Configuration
# EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"
# ANYMAIL = {
#     # AWS credentials (using existing system credentials or specific SES credentials)
#     "AMAZON_SES_SESSION_PARAMS": {
#         "aws_access_key_id": config("AWS_SES_ACCESS_KEY_ID", default=config("AWS_ACCESS_KEY_ID", default=None)),
#         "aws_secret_access_key": config("AWS_SES_SECRET_ACCESS_KEY", default=config("AWS_SECRET_ACCESS_KEY", default=None)),
#         "region_name": config("AWS_SES_REGION", default="us-east-1"),
#     },
#     # SES Configuration Set for tracking and monitoring
#     "AMAZON_SES_CONFIGURATION_SET_NAME": config("SES_CONFIGURATION_SET", default="emergencyiq-dev"),
#     # Optional: SES-specific settings
#     "AMAZON_SES_AUTO_CONFIRM_SNS_SUBSCRIPTIONS": True,
#     "WEBHOOK_SECRET": config("ANYMAIL_WEBHOOK_SECRET", default=None),
# }

# SendGrid Email Configuration
EMAIL_BACKEND = "anymail.backends.sendgrid.EmailBackend"
ANYMAIL = {
    "SENDGRID_API_KEY": config("SENDGRID_API_KEY", default=""),
    "SENDGRID_MERGE_FIELD_FORMAT": "-{}-",
    "WEBHOOK_SECRET": config("SENDGRID_WEBHOOK_SECRET", default=None),
}

# Default FROM email (must be verified in SendGrid)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@sportscardkickoff.com")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Static file finders (django-tenants is not used by this project, so the
# standard Django finders are sufficient).
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]


# AWS S3 Config
# Django Storages settings for separate static and media buckets
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-1")

# Static files bucket
AWS_STORAGE_BUCKET_NAME_STATIC = config("AWS_STORAGE_BUCKET_NAME_STATIC", default="")
AWS_S3_CUSTOM_DOMAIN_STATIC = f"{AWS_STORAGE_BUCKET_NAME_STATIC}.s3.amazonaws.com"

# Media files bucket
AWS_STORAGE_BUCKET_NAME_MEDIA = config("AWS_STORAGE_BUCKET_NAME_MEDIA", default="")
AWS_S3_CUSTOM_DOMAIN_MEDIA = f"{AWS_STORAGE_BUCKET_NAME_MEDIA}.s3.amazonaws.com"

# S3 Object parameters
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

AWS_HEADERS = {
    "Access-Control-Allow-Origin": "*",  # Allow all origins
}

# Static files configuration
AWS_STATIC_LOCATION = "static"
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN_STATIC}/{AWS_STATIC_LOCATION}/"

# Media files configuration
AWS_MEDIA_LOCATION = "media"
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN_MEDIA}/{AWS_MEDIA_LOCATION}/"

# Django 4.2+ Storage backends configuration
# https://docs.djangoproject.com/en/5.0/ref/settings/#storages
STORAGES = {
    "default": {
        "BACKEND": "config.integrations.aws_services.storage_backends.PrivateMediaStorage",
    },
    "staticfiles": {
        "BACKEND": "config.integrations.aws_services.storage_backends.StaticStorage",
    },
}

# Configuring media file storage
# DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
# DEFAULT_FILE_STORAGE = "django_tenants.files.storage.TenantFileSystemStorage"
FILE_UPLOAD_PERMISSIONS = 0o644
DATA_UPLOAD_MAX_MEMORY_SIZE = 200 * 1024 * 1024  # 200 MB


# Databases
PGCRYPTO_KEY = config("PGCRYPTO_KEY", default="")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="sportcards_db"),
        "USER": config("POSTGRES_USER", default="postgres"),
        "PASSWORD": config("POSTGRES_PASSWORD", default=""),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    },
}

# import sentry_sdk

# # from sentry_sdk.integrations.django import DjangoIntegration

# sentry_sdk.init(
#     dsn="https://4d5eece4538beabe4da263843a94b0b9@o1353781.ingest.us.sentry.io/4508645558583296",
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


from celery.schedules import crontab
from datetime import timedelta
from decouple import config
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# __file__ is config/settings/base.py, so parent.parent.parent = project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-default-key-change-in-production')

# Application-level field encryption (apps.core.fields.EncryptedCharField).
# Provide one or more comma-separated urlsafe-base64 Fernet keys via
# FIELD_ENCRYPTION_KEY (first encrypts, all are tried on decrypt for rotation).
# If unset, a key is derived from SECRET_KEY — fine for dev, NOT for production.
FIELD_ENCRYPTION_KEYS = config(
    'FIELD_ENCRYPTION_KEY',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)

# SECURITY WARNING: don't run with debug turned on in production!
# Driven by environment so production defaults to a safe value. Each
# environment-specific settings module may override this explicitly.
DEBUG = config('DEBUG', default=False, cast=bool)


# Application definition
INSTALLED_APPS = [
    'channels',
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',

    'drf_spectacular',
    'drf_spectacular_sidecar',

    'django_celery_beat',
    'django_celery_results',
    'storages',
    'anymail',
    'solo',  # django-solo for singleton models

    # Local apps
    'apps.core',  # Core configuration (must be first)
    'apps.accounts',
    'apps.scraping',
    'apps.search',
    'apps.catalog',
    'apps.portfolio',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
# Closed by default. Development settings may open this up; production should
# set CORS_ALLOWED_ORIGINS explicitly to the trusted frontend domains.
CORS_ALLOW_ALL_ORIGINS = False

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'config.asgi.application'
WSGI_APPLICATION = 'config.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/
def gettext(s): return s

LANGUAGE_CODE = "en"

LOCALE_PATHS = [BASE_DIR /"locale"]

LANGUAGES = (
    ("en", "English"), 
    ("es", "Español")
)

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

DEFAULT_CHARSET = 'utf-8'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REDIS_HOST = config("REDIS_HOST", "127.0.0.1")
REDIS_PORT = config("REDIS_PORT", 6379)
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

# Caches configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PARSER_CLASS": "redis.connection._HiredisParser",
        },
    },
    'celery': {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    },
    'local': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "mail_admins": {"level": "ERROR", "class": "django.utils.log.AdminEmailHandler", "formatter": "verbose"},
        "console": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "verbose"},
        "logfile": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": BASE_DIR / 'logs/system.log',
            "when": "midnight",
            "interval": 1,
            "backupCount": 100,
            "formatter": "verbose",
        },
    },
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        }
    },
    "loggers": {
        "": {"handlers": ["console", "logfile"],
             "level": "INFO",
             "propagate": True},
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [(REDIS_HOST, REDIS_PORT)], "expiry": 60, "capacity": 10000, "serializer_format": "json",},
    }
}

# Celery configuration
# With redis
# CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/3"
# With django-celery-results
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'celery'
CELERY_RESULT_EXTENDED = True
CELERY_BROKER_URL = config("CELERY_BROKER_URL", REDIS_URL) # Use rabbitmq broker
CELERY_BROKER_CONNECTION_TIMEOUT = 30  # En segundos
CELERY_BROKER_HEARTBEAT = 10  # Heartbeat interval
CELERY_BROKER_CONNECTION_MAX_RETRIES = None  # Número ilimitado de reintentos
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZE = "json"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_QUEUES = {
    # 'devices_queue': {
    #     'exchange': 'devices_exchange',
    #     'exchange_type': 'direct',
    #     'binding_key': 'devices_queue',
    # },
    # 'notifications_queue': {
    #     'exchange': 'notifications_exchange',
    #     'exchange_type': 'direct',
    #     'binding_key': 'notifications_queue',
    # }
}

# Configuración específica de django-celery-beat
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    # Weekly portfolio digest: Mondays at 08:00 UTC.
    'send_portfolio_digests': {
        'task': 'apps.portfolio.tasks.send_portfolio_digests',
        'schedule': crontab(minute=0, hour=8, day_of_week=1),
    },
}

# JWT Configuration
# Use RS256 (RSA keys) in production, HS256 (symmetric key) in testing/dev without keys
_private_key = config('PRIVATE_KEY', default=None)
_public_key = config('PUBLIC_KEY', default=None)

if _private_key and _public_key:
    # Production: Use RSA keys
    JWT_ALGORITHM = "RS256"
    JWT_SIGNING_KEY = _private_key.replace('\\n', '\n')
    JWT_VERIFYING_KEY = _public_key.replace('\\n', '\n')
else:
    # Development/Testing: Use symmetric key
    JWT_ALGORITHM = "HS256"
    JWT_SIGNING_KEY = SECRET_KEY
    JWT_VERIFYING_KEY = None

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,

    "ALGORITHM": JWT_ALGORITHM,
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "VERIFYING_KEY": JWT_VERIFYING_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "account_id",
    "USER_ID_CLAIM": "account_id",
    "ISSUER": "Sports Card Kickoff",
    
    # "TOKEN_OBTAIN_SERIALIZER": "users.serializers.MyTokenObtainPairSerializer",
}

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'drf_standardized_errors.handler.exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_standardized_errors.openapi.AutoSchema',
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.SearchFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    # Rate limiting. Sensitive auth endpoints use scoped throttles (applied per
    # view); these are the production defaults. Development/test settings relax
    # them so the suite is not affected.
    'DEFAULT_THROTTLE_RATES': {
        'auth_login': '10/min',
        'auth_register': '5/hour',
        'auth_password_reset': '5/hour',
    },
}

# ==================================#
# API DOCUMENTATION DRF-SPECTACULAR #
# ==================================#
SPECTACULAR_SETTINGS = {
    "TITLE": "Sports Card Kickoff API",
    "DESCRIPTION": """
# Sports Card Kickoff API Documentation

Welcome to the Sports Card Kickoff API. This RESTful API provides comprehensive access to sports card data,
authentication, and scraping services.

## Features

- **Authentication & User Management**: JWT-based authentication with secure token management
- **Sports Card Scraping**: Automated scraping from major sports card marketplaces
- **Search & Discovery**: Advanced search capabilities across multiple platforms
- **AI-Powered Extraction**: LLM-based data extraction for accurate card information

## Authentication

All authenticated endpoints require a JWT Bearer token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

### Obtaining Tokens

1. Register a new account: `POST /api/v1/auth/register/`
2. Login with credentials: `POST /api/v1/auth/login/`
3. Receive access token (valid 1 day) and refresh token (valid 7 days)
4. Use access token for authenticated requests
5. Refresh tokens when expired: `POST /api/v1/auth/token/refresh/`

## Rate Limiting

API requests are rate-limited to ensure service quality:
- Authenticated users: 1000 requests/hour
- Anonymous users: 100 requests/hour

## Response Format

All API responses follow a consistent format with proper HTTP status codes.

## Support

For questions or issues, contact support@sportscardkickoff.com
    """,
    "VERSION": "1.0.0",
    "CONTACT": {
        "name": "Sports Card Kickoff Support",
        "email": "support@sportscardkickoff.com",
        "url": "https://sportscardkickoff.com/",
    },
    "LICENSE": {
        "name": "Proprietary",
    },
    "SERVE_PUBLIC": True,
    "SERVE_INCLUDE_SCHEMA": False,
    "CAMELIZE_NAMES": False,
    "COMPONENT_SPLIT_PATCH": True,
    "COMPONENT_SPLIT_REQUEST": True,
    "AUTHENTICATION_WHITELIST": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "SECURITY": [
        {
            "bearerAuth": []
        }
    ],
    "COMPONENTS": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Bearer token authentication. Obtain tokens via login endpoint."
            }
        }
    },
    "TAGS": [
        {
            "name": "Authentication",
            "description": "User registration, login, logout, and token management endpoints"
        },
        {
            "name": "Password Management",
            "description": "Password reset, change, and recovery endpoints"
        },
        {
            "name": "User Profile",
            "description": "User profile retrieval and update endpoints"
        },
        {
            "name": "System Configuration",
            "description": "System settings and configuration management endpoints (admin only)"
        },
        {
            "name": "Search",
            "description": "Sports card search operations with AI-powered query parsing and multi-site scraping"
        },
    ],
    "ENUM_NAME_OVERRIDES": {
        "ValidationErrorEnum": "drf_standardized_errors.openapi_serializers.ValidationErrorEnum.choices",
        "ClientErrorEnum": "drf_standardized_errors.openapi_serializers.ClientErrorEnum.choices",
        "ServerErrorEnum": "drf_standardized_errors.openapi_serializers.ServerErrorEnum.choices",
        "ErrorCode401Enum": "drf_standardized_errors.openapi_serializers.ErrorCode401Enum.choices",
        "ErrorCode403Enum": "drf_standardized_errors.openapi_serializers.ErrorCode403Enum.choices",
        "ErrorCode404Enum": "drf_standardized_errors.openapi_serializers.ErrorCode404Enum.choices",
        "ErrorCode405Enum": "drf_standardized_errors.openapi_serializers.ErrorCode405Enum.choices",
        "ErrorCode406Enum": "drf_standardized_errors.openapi_serializers.ErrorCode406Enum.choices",
        "ErrorCode415Enum": "drf_standardized_errors.openapi_serializers.ErrorCode415Enum.choices",
        "ErrorCode429Enum": "drf_standardized_errors.openapi_serializers.ErrorCode429Enum.choices",
        "ErrorCode500Enum": "drf_standardized_errors.openapi_serializers.ErrorCode500Enum.choices",
        # Fix enum naming collisions from drf-standardized-errors
        # These are auto-generated collisions that can be safely ignored
    },
    "ENUM_GENERATE_CHOICE_DESCRIPTION": True,
    "DISABLE_ERRORS_AND_WARNINGS": True,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
    'SWAGGER_UI_SETTINGS': {
        'supportedSubmitMethods': ['get', 'post', 'put', 'patch', 'delete'],
        'persistAuthorization': True,
        'deepLinking': True,
        'displayOperationId': False,
        'defaultModelsExpandDepth': 1,
        'defaultModelExpandDepth': 1,
        'defaultModelRendering': 'example',
        'displayRequestDuration': True,
        'docExpansion': 'none',
        'filter': True,
        'operationsSorter': 'alpha',
        'showExtensions': True,
        'tagsSorter': 'alpha',
        'tryItOutEnabled': True,
    },
}

# ============================================================================
# LLM / AI Configuration
# ============================================================================

# API keys are managed dynamically through SystemConfiguration model (apps.core).
# Scraping agents load configuration from database at runtime.
# This allows changing API keys through Django admin without server restart.
#
# No API keys are stored in settings.py or environment variables.
# All configuration is centralized in the database.
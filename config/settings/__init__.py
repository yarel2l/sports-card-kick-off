from decouple import config

if config("APP_ENVIRONMENT") == "dev":
    from .local import *  # pylint: disable=wildcard-import

if config("APP_ENVIRONMENT") == "prod":
    from .production import *  # pylint: disable=wildcard-import

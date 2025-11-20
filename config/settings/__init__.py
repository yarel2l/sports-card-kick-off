from decouple import config

# Default to local settings if APP_ENVIRONMENT is not set
app_env = config("APP_ENVIRONMENT", default="dev")

if app_env == "dev":
    from .local import *  # pylint: disable=wildcard-import
elif app_env == "prod":
    from .production import *  # pylint: disable=wildcard-import

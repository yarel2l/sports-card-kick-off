import os

from django.core.asgi import get_asgi_application

# Configurar Django ANTES de importar cualquier cosa que dependa de él
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Inicializar Django
django_asgi_app = get_asgi_application()

# Importar después de inicializar Django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from config.channels.routing import websocket_urlpatterns
from config.channels.auth import JWTAuthMiddlewareStack


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            )
        ),
    }
)
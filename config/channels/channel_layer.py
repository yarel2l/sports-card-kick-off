"""
Solución para problemas específicos de channels_redis
Maneja el error "Incoming message has no 'type' attribute"
"""

import logging
from typing import Dict, Any, Optional
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class ChannelLayerFix:
    """
    Clase para manejar problemas específicos de channels_redis
    """
    
    @staticmethod
    def safe_group_add(group_name: str, channel_name: str) -> bool:
        """
        Agregar canal a grupo de forma segura (versión sync)
        """
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_add)(group_name, channel_name)
            return True
        except ValueError as e:
            if "Incoming message has no 'type' attribute" in str(e):
                logger.debug(f"Channel layer fix: Saltando mensaje interno para group_add")
                return True
            else:
                logger.error(f"Error en group_add: {e}")
                return False
        except Exception as e:
            logger.error(f"Error inesperado en group_add: {e}")
            return False
    
    @staticmethod
    async def async_safe_group_add(group_name: str, channel_name: str) -> bool:
        """
        Agregar canal a grupo de forma segura (versión async)
        """
        try:
            channel_layer = get_channel_layer()
            await channel_layer.group_add(group_name, channel_name)
            return True
        except ValueError as e:
            if "Incoming message has no 'type' attribute" in str(e):
                logger.debug(f"Channel layer fix: Saltando mensaje interno para async_group_add")
                return True
            else:
                logger.error(f"Error en async_group_add: {e}")
                return False
        except Exception as e:
            logger.error(f"Error inesperado en async_group_add: {e}")
            return False
    
    @staticmethod
    def safe_group_discard(group_name: str, channel_name: str) -> bool:
        """
        Remover canal de grupo de forma segura (versión sync)
        """
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_discard)(group_name, channel_name)
            return True
        except ValueError as e:
            if "Incoming message has no 'type' attribute" in str(e):
                logger.debug(f"Channel layer fix: Saltando mensaje interno para group_discard")
                return True
            else:
                logger.error(f"Error en group_discard: {e}")
                return False
        except Exception as e:
            logger.error(f"Error inesperado en group_discard: {e}")
            return False
    
    @staticmethod
    async def async_safe_group_discard(group_name: str, channel_name: str) -> bool:
        """
        Remover canal de grupo de forma segura (versión async)
        """
        try:
            channel_layer = get_channel_layer()
            await channel_layer.group_discard(group_name, channel_name)
            return True
        except ValueError as e:
            if "Incoming message has no 'type' attribute" in str(e):
                logger.debug(f"Channel layer fix: Saltando mensaje interno para async_group_discard")
                return True
            else:
                logger.error(f"Error en async_group_discard: {e}")
                return False
        except Exception as e:
            logger.error(f"Error inesperado en async_group_discard: {e}")
            return False
    
    @staticmethod
    def safe_group_send(group_name: str, message: Dict[str, Any]) -> bool:
        """
        Enviar mensaje a grupo de forma segura (versión sync)
        """
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(group_name, message)
            return True
        except ValueError as e:
            if "Incoming message has no 'type' attribute" in str(e):
                logger.debug(f"Channel layer fix: Saltando mensaje interno para group_send")
                return True
            else:
                logger.error(f"Error en group_send: {e}")
                return False
        except Exception as e:
            logger.error(f"Error inesperado en group_send: {e}")
            return False
    
    @staticmethod
    async def async_safe_group_send(group_name: str, message: Dict[str, Any]) -> bool:
        """
        Enviar mensaje a grupo de forma segura (versión async)
        """
        try:
            channel_layer = get_channel_layer()
            await channel_layer.group_send(group_name, message)
            return True
        except ValueError as e:
            if "Incoming message has no 'type' attribute" in str(e):
                logger.debug(f"Channel layer fix: Saltando mensaje interno para async_group_send")
                return True
            else:
                logger.error(f"Error en async_group_send: {e}")
                return False
        except Exception as e:
            logger.error(f"Error inesperado en async_group_send: {e}")
            return False
    
    @staticmethod
    def safe_send(channel_name: str, message: Dict[str, Any]) -> bool:
        """
        Enviar mensaje a canal específico de forma segura (versión sync)
        """
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.send)(channel_name, message)
            return True
        except ValueError as e:
            if "Incoming message has no 'type' attribute" in str(e):
                logger.debug(f"Channel layer fix: Saltando mensaje interno para send")
                return True
            else:
                logger.error(f"Error en send: {e}")
                return False
        except Exception as e:
            logger.error(f"Error inesperado en send: {e}")
            return False
    
    @staticmethod
    async def async_safe_send(channel_name: str, message: Dict[str, Any]) -> bool:
        """
        Enviar mensaje a canal específico de forma segura (versión async)
        """
        try:
            channel_layer = get_channel_layer()
            await channel_layer.send(channel_name, message)
            return True
        except ValueError as e:
            if "Incoming message has no 'type' attribute" in str(e):
                logger.debug(f"Channel layer fix: Saltando mensaje interno para async_send")
                return True
            else:
                logger.error(f"Error en async_send: {e}")
                return False
        except Exception as e:
            logger.error(f"Error inesperado en async_send: {e}")
            return False


# Instancia global para usar en otros módulos
channel_layer_fix = ChannelLayerFix()

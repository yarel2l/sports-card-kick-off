from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging
from typing import List, Dict, Any, Union
from django.utils import timezone


logger = logging.getLogger(__name__)


def add_channels_to_group(group_name: str, channel_names: List[str]) -> None:
    """
    Suscribe uno o varios canales al grupo especificado.
    
    Args:
        group_name: Nombre del grupo
        channel_names: Lista de nombres de canales
    """
    from .channel_layer import channel_layer_fix
    for channel_name in channel_names:
        logger.info(f"Subscribing channel: {channel_name} to group: {group_name}")
        channel_layer_fix.safe_group_add(group_name, channel_name)


def remove_channels_from_group(group_name: str, channel_names: List[str]) -> None:
    """
    Elimina uno o varios canales del grupo especificado.
    
    Args:
        group_name: Nombre del grupo
        channel_names: Lista de nombres de canales
    """
    from .channel_layer import channel_layer_fix
    for channel_name in channel_names:
        logger.info(f"Unsubscribing channel: {channel_name} from group: {group_name}")
        channel_layer_fix.safe_group_discard(group_name, channel_name)


def send_to_group(group_name: str, message: Dict[str, Any]) -> None:
    """
    Envía un mensaje a un grupo.
    
    Args:
        group_name: Nombre del grupo
        message: Mensaje a enviar
    """
    from .channel_layer import channel_layer_fix
    logger.info(f"Sending message to group: {group_name}")
    channel_layer_fix.safe_group_send(group_name, message)


def send_to_channels(channel_names: List[str], message: Dict[str, Any]) -> None:
    """
    Envía un mensaje a uno o varios canales individuales.
    
    Args:
        channel_names: Lista de nombres de canales
        message: Mensaje a enviar
    """
    from .channel_layer import channel_layer_fix
    for channel_name in channel_names:
        logger.info(f"Sending message to channel: {channel_name}")
        channel_layer_fix.safe_send(channel_name, message)
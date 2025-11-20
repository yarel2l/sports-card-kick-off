import boto3
from django.conf import settings


def get_permanent_s3_url(file_name):
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    media_location = getattr(settings, "AWS_PRIVATE_MEDIA_LOCATION", "media")
    permanent_url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME_MEDIA,
            "Key": f"{media_location}/{file_name}",
        },
        ExpiresIn=60
        * 60
        * 24
        * 365
        * 10,  # 🔥 URL válida por 10 años (ajústalo según necesites)
    )
    return permanent_url


def get_private_media_url(file_name):
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    media_location = getattr(settings, "AWS_PRIVATE_MEDIA_LOCATION", "media")
    presigned_url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME_MEDIA,
            "Key": f"{media_location}/{file_name}",
        },
        ExpiresIn=86400,  # 86400
    )
    return presigned_url


def safe_get_private_media_url(file_name, is_permanent=False):
    """
    Intenta acceder a una URL firmada y la renueva si es necesario.
    """
    try:
        url = (
            get_private_media_url(file_name)
            if not is_permanent
            else get_permanent_s3_url(file_name)
        )
        return url
    except Exception as e:
        # Log el error si es necesario
        print(f"Error al generar la URL prefirmada: {str(e)}")
        # Regenerar la URL
        return (
            get_private_media_url(file_name)
            if not is_permanent
            else get_permanent_s3_url(file_name)
        )

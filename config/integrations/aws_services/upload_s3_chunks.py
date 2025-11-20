import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from django.conf import settings


def upload_file_to_s3_in_chunks(file_obj, key, chunk_size=5 * 1024 * 1024):
    """
    Sube un archivo a S3 utilizando la subida multipart.
    :param file_obj: Archivo a subir (archivo abierto en modo binario)
    :param bucket_name: Nombre del bucket S3
    :param key: Key o nombre del archivo en el bucket
    :param chunk_size: Tamaño de cada chunk en bytes (5 MB por defecto)
    """
    s3_client = boto3.client("s3")
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME_MEDIA

    try:
        # Inicia una subida multipart
        response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=key)
        upload_id = response["UploadId"]

        parts = []
        part_number = 1

        while chunk := file_obj.read(chunk_size):
            # Sube cada chunk como una parte
            part = s3_client.upload_part(
                Bucket=bucket_name,
                Key=key,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=chunk,
            )
            parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
            part_number += 1

        # Finaliza la subida multipart
        s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )

        return f"File uploaded successfully: s3://{bucket_name}/{key}"

    except (NoCredentialsError, PartialCredentialsError) as e:
        return f"Credentials error: {str(e)}"

    except Exception as e:
        # Manejar cualquier error interrumpido finalizando la subida
        if "upload_id" in locals():
            s3_client.abort_multipart_upload(
                Bucket=bucket_name, Key=key, UploadId=upload_id
            )
        raise e

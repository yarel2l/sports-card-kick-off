import os
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """
    Storage backend for static files on S3.
    Used by collectstatic to upload static files directly to S3 bucket.
    """
    bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME_STATIC", "")
    location = getattr(settings, "AWS_STATIC_LOCATION", "static")
    # ACLs are disabled on this bucket (Bucket owner enforced)
    # Access control is managed by bucket policy instead
    default_acl = None
    file_overwrite = True
    custom_domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN_STATIC", None)
    # Querystring auth must be disabled so that the static files are accessible
    querystring_auth = False


class PrivateMediaStorage(S3Boto3Storage):
    """
    Storage backend for media files on S3.
    Used for user-uploaded files (private by default).
    Pre-signed URLs are generated automatically for secure access.
    """
    bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME_MEDIA", "")
    location = getattr(settings, "AWS_MEDIA_LOCATION", "media")
    # ACLs are disabled on this bucket (Bucket owner enforced)
    # Files are private by default via bucket policy
    default_acl = None
    file_overwrite = False
    # IMPORTANT: Do NOT use custom_domain with querystring_auth (pre-signed URLs)
    # Custom domains don't work with S3 pre-signed URLs
    # The URL must use the native S3 endpoint for signatures to work
    custom_domain = None
    # Media files should use signed URLs for access control
    querystring_auth = True
    # Pre-signed URL expiration time in seconds (4 hours)
    # This gives enough time for users to view media without constant regeneration
    querystring_expire = 14400  # 4 hours

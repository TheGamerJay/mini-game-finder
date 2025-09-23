"""Image utilities for Mini Game Finder."""
import hashlib
import io
import os
import uuid
from typing import Optional, Tuple
from flask import Flask
from PIL import Image
from flask.globals import current_app
from werkzeug.utils import secure_filename


def validate_image(file_storage) -> Tuple[bool, Optional[str]]:
    """
    Validate an uploaded image file.
    Returns (is_valid: bool, error_message: Optional[str])
    """
    try:
        # Check file size (5MB limit)
        file_storage.seek(0, 2)  # Seek to end
        size = file_storage.tell()
        if size > 5 * 1024 * 1024:
            return False, "File too large (max 5MB)"
        
        # Reset to start
        file_storage.seek(0)
        
        # Read first 2MB to check format
        header = file_storage.read(2 * 1024 * 1024)
        try:
            # Try to open and verify as image
            img = Image.open(io.BytesIO(header))
            img.verify()
            
            # Check dimensions
            if img.size[0] > 4096 or img.size[1] > 4096:
                return False, "Image dimensions too large (max 4096x4096)"
            
            # Reset file pointer
            file_storage.seek(0)
            return True, None
            
        except Exception:
            file_storage.seek(0)
            return False, "Invalid image file format"
            
    except Exception as e:
        file_storage.seek(0)
        return False, f"Error validating image: {str(e)}"


def save_to_storage(file_storage, *, storage_backend: str = "local", config: dict):
    """
    Save an uploaded file to the configured storage backend.
    Returns the public URL of the saved file.
    
    Args:
        file_storage: The uploaded file object
        storage_backend: Storage backend to use ("local", "s3", or "supabase")
        config: Flask app config dict with storage settings
        
    Returns:
        str: The public URL of the saved file
        
    Raises:
        ValueError: If the file is invalid
        RuntimeError: If there's a storage error
    """
    # Validate file format & extension
    filename = file_storage.filename or ""
    if not filename:
        raise ValueError("No filename provided")
        
    # Get extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        raise ValueError("Only JPG, PNG, WEBP images allowed")
        
    # Validate MIME type
    content_type = file_storage.mimetype or ""
    if not content_type or content_type.lower() not in {
        "image/jpeg",
        "image/png", 
        "image/webp"
    }:
        raise ValueError("Invalid image type")
        
    # Validate image contents
    valid, error = validate_image(file_storage)
    if not valid:
        raise ValueError(error or "Invalid image file")
        
    # Generate storage key
    key = f"profiles/{uuid.uuid4().hex}.{ext}"
    
    # Save based on backend
    if storage_backend == "local":
        dest = os.path.join(config["UPLOADS_DIR"], key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        file_storage.save(dest)
        rel = os.path.relpath(dest, start=os.path.join(current_app.root_path, "static"))
        return f"/static/{rel.replace(os.sep, '/')}"
        
    elif storage_backend == "s3":
        bucket = config["S3_BUCKET"]
        if not bucket:
            raise RuntimeError("S3_BUCKET required for s3 storage")
            
        # Get lazy-init s3 client from app.py
        try:
            from app import _get_s3_client
            s3 = _get_s3_client()
        except ImportError:
            # Fallback to direct import if app import fails
            try:
                import boto3
            except ImportError:
                raise RuntimeError("boto3 not installed (required for s3)")
                
            s3 = boto3.client(
                "s3",
                region_name=config["S3_REGION"],
                endpoint_url=config["S3_ENDPOINT_URL"] or None,
                aws_access_key_id=config["S3_ACCESS_KEY_ID"] or None,
                aws_secret_access_key=config["S3_SECRET_ACCESS_KEY"] or None,
            )
        
        # Upload with metadata
        s3.upload_fileobj(
            file_storage,
            bucket,
            key,
            ExtraArgs={
                "ContentType": content_type,
                "ACL": "public-read",
                "CacheControl": "public, max-age=31536000, immutable"
            }
        )
        
        # Return URL
        cdn = config["S3_CDN_BASE_URL"]
        if cdn:
            return f"{cdn.rstrip('/')}/{key}"
        endpoint = config["S3_ENDPOINT_URL"]
        if endpoint:
            return f"{endpoint.rstrip('/')}/{bucket}/{key}"
        region = config["S3_REGION"]
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        
    elif storage_backend == "supabase":
        bucket = config["SUPABASE_BUCKET"]
        if not bucket:
            raise RuntimeError("SUPABASE_BUCKET required for supabase storage")
            
        # Get lazy-init supabase client from app.py
        try:
            from app import _get_supabase_client
            sb = _get_supabase_client()
        except ImportError:
            # Fallback to direct import if app import fails
            try:
                from supabase import create_client
            except ImportError:
                raise RuntimeError("supabase-py not installed")
                
            url = config["SUPABASE_URL"]
            anon_key = config["SUPABASE_ANON_KEY"]
            if not url or not anon_key:
                raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY required")
                
            sb = create_client(url, anon_key)
        
        # Upload
        data = file_storage.read()
        sb.storage.from_(bucket).upload(
            path=key,
            file=data,
            file_options={
                "contentType": content_type,
                "upsert": True
            }
        )
        
        # Get URL
        public_url = sb.storage.from_(bucket).get_public_url(key)
        if not public_url:
            raise RuntimeError("Failed to get Supabase public URL") 
        return public_url
        
    else:
        raise RuntimeError(f"Unknown storage backend: {storage_backend}")

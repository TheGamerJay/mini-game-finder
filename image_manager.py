"""
Profile Image Manager for Mini Word Finder
Handles image upload, processing, validation and serving with base64 storage
"""
import base64
import io
import logging
from typing import Dict, Any, Optional, Tuple
from PIL import Image
from models import db, User

logger = logging.getLogger(__name__)


class ProfileImageManager:
    """Manages user profile images with base64 database storage"""

    def __init__(self):
        # File size limits
        self.max_image_size = 5 * 1024 * 1024  # 5MB for images
        self.max_video_size = 50 * 1024 * 1024  # 50MB for videos

        # Image processing settings
        self.max_dimension = 1024  # Max width/height in pixels
        self.jpeg_quality = 85

        # Supported formats
        self.supported_image_formats = {'JPEG', 'PNG', 'WEBP'}
        self.supported_video_formats = {'MP4'}

    def upload_profile_image(self, user_id: int, file) -> Dict[str, Any]:
        """
        Upload and process a profile image for a user

        Args:
            user_id: The user's ID
            file: The uploaded file object

        Returns:
            Dict with success status, profileImage data URL, and any errors
        """
        try:
            # Get user
            user = db.session.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            # Read file data
            file.seek(0)
            file_data = file.read()

            if not file_data:
                return {"success": False, "error": "Empty file"}

            # Validate file
            validation_result = self._validate_media_file_data(file_data)
            if not validation_result['valid']:
                return {"success": False, "error": validation_result['error']}

            media_type = validation_result['media_type']
            format_type = validation_result['format_type']

            # Process based on media type
            if media_type == 'image':
                process_result = self._process_image(file_data)
                if not process_result['success']:
                    return {"success": False, "error": process_result['error']}

                data_url = process_result['data_url']
                mime_type = "image/jpeg"  # All images converted to JPEG

            elif media_type == 'video':
                # For videos, store as base64 without processing
                base64_data = base64.b64encode(file_data).decode('utf-8')
                data_url = f"data:video/mp4;base64,{base64_data}"
                mime_type = "video/mp4"

            else:
                return {"success": False, "error": "Unsupported media type"}

            # Store in database
            user.profile_image_data = data_url
            user.profile_image_mime_type = mime_type
            # Clear the old file-based URL
            user.profile_image_url = None

            db.session.commit()

            logger.info(f"Profile image uploaded successfully for user {user_id}: {format_type}")

            return {
                "success": True,
                "profileImage": data_url,
                "message": f"Profile {media_type} uploaded successfully",
                "format": format_type,
                "size": len(file_data)
            }

        except Exception as e:
            logger.error(f"Profile image upload error for user {user_id}: {e}")
            db.session.rollback()
            return {"success": False, "error": "Server error during upload"}

    def _validate_media_file_data(self, file_data: bytes) -> Dict[str, Any]:
        """Validate uploaded media file by examining file headers"""
        if len(file_data) < 12:
            return {"valid": False, "error": "File too small or corrupted"}

        # Check file size first
        file_size = len(file_data)

        # Read file header
        header = file_data[:12]

        # Detect format from header
        if header.startswith(b'\xFF\xD8\xFF'):
            format_type = 'JPEG'
            media_type = 'image'
            max_size = self.max_image_size
        elif header.startswith(b'\x89PNG\r\n\x1a\n'):
            format_type = 'PNG'
            media_type = 'image'
            max_size = self.max_image_size
        elif header.startswith(b'RIFF') and b'WEBP' in header:
            format_type = 'WEBP'
            media_type = 'image'
            max_size = self.max_image_size
        elif header.startswith(b'\x00\x00\x00') and b'ftyp' in header:
            format_type = 'MP4'
            media_type = 'video'
            max_size = self.max_video_size
        else:
            return {"valid": False, "error": "Unsupported file format. Please use JPEG, PNG, WEBP, or MP4"}

        # Check file size against limits
        if file_size > max_size:
            size_mb = max_size / (1024 * 1024)
            return {"valid": False, "error": f"File too large. {media_type.capitalize()} files must be under {size_mb:.0f}MB"}

        return {
            "valid": True,
            "format_type": format_type,
            "media_type": media_type,
            "file_size": file_size
        }

    def _process_image(self, image_data: bytes) -> Dict[str, Any]:
        """Process image: resize, optimize, and convert to base64 JPEG"""
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_data))

            # Convert RGBA/transparent to RGB with white background
            if image.mode in ['RGBA', 'LA', 'P']:
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                # Handle transparency
                if image.mode in ['RGBA', 'LA']:
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background

            # Resize if too large (maintain aspect ratio)
            if max(image.size) > self.max_dimension:
                image.thumbnail((self.max_dimension, self.max_dimension), Image.Resampling.LANCZOS)

            # Convert to JPEG and encode as base64
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=self.jpeg_quality, optimize=True)
            jpeg_data = output.getvalue()
            base64_data = base64.b64encode(jpeg_data).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{base64_data}"

            return {
                "success": True,
                "data_url": data_url,
                "processed_size": len(jpeg_data),
                "dimensions": image.size
            }

        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return {"success": False, "error": "Failed to process image"}

    def serve_profile_image(self, user_id: int) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Get profile image data for serving

        Args:
            user_id: The user's ID

        Returns:
            Tuple of (image_bytes, mime_type) or (None, None) if no image
        """
        try:
            user = db.session.get(User, user_id)
            if not user or not user.profile_image_data:
                return None, None

            # Extract data from data URL
            data_url = user.profile_image_data
            if not data_url.startswith('data:'):
                return None, None

            # Parse data URL: data:mime_type;base64,data
            header, data = data_url.split(',', 1)
            mime_type = header.split(';')[0].split(':')[1]

            # Decode base64 data
            image_bytes = base64.b64decode(data)

            return image_bytes, mime_type

        except Exception as e:
            logger.error(f"Error serving profile image for user {user_id}: {e}")
            return None, None

    def delete_profile_image(self, user_id: int) -> Dict[str, Any]:
        """Delete a user's profile image"""
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            # Clear image data
            user.profile_image_data = None
            user.profile_image_mime_type = None
            user.profile_image_url = None  # Also clear old file-based URL

            db.session.commit()

            logger.info(f"Profile image deleted for user {user_id}")
            return {"success": True, "message": "Profile image deleted successfully"}

        except Exception as e:
            logger.error(f"Error deleting profile image for user {user_id}: {e}")
            db.session.rollback()
            return {"success": False, "error": "Server error during deletion"}


# Global instance
image_manager = ProfileImageManager()
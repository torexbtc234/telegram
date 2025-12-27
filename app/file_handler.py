"""
File handling for uploads and downloads
"""
import asyncio
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import magic
from PIL import Image
import aiofiles

from config.config import settings

logger = logging.getLogger(__name__)

class FileHandler:
    """Handles file operations for the chat system"""
    
    def __init__(self):
        self.temp_dir = Path(settings.TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize magic for file type detection
        self.magic = magic.Magic(mime=True)
    
    async def detect_file_type(self, file_data: bytes) -> str:
        """Detect file type from binary data"""
        try:
            mime_type = self.magic.from_buffer(file_data[:1024])  # Check first 1KB
            
            # Map MIME types to our message types
            if mime_type.startswith('image/'):
                return 'image'
            elif mime_type.startswith('audio/'):
                return 'audio'
            elif mime_type.startswith('video/'):
                return 'video'
            elif mime_type in ['application/pdf', 'application/msword', 
                              'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return 'document'
            else:
                return 'file'
                
        except Exception as e:
            logger.error(f"Error detecting file type: {e}")
            return 'file'
    
    async def save_temp_file(self, file_data: bytes, session_id: str, file_type: str) -> str:
        """Save file to temporary storage and return path"""
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{session_id}_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        # Add appropriate extension based on file type
        extensions = {
            'image': '.jpg',
            'audio': '.ogg',
            'video': '.mp4',
            'document': '.pdf',
            'file': '.bin'
        }
        
        ext = extensions.get(file_type, '.bin')
        filepath = self.temp_dir / f"{filename}{ext}"
        
        # Save file
        async with aiofiles.open(filepath, 'wb') as f:
            await f.write(file_data)
        
        logger.info(f"Saved temp file: {filepath} ({len(file_data)} bytes)")
        return str(filepath)
    
    async def compress_image(self, image_path: str, max_size_kb: int = 1024) -> Optional[str]:
        """Compress image to reduce size"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Calculate compression quality
                original_size = os.path.getsize(image_path) / 1024
                if original_size <= max_size_kb:
                    return image_path
                
                # Calculate target quality
                quality = int((max_size_kb / original_size) * 85)
                quality = max(30, min(quality, 95))
                
                # Create compressed version
                compressed_path = image_path.replace('.jpg', '_compressed.jpg')
                img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
                
                # Replace original if significantly smaller
                compressed_size = os.path.getsize(compressed_path) / 1024
                if compressed_size < original_size * 0.8:  # At least 20% smaller
                    os.replace(compressed_path, image_path)
                    logger.info(f"Compressed image: {original_size:.1f}KB -> {compressed_size:.1f}KB")
                else:
                    os.remove(compressed_path)
                
                return image_path
                
        except Exception as e:
            logger.error(f"Error compressing image {image_path}: {e}")
            return image_path
    
    async def cleanup_old_files(self, max_age_hours: int = 24):
        """Cleanup old temporary files"""
        try:
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            
            for filepath in self.temp_dir.glob('*'):
                if filepath.is_file():
                    file_age = filepath.stat().st_mtime
                    
                    if file_age < cutoff_time:
                        try:
                            os.remove(filepath)
                            logger.debug(f"Cleaned up old file: {filepath.name}")
                        except Exception as e:
                            logger.error(f"Error removing file {filepath}: {e}")
            
        except Exception as e:
            logger.error(f"Error in file cleanup: {e}")
    
    def get_file_info(self, filepath: str) -> Optional[dict]:
        """Get information about a file"""
        if not os.path.exists(filepath):
            return None
        
        try:
            stat = os.stat(filepath)
            return {
                'path': filepath,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'extension': Path(filepath).suffix.lower()
            }
        except Exception as e:
            logger.error(f"Error getting file info for {filepath}: {e}")
            return None
    
    async def read_file(self, filepath: str) -> Optional[bytes]:
        """Read file as bytes"""
        try:
            async with aiofiles.open(filepath, 'rb') as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return None
    
    async def delete_file(self, filepath: str) -> bool:
        """Delete a file"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted file: {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {filepath}: {e}")
            return False

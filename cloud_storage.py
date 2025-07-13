"""
Cloud storage module for handling file uploads.
This provides a fallback when local storage isn't available (like in production deployments).
"""

import os
import requests
import base64
from io import BytesIO
from PIL import Image
import uuid

class CloudStorage:
    def __init__(self):
        self.use_cloudinary = os.getenv('CLOUDINARY_URL') is not None
        self.use_imgbb = os.getenv('IMGBB_API_KEY') is not None
        
    def upload_file(self, file, file_type='image'):
        """
        Upload a file to cloud storage.
        Returns the URL of the uploaded file.
        """
        if self.use_cloudinary:
            return self._upload_to_cloudinary(file, file_type)
        elif self.use_imgbb and file_type == 'image':
            return self._upload_to_imgbb(file)
        else:
            # Fallback to local storage
            return self._save_locally(file, file_type)
    
    def _upload_to_cloudinary(self, file, file_type):
        """Upload to Cloudinary (free tier available)"""
        try:
            import cloudinary
            import cloudinary.uploader
            
            # Configure Cloudinary
            cloudinary.config(
                cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
                api_key=os.getenv('CLOUDINARY_API_KEY'),
                api_secret=os.getenv('CLOUDINARY_API_SECRET')
            )
            
            # Upload file
            result = cloudinary.uploader.upload(
                file,
                folder=f"gamer_cred/{file_type}s",
                public_id=f"bg_{uuid.uuid4().hex}"
            )
            
            return result['secure_url']
        except Exception as e:
            print(f"Cloudinary upload failed: {e}")
            return self._save_locally(file, file_type)
    
    def _upload_to_imgbb(self, file):
        """Upload to ImgBB (free image hosting)"""
        try:
            # Convert file to base64
            file.seek(0)
            file_data = file.read()
            encoded_image = base64.b64encode(file_data).decode('utf-8')
            
            # Upload to ImgBB
            url = "https://api.imgbb.com/1/upload"
            payload = {
                'key': os.getenv('IMGBB_API_KEY'),
                'image': encoded_image,
                'name': f"bg_{uuid.uuid4().hex}"
            }
            
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                result = response.json()
                return result['data']['url']
            else:
                raise Exception(f"ImgBB upload failed: {response.text}")
        except Exception as e:
            print(f"ImgBB upload failed: {e}")
            return self._save_locally(file, 'image')
    
    def _save_locally(self, file, file_type):
        """Save file locally (fallback method)"""
        try:
            # Create uploads directory structure
            upload_dir = os.path.join('website', 'public', 'uploads', 'backgrounds', f'{file_type}s')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate filename
            filename = f"bg_{uuid.uuid4().hex}.{self._get_file_extension(file)}"
            file_path = os.path.join(upload_dir, filename)
            
            # Save file
            file.seek(0)
            with open(file_path, 'wb') as f:
                f.write(file.read())
            
            # Return relative URL
            return f"/uploads/backgrounds/{file_type}s/{filename}"
        except Exception as e:
            print(f"Local save failed: {e}")
            raise
    
    def _get_file_extension(self, file):
        """Get file extension from filename or content"""
        if hasattr(file, 'filename') and file.filename:
            return file.filename.split('.')[-1].lower()
        else:
            # Try to detect from content
            file.seek(0)
            header = file.read(8)
            file.seek(0)
            
            if header.startswith(b'\xff\xd8\xff'):
                return 'jpg'
            elif header.startswith(b'\x89PNG'):
                return 'png'
            elif header.startswith(b'GIF8'):
                return 'gif'
            elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
                return 'webp'
            else:
                return 'jpg'  # Default

# Global instance
cloud_storage = CloudStorage() 
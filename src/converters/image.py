from typing import Optional, BinaryIO
import io
import base64
from PIL import Image

from ..core.exceptions import ConversionException
from ..core.config import settings
from .base import BaseConverter, ConverterResult
from ..services.ocr_service import ocr_service


class ImageConverter(BaseConverter):
    """Converter for image files with base64 encoding and lossless compression"""
    
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico', '.tiff'}
    IMAGE_MIMETYPES = {
        'image/png', 'image/jpeg', 'image/gif', 'image/bmp',
        'image/webp', 'image/x-icon', 'image/tiff'
    }
    
    def accepts(self, file: BinaryIO, mimetype: Optional[str] = None,
                extension: Optional[str] = None) -> bool:
        """Check if this is an image file"""
        if extension and extension.lower() in self.IMAGE_EXTENSIONS:
            return True
        
        if mimetype and mimetype in self.IMAGE_MIMETYPES:
            return True
        
        # Try to open as image
        try:
            Image.open(file)
            return True
        except Exception:
            return False
        finally:
            self._reset_file_position(file)
    
    async def convert(self, file: BinaryIO, **kwargs) -> ConverterResult:
        """Convert image to markdown with base64 encoding"""
        try:
            # Read original image
            original_data = file.read()  # noqa: F841
            file.seek(0)
            
            # Open image with PIL
            img = Image.open(file)
            
            # Process image for optimal storage
            processed_img, image_format = await self._process_image(img)
            
            # Check if OCR is requested
            use_ocr = kwargs.get('use_ocr', False)
            ocr_provider = kwargs.get('ocr_provider', 'paddle')
            
            # Build content
            content_parts = [f"# Image: {kwargs.get('filename', 'Untitled')}\n"]
            
            # Initialize variables for conditional image encoding
            # When OCR is used, exclude the base64 image to save space
            include_image = not use_ocr
            ocr_text_extracted = False
            
            # Add OCR text if requested
            if use_ocr:
                try:
                    if ocr_service.is_provider_available(ocr_provider):
                        ocr_result = ocr_service.extract_text(img, ocr_provider)
                        
                        if ocr_result.text.strip():
                            ocr_text_extracted = True  # noqa: F841
                            content_parts.append("## Extracted Text (OCR)\n")
                            content_parts.append("\n**Text Content**:\n")
                            content_parts.append("```")
                            content_parts.append(ocr_result.text)
                            content_parts.append("```\n")
                        else:
                            content_parts.append("## OCR Result\n")
                            content_parts.append("*No text detected in image*\n")
                    else:
                        content_parts.append("## OCR Result\n")
                        content_parts.append(f"*OCR provider '{ocr_provider}' not available*\n")
                except Exception as e:
                    content_parts.append("## OCR Result\n")
                    content_parts.append(f"*OCR failed: {str(e)}*\n")
            
            # Add image if requested (only when OCR is not used)
            if include_image:
                # Convert to base64
                img_buffer = io.BytesIO()
                processed_img.save(img_buffer, format=image_format)
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                
                # Add image to markdown
                content_parts.append("## Image\n")
                content_parts.append(f"![{kwargs.get('filename', 'Image')}](data:image/{image_format.lower()};base64,{img_base64})\n")
            
            # Join content
            content = "\n".join(content_parts)
            
            # Set title
            title = kwargs.get('filename', 'Untitled Image')
            
            return ConverterResult(
                content=content,
                title=title
            )
            
        except Exception as e:
            raise ConversionException(f"Failed to convert image: {str(e)}")
    
    async def _process_image(self, img: Image.Image) -> tuple[Image.Image, str]:
        """Process image for optimal storage with compression"""
        # Convert to RGB if necessary (for JPEG compatibility)
        if img.mode in ('RGBA', 'LA', 'P'):
            # For images with transparency, use PNG
            if img.mode == 'RGBA' or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGBA')
                return img, 'PNG'
            else:
                # Convert to RGB for JPEG
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
        
        # Resize if too large
        max_width = settings.image_max_width
        max_height = settings.image_max_height
        
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Use PNG for better quality, JPEG for smaller size
        if img.mode == 'RGBA':
            return img, 'PNG'
        else:
            return img, 'JPEG'
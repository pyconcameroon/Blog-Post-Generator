"""Free and open-source image analysis and optimization tools"""
import os
import requests
import logging
from PIL import Image
from io import BytesIO
from typing import Tuple, Optional, Dict
from bs4 import BeautifulSoup
import nltk
from urllib.parse import urlparse

class ImageOptimizer:
    def __init__(self):
        self.max_size = (1200, 1200)  # Max dimensions
        self.quality = 85  # JPEG quality
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.webp'}
    
    def optimize_image(self, image_bytes: bytes) -> Tuple[bytes, str]:
        """Optimize image for web use"""
        try:
            # Open image
            img = Image.open(BytesIO(image_bytes))
            
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            
            # Resize if too large
            if img.size[0] > self.max_size[0] or img.size[1] > self.max_size[1]:
                img.thumbnail(self.max_size, Image.LANCZOS)
            
            # Save optimized image
            output = BytesIO()
            img.save(output, format='JPEG', quality=self.quality, optimize=True)
            return output.getvalue(), 'image/jpeg'
            
        except Exception as e:
            logging.error(f"Image optimization failed: {str(e)}")
            return image_bytes, 'image/jpeg'
    
    def generate_alt_text(self, image_url: str, title: str, content_context: str = "") -> str:
        """Generate SEO-friendly alt text using NLP"""
        try:
            # Extract keywords from title and context
            tokens = nltk.word_tokenize(f"{title} {content_context}")
            tagged = nltk.pos_tag(tokens)
            
            # Extract nouns and adjectives
            keywords = [word for word, pos in tagged 
                      if pos.startswith(('NN', 'JJ')) and len(word) > 3]
            
            # Get image filename
            filename = os.path.splitext(os.path.basename(urlparse(image_url).path))[0]
            filename = filename.replace('-', ' ').replace('_', ' ')
            
            # Combine keywords with filename words
            all_words = set(keywords + filename.split())
            
            # Create alt text (max 125 chars)
            alt_text = ' '.join(list(all_words)[:7])
            return alt_text[:125]
            
        except Exception as e:
            logging.warning(f"Alt text generation failed: {str(e)}")
            return title[:125]
    
    def analyze_image_seo(self, html_content: str) -> Dict[str, list]:
        """Analyze images in HTML content for SEO issues"""
        issues = {
            'missing_alt': [],
            'large_images': [],
            'broken_images': [],
            'poor_filenames': []
        }
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for img in soup.find_all('img'):
            # Check alt text
            if not img.get('alt'):
                issues['missing_alt'].append(img.get('src', 'Unknown source'))
            
            # Check image URL/filename
            src = img.get('src', '')
            if src:
                filename = os.path.basename(urlparse(src).path)
                if not self._is_seo_friendly_filename(filename):
                    issues['poor_filenames'].append(src)
                
                # Check if image exists and size
                try:
                    response = requests.head(src, timeout=5)
                    if response.status_code != 200:
                        issues['broken_images'].append(src)
                    else:
                        size = int(response.headers.get('content-length', 0))
                        if size > 500 * 1024:  # 500KB
                            issues['large_images'].append(src)
                except:
                    issues['broken_images'].append(src)
        
        return issues
    
    def _is_seo_friendly_filename(self, filename: str) -> bool:
        """Check if filename is SEO friendly"""
        # Remove extension
        name = os.path.splitext(filename)[0]
        
        # Check length
        if len(name) < 3 or len(name) > 50:
            return False
        
        # Check for keywords vs random strings
        words = name.replace('-', ' ').replace('_', ' ').split()
        if not words:
            return False
        
        # Check if mostly numbers or random characters
        non_alpha = sum(1 for c in name if not c.isalpha())
        if non_alpha / len(name) > 0.5:
            return False
            
        return True

"""WordPress API client for the blog post generator"""
import requests
import base64
import time
from typing import Optional, Dict, Any
from logger import Logger

class WordPressClient:
    def __init__(self, url: str, username: str, password: str, logger: Logger):
        self.url = url.rstrip('/')
        self.auth = base64.b64encode(
            f'{username}:{password}'.encode('utf-8')
        ).decode('utf-8')
        self.logger = logger
    
    def _make_request(
        self, 
        endpoint: str, 
        method: str = 'GET',
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: int = 5
    ) -> Dict[str, Any]:
        """Make a request to WordPress API with retry logic"""
        headers = {
            'Authorization': f'Basic {self.auth}'
        }
        
        # Don't set Content-Type for file uploads, let requests handle it
        if not files:
            headers['Content-Type'] = 'application/json'
        
        url = f'{self.url}/{endpoint.lstrip("/")}'
        
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if not files else None,
                    files=files,
                    timeout=30
                )
                
                if response.status_code in (200, 201):
                    return response.json()
                elif response.status_code == 401:
                    raise Exception("Invalid WordPress credentials")
                elif response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', retry_delay))
                    time.sleep(retry_after)
                    continue
                else:
                    raise Exception(f"WordPress API error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"Request failed, retrying: {str(e)}")
                time.sleep(retry_delay)
    
    def validate_connection(self) -> bool:
        """Test WordPress API connection"""
        try:
            self._make_request('wp/v2/posts?per_page=1')
            return True
        except Exception as e:
            self.logger.error(f"WordPress connection failed: {str(e)}")
            return False
    
    def create_post(
        self,
        title: str,
        content: str,
        excerpt: str,
        slug: str,
        meta: Dict[str, str],
        featured_media_id: Optional[int] = None
    ) -> int:
        """Create a new WordPress post"""
        data = {
            'title': title,
            'content': content,
            'excerpt': excerpt,
            'slug': slug,
            'status': 'publish',
            'meta': meta
        }
        
        if featured_media_id:
            data['featured_media'] = featured_media_id
            
        response = self._make_request(
            'wp/v2/posts',
            method='POST',
            data=data
        )
        
        return response['id']
    
    def upload_media(
        self,
        file_content: bytes,
        filename: str,
        alt_text: str = "",
        caption: str = ""
    ) -> int:
        """Upload media to WordPress"""
        # Determine MIME type based on file extension
        if filename.lower().endswith('.png'):
            mime_type = 'image/png'
        elif filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
            mime_type = 'image/jpeg'
        else:
            mime_type = 'image/png'  # Default to PNG
            
        files = {
            'file': (filename, file_content, mime_type)
        }
        
        data = {}
        if alt_text:
            data['alt_text'] = alt_text
        if caption:
            data['caption'] = caption
            
        response = self._make_request(
            'wp/v2/media',
            method='POST',
            files=files,
            data=data
        )
        
        return response['id']

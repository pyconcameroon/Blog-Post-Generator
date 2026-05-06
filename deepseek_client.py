"""DeepSeek API client with robust retry handling"""
import requests
import time
import logging
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class DeepSeekAPIError(Exception):
    """Base exception for DeepSeek API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message

    @classmethod
    def from_response(cls, response: requests.Response) -> 'DeepSeekAPIError':
        """Create an error from a response object"""
        message = f"API error {response.status_code}: {response.text}"
        return cls(message, response.status_code)

class DeepSeekClient:
    """Client for interacting with DeepSeek's API with robust retry handling"""
    
    BASE_URL = "https://api.deepseek.com/v1"
    
    def __init__(self, api_key: str, timeout: int = 120):  # Increased from 60 to 120 seconds
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    @retry(
        stop=stop_after_attempt(5),  # Increased attempts
        wait=wait_exponential(multiplier=2, min=5, max=60),  # Longer wait times
        retry=retry_if_exception_type(
            (requests.exceptions.Timeout, 
             requests.exceptions.ConnectionError,
             requests.exceptions.RequestException,
             DeepSeekAPIError)
        )
    )
    def _make_request(
        self, 
        endpoint: str, 
        method: str = "POST", 
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to the DeepSeek API with automatic retry handling"""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
                
            # Don't retry auth errors
            if response.status_code == 401:
                raise DeepSeekAPIError(f"Authentication failed: {response.text}", 401)
                
            # Retry rate limits and server errors
            if response.status_code in (429, 500, 502, 503, 504):
                error_msg = f"Retryable API error {response.status_code}: {response.text}"
                raise DeepSeekAPIError(error_msg, response.status_code)
                
            # Don't retry other client errors
            if response.status_code >= 400:
                error_msg = f"Client error {response.status_code}: {response.text}"
                raise DeepSeekAPIError(error_msg, response.status_code)
                
            # Unexpected success codes
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise DeepSeekAPIError(f"Network error: {str(e)}", 0)
    
    def generate_content(
        self,
        prompt: str,
        model: str = "deepseek-chat",
        temperature: float = 0.3,
        max_tokens: int = 8000,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate content using DeepSeek chat API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self._make_request(
            "chat/completions",
            json_data={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )
        
        return response['choices'][0]['message']['content']
    
    def search_images(
        self,
        query: str,
        num_results: int = 5,
        safe_search: bool = True,
        image_type: str = "photo",
        aspect_ratio: Optional[str] = None,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None
    ) -> list:
        """Search for images using DeepSeek's image search capability"""
        params = {
            "q": query,
            "num": num_results,
            "safe": "on" if safe_search else "off",
            "imgType": image_type
        }
        
        if aspect_ratio:
            params["aspect"] = aspect_ratio
        if min_width:
            params["minWidth"] = min_width
        if min_height:
            params["minHeight"] = min_height
            
        response = self._make_request(
            "image/search",
            method="GET",
            params=params
        )
        
        return response.get("images", [])

    def search_authoritative_links(
        self,
        query: str,
        topic_keywords: list[str],
        num_results: int = 10
    ) -> list[dict]:
        """
        Search for relevant authoritative links based on article topic and keywords.
        Returns a list of dictionaries with url, title, snippet, and domain information.
        """
        # Authoritative domains to prioritize
        authority_domains = [
            'wikipedia.org',
            'scholar.google.com',
            'ncbi.nlm.nih.gov',
            'research.gov',
            '.edu',
            '.gov',
            '.org',
            'forbes.com',
            'harvard.edu',
            'mit.edu',
            'stanford.edu',
            'nature.com',
            'sciencedirect.com'
        ]
        
        # Combine main query with topic keywords for better relevance
        search_query = f"{query} {' '.join(topic_keywords[:3])}"
        
        # Add site: operators for authoritative domains
        site_queries = []
        for domain in authority_domains:
            site_query = f"{search_query} site:{domain}"
            try:
                response = self._make_request(
                    "search",
                    method="GET",
                    params={
                        "q": site_query,
                        "num": 3,  # Get top 3 from each domain
                        "type": "web"
                    }
                )
                if response.get("results"):
                    site_queries.extend(response["results"])
            except DeepSeekAPIError as e:
                logger.warning(f"Failed to search {domain}: {str(e)}")
                continue
                
        # Sort results by relevance score if available
        results = sorted(
            site_queries,
            key=lambda x: x.get("score", 0),
            reverse=True
        )[:num_results]
        
        # Process and validate results
        validated_results = []
        for result in results:
            url = result.get("url", "")
            # Skip results from competitor domains or non-authoritative sources
            if any(domain in url.lower() for domain in authority_domains):
                validated_results.append({
                    "url": url,
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "domain": url.split("/")[2] if "/" in url else url
                })
                if len(validated_results) >= num_results:
                    break
                    
        return validated_results

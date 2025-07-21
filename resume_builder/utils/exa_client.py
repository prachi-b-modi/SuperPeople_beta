"""
Exa.ai client wrapper for Resume Builder CLI
"""

import time
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from ..config.settings import ExaConfig
from ..core.exceptions import (
    ExaError, 
    ExaAPIError, 
    ExaRateLimitError, 
    ExaContentExtractionError,
    URLValidationError
)
from ..utils.logger import get_logger, ContextualLogger

logger = get_logger(__name__)


class ExaClient:
    """
    Exa.ai API client with retry logic and error handling
    
    Provides methods for extracting content from URLs using the Exa.ai API,
    with built-in retry logic, rate limiting, and comprehensive error handling.
    """
    
    def __init__(self, config: ExaConfig):
        """
        Initialize Exa client
        
        Args:
            config: Exa.ai configuration object
        """
        self.config = config
        self.base_url = config.base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': config.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Resume-Builder-CLI/1.0'
        })
        
        self.logger = ContextualLogger(logger, {"component": "exa_client"})
        self.logger.info("Exa client initialized")
    
    def validate_url(self, url: str) -> str:
        """
        Validate and normalize URL
        
        Args:
            url: URL to validate
            
        Returns:
            Normalized URL
            
        Raises:
            URLValidationError: If URL is invalid
        """
        if not url or not url.strip():
            raise URLValidationError("URL cannot be empty")
        
        url = url.strip()
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                raise URLValidationError(f"Invalid URL format: {url}")
            
            # Rebuild URL to normalize it
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized += f"?{parsed.query}"
            if parsed.fragment:
                normalized += f"#{parsed.fragment}"
            
            self.logger.debug(f"URL validated: {normalized}")
            return normalized
            
        except Exception as e:
            raise URLValidationError(f"Invalid URL: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ExaAPIError, requests.RequestException))
    )
    def extract_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content from URL using Exa.ai /contents endpoint
        
        Args:
            url: URL to extract content from
            
        Returns:
            Dictionary containing extracted content and metadata
            
        Raises:
            ExaContentExtractionError: If content extraction fails
            ExaAPIError: If API call fails
            ExaRateLimitError: If rate limit is exceeded
        """
        validated_url = self.validate_url(url)
        
        # Prepare request payload
        payload = {
            "urls": [validated_url],
            "text": self.config.content_extraction.text,
            "summary": {
                "query": self.config.content_extraction.summary_query
            },
            "highlights": {
                "query": self.config.content_extraction.highlights_query,
                "highlightsPerUrl": self.config.content_extraction.highlights_per_url,
                "numSentences": 2
            }
        }
        
        # Add text extraction options
        if self.config.content_extraction.max_characters:
            payload["text"] = {
                "maxCharacters": self.config.content_extraction.max_characters,
                "includeHtmlTags": False
            }
        
        self.logger.info(f"Extracting content from URL: {validated_url}")
        
        try:
            response = self.session.post(
                f"{self.base_url}/contents",
                json=payload,
                timeout=self.config.timeout
            )
            
            self._handle_response_errors(response)
            
            data = response.json()
            
            if not data.get('results'):
                raise ExaContentExtractionError(f"No content extracted from URL: {validated_url}")
            
            result = data['results'][0]
            
            # Check if extraction was successful
            if not result.get('text') and not result.get('summary'):
                raise ExaContentExtractionError(f"Failed to extract meaningful content from: {validated_url}")
            
            self.logger.info(f"Successfully extracted content from: {validated_url}")
            
            return {
                'url': validated_url,
                'original_url': url,
                'title': result.get('title', ''),
                'text': result.get('text', ''),
                'summary': result.get('summary', ''),
                'highlights': result.get('highlights', []),
                'author': result.get('author', ''),
                'published_date': result.get('publishedDate', ''),
                'domain': self._extract_domain(validated_url),
                'extraction_metadata': {
                    'cost_dollars': data.get('costDollars', {}),
                    'request_id': data.get('requestId', ''),
                    'extraction_time': time.time()
                }
            }
            
        except requests.RequestException as e:
            self.logger.error(f"Request failed for URL {validated_url}: {e}")
            raise ExaAPIError(f"Failed to extract content from {validated_url}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error extracting content: {e}")
            raise ExaContentExtractionError(f"Unexpected error: {e}")
    
    def extract_multiple_contents(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extract content from multiple URLs
        
        Args:
            urls: List of URLs to extract content from
            
        Returns:
            List of dictionaries containing extracted content
            
        Note:
            This method processes URLs individually to provide better error
            handling and retry logic for each URL.
        """
        results = []
        failed_urls = []
        
        self.logger.info(f"Extracting content from {len(urls)} URLs")
        
        for url in urls:
            try:
                result = self.extract_content(url)
                results.append(result)
            except (ExaContentExtractionError, ExaAPIError, URLValidationError) as e:
                self.logger.warning(f"Failed to extract content from {url}: {e}")
                failed_urls.append({'url': url, 'error': str(e)})
        
        if failed_urls:
            self.logger.warning(f"Failed to extract content from {len(failed_urls)} URLs")
        
        return results
    
    def _handle_response_errors(self, response: requests.Response):
        """Handle HTTP response errors"""
        if response.status_code == 200:
            return
        
        # Parse error message if available
        error_message = "Unknown error"
        try:
            error_data = response.json()
            error_message = error_data.get('message', error_data.get('error', error_message))
        except:
            error_message = response.text or f"HTTP {response.status_code}"
        
        # Handle specific status codes
        if response.status_code == 401:
            raise ExaAPIError(f"Authentication failed: {error_message}")
        elif response.status_code == 403:
            raise ExaAPIError(f"Access forbidden: {error_message}")
        elif response.status_code == 429:
            raise ExaRateLimitError(f"Rate limit exceeded: {error_message}")
        elif response.status_code == 404:
            raise ExaContentExtractionError(f"Content not found: {error_message}")
        elif 400 <= response.status_code < 500:
            raise ExaAPIError(f"Client error ({response.status_code}): {error_message}")
        elif 500 <= response.status_code < 600:
            raise ExaAPIError(f"Server error ({response.status_code}): {error_message}")
        else:
            raise ExaAPIError(f"HTTP {response.status_code}: {error_message}")
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return "unknown"
    
    def test_connection(self) -> bool:
        """
        Test connection to Exa.ai API
        
        Returns:
            True if connection is successful, False otherwise
        """
        test_url = "https://example.com"
        
        try:
            self.extract_content(test_url)
            self.logger.info("Exa.ai API connection test successful")
            return True
        except Exception as e:
            self.logger.error(f"Exa.ai API connection test failed: {e}")
            return False
    
    def get_usage_info(self) -> Dict[str, Any]:
        """
        Get API usage information
        
        Returns:
            Dictionary with usage statistics if available
        """
        # Note: Exa.ai doesn't have a dedicated usage endpoint,
        # so we return basic client information
        return {
            'client_initialized': True,
            'base_url': self.base_url,
            'timeout': self.config.timeout,
            'max_retries': self.config.max_retries,
            'content_extraction': {
                'max_characters': self.config.content_extraction.max_characters,
                'summary_query': self.config.content_extraction.summary_query,
                'highlights_query': self.config.content_extraction.highlights_query
            }
        }
    
    def __del__(self):
        """Clean up session on deletion"""
        if hasattr(self, 'session'):
            self.session.close()


def create_exa_client(config: ExaConfig) -> ExaClient:
    """
    Factory function to create Exa client
    
    Args:
        config: Exa.ai configuration
        
    Returns:
        Configured ExaClient instance
        
    Raises:
        ExaError: If client creation fails
    """
    try:
        client = ExaClient(config)
        logger.info("Exa client created successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to create Exa client: {e}")
        raise ExaError(f"Failed to create Exa client: {e}")


def validate_exa_config(config: ExaConfig) -> bool:
    """
    Validate Exa.ai configuration
    
    Args:
        config: Exa.ai configuration to validate
        
    Returns:
        True if configuration is valid
        
    Raises:
        ExaError: If configuration is invalid
    """
    if not config.api_key:
        raise ExaError("Exa.ai API key is required")
    
    if not config.base_url:
        raise ExaError("Exa.ai base URL is required")
    
    if config.timeout <= 0:
        raise ExaError("Timeout must be positive")
    
    if config.max_retries < 0:
        raise ExaError("Max retries cannot be negative")
    
    logger.info("Exa.ai configuration validated successfully")
    return True 
"""
Configuration management for Resume Builder CLI
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class OpenAIConfig(BaseModel):
    """OpenAI configuration model"""
    api_key: str
    model: str = "gpt-4.1-mini"
    extraction_temperature: float = 0.3
    max_retries: int = 3
    timeout: int = 30


class LocalWeaviateConfig(BaseModel):
    """Local Weaviate configuration model"""
    host: str = "localhost"
    port: int = 8080
    scheme: str = "http"


class CloudWeaviateConfig(BaseModel):
    """Cloud Weaviate configuration model"""
    cluster_url: str
    api_key: str


class WeaviateCollectionConfig(BaseModel):
    """Weaviate collection configuration model"""
    name: str = "Experience"
    vectorizer: str = "text2vec-openai"
    vectorizer_config: Dict[str, Any] = {
        "model": "text-embedding-3-small",
        "dimensions": 1536,
        "type": "text"
    }


class WeaviateConfig(BaseModel):
    """Weaviate configuration model"""
    type: str = "local"  # "local" or "cloud"
    local: LocalWeaviateConfig = LocalWeaviateConfig()
    cloud: Optional[CloudWeaviateConfig] = None
    collection: WeaviateCollectionConfig = WeaviateCollectionConfig()


class LoggingConfig(BaseModel):
    """Logging configuration model"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None


class ExaContentExtractionConfig(BaseModel):
    """Exa.ai content extraction configuration"""
    text: bool = True
    max_characters: int = 5000
    summary_query: str = "job requirements, qualifications, and key skills"
    highlights_query: str = "required experience and technical skills"
    highlights_per_url: int = 3


class ExaConfig(BaseModel):
    """Exa.ai configuration model"""
    api_key: str
    base_url: str = "https://api.exa.ai"
    timeout: int = 30
    max_retries: int = 3
    content_extraction: ExaContentExtractionConfig = ExaContentExtractionConfig()


class JobMatchingConfig(BaseModel):
    """Job matching configuration model"""
    max_experiences_to_match: int = 10
    min_relevance_score: float = 0.3
    search_diversity: bool = True
    refinement_enabled: bool = True
    enable_caching: bool = True
    cache_duration_hours: int = 24


class AppConfig(BaseModel):
    """Application configuration model"""
    retry_attempts: int = 3
    retry_delay: float = 1.0
    batch_size: int = 10
    enable_rich_output: bool = True


class Config:
    """Main configuration class with environment variable expansion"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to configuration file. If None, uses default.
        """
        if config_path is None:
            # Use default config path
            config_path = Path(__file__).parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self._raw_data = self._load_config()
        self._expanded_data = self._expand_env_vars(self._raw_data)
        
        # Validate and create typed configuration objects
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
    
    def _expand_env_vars(self, data: Any) -> Any:
        """
        Recursively expand environment variables in configuration
        
        Supports ${VAR_NAME} syntax
        """
        if isinstance(data, dict):
            return {key: self._expand_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._expand_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Find all ${VAR_NAME} patterns
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, data)
            
            result = data
            for var_name in matches:
                env_value = os.getenv(var_name)
                if env_value is None:
                    raise ValueError(f"Environment variable '{var_name}' is not set")
                result = result.replace(f"${{{var_name}}}", env_value)
            
            return result
        else:
            return data
    
    def _validate_config(self):
        """Validate configuration and create typed objects"""
        try:
            # Validate OpenAI config
            self.openai = OpenAIConfig(**self._expanded_data.get('openai', {}))
            
            # Validate Exa config (optional - only for job matching)
            exa_data = self._expanded_data.get('exa', {})
            if exa_data:
                self.exa = ExaConfig(**exa_data)
            else:
                self.exa = None
            
            # Validate job matching config
            self.job_matching = JobMatchingConfig(**self._expanded_data.get('job_matching', {}))
            
            # Validate Weaviate config
            weaviate_data = self._expanded_data.get('weaviate', {})
            self.weaviate = WeaviateConfig(**weaviate_data)
            
            # Validate logging config
            self.logging = LoggingConfig(**self._expanded_data.get('logging', {}))
            
            # Validate app config
            self.app = AppConfig(**self._expanded_data.get('app', {}))
            
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    @property
    def openai_config(self) -> OpenAIConfig:
        """Get OpenAI configuration"""
        return self.openai
    
    @property
    def weaviate_config(self) -> WeaviateConfig:
        """Get Weaviate configuration"""
        return self.weaviate
    
    @property
    def logging_config(self) -> LoggingConfig:
        """Get logging configuration"""
        return self.logging
    
    @property
    def app_config(self) -> AppConfig:
        """Get application configuration"""
        return self.app
    
    @property
    def exa_config(self) -> Optional[ExaConfig]:
        """Get Exa.ai configuration"""
        return self.exa
    
    @property
    def job_matching_config(self) -> JobMatchingConfig:
        """Get job matching configuration"""
        return self.job_matching
    
    def get_weaviate_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for Weaviate based on type"""
        if self.weaviate.type == "local":
            return {
                "host": self.weaviate.local.host,
                "port": self.weaviate.local.port,
                "scheme": self.weaviate.local.scheme
            }
        elif self.weaviate.type == "cloud":
            if self.weaviate.cloud is None:
                raise ValueError("Cloud Weaviate configuration is missing")
            return {
                "cluster_url": self.weaviate.cloud.cluster_url,
                "api_key": self.weaviate.cloud.api_key
            }
        else:
            raise ValueError(f"Unknown Weaviate type: {self.weaviate.type}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return self._expanded_data
    
    def __repr__(self) -> str:
        return f"Config(path={self.config_path}, type={self.weaviate.type})"


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Convenience function to load configuration
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Loaded and validated configuration
    """
    return Config(config_path) 
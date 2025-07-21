"""
Abstract database interface for Resume Builder CLI
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from ..models.experience import ExperienceData
from ..core.exceptions import WeaviateError


class WeaviateDatabase(ABC):
    """
    Abstract base class for Weaviate database operations
    
    This interface defines the contract for both local and cloud
    Weaviate implementations, ensuring consistent behavior.
    """
    
    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to Weaviate instance
        
        Raises:
            WeaviateConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to Weaviate instance
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if Weaviate instance is healthy and accessible
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def create_schema(self) -> None:
        """
        Create the Experience collection schema
        
        Raises:
            WeaviateSchemaError: If schema creation fails
        """
        pass
    
    @abstractmethod
    def delete_schema(self) -> None:
        """
        Delete the Experience collection schema
        
        Raises:
            WeaviateSchemaError: If schema deletion fails
        """
        pass
    
    @abstractmethod
    def schema_exists(self) -> bool:
        """
        Check if the Experience collection schema exists
        
        Returns:
            True if schema exists, False otherwise
        """
        pass
    
    @abstractmethod
    def store_experience(self, experience: ExperienceData) -> str:
        """
        Store a professional experience in Weaviate
        
        Args:
            experience: Experience data to store
            
        Returns:
            Unique identifier of the stored experience
            
        Raises:
            WeaviateDataError: If storage fails
        """
        pass
    
    @abstractmethod
    def get_experience(self, experience_id: str) -> Optional[ExperienceData]:
        """
        Retrieve a specific experience by ID
        
        Args:
            experience_id: Unique identifier of the experience
            
        Returns:
            Experience data if found, None otherwise
            
        Raises:
            WeaviateDataError: If retrieval fails
        """
        pass
    
    @abstractmethod
    def update_experience(self, experience_id: str, experience: ExperienceData) -> bool:
        """
        Update an existing experience
        
        Args:
            experience_id: Unique identifier of the experience
            experience: Updated experience data
            
        Returns:
            True if update was successful, False otherwise
            
        Raises:
            WeaviateDataError: If update fails
        """
        pass
    
    @abstractmethod
    def delete_experience(self, experience_id: str) -> bool:
        """
        Delete a specific experience
        
        Args:
            experience_id: Unique identifier of the experience
            
        Returns:
            True if deletion was successful, False otherwise
            
        Raises:
            WeaviateDataError: If deletion fails
        """
        pass
    
    @abstractmethod
    def list_experiences(self, 
                        limit: Optional[int] = None,
                        offset: Optional[int] = None,
                        company_filter: Optional[str] = None,
                        date_from: Optional[datetime] = None,
                        date_to: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        List experiences with optional filtering
        
        Args:
            limit: Maximum number of experiences to return
            offset: Number of experiences to skip
            company_filter: Filter by company name
            date_from: Filter experiences created after this date
            date_to: Filter experiences created before this date
            
        Returns:
            List of experience data dictionaries
            
        Raises:
            WeaviateDataError: If listing fails
        """
        pass
    
    @abstractmethod
    def search_experiences(self, 
                          query: str,
                          limit: Optional[int] = None,
                          min_score: Optional[float] = None,
                          company_filter: Optional[str] = None,
                          skills_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search on experiences
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            min_score: Minimum similarity score for results
            company_filter: Filter by company name
            skills_filter: Filter by specific skills
            
        Returns:
            List of search results with scores and experience data
            
        Raises:
            WeaviateDataError: If search fails
        """
        pass

    @abstractmethod
    def search_experiences_multi_query(self,
                                     queries: List[Dict[str, Any]], 
                                     limit: Optional[int] = None,
                                     min_score: Optional[float] = None,
                                     deduplicate: bool = True) -> List[Dict[str, Any]]:
        """
        Perform semantic search using multiple queries with result aggregation
        
        Args:
            queries: List of query dictionaries with 'query' and metadata
            limit: Maximum number of results to return
            min_score: Minimum similarity score for results
            deduplicate: Whether to remove duplicate results
            
        Returns:
            List of aggregated search results with combined scores
            
        Raises:
            WeaviateDataError: If search fails
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Dictionary containing various statistics about the database
            
        Raises:
            WeaviateDataError: If statistics retrieval fails
        """
        pass
    
    @abstractmethod
    def backup_data(self, output_path: str) -> bool:
        """
        Backup all experience data to a file
        
        Args:
            output_path: Path to output backup file
            
        Returns:
            True if backup was successful, False otherwise
            
        Raises:
            WeaviateDataError: If backup fails
        """
        pass
    
    @abstractmethod
    def restore_data(self, input_path: str) -> bool:
        """
        Restore experience data from a backup file
        
        Args:
            input_path: Path to backup file
            
        Returns:
            True if restore was successful, False otherwise
            
        Raises:
            WeaviateDataError: If restore fails
        """
        pass
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


class DatabaseFactory:
    """
    Factory class for creating database instances
    """
    
    @staticmethod
    def create_database(db_type: str, **kwargs) -> WeaviateDatabase:
        """
        Create a database instance based on type
        
        Args:
            db_type: Type of database ("local" or "cloud")
            **kwargs: Additional configuration parameters
            
        Returns:
            Database instance
            
        Raises:
            ValueError: If db_type is not supported
        """
        if db_type == "local":
            from .local_weaviate import LocalWeaviateDatabase
            return LocalWeaviateDatabase(**kwargs)
        elif db_type == "cloud":
            from .cloud_weaviate import CloudWeaviateDatabase
            return CloudWeaviateDatabase(**kwargs)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")


def create_database_from_config(config) -> WeaviateDatabase:
    """
    Create database instance from configuration
    
    Args:
        config: Configuration object with Weaviate settings
        
    Returns:
        Database instance
    """
    weaviate_config = config.weaviate_config
    connection_params = config.get_weaviate_connection_params()
    
    # Add collection config to connection params
    connection_params['collection_config'] = weaviate_config.collection
    
    return DatabaseFactory.create_database(
        weaviate_config.type,
        **connection_params
    ) 
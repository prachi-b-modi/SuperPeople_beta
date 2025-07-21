"""
Weaviate schema definitions and management for Resume Builder CLI
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import weaviate
from weaviate.classes.config import Configure, Property, DataType

from ..config.settings import WeaviateCollectionConfig
from ..core.exceptions import WeaviateSchemaError


@dataclass
class SchemaProperty:
    """Represents a Weaviate schema property"""
    name: str
    data_type: str
    description: str
    tokenization: Optional[str] = None
    index_searchable: bool = True
    index_filterable: bool = True
    vectorize_property_name: bool = False
    skip_vectorization: bool = False


class ExperienceSchema:
    """
    Schema definition for Experience collection in Weaviate
    """
    
    @staticmethod
    def get_collection_name() -> str:
        """Get the collection name"""
        return "Experience"
    
    @staticmethod
    def get_properties() -> List[SchemaProperty]:
        """
        Get schema properties for Experience collection
        
        Returns:
            List of schema properties
        """
        return [
            SchemaProperty(
                name="original_text",
                data_type="text",
                description="Original experience description text",
                skip_vectorization=False,
                vectorize_property_name=False
            ),
            SchemaProperty(
                name="skills",
                data_type="text[]",
                description="Extracted core skills from the experience",
                skip_vectorization=True,  # Skills are metadata, not for vectorization
                index_searchable=True,
                index_filterable=True
            ),
            SchemaProperty(
                name="categories",
                data_type="text[]",
                description="Experience categories and domains",
                skip_vectorization=True,
                index_searchable=True,
                index_filterable=True
            ),
            SchemaProperty(
                name="relevant_jobs",
                data_type="text[]",
                description="Job titles that would value this experience",
                skip_vectorization=True,
                index_searchable=True,
                index_filterable=True
            ),
            SchemaProperty(
                name="company_name",
                data_type="text",
                description="Company where the experience was gained",
                skip_vectorization=True,
                index_searchable=True,
                index_filterable=True,
                tokenization="field"
            ),
            SchemaProperty(
                name="created_date",
                data_type="date",
                description="When the experience entry was created",
                skip_vectorization=True,
                index_searchable=False,
                index_filterable=True
            ),
            SchemaProperty(
                name="combined_text",
                data_type="text",
                description="Combined text including original text and extracted metadata for enhanced vectorization",
                skip_vectorization=False,
                vectorize_property_name=False
            )
        ]
    
    @staticmethod
    def get_weaviate_config(collection_config: WeaviateCollectionConfig) -> Dict[str, Any]:
        """
        Get Weaviate collection configuration
        
        Args:
            collection_config: Collection configuration from settings
            
        Returns:
            Weaviate collection configuration dictionary
        """
        return 
        {
            "class": ExperienceSchema.get_collection_name(),
            "description": "Professional experience entries for resume building with semantic search capabilities",
            "vectorizer": collection_config.vectorizer,
            "moduleConfig": 
            {
                collection_config.vectorizer: collection_config.vectorizer_config
            },
            "properties": [
                prop.to_weaviate_property() for prop in ExperienceSchema.get_properties()
            ]
        }
    
    @staticmethod
    def create_collection_config(collection_config: WeaviateCollectionConfig) -> Any:
        """
        Create Weaviate v4 collection configuration
        
        Args:
            collection_config: Collection configuration from settings
            
        Returns:
            Weaviate collection configuration object
        """
        # Convert properties to Weaviate v4 format
        properties = []
        for prop in ExperienceSchema.get_properties():
            properties.append(prop.to_weaviate_v4_property())
        
        # Configure vectorizer
        if collection_config.vectorizer == "text2vec-openai":
            vectorizer_config = Configure.Vectorizer.text2vec_openai(
                model=collection_config.vectorizer_config.get("model", "text-embedding-3-small"),
                type_=collection_config.vectorizer_config.get("type", "text")
            )
        else:
            # Default fallback
            vectorizer_config = Configure.Vectorizer.text2vec_openai()
        
        return {
            "name": ExperienceSchema.get_collection_name(),
            "description": "Professional experience entries for resume building",
            "properties": properties,
            "vectorizer_config": vectorizer_config
        }


# Extend SchemaProperty with Weaviate-specific methods
def to_weaviate_property(self) -> Dict[str, Any]:
    """
    Convert to Weaviate property format (v3 style)
    
    Returns:
        Weaviate property dictionary
    """
    prop =     {
        "name": self.name,
        "dataType": [self.data_type],
        "description": self.description
    }
    
    if self.tokenization:
        prop["tokenization"] = self.tokenization
    
    # Add module configuration for vectorization
    if hasattr(self, 'skip_vectorization') and self.skip_vectorization is not None:
        prop["moduleConfig"] =         {
            "text2vec-openai": 
            {
                "skip": self.skip_vectorization,
                "vectorizePropertyName": self.vectorize_property_name
            }
        }
    
    return prop


def to_weaviate_v4_property(self) -> Property:
    """
    Convert to Weaviate v4 Property format
    
    Returns:
        Weaviate v4 Property object
    """
    # Map data types
    if self.data_type == "text":
        data_type = DataType.TEXT
    elif self.data_type == "text[]":
        data_type = DataType.TEXT_ARRAY
    elif self.data_type == "string":
        data_type = DataType.TEXT
    elif self.data_type == "date":
        data_type = DataType.DATE
    else:
        data_type = DataType.TEXT  # Default fallback
    
    return Property(
        name=self.name,
        data_type=data_type,
        description=self.description,
        skip_vectorization=self.skip_vectorization,
        vectorize_property_name=self.vectorize_property_name,
        index_searchable=self.index_searchable,
        index_filterable=self.index_filterable
    )


# Add methods to SchemaProperty class
SchemaProperty.to_weaviate_property = to_weaviate_property
SchemaProperty.to_weaviate_v4_property = to_weaviate_v4_property


class SchemaManager:
    """
    Manages Weaviate schema operations
    """
    
    def __init__(self, client: weaviate.WeaviateClient, collection_config: WeaviateCollectionConfig):
        """
        Initialize schema manager
        
        Args:
            client: Weaviate client instance
            collection_config: Collection configuration
        """
        self.client = client
        self.collection_config = collection_config
        self.collection_name = ExperienceSchema.get_collection_name()
    
    def collection_exists(self) -> bool:
        """
        Check if the Experience collection exists
        
        Returns:
            True if collection exists, False otherwise
        """
        try:
            return self.client.collections.exists(self.collection_name)
        except Exception as e:
            raise WeaviateSchemaError(f"Failed to check collection existence: {str(e)}")
    
    def create_collection(self) -> None:
        """
        Create the Experience collection with proper schema
        
        Raises:
            WeaviateSchemaError: If collection creation fails
        """
        try:
            if self.collection_exists():
                raise WeaviateSchemaError(f"Collection '{self.collection_name}' already exists")
            
            # Get collection configuration
            config = ExperienceSchema.create_collection_config(self.collection_config)
            
            # Create collection
            self.client.collections.create(**config)
            
        except Exception as e:
            raise WeaviateSchemaError(f"Failed to create collection: {str(e)}")
    
    def delete_collection(self) -> None:
        """
        Delete the Experience collection
        
        Raises:
            WeaviateSchemaError: If collection deletion fails
        """
        try:
            if not self.collection_exists():
                raise WeaviateSchemaError(f"Collection '{self.collection_name}' does not exist")
            
            self.client.collections.delete(self.collection_name)
            
        except Exception as e:
            raise WeaviateSchemaError(f"Failed to delete collection: {str(e)}")
    
    def recreate_collection(self) -> None:
        """
        Recreate the Experience collection (delete and create)
        
        Raises:
            WeaviateSchemaError: If recreation fails
        """
        if self.collection_exists():
            self.delete_collection()
        
        self.create_collection()
    
    def get_collection_schema(self) -> Dict[str, Any]:
        """
        Get the current collection schema
        
        Returns:
            Collection schema dictionary
            
        Raises:
            WeaviateSchemaError: If schema retrieval fails
        """
        try:
            if not self.collection_exists():
                raise WeaviateSchemaError(f"Collection '{self.collection_name}' does not exist")
            
            collection = self.client.collections.get(self.collection_name)
            return collection.config.get()
            
        except Exception as e:
            raise WeaviateSchemaError(f"Failed to get collection schema: {str(e)}")
    
    def validate_schema(self) -> bool:
        """
        Validate that the current schema matches expected schema
        
        Returns:
            True if schema is valid, False otherwise
        """
        try:
            if not self.collection_exists():
                return False
            
            current_schema = self.get_collection_schema()
            expected_properties = [prop.name for prop in ExperienceSchema.get_properties()]
            
            # Check if all expected properties exist
            current_properties = [prop.name for prop in current_schema.get('properties', [])]
            
            return set(expected_properties).issubset(set(current_properties))
            
        except Exception:
            return False
    
    def ensure_collection(self) -> None:
        """
        Ensure the collection exists with correct schema
        
        Creates the collection if it doesn't exist or if schema is invalid
        
        Raises:
            WeaviateSchemaError: If collection creation fails
        """
        if not self.collection_exists():
            self.create_collection()
        elif not self.validate_schema():
            # Schema is invalid, recreate collection
            self.recreate_collection()


def create_schema_manager(client: weaviate.WeaviateClient, 
                         collection_config: WeaviateCollectionConfig) -> SchemaManager:
    """
    Factory function to create schema manager
    
    Args:
        client: Weaviate client instance
        collection_config: Collection configuration
        
    Returns:
        SchemaManager instance
    """
    return SchemaManager(client, collection_config) 
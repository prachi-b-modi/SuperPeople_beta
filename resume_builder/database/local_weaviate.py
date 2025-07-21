"""
Local Weaviate database implementation for Resume Builder CLI
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import weaviate
from weaviate.classes.query import Filter

from .base import WeaviateDatabase
from ..models.experience import ExperienceData
from ..models.schemas import SchemaManager, create_schema_manager
from ..config.settings import WeaviateCollectionConfig
from ..core.exceptions import (
    WeaviateConnectionError,
    WeaviateSchemaError,
    WeaviateDataError
)
from ..utils.logger import get_logger
from ..utils.helpers import safe_json_loads, safe_json_dumps

logger = get_logger(__name__)


class LocalWeaviateDatabase(WeaviateDatabase):
    """
    Local Weaviate database implementation
    
    Handles connections to a locally running Weaviate instance
    (typically via Docker)
    """
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 8080, 
                 scheme: str = "http",
                 collection_config: Optional[WeaviateCollectionConfig] = None):
        """
        Initialize local Weaviate database
        
        Args:
            host: Weaviate host
            port: Weaviate port
            scheme: Connection scheme (http/https)
            collection_config: Collection configuration
        """
        self.host = host
        self.port = port
        self.scheme = scheme
        self.collection_config = collection_config or WeaviateCollectionConfig()
        self.client: Optional[weaviate.WeaviateClient] = None
        self.schema_manager: Optional[SchemaManager] = None
        self.collection_name = "Experience"
        
        logger.info(f"Initialized LocalWeaviateDatabase for {scheme}://{host}:{port}")
    
    def connect(self) -> None:
        """
        Establish connection to local Weaviate instance
        
        Raises:
            WeaviateConnectionError: If connection fails
        """
        try:
            logger.info(f"Connecting to Weaviate at {self.scheme}://{self.host}:{self.port}")
            
            self.client = weaviate.connect_to_local(
                host=self.host,
                port=self.port,
                grpc_port=50051,  # Default gRPC port
                headers=                {
                    "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")
                }
            )
            
            # Test connection
            if not self.client.is_ready():
                raise WeaviateConnectionError("Weaviate client not ready")
            
            # Initialize schema manager
            self.schema_manager = create_schema_manager(self.client, self.collection_config)
            
            logger.info("Successfully connected to local Weaviate")
            
        except Exception as e:
            error_msg = f"Failed to connect to local Weaviate: {str(e)}"
            logger.error(error_msg)
            raise WeaviateConnectionError(error_msg)
    
    def disconnect(self) -> None:
        """Close connection to Weaviate instance"""
        if self.client:
            try:
                self.client.close()
                logger.info("Disconnected from local Weaviate")
            except Exception as e:
                logger.warning(f"Error during disconnect: {str(e)}")
            finally:
                self.client = None
                self.schema_manager = None
    
    def health_check(self) -> bool:
        """
        Check if Weaviate instance is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.client:
                return False
            
            return self.client.is_ready()
            
        except Exception as e:
            logger.warning(f"Health check failed: {str(e)}")
            return False
    
    def create_schema(self) -> None:
        """
        Create the Experience collection schema
        
        Raises:
            WeaviateSchemaError: If schema creation fails
        """
        if not self.schema_manager:
            raise WeaviateSchemaError("Schema manager not initialized")
        
        try:
            self.schema_manager.ensure_collection()
            logger.info("Experience collection schema created/verified")
            
        except Exception as e:
            error_msg = f"Failed to create schema: {str(e)}"
            logger.error(error_msg)
            raise WeaviateSchemaError(error_msg)
    
    def delete_schema(self) -> None:
        """
        Delete the Experience collection schema
        
        Raises:
            WeaviateSchemaError: If schema deletion fails
        """
        if not self.schema_manager:
            raise WeaviateSchemaError("Schema manager not initialized")
        
        try:
            self.schema_manager.delete_collection()
            logger.info("Experience collection schema deleted")
            
        except Exception as e:
            error_msg = f"Failed to delete schema: {str(e)}"
            logger.error(error_msg)
            raise WeaviateSchemaError(error_msg)
    
    def schema_exists(self) -> bool:
        """
        Check if the Experience collection schema exists
        
        Returns:
            True if schema exists, False otherwise
        """
        try:
            if not self.schema_manager:
                return False
            
            return self.schema_manager.collection_exists()
            
        except Exception as e:
            logger.warning(f"Failed to check schema existence: {str(e)}")
            return False
    
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
        if not self.client:
            raise WeaviateDataError("Database not connected")
        
        try:
            # Ensure schema exists
            if not self.schema_exists():
                self.create_schema()
            
            collection = self.client.collections.get(self.collection_name)
            
            # Prepare data for storage
            properties =             {
                "original_text": experience.original_text,
                "skills": experience.skills,
                "categories": experience.categories,
                "relevant_jobs": experience.relevant_jobs,
                "company_name": experience.company_name,
                "created_date": experience.created_date.replace(tzinfo=timezone.utc).isoformat(),
                "combined_text": experience.combined_text
            }
            
            # Store in Weaviate
            result = collection.data.insert(properties)
            
            logger.info(f"Successfully stored experience: {result}")
            return str(result)
            
        except Exception as e:
            error_msg = f"Failed to store experience: {str(e)}"
            logger.error(error_msg)
            raise WeaviateDataError(error_msg)
    
    def get_experience(self, experience_id: str) -> Optional[ExperienceData]:
        """
        Retrieve a specific experience by ID
        
        Args:
            experience_id: Unique identifier of the experience
            
        Returns:
            Experience data if found, None otherwise
        """
        if not self.client:
            raise WeaviateDataError("Database not connected")
        
        try:
            collection = self.client.collections.get(self.collection_name)
            
            result = collection.data.get_by_id(experience_id)
            
            if not result:
                return None
            
            # Convert back to ExperienceData
            properties = result.properties
            return self._convert_to_experience_data(properties)
            
        except Exception as e:
            error_msg = f"Failed to retrieve experience {experience_id}: {str(e)}"
            logger.error(error_msg)
            raise WeaviateDataError(error_msg)
    
    def update_experience(self, experience_id: str, experience: ExperienceData) -> bool:
        """
        Update an existing experience
        
        Args:
            experience_id: Unique identifier of the experience
            experience: Updated experience data
            
        Returns:
            True if update was successful, False otherwise
        """
        if not self.client:
            raise WeaviateDataError("Database not connected")
        
        try:
            collection = self.client.collections.get(self.collection_name)
            
            # Prepare updated properties
            properties =             {
                "original_text": experience.original_text,
                "skills": experience.skills,
                "categories": experience.categories,
                "relevant_jobs": experience.relevant_jobs,
                "company_name": experience.company_name,
                "created_date": experience.created_date.replace(tzinfo=timezone.utc).isoformat(),
                "combined_text": experience.combined_text
            }
            
            # Update in Weaviate
            collection.data.update(experience_id, properties)
            
            logger.info(f"Successfully updated experience: {experience_id}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to update experience {experience_id}: {str(e)}"
            logger.error(error_msg)
            raise WeaviateDataError(error_msg)
    
    def delete_experience(self, experience_id: str) -> bool:
        """
        Delete a specific experience
        
        Args:
            experience_id: Unique identifier of the experience
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.client:
            raise WeaviateDataError("Database not connected")
        
        try:
            collection = self.client.collections.get(self.collection_name)
            
            # Delete from Weaviate
            collection.data.delete_by_id(experience_id)
            
            logger.info(f"Successfully deleted experience: {experience_id}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to delete experience {experience_id}: {str(e)}"
            logger.error(error_msg)
            raise WeaviateDataError(error_msg)
    
    def list_experiences(self, 
                        limit: Optional[int] = None,
                        offset: Optional[int] = None,
                        company_filter: Optional[str] = None,
                        date_from: Optional[datetime] = None,
                        date_to: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        List experiences with optional filtering
        """
        if not self.client:
            raise WeaviateDataError("Database not connected")
        
        try:
            collection = self.client.collections.get(self.collection_name)
            
            # Build query
            query = collection.query.fetch_objects(
                limit=limit or 100,
                offset=offset or 0
            )
            
            # Apply filters if provided
            if company_filter:
                query = query.where(Filter.by_property("company_name").equal(company_filter))
            
            if date_from:
                query = query.where(Filter.by_property("created_date").greater_or_equal(date_from.isoformat()))
            
            if date_to:
                query = query.where(Filter.by_property("created_date").less_or_equal(date_to.isoformat()))
            
            # Execute query
            results = query.objects
            
            # Convert to dictionaries
            experiences = []
            for result in results:
                exp_dict = result.properties.copy()
                exp_dict['id'] = str(result.uuid)
                experiences.append(exp_dict)
            
            logger.info(f"Retrieved {len(experiences)} experiences")
            return experiences
            
        except Exception as e:
            error_msg = f"Failed to list experiences: {str(e)}"
            logger.error(error_msg)
            raise WeaviateDataError(error_msg)
    
    def search_experiences(self, 
                          query: str,
                          limit: Optional[int] = None,
                          min_score: Optional[float] = None,
                          company_filter: Optional[str] = None,
                          skills_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search on experiences
        """
        if not self.client:
            raise WeaviateDataError("Database not connected")
        
        try:
            collection = self.client.collections.get(self.collection_name)
            
            # Build semantic search query
            search_query = collection.query.near_text(
                query=query,
                limit=limit or 10,
                return_metadata=["score", "distance"]
            )
            
            # Apply filters if provided
            if company_filter:
                search_query = search_query.where(Filter.by_property("company_name").equal(company_filter))
            
            if skills_filter:
                # Create filter for any of the specified skills
                skill_filters = [Filter.by_property("skills").contains_any(skills_filter)]
                search_query = search_query.where(Filter.any_of(skill_filters))
            
            # Execute search
            results = search_query.objects
            
            # Convert to dictionaries with scores
            search_results = []
            for result in results:
                exp_dict = result.properties.copy()
                exp_dict['id'] = str(result.uuid)
                exp_dict['score'] = result.metadata.score if result.metadata else 0.0
                exp_dict['distance'] = result.metadata.distance if result.metadata else 1.0
                
                # Apply minimum score filter
                if min_score is None or exp_dict['score'] >= min_score:
                    search_results.append(exp_dict)
            
            logger.info(f"Found {len(search_results)} relevant experiences for query: '{query}'")
            return search_results
            
        except Exception as e:
            error_msg = f"Failed to search experiences: {str(e)}"
            logger.error(error_msg)
            raise WeaviateDataError(error_msg)

    def search_experiences_multi_query(self,
                                     queries: List[Dict[str, Any]], 
                                     limit: Optional[int] = None,
                                     min_score: Optional[float] = None,
                                     deduplicate: bool = True) -> List[Dict[str, Any]]:
        """
        Perform semantic search using multiple queries with result aggregation
        """
        if not self.client:
            raise WeaviateDataError("Database not connected")
            
        try:
            if not queries:
                return []
            
            all_results = []
            search_limit = (limit or 10) * 2  # Search for more to account for deduplication
            
            logger.info(f"Executing multi-query search with {len(queries)} queries")
            
            # Execute each query
            for query_info in queries:
                query_text = query_info.get('query', '').strip()
                if not query_text:
                    continue
                
                query_priority = query_info.get('priority', 1.0)
                query_type = query_info.get('type', 'unknown')
                
                logger.debug(f"Executing {query_type} query: {query_text[:50]}...")
                
                # Execute single query
                query_results = self.search_experiences(
                    query=query_text,
                    limit=search_limit,
                    min_score=min_score
                )
                
                # Add query metadata to results
                for result in query_results:
                    result['query_info'] = {
                        'query': query_text,
                        'type': query_type,
                        'priority': query_priority,
                        'rank': query_info.get('rank', 0)
                    }
                    # Adjust score based on query priority
                    result['original_score'] = result['score']
                    result['score'] = result['score'] * query_priority
                
                all_results.extend(query_results)
            
            # Deduplicate and aggregate results
            if deduplicate:
                aggregated_results = self._aggregate_multi_query_results(all_results)
            else:
                aggregated_results = all_results
            
            # Sort by final score and limit
            final_results = sorted(aggregated_results, 
                                 key=lambda x: x.get('final_score', x.get('score', 0)), 
                                 reverse=True)
            
            if limit:
                final_results = final_results[:limit]
            
            logger.info(f"Multi-query search returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            error_msg = f"Multi-query search failed: {str(e)}"
            logger.error(error_msg)
            raise WeaviateDataError(error_msg)
    
    def _aggregate_multi_query_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate results from multiple queries, combining scores for duplicates"""
        experience_map = {}
        
        for result in results:
            exp_id = result.get('id')
            if not exp_id:
                continue
            
            if exp_id in experience_map:
                # Combine scores for duplicate experiences
                existing = experience_map[exp_id]
                
                # Use weighted average of scores
                existing_weight = existing.get('query_count', 1)
                new_weight = 1
                total_weight = existing_weight + new_weight
                
                combined_score = (
                    (existing['score'] * existing_weight + result['score'] * new_weight) 
                    / total_weight
                )
                
                existing['score'] = combined_score
                existing['final_score'] = combined_score
                existing['query_count'] = total_weight
                
                # Add query info to list
                if 'query_matches' not in existing:
                    existing['query_matches'] = [existing.get('query_info', {})]
                existing['query_matches'].append(result.get('query_info', {}))
                
                # Boost score for multiple query matches
                boost_factor = 1.0 + (total_weight - 1) * 0.1  # 10% boost per additional match
                existing['final_score'] = combined_score * boost_factor
                
            else:
                # First time seeing this experience
                result['query_count'] = 1
                result['final_score'] = result['score']
                result['query_matches'] = [result.get('query_info', {})]
                experience_map[exp_id] = result
        
        return list(experience_map.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics
        """
        if not self.client:
            raise WeaviateDataError("Database not connected")
        
        try:
            collection = self.client.collections.get(self.collection_name)
            
            # Get total count
            total_count = collection.aggregate.over_all().total_count
            
            # Get experiences by company (top 10)
            companies_query = collection.query.fetch_objects(
                limit=1000  # Get reasonable sample
            )
            
            company_counts = {}
            skill_counts = {}
            category_counts = {}
            
            for result in companies_query.objects:
                props = result.properties
                
                # Count by company
                company = props.get('company_name', 'Unknown')
                company_counts[company] = company_counts.get(company, 0) + 1
                
                # Count skills
                for skill in props.get('skills', []):
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1
                
                # Count categories
                for category in props.get('categories', []):
                    category_counts[category] = category_counts.get(category, 0) + 1
            
            stats =             {
                "total_experiences": total_count,
                "unique_companies": len(company_counts),
                "unique_skills": len(skill_counts),
                "unique_categories": len(category_counts),
                "top_companies": sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                "top_skills": sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:20],
                "top_categories": sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                "collection_name": self.collection_name,
                "database_type": "local"
            }
            
            logger.info(f"Generated statistics for {total_count} experiences")
            return stats
            
        except Exception as e:
            error_msg = f"Failed to get statistics: {str(e)}"
            logger.error(error_msg)
            raise WeaviateDataError(error_msg)
    
    def backup_data(self, output_path: str) -> bool:
        """
        Backup all experience data to a JSON file
        """
        try:
            experiences = self.list_experiences(limit=10000)  # Get all experiences
            
            backup_data =             {
                "backup_date": datetime.now(timezone.utc).isoformat(),
                "database_type": "local",
                "collection_name": self.collection_name,
                "total_experiences": len(experiences),
                "experiences": experiences
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully backed up {len(experiences)} experiences to {output_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to backup data: {str(e)}"
            logger.error(error_msg)
            return False
    
    def restore_data(self, input_path: str) -> bool:
        """
        Restore experience data from a backup file
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            experiences = backup_data.get('experiences', [])
            
            # Ensure schema exists
            if not self.schema_exists():
                self.create_schema()
            
            # Restore each experience
            restored_count = 0
            for exp_data in experiences:
                try:
                    # Remove ID if present (will be auto-generated)
                    exp_data.pop('id', None)
                    
                    # Convert to ExperienceData
                    experience = self._convert_to_experience_data(exp_data)
                    
                    # Store experience
                    self.store_experience(experience)
                    restored_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to restore experience: {str(e)}")
                    continue
            
            logger.info(f"Successfully restored {restored_count} out of {len(experiences)} experiences")
            return restored_count > 0
            
        except Exception as e:
            error_msg = f"Failed to restore data: {str(e)}"
            logger.error(error_msg)
            return False
    
    def _convert_to_experience_data(self, properties: Dict[str, Any]) -> ExperienceData:
        """
        Convert Weaviate properties to ExperienceData
        
        Args:
            properties: Weaviate object properties
            
        Returns:
            ExperienceData instance
        """
        # Handle datetime conversion
        created_date = properties.get('created_date')
        if isinstance(created_date, str):
            created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
        elif created_date is None:
            created_date = datetime.now()
        
        return ExperienceData(
            original_text=properties.get('original_text', ''),
            company_name=properties.get('company_name', ''),
            skills=properties.get('skills', []),
            categories=properties.get('categories', []),
            relevant_jobs=properties.get('relevant_jobs', []),
            created_date=created_date,
            combined_text=properties.get('combined_text', '')
        ) 
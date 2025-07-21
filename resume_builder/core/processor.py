"""
Main processing pipeline for Resume Builder CLI
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from ..models.experience import ExperienceData, ExperienceValidator
from ..core.extractor import ExperienceExtractor, create_extractor
from ..database.base import WeaviateDatabase, create_database_from_config
from ..config.settings import Config
from ..core.exceptions import (
    ProcessingError,
    ValidationError,
    OpenAIExtractionError,
    WeaviateDataError,
    ConfigurationError
)
from ..utils.logger import get_logger, ContextualLogger
from ..utils.helpers import RichOutputHelper, normalize_text

logger = get_logger(__name__)


class ExperienceProcessor:
    """
    Main processing pipeline for professional experiences
    
    Orchestrates the entire workflow from text input to vectorized storage:
    1. Text validation and cleaning
    2. OpenAI-based information extraction  
    3. Data validation and structuring
    4. Weaviate storage with vectorization
    """
    
    def __init__(self, config: Config, output_helper: Optional[RichOutputHelper] = None):
        """
        Initialize the experience processor
        
        Args:
            config: Application configuration
            output_helper: Optional Rich output helper for console formatting
        """
        self.config = config
        self.output_helper = output_helper or RichOutputHelper(
            enabled=config.app_config.enable_rich_output
        )
        
        # Initialize components
        self.extractor: Optional[ExperienceExtractor] = None
        self.database: Optional[WeaviateDatabase] = None
        
        # Contextual logger
        self.logger = ContextualLogger(logger, {"component": "processor"})
        
        self.logger.info("ExperienceProcessor initialized")
    
    def initialize(self) -> None:
        """
        Initialize all components (extractor and database)
        
        Raises:
            ConfigurationError: If initialization fails
        """
        try:
            self.logger.info("Initializing processor components")
            
            # Initialize OpenAI extractor
            self.extractor = create_extractor(self.config.openai_config)
            
            # Initialize database connection
            self.database = create_database_from_config(self.config)
            self.database.connect()
            
            # Ensure database schema exists
            if not self.database.schema_exists():
                self.logger.info("Creating database schema")
                self.database.create_schema()
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize processor: {str(e)}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    def cleanup(self) -> None:
        """Clean up resources"""
        if self.database:
            try:
                self.database.disconnect()
            except Exception as e:
                self.logger.warning(f"Error during database cleanup: {str(e)}")
    
    def process_experience(self, 
                          text: str, 
                          company: str,
                          duration: str = None,
                          role: str = None,
                          extract_metadata: bool = True,
                          validate_input: bool = True) -> Dict[str, Any]:
        """
        Process a professional experience through the complete pipeline
        
        Args:
            text: Professional experience description
            company: Company name
            duration: Duration of the experience (e.g., "Jan 2020 - Dec 2021")
            role: Job role or title for this experience
            extract_metadata: Whether to extract skills/categories via OpenAI
            validate_input: Whether to validate input data
            
        Returns:
            Dictionary containing processing results:
            - success: Whether processing succeeded
            - experience_id: ID of stored experience (if successful)
            - experience_data: Processed experience data
            - extraction_results: Raw extraction results from OpenAI
            - errors: List of any errors encountered
            
        Raises:
            ProcessingError: If processing fails completely
        """
        if not self.extractor or not self.database:
            raise ProcessingError("Processor not initialized. Call initialize() first.")
        
        # Setup contextual logging for this operation
        operation_logger = self.logger.with_context(
            operation="process_experience",
            company=company
        )
        
        operation_logger.info(f"Starting experience processing ({len(text)} chars)")
        
        # Track processing results
        results =         {
            "success": False,
            "experience_id": None,
            "experience_data": None,
            "extraction_results": None,
            "errors": [],
            "processing_time": None,
            "metadata": 
            {
                "text_length": len(text),
                "company": company,
                "duration": duration,
                "role": role,
                "extraction_enabled": extract_metadata,
                "validation_enabled": validate_input
            }
        }
        
        start_time = datetime.now()
        
        try:
            # Step 1: Input validation
            if validate_input:
                operation_logger.info("Validating input data")
                self._validate_input(text, company)
            
            # Step 2: Create initial experience object
            experience = ExperienceData(
                original_text=normalize_text(text),
                company_name=normalize_text(company),
                duration=duration,
                role=role
            )
            
            # Step 3: Extract metadata if requested
            extraction_results = {}
            if extract_metadata:
                operation_logger.info("Extracting metadata with OpenAI")
                try:
                    extraction_results = self.extractor.extract_information(text)
                    
                    # Update experience with extracted data
                    experience.update_metadata(
                        skills=extraction_results.get('skills', []),
                        categories=extraction_results.get('categories', []),
                        relevant_jobs=extraction_results.get('relevant_jobs', [])
                    )
                    
                    operation_logger.info(
                        f"Extracted {len(experience.skills)} skills, "
                        f"{len(experience.categories)} categories, "
                        f"{len(experience.relevant_jobs)} relevant jobs"
                    )
                    
                except OpenAIExtractionError as e:
                    operation_logger.warning(f"Extraction failed, proceeding without metadata: {str(e)}")
                    results["errors"].append(f"Extraction failed: {str(e)}")
                    # Continue processing without extracted metadata
            
            results["extraction_results"] = extraction_results
            
            # Step 4: Final validation
            if validate_input:
                self._validate_experience_data(experience)
            
            # Step 5: Store in database
            operation_logger.info("Storing experience in database")
            experience_id = self.database.store_experience(experience)
            
            # Success!
            results.update({
                "success": True,
                "experience_id": experience_id,
                "experience_data": experience.to_dict()
            })
            
            operation_logger.info(f"Successfully processed experience: {experience_id}")
            
            return results
            
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            operation_logger.error(error_msg)
            results["errors"].append(error_msg)
            
            # Don't re-raise, return error in results instead
            return results
            
        finally:
            # Record processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            results["processing_time"] = processing_time
            
            operation_logger.info(f"Processing completed in {processing_time:.2f}s")
    
    def process_batch(self, 
                     experiences: List[Dict[str, str]],
                     extract_metadata: bool = True,
                     continue_on_error: bool = True) -> List[Dict[str, Any]]:
        """
        Process multiple experiences in batch
        
        Args:
            experiences: List of dicts with 'text' and 'company' keys
            extract_metadata: Whether to extract metadata for all experiences
            continue_on_error: Whether to continue processing if one fails
            
        Returns:
            List of processing results for each experience
        """
        if not self.extractor or not self.database:
            raise ProcessingError("Processor not initialized. Call initialize() first.")
        
        self.logger.info(f"Starting batch processing of {len(experiences)} experiences")
        
        results = []
        successful_count = 0
        
        for i, exp_data in enumerate(experiences):
            try:
                text = exp_data.get('text', '')
                company = exp_data.get('company', '')
                
                if not text or not company:
                    results.append({
                        "success": False,
                        "errors": ["Missing text or company"],
                        "experience_data": exp_data
                    })
                    continue
                
                # Process individual experience
                result = self.process_experience(
                    text=text,
                    company=company,
                    extract_metadata=extract_metadata
                )
                
                results.append(result)
                
                if result["success"]:
                    successful_count += 1
                
                # Progress logging
                if (i + 1) % 5 == 0:
                    self.logger.info(f"Processed {i + 1}/{len(experiences)} experiences")
                
            except Exception as e:
                error_result =                 {
                    "success": False,
                    "errors": [f"Batch processing error: {str(e)}"],
                    "experience_data": exp_data
                }
                results.append(error_result)
                
                if not continue_on_error:
                    self.logger.error(f"Stopping batch processing due to error: {str(e)}")
                    break
        
        self.logger.info(f"Batch processing completed: {successful_count}/{len(experiences)} successful")
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components
        
        Returns:
            Dictionary with health status of each component
        """
        health_status =         {
            "overall_healthy": True,
            "components": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Check OpenAI extractor
        try:
            if self.extractor:
                openai_healthy = self.extractor.test_connection()
            else:
                openai_healthy = False
            
            health_status["components"]["openai"] =             {
                "healthy": openai_healthy,
                "status": "connected" if openai_healthy else "disconnected"
            }
            
        except Exception as e:
            health_status["components"]["openai"] =             {
                "healthy": False,
                "status": f"error: {str(e)}"
            }
        
        # Check database
        try:
            if self.database:
                db_healthy = self.database.health_check()
                schema_exists = self.database.schema_exists()
            else:
                db_healthy = False
                schema_exists = False
            
            health_status["components"]["database"] =             {
                "healthy": db_healthy,
                "status": "connected" if db_healthy else "disconnected",
                "schema_exists": schema_exists
            }
            
        except Exception as e:
            health_status["components"]["database"] =             {
                "healthy": False,
                "status": f"error: {str(e)}",
                "schema_exists": False
            }
        
        # Determine overall health
        component_health = [comp["healthy"] for comp in health_status["components"].values()]
        health_status["overall_healthy"] = all(component_health)
        
        return health_status
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about processed experiences
        
        Returns:
            Statistics dictionary
        """
        if not self.database:
            raise ProcessingError("Database not initialized")
        
        try:
            # Get database statistics
            db_stats = self.database.get_statistics()
            
            # Add processor-specific statistics
            stats =             {
                **db_stats,
                "processor_info": 
                {
                    "openai_model": self.config.openai_config.model if self.extractor else None,
                    "database_type": self.config.weaviate_config.type,
                    "extraction_enabled": True if self.extractor else False
                }
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {str(e)}")
            raise ProcessingError(f"Statistics retrieval failed: {str(e)}")
    
    def _validate_input(self, text: str, company: str) -> None:
        """
        Validate input text and company
        
        Args:
            text: Experience text
            company: Company name
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Use Pydantic validator
            validator = ExperienceValidator(
                original_text=text,
                company_name=company
            )
            
        except Exception as e:
            raise ValidationError(f"Input validation failed: {str(e)}")
    
    def _validate_experience_data(self, experience: ExperienceData) -> None:
        """
        Validate complete experience data
        
        Args:
            experience: Experience data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Convert to validator for validation
            validator = ExperienceValidator(
                original_text=experience.original_text,
                company_name=experience.company_name,
                skills=experience.skills,
                categories=experience.categories,
                relevant_jobs=experience.relevant_jobs
            )
            
        except Exception as e:
            raise ValidationError(f"Experience validation failed: {str(e)}")
    
    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


def create_processor(config: Config, output_helper: Optional[RichOutputHelper] = None) -> ExperienceProcessor:
    """
    Factory function to create an experience processor
    
    Args:
        config: Application configuration
        output_helper: Optional Rich output helper
        
    Returns:
        ExperienceProcessor instance
    """
    return ExperienceProcessor(config, output_helper)
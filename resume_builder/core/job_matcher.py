"""
Job Matcher - Main orchestrator for job-specific resume tailoring
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

from ..models.experience import Experience
from ..models.job_description import JobDescription
from ..models.match_result import RefinedExperience, JobMatchResult
from ..core.job_extractor import JobExtractor
from ..core.search_optimizer import SearchQueryOptimizer
from ..core.experience_refiner import ExperienceRefiner
from ..core.processor import ExperienceProcessor
from ..core.exceptions import (
    JobMatchingError,
    ContentExtractionError,
    DatabaseError,
    ExperienceRefinementError
)
from ..utils.logger import get_logger, ContextualLogger
from ..config.settings import Config


logger = get_logger(__name__)


class JobMatcher:
    """
    Main orchestrator for job-specific resume tailoring
    
    Coordinates the entire workflow:
    1. Extract job description from URL
    2. Generate optimized search queries
    3. Search experiences in database
    4. Refine experiences for job relevance
    5. Return ranked and tailored results
    """
    
    def __init__(self, config: Config):
        """
        Initialize JobMatcher
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = ContextualLogger(logger, {"component": "job_matcher"})
        
        # Initialize core components
        self.job_extractor = None
        self.search_optimizer = None
        self.experience_refiner = None
        self.experience_processor = None
        
        # Configuration
        self.max_experiences = config.job_matching_config.max_experiences_to_match
        self.min_relevance_score = config.job_matching_config.min_relevance_score
        self.enable_refinement = config.job_matching_config.refinement_enabled
        self.enable_caching = config.job_matching_config.enable_caching
        
        # Internal state
        self._cache = {} if self.enable_caching else None
        self._stats = {
            "jobs_processed": 0,
            "successful_matches": 0,
            "failed_matches": 0,
            "cache_hits": 0,
            "total_experiences_found": 0,
            "total_experiences_refined": 0
        }
        
        self.logger.info("JobMatcher initialized")
    
    async def initialize_components(self):
        """Initialize all components asynchronously"""
        try:
            self.logger.info("Initializing JobMatcher components")
            
            # Initialize components
            self.job_extractor = JobExtractor(self.config)
            self.search_optimizer = SearchQueryOptimizer(self.config)
            self.experience_refiner = ExperienceRefiner(self.config)
            self.experience_processor = ExperienceProcessor(self.config)
            
            self.logger.info("All JobMatcher components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize JobMatcher components: {str(e)}")
            raise JobMatchingError(f"Component initialization failed: {str(e)}") from e
    
    def match_job_from_url(
        self,
        job_url: str,
        refinement_type: str = "job_specific",
        output_format: str = "detailed"
    ) -> JobMatchResult:
        """
        Complete job matching workflow from URL
        
        Args:
            job_url: URL of job posting to analyze
            refinement_type: Type of experience refinement to apply
            output_format: Format for results ("detailed", "summary", "json")
            
        Returns:
            Complete job matching results
            
        Raises:
            JobMatchingError: If any step in the workflow fails
        """
        self.logger.info(f"Starting job matching for URL: {job_url}")
        self._stats["jobs_processed"] += 1
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(job_url, refinement_type)
            if self._cache and cache_key in self._cache:
                self.logger.info("Using cached job matching result")
                self._stats["cache_hits"] += 1
                return self._cache[cache_key]
            
            # Step 1: Extract job description
            self.logger.info("Step 1: Extracting job description")
            job_description = self._extract_job_description(job_url)
            
            # Step 2: Generate search queries
            self.logger.info("Step 2: Generating optimized search queries")
            search_queries = self._generate_search_queries(job_description)
            
            # Step 3: Search for relevant experiences
            self.logger.info("Step 3: Searching for relevant experiences")
            relevant_experiences = self._search_relevant_experiences(search_queries)
            
            # Step 4: Refine experiences for job relevance
            self.logger.info("Step 4: Refining experiences")
            refined_experiences = self._refine_experiences(
                relevant_experiences, job_description, refinement_type
            )
            
            # Step 5: Create final result
            self.logger.info("Step 5: Creating final result")
            job_match_result = self._create_job_match_result(
                job_description, refined_experiences, search_queries
            )
            
            # Cache result if enabled
            if self._cache:
                self._cache[cache_key] = job_match_result
            
            self._stats["successful_matches"] += 1
            self.logger.info(f"Job matching completed successfully: {len(refined_experiences)} experiences matched")
            
            return job_match_result
            
        except Exception as e:
            self._stats["failed_matches"] += 1
            self.logger.error(f"Job matching failed: {str(e)}")
            raise JobMatchingError(f"Job matching workflow failed: {str(e)}") from e
    
    def match_job_from_description(
        self,
        job_title: str,
        company: str,
        job_description_text: str,
        refinement_type: str = "job_specific"
    ) -> JobMatchResult:
        """
        Job matching workflow from manual job description
        
        Args:
            job_title: Position title
            company: Company name
            job_description_text: Job description content
            refinement_type: Type of experience refinement
            
        Returns:
            Complete job matching results
        """
        self.logger.info(f"Starting job matching for manual description: {job_title} at {company}")
        
        try:
            # Create job description object
            job_description = JobDescription(
                title=job_title,
                company=company,
                url="manual_input",
                summary=job_description_text,
                raw_content=job_description_text
            )
            
            # Process with OpenAI to extract skills and keywords
            job_description = self.job_extractor._enhance_with_openai(job_description)
            
            # Continue with normal workflow
            search_queries = self._generate_search_queries(job_description)
            relevant_experiences = self._search_relevant_experiences(search_queries)
            refined_experiences = self._refine_experiences(
                relevant_experiences, job_description, refinement_type
            )
            
            return self._create_job_match_result(
                job_description, refined_experiences, search_queries
            )
            
        except Exception as e:
            self.logger.error(f"Manual job matching failed: {str(e)}")
            raise JobMatchingError(f"Manual job matching failed: {str(e)}") from e
    
    def get_matching_stats(self) -> Dict:
        """Get job matching statistics"""
        total_jobs = self._stats["jobs_processed"]
        success_rate = (
            self._stats["successful_matches"] / total_jobs 
            if total_jobs > 0 else 0.0
        )
        
        return {
            **self._stats,
            "success_rate": success_rate,
            "avg_experiences_per_job": (
                self._stats["total_experiences_found"] / max(self._stats["successful_matches"], 1)
            ),
            "cache_efficiency": (
                self._stats["cache_hits"] / total_jobs if total_jobs > 0 else 0.0
            )
        }
    
    def clear_cache(self):
        """Clear the matching cache"""
        if self._cache:
            self._cache.clear()
            self.logger.info("Job matching cache cleared")
    
    def _extract_job_description(self, job_url: str) -> JobDescription:
        """Extract and parse job description from URL"""
        try:
            if not self.job_extractor:
                raise JobMatchingError("Job extractor not initialized")
            
            return self.job_extractor.extract_and_parse(job_url)
            
        except Exception as e:
            raise ContentExtractionError(f"Failed to extract job description: {str(e)}") from e
    
    def _generate_search_queries(self, job_description: JobDescription) -> List[Dict]:
        """Generate optimized search queries"""
        try:
            if not self.search_optimizer:
                raise JobMatchingError("Search optimizer not initialized")
            
            return self.search_optimizer.generate_search_queries(job_description)
            
        except Exception as e:
            self.logger.warning(f"Search query generation failed: {str(e)}")
            # Fallback to basic queries
            return [
                {
                    "query": " ".join(job_description.skills_mentioned[:5]),
                    "strategy": "fallback",
                    "priority": 1.0
                }
            ]
    
    def _search_relevant_experiences(self, search_queries: List[Dict]) -> List[Experience]:
        """Search for relevant experiences using optimized queries"""
        try:
            if not self.experience_processor:
                raise JobMatchingError("Experience processor not initialized")
            
            # Extract query strings
            query_strings = [q["query"] for q in search_queries if q.get("query")]
            
            if not query_strings:
                raise DatabaseError("No valid search queries generated")
            
            # Use multi-query search
            experiences = self.experience_processor.database.search_experiences_multi_query(
                queries=query_strings,
                limit=self.max_experiences,
                min_score=self.min_relevance_score
            )
            
            self._stats["total_experiences_found"] += len(experiences)
            self.logger.info(f"Found {len(experiences)} relevant experiences")
            
            return experiences
            
        except Exception as e:
            raise DatabaseError(f"Experience search failed: {str(e)}") from e
    
    def _refine_experiences(
        self,
        experiences: List[Experience],
        job_description: JobDescription,
        refinement_type: str
    ) -> List[RefinedExperience]:
        """Refine experiences for job relevance"""
        try:
            if not self.enable_refinement:
                # Return unrefined experiences as RefinedExperience objects
                return self._convert_to_refined_experiences(experiences, job_description)
            
            if not self.experience_refiner:
                raise JobMatchingError("Experience refiner not initialized")
            
            # Use batch refinement for efficiency
            refined_experiences = self.experience_refiner.refine_experiences_batch(
                experiences, job_description, self.max_experiences
            )
            
            # Filter by relevance score
            filtered_experiences = [
                exp for exp in refined_experiences 
                if exp.relevance_score >= self.min_relevance_score
            ]
            
            # Sort by relevance score (descending)
            filtered_experiences.sort(key=lambda x: x.relevance_score, reverse=True)
            
            self._stats["total_experiences_refined"] += len(filtered_experiences)
            self.logger.info(f"Refined {len(filtered_experiences)} experiences")
            
            return filtered_experiences
            
        except Exception as e:
            self.logger.error(f"Experience refinement failed: {str(e)}")
            # Fallback to unrefined experiences
            return self._convert_to_refined_experiences(experiences, job_description)
    
    def _convert_to_refined_experiences(
        self,
        experiences: List[Experience],
        job_description: JobDescription
    ) -> List[RefinedExperience]:
        """Convert raw experiences to RefinedExperience format without AI refinement"""
        
        refined_experiences = []
        for experience in experiences:
            # Calculate basic relevance score
            relevance_score = self._calculate_basic_relevance(experience, job_description)
            
            refined_exp = RefinedExperience(
                original_experience_id=experience.id,
                company=experience.company,
                role=experience.role,
                accomplishments=[experience.text],
                skills=experience.skills,
                tools_technologies=[],
                relevance_score=relevance_score,
                confidence_score=0.7,
                keywords_matched=[],
                refinement_notes="No AI refinement applied"
            )
            refined_experiences.append(refined_exp)
        
        return refined_experiences
    
    def _calculate_basic_relevance(
        self,
        experience: Experience,
        job_description: JobDescription
    ) -> float:
        """Calculate basic relevance score without AI"""
        
        # Simple keyword matching
        exp_text = experience.text.lower()
        job_keywords = [kw.lower() for kw in job_description.skills_mentioned + job_description.extracted_keywords]
        
        matches = sum(1 for keyword in job_keywords if keyword in exp_text)
        relevance_score = matches / max(len(job_keywords), 1) if job_keywords else 0.0
        
        return min(relevance_score, 1.0)
    
    def _create_job_match_result(
        self,
        job_description: JobDescription,
        refined_experiences: List[RefinedExperience],
        search_queries: List[Dict]
    ) -> JobMatchResult:
        """Create final job match result"""
        
        try:
            # Aggregate all skills and tools
            all_skills = set()
            all_tools = set()
            
            for exp in refined_experiences:
                all_skills.update(exp.skills)
                all_tools.update(exp.tools_technologies)
            
            # Calculate overall match confidence
            if refined_experiences:
                avg_relevance = sum(exp.relevance_score for exp in refined_experiences) / len(refined_experiences)
                avg_confidence = sum(exp.confidence_score for exp in refined_experiences) / len(refined_experiences)
                overall_confidence = (avg_relevance + avg_confidence) / 2
            else:
                overall_confidence = 0.0
            
            return JobMatchResult(
                job_description=job_description,
                refined_experiences=refined_experiences,
                aggregated_skills=list(all_skills),
                aggregated_tools=list(all_tools),
                overall_match_score=overall_confidence,
                search_queries_used=[q.get("query", "") for q in search_queries],
                matching_summary={
                    "total_experiences_found": len(refined_experiences),
                    "avg_relevance_score": avg_relevance if refined_experiences else 0.0,
                    "top_skills": list(all_skills)[:10],
                    "search_strategies_used": list(set(q.get("strategy", "unknown") for q in search_queries))
                }
            )
            
        except Exception as e:
            raise JobMatchingError(f"Failed to create job match result: {str(e)}") from e
    
    def _generate_cache_key(self, job_url: str, refinement_type: str) -> str:
        """Generate cache key for job matching result"""
        return f"{hash(job_url)}_{refinement_type}_{self.max_experiences}_{self.min_relevance_score}"


def create_job_matcher(config: Config) -> JobMatcher:
    """
    Factory function to create JobMatcher instance
    
    Args:
        config: Application configuration
        
    Returns:
        Configured JobMatcher instance
    """
    try:
        matcher = JobMatcher(config)
        logger.info("JobMatcher created successfully")
        return matcher
        
    except Exception as e:
        logger.error(f"Failed to create JobMatcher: {str(e)}")
        raise JobMatchingError(f"Failed to create JobMatcher: {str(e)}") from e 
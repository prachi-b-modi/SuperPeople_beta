"""
AI-powered experience refinement for job-specific resume tailoring
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import asdict

from ..models.experience import Experience
from ..models.job_description import JobDescription
from ..models.match_result import RefinedExperience, JobMatchResult
from ..core.extractor import ExperienceExtractor
from ..core.prompts import PromptBuilder, PromptOptimizer, get_specialized_prompt
from ..core.exceptions import (
    ExperienceRefinementError,
    OpenAIIntegrationError,
    ValidationError
)
from ..utils.logger import get_logger, ContextualLogger
from ..config.settings import Config


logger = get_logger(__name__)


class ExperienceRefiner:
    """
    AI-powered experience refinement engine
    
    Transforms raw professional experiences into polished, job-tailored
    resume accomplishments using OpenAI and sophisticated prompt engineering.
    """
    
    def __init__(self, config: Config):
        """
        Initialize ExperienceRefiner
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = ContextualLogger(logger, {"component": "experience_refiner"})
        
        # Initialize OpenAI extractor for AI processing
        self.openai_extractor = ExperienceExtractor(config.openai_config)
        
        # Initialize prompt building components
        self.prompt_builder = PromptBuilder()
        self.prompt_optimizer = PromptOptimizer()
        
        # Configuration
        self.max_retries = config.app_config.retry_attempts
        self.enable_caching = config.job_matching_config.enable_caching
        
        # Internal state
        self._cache = {} if self.enable_caching else None
        self._stats = {
            "experiences_refined": 0,
            "successful_refinements": 0,
            "failed_refinements": 0,
            "cache_hits": 0
        }
        
        self.logger.info("ExperienceRefiner initialized")
    
    def refine_experience(
        self,
        experience: Experience,
        job_context: Optional[JobDescription] = None,
        refinement_type: str = "general",
        specialization: Optional[str] = None
    ) -> RefinedExperience:
        """
        Refine a single experience for job-specific tailoring
        
        Args:
            experience: Raw experience to refine
            job_context: Target job description for tailoring
            refinement_type: Type of refinement ("general", "job_specific", "skills_focused")
            specialization: Role specialization ("technical_role", "management_role", etc.)
            
        Returns:
            Refined experience with polished accomplishments
            
        Raises:
            ExperienceRefinementError: If refinement fails
        """
        self.logger.info(f"Refining experience for {experience.company}")
        self._stats["experiences_refined"] += 1
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(experience, job_context, refinement_type)
            if self._cache and cache_key in self._cache:
                self.logger.info("Using cached refinement result")
                self._stats["cache_hits"] += 1
                return self._cache[cache_key]
            
            # Build appropriate prompt
            prompt = self._build_refinement_prompt(
                experience, job_context, refinement_type, specialization
            )
            
            # Get AI refinement
            refinement_result = self._call_openai_refinement(prompt)
            
            # Parse and validate result
            refined_experience = self._parse_refinement_result(
                experience, refinement_result, job_context
            )
            
            # Cache result if enabled
            if self._cache:
                self._cache[cache_key] = refined_experience
            
            self._stats["successful_refinements"] += 1
            self.logger.info(f"Successfully refined experience: {len(refined_experience.accomplishments)} accomplishments")
            
            return refined_experience
            
        except Exception as e:
            self._stats["failed_refinements"] += 1
            self.logger.error(f"Failed to refine experience: {str(e)}")
            raise ExperienceRefinementError(f"Experience refinement failed: {str(e)}") from e
    
    def refine_experiences_batch(
        self,
        experiences: List[Experience],
        job_context: Optional[JobDescription] = None,
        max_experiences: int = 10
    ) -> List[RefinedExperience]:
        """
        Refine multiple experiences in batch for efficiency
        
        Args:
            experiences: List of experiences to refine
            job_context: Target job description for tailoring
            max_experiences: Maximum number of experiences to process
            
        Returns:
            List of refined experiences
        """
        self.logger.info(f"Batch refining {len(experiences)} experiences")
        
        # Limit to max experiences
        experiences_to_process = experiences[:max_experiences]
        
        try:
            # Build batch prompt
            prompt = self.prompt_builder.build_batch_refinement_prompt(
                experiences_to_process, job_context
            )
            
            # Optimize prompt for token limits
            prompt = self.prompt_optimizer.optimize_for_tokens(prompt, max_tokens=3500)
            
            # Get AI batch refinement
            batch_result = self._call_openai_refinement(prompt)
            
            # Parse batch results
            refined_experiences = self._parse_batch_refinement_result(
                experiences_to_process, batch_result, job_context
            )
            
            self.logger.info(f"Successfully batch refined {len(refined_experiences)} experiences")
            return refined_experiences
            
        except Exception as e:
            self.logger.error(f"Batch refinement failed: {str(e)}")
            # Fallback to individual refinement
            return self._fallback_individual_refinement(experiences_to_process, job_context)
    
    def extract_skills_and_tools(
        self,
        experience: Experience,
        enhanced_extraction: bool = True
    ) -> Dict[str, List[str]]:
        """
        Extract skills and tools from an experience
        
        Args:
            experience: Experience to analyze
            enhanced_extraction: Use AI for enhanced extraction
            
        Returns:
            Dictionary with categorized skills and tools
        """
        self.logger.info(f"Extracting skills from {experience.company} experience")
        
        try:
            if enhanced_extraction:
                # Use AI for comprehensive skill extraction
                prompt = self.prompt_builder.build_skills_extraction_prompt(experience)
                result = self._call_openai_refinement(prompt)
                
                return {
                    "technical_skills": result.get("technical_skills", []),
                    "soft_skills": result.get("soft_skills", []),
                    "tools_technologies": result.get("tools_technologies", []),
                    "certifications": result.get("certifications", []),
                    "methodologies": result.get("methodologies", [])
                }
            else:
                # Use basic extraction from existing experience data
                return {
                    "technical_skills": [s for s in experience.skills if self._is_technical_skill(s)],
                    "soft_skills": [s for s in experience.skills if not self._is_technical_skill(s)],
                    "tools_technologies": [],
                    "certifications": [],
                    "methodologies": []
                }
                
        except Exception as e:
            self.logger.error(f"Skill extraction failed: {str(e)}")
            return {
                "technical_skills": [],
                "soft_skills": [],
                "tools_technologies": [],
                "certifications": [],
                "methodologies": []
            }
    
    def calculate_relevance_score(
        self,
        experience: Experience,
        job_context: JobDescription
    ) -> float:
        """
        Calculate relevance score between experience and job
        
        Args:
            experience: Experience to score
            job_context: Target job description
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        try:
            # Calculate skill overlap
            exp_skills = set(s.lower() for s in experience.skills)
            job_skills = set(s.lower() for s in job_context.skills_mentioned)
            
            skill_overlap = len(exp_skills.intersection(job_skills))
            skill_score = skill_overlap / max(len(job_skills), 1) if job_skills else 0.0
            
            # Calculate keyword overlap
            exp_text = experience.text.lower()
            keyword_matches = sum(1 for keyword in job_context.extracted_keywords 
                                if keyword.lower() in exp_text)
            keyword_score = keyword_matches / max(len(job_context.extracted_keywords), 1)
            
            # Calculate category relevance
            exp_categories = set(c.lower() for c in experience.categories)
            job_categories = set(c.lower() for c in job_context.categories)
            category_overlap = len(exp_categories.intersection(job_categories))
            category_score = category_overlap / max(len(job_categories), 1) if job_categories else 0.0
            
            # Weighted combination
            relevance_score = (
                skill_score * 0.5 +
                keyword_score * 0.3 +
                category_score * 0.2
            )
            
            return min(relevance_score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Relevance calculation failed: {str(e)}")
            return 0.0
    
    def get_refinement_stats(self) -> Dict[str, Union[int, float]]:
        """Get refinement statistics"""
        total_attempts = self._stats["experiences_refined"]
        success_rate = (
            self._stats["successful_refinements"] / total_attempts 
            if total_attempts > 0 else 0.0
        )
        
        return {
            **self._stats,
            "success_rate": success_rate,
            "cache_efficiency": self._stats["cache_hits"] / total_attempts if total_attempts > 0 else 0.0
        }
    
    def _build_refinement_prompt(
        self,
        experience: Experience,
        job_context: Optional[JobDescription],
        refinement_type: str,
        specialization: Optional[str]
    ) -> str:
        """Build appropriate prompt for refinement"""
        
        # Build base prompt
        prompt = self.prompt_builder.build_experience_refinement_prompt(
            experience, refinement_type, job_context
        )
        
        # Add specialization if specified
        if specialization:
            prompt = get_specialized_prompt(prompt, specialization)
        
        # Optimize for token limits
        prompt = self.prompt_optimizer.optimize_for_tokens(prompt)
        
        # Validate prompt structure
        validation = self.prompt_optimizer.validate_prompt_structure(prompt)
        if not all(validation.values()):
            self.logger.warning(f"Prompt validation issues: {validation}")
        
        return prompt
    
    def _call_openai_refinement(self, prompt: str) -> Dict:
        """Call OpenAI API for refinement with retry logic"""
        
        for attempt in range(self.max_retries):
            try:
                # Use the extract_information method which returns structured data
                # For refinement, we'll use it as a general text processor
                response = self.openai_extractor.extract_information(prompt)
                
                # If response is already structured, return it
                if isinstance(response, dict):
                    return response
                
                # Otherwise try to parse as JSON
                if isinstance(response, str):
                    try:
                        return json.loads(response)
                    except json.JSONDecodeError:
                        # If not JSON, create a structured response
                        return {
                            "refined_accomplishments": [response],
                            "key_skills": [],
                            "tools_technologies": [],
                            "confidence_score": 0.8
                        }
                
                return response
                
            except Exception as e:
                self.logger.warning(f"OpenAI call attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise OpenAIIntegrationError(f"All OpenAI attempts failed: {str(e)}")
        
        raise OpenAIIntegrationError("Maximum retries exceeded")
    
    def _parse_refinement_result(
        self,
        original_experience: Experience,
        ai_result: Dict,
        job_context: Optional[JobDescription]
    ) -> RefinedExperience:
        """Parse AI refinement result into structured format"""
        
        try:
            # Extract accomplishments
            accomplishments = ai_result.get("refined_accomplishments", [])
            if not accomplishments:
                accomplishments = ai_result.get("tailored_accomplishments", [])
            if not accomplishments:
                # Fallback to original text
                accomplishments = [original_experience.text]
            
            # Extract skills
            skills = []
            skills.extend(ai_result.get("key_skills", []))
            skills.extend(ai_result.get("relevant_skills", []))
            skills.extend(ai_result.get("technical_skills", []))
            skills.extend(ai_result.get("soft_skills", []))
            
            # Remove duplicates while preserving order
            skills = list(dict.fromkeys(skills))
            
            # Extract tools and technologies
            tools = ai_result.get("tools_technologies", [])
            
            # Calculate relevance score
            relevance_score = ai_result.get("relevance_score", 0.0)
            if relevance_score == 0.0 and job_context:
                relevance_score = self.calculate_relevance_score(original_experience, job_context)
            
            # Extract keywords
            keywords = ai_result.get("matching_keywords", [])
            keywords.extend(ai_result.get("extracted_keywords", []))
            keywords = list(dict.fromkeys(keywords))  # Remove duplicates
            
            return RefinedExperience(
                original_experience_id=original_experience.id,
                company=original_experience.company,
                role=original_experience.role,
                accomplishments=accomplishments,
                skills=skills,
                tools_technologies=tools,
                relevance_score=relevance_score,
                confidence_score=ai_result.get("confidence_score", 0.8),
                keywords_matched=keywords,
                refinement_notes=ai_result.get("tailoring_notes", "")
            )
            
        except Exception as e:
            raise ValidationError(f"Failed to parse refinement result: {str(e)}")
    
    def _parse_batch_refinement_result(
        self,
        original_experiences: List[Experience],
        ai_result: Dict,
        job_context: Optional[JobDescription]
    ) -> List[RefinedExperience]:
        """Parse batch AI refinement result"""
        
        try:
            refined_experiences = []
            batch_results = ai_result.get("refined_experiences", [])
            
            for i, original_exp in enumerate(original_experiences):
                # Find corresponding result
                result = None
                for batch_result in batch_results:
                    if batch_result.get("original_index") == i:
                        result = batch_result
                        break
                
                if not result:
                    # Fallback for missing results
                    result = {
                        "refined_accomplishments": [original_exp.text],
                        "key_skills": original_exp.skills,
                        "relevance_score": 0.5
                    }
                
                # Convert to RefinedExperience
                refined_exp = self._parse_refinement_result(original_exp, result, job_context)
                refined_experiences.append(refined_exp)
            
            return refined_experiences
            
        except Exception as e:
            raise ValidationError(f"Failed to parse batch refinement result: {str(e)}")
    
    def _fallback_individual_refinement(
        self,
        experiences: List[Experience],
        job_context: Optional[JobDescription]
    ) -> List[RefinedExperience]:
        """Fallback to individual refinement if batch fails"""
        
        self.logger.info("Falling back to individual refinement")
        refined_experiences = []
        
        for experience in experiences:
            try:
                refined_exp = self.refine_experience(experience, job_context)
                refined_experiences.append(refined_exp)
            except Exception as e:
                self.logger.error(f"Individual refinement failed for {experience.company}: {str(e)}")
                # Create minimal refined experience
                refined_exp = RefinedExperience(
                    original_experience_id=experience.id,
                    company=experience.company,
                    role=experience.role,
                    accomplishments=[experience.text],
                    skills=experience.skills,
                    tools_technologies=[],
                    relevance_score=0.0,
                    confidence_score=0.5,
                    keywords_matched=[],
                    refinement_notes="Fallback processing"
                )
                refined_experiences.append(refined_exp)
        
        return refined_experiences
    
    def _generate_cache_key(
        self,
        experience: Experience,
        job_context: Optional[JobDescription],
        refinement_type: str
    ) -> str:
        """Generate cache key for refinement result"""
        
        job_key = ""
        if job_context:
            job_key = f"{job_context.title}_{job_context.company}_{hash(str(job_context.skills_mentioned))}"
        
        exp_key = f"{experience.company}_{hash(experience.text)}"
        
        return f"{exp_key}_{job_key}_{refinement_type}"
    
    def _is_technical_skill(self, skill: str) -> bool:
        """Determine if a skill is technical or soft skill"""
        
        technical_indicators = [
            "python", "java", "javascript", "docker", "kubernetes", "aws", "git",
            "sql", "nosql", "api", "rest", "microservices", "cloud", "linux",
            "react", "angular", "vue", "node", "express", "django", "flask",
            "machine learning", "ai", "data science", "analytics", "etl"
        ]
        
        skill_lower = skill.lower()
        return any(indicator in skill_lower for indicator in technical_indicators)


def create_experience_refiner(config: Config) -> ExperienceRefiner:
    """
    Factory function to create ExperienceRefiner instance
    
    Args:
        config: Application configuration
        
    Returns:
        Configured ExperienceRefiner instance
    """
    try:
        refiner = ExperienceRefiner(config)
        logger.info("ExperienceRefiner created successfully")
        return refiner
        
    except Exception as e:
        logger.error(f"Failed to create ExperienceRefiner: {str(e)}")
        raise ExperienceRefinementError(f"Failed to create ExperienceRefiner: {str(e)}") from e 
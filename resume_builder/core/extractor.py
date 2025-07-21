"""
OpenAI integration for extracting information from professional experience text
"""

import json
import time
from typing import Dict, List, Any, Optional
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config.settings import OpenAIConfig
from ..core.exceptions import (
    OpenAIAPIError, 
    OpenAIRateLimitError, 
    OpenAIExtractionError,
    RetryExhaustedError
)
from ..utils.logger import get_logger
from ..utils.helpers import safe_json_loads, normalize_text

logger = get_logger(__name__)


class ExperienceExtractor:
    """
    Extracts structured information from professional experience text using OpenAI
    """
    
    def __init__(self, config: OpenAIConfig):
        """
        Initialize the experience extractor
        
        Args:
            config: OpenAI configuration
        """
        self.config = config
        self.client = OpenAI(api_key=config.api_key)
        self.model = config.model
        self.temperature = config.extraction_temperature
        self.max_retries = config.max_retries
        self.timeout = config.timeout
        
        logger.info(f"Initialized ExperienceExtractor with model: {self.model}")
    
    def extract_information(self, text: str) -> Dict[str, List[str]]:
        """
        Extract skills, categories, and relevant jobs from experience text
        
        Args:
            text: Professional experience description
            
        Returns:
            Dictionary containing extracted information with keys:
            - skills: List of extracted skills
            - categories: List of professional categories
            - relevant_jobs: List of relevant job titles
            
        Raises:
            OpenAIExtractionError: If extraction fails or returns invalid data
            OpenAIAPIError: If API call fails
            RetryExhaustedError: If all retry attempts are exhausted
        """
        text = normalize_text(text)
        
        if len(text) < 10:
            raise OpenAIExtractionError("Text too short for meaningful extraction")
        
        logger.info(f"Extracting information from text ({len(text)} characters)")
        
        try:
            result = self._extract_with_retry(text)
            validated_result = self._validate_extraction_result(result)
            
            logger.info(
                f"Successfully extracted: {len(validated_result['skills'])} skills, "
                f"{len(validated_result['categories'])} categories, "
                f"{len(validated_result['relevant_jobs'])} relevant jobs"
            )
            
            return validated_result
            
        except Exception as e:
            logger.error(f"Failed to extract information: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OpenAIAPIError, OpenAIRateLimitError))
    )
    def _extract_with_retry(self, text: str) -> Dict[str, List[str]]:
        """
        Extract information with retry logic
        
        Args:
            text: Text to extract from
            
        Returns:
            Extracted information dictionary
        """
        try:
            prompt = self._build_extraction_prompt(text)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature,
                timeout=self.timeout
            )
            
            content = response.choices[0].message.content
            if not content:
                raise OpenAIExtractionError("Empty response from OpenAI")
            
            result = safe_json_loads(content)
            if result is None:
                raise OpenAIExtractionError("Invalid JSON response from OpenAI")
            
            return result
            
        except Exception as e:
            if "rate_limit" in str(e).lower():
                logger.warning("Rate limit encountered, will retry")
                raise OpenAIRateLimitError(f"Rate limit exceeded: {str(e)}")
            elif "api" in str(e).lower() or "timeout" in str(e).lower():
                logger.warning(f"API error encountered: {str(e)}")
                raise OpenAIAPIError(f"OpenAI API error: {str(e)}")
            else:
                logger.error(f"Unexpected error during extraction: {str(e)}")
                raise OpenAIExtractionError(f"Extraction failed: {str(e)}")
    
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for extraction
        
        Returns:
            System prompt string
        """
        return """You are an expert at analyzing professional experience descriptions and extracting structured information. 

Your task is to extract:
1. **Skills**: Both technical skills (programming languages, tools, frameworks, etc.) and soft skills (leadership, communication, etc.)
2. **Categories**: Professional domains, industries, or functional areas (e.g., "Software Development", "Project Management", "Data Analysis")
3. **Relevant Jobs**: Job titles or roles that would highly value this specific experience

Guidelines:
- Be comprehensive but precise
- Include both explicit and implicit skills
- Focus on transferable skills and experiences
- Use standard industry terminology
- Avoid overly generic terms
- Each list should have 3-10 items maximum

Always respond with valid JSON in the exact format requested."""
    
    def _build_extraction_prompt(self, text: str) -> str:
        """
        Build the extraction prompt for the given text
        
        Args:
            text: Experience text to analyze
            
        Returns:
            Formatted prompt string
        """
        return f"""Analyze this professional experience and extract structured information:

EXPERIENCE TEXT:
{text}

Extract the following information and return as JSON:

{{
    "skills": ["skill1", "skill2", "skill3", ...],
    "categories": ["category1", "category2", "category3", ...],
    "relevant_jobs": ["job_title1", "job_title2", "job_title3", ...]
}}

Requirements:
- Skills: Include both technical and soft skills demonstrated or used
- Categories: Professional domains, industries, or functional areas this experience relates to
- Relevant Jobs: Specific job titles that would value this experience highly

Ensure the JSON is valid and properly formatted."""
    
    def _validate_extraction_result(self, result: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate and clean the extraction result
        
        Args:
            result: Raw extraction result
            
        Returns:
            Validated and cleaned result
            
        Raises:
            OpenAIExtractionError: If result is invalid
        """
        if not isinstance(result, dict):
            raise OpenAIExtractionError("Extraction result must be a dictionary")
        
        required_keys = ["skills", "categories", "relevant_jobs"]
        for key in required_keys:
            if key not in result:
                raise OpenAIExtractionError(f"Missing required key: {key}")
        
        validated_result = {}
        
        for key in required_keys:
            value = result[key]
            
            # Ensure it's a list
            if not isinstance(value, list):
                if isinstance(value, str):
                    # Try to split string by common delimiters
                    value = [item.strip() for item in value.replace(',', '\n').split('\n') if item.strip()]
                else:
                    logger.warning(f"Invalid type for {key}: {type(value)}, setting to empty list")
                    value = []
            
            # Clean and normalize items
            cleaned_items = []
            for item in value:
                if isinstance(item, str):
                    item = normalize_text(item)
                    if item and len(item) > 1:  # Skip very short items
                        cleaned_items.append(item)
                else:
                    logger.warning(f"Non-string item in {key}: {item}")
            
            # Limit to reasonable number of items
            max_items = 15
            if len(cleaned_items) > max_items:
                logger.warning(f"Too many {key} ({len(cleaned_items)}), limiting to {max_items}")
                cleaned_items = cleaned_items[:max_items]
            
            validated_result[key] = cleaned_items
        
        # Log validation results
        total_items = sum(len(items) for items in validated_result.values())
        if total_items == 0:
            logger.warning("No valid items extracted from text")
        
        return validated_result
    
    def extract_batch(self, texts: List[str]) -> List[Dict[str, List[str]]]:
        """
        Extract information from multiple texts
        
        Args:
            texts: List of experience texts
            
        Returns:
            List of extraction results
        """
        results = []
        
        for i, text in enumerate(texts):
            try:
                result = self.extract_information(text)
                results.append(result)
                
                # Small delay to respect rate limits
                if i < len(texts) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Failed to extract from text {i + 1}: {str(e)}")
                # Return empty result for failed extractions
                results.append({
                    "skills": [],
                    "categories": [],
                    "relevant_jobs": []
                })
        
        return results
    
    def test_connection(self) -> bool:
        """
        Test the OpenAI API connection
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            test_text = "Software engineer with Python experience"
            self.extract_information(test_text)
            logger.info("OpenAI connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {str(e)}")
            return False
    
    def get_extraction_stats(self, text: str) -> Dict[str, Any]:
        """
        Get statistics about what would be extracted without making API call
        
        Args:
            text: Text to analyze
            
        Returns:
            Statistics dictionary
        """
        text = normalize_text(text)
        
        return {
            "text_length": len(text),
            "word_count": len(text.split()),
            "estimated_tokens": len(text) // 4,  # Rough estimate
            "has_technical_terms": any(term in text.lower() for term in [
                "python", "javascript", "sql", "api", "database", "framework",
                "programming", "development", "software", "system", "code"
            ]),
            "has_management_terms": any(term in text.lower() for term in [
                "team", "lead", "manage", "project", "coordinate", "organize",
                "strategy", "planning", "budget", "stakeholder"
            ])
        }


def create_extractor(config: OpenAIConfig) -> ExperienceExtractor:
    """
    Factory function to create an experience extractor
    
    Args:
        config: OpenAI configuration
        
    Returns:
        ExperienceExtractor instance
    """
    return ExperienceExtractor(config) 
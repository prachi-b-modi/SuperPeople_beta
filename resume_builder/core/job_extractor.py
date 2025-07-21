"""
Job content extractor using Exa.ai for Resume Builder CLI
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

from ..models.job_description import JobDescription
from ..utils.exa_client import ExaClient, create_exa_client
from ..core.extractor import ExperienceExtractor
from ..config.settings import Config
from ..core.exceptions import (
    JobExtractionError,
    ExaContentExtractionError,
    OpenAIExtractionError,
    URLValidationError
)
from ..utils.logger import get_logger, ContextualLogger

logger = get_logger(__name__)


class JobExtractor:
    """
    Extract and parse job description content using Exa.ai
    
    This class handles the complete workflow of extracting job postings
    from URLs, parsing the content, and structuring it into JobDescription objects.
    """
    
    def __init__(self, config: Config):
        """
        Initialize job extractor
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = ContextualLogger(logger, {"component": "job_extractor"})
        
        # Initialize Exa client
        if not config.exa_config:
            raise JobExtractionError("Exa.ai configuration is required for job extraction")
        
        self.exa_client = create_exa_client(config.exa_config)
        
        # Initialize OpenAI extractor for parsing job requirements
        self.openai_extractor = ExperienceExtractor(config.openai_config)
        
        self.logger.info("JobExtractor initialized")
    
    def extract_job_description(self, url: str) -> JobDescription:
        """
        Extract complete job description from URL
        
        Args:
            url: Job posting URL
            
        Returns:
            Structured JobDescription object
            
        Raises:
            JobExtractionError: If extraction fails
        """
        self.logger.info(f"Extracting job description from: {url}")
        
        try:
            # Step 1: Extract raw content using Exa.ai
            raw_content = self.exa_client.extract_content(url)
            
            # Step 2: Parse and structure the content
            job_data = self._parse_job_content(raw_content)
            
            # Step 3: Enhance with OpenAI parsing
            enhanced_data = self._enhance_with_openai(job_data)
            
            # Step 4: Create JobDescription object
            job_description = JobDescription(
                url=enhanced_data['url'],
                title=enhanced_data['title'],
                company=enhanced_data['company'],
                full_text=enhanced_data['full_text'],
                requirements=enhanced_data.get('requirements', []),
                skills_mentioned=enhanced_data.get('skills_mentioned', []),
                responsibilities=enhanced_data.get('responsibilities', []),
                extracted_keywords=enhanced_data.get('extracted_keywords', []),
                summary=enhanced_data.get('summary', '')
            )
            
            self.logger.info(f"Successfully extracted job: {job_description.title} at {job_description.company}")
            return job_description
            
        except ExaContentExtractionError as e:
            self.logger.error(f"Failed to extract content from URL: {e}")
            raise JobExtractionError(f"Content extraction failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during job extraction: {e}")
            raise JobExtractionError(f"Job extraction failed: {e}")
    
    def _parse_job_content(self, raw_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw content from Exa.ai into structured job data
        
        Args:
            raw_content: Raw content from Exa.ai
            
        Returns:
            Parsed job data dictionary
        """
        self.logger.debug("Parsing job content from Exa.ai response")
        
        # Extract basic information
        title = self._extract_job_title(raw_content)
        company = self._extract_company_name(raw_content)
        full_text = raw_content.get('text', '')
        summary = raw_content.get('summary', '')
        
        # Combine text sources for analysis
        combined_text = self._combine_text_sources(raw_content)
        
        # Parse sections using pattern matching
        requirements = self._extract_requirements(combined_text)
        responsibilities = self._extract_responsibilities(combined_text)
        skills = self._extract_skills_mentioned(combined_text)
        keywords = self._extract_technical_keywords(combined_text)
        
        return {
            'url': raw_content['url'],
            'title': title,
            'company': company,
            'full_text': full_text,
            'summary': summary,
            'requirements': requirements,
            'responsibilities': responsibilities,
            'skills_mentioned': skills,
            'extracted_keywords': keywords,
            'raw_content': raw_content
        }
    
    def _extract_job_title(self, raw_content: Dict[str, Any]) -> str:
        """Extract job title from content"""
        # Try title from Exa.ai first
        title = raw_content.get('title', '').strip()
        
        if title and not self._is_generic_title(title):
            return self._clean_job_title(title)
        
        # Fall back to parsing from text
        text = raw_content.get('text', '')
        
        # Look for common job title patterns
        title_patterns = [
            r'(?:Job Title|Position|Role):\s*([^\n]+)',
            r'<h1[^>]*>([^<]+)</h1>',
            r'^([^-\n]+)(?:\s*-\s*[^-\n]+)?$',  # First line pattern
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                candidate = match.group(1).strip()
                if candidate and not self._is_generic_title(candidate):
                    return self._clean_job_title(candidate)
        
        return "Unknown Position"
    
    def _extract_company_name(self, raw_content: Dict[str, Any]) -> str:
        """Extract company name from content"""
        text = raw_content.get('text', '')
        domain = raw_content.get('domain', '')
        
        # Try to extract from domain first
        if domain:
            company_from_domain = self._company_from_domain(domain)
            if company_from_domain:
                return company_from_domain
        
        # Look for company name patterns in text
        company_patterns = [
            r'(?:Company|Organization|Employer):\s*([^\n]+)',
            r'(?:at|@)\s+([A-Z][^,\n.]+?)(?:\s+is|\s+seeks|\s*,)',
            r'([A-Z][^,\n.]+?)(?:\s+is\s+(?:seeking|looking|hiring))',
            r'Join\s+([A-Z][^,\n.]+?)(?:\s+as|\s+in|\s*,)',
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if self._is_valid_company_name(candidate):
                    return self._clean_company_name(candidate)
        
        # Fall back to domain-based extraction
        if domain:
            return self._company_from_domain(domain) or "Unknown Company"
        
        return "Unknown Company"
    
    def _combine_text_sources(self, raw_content: Dict[str, Any]) -> str:
        """Combine all text sources for comprehensive analysis"""
        sources = [
            raw_content.get('text', ''),
            raw_content.get('summary', ''),
            ' '.join(raw_content.get('highlights', []))
        ]
        
        return '\n\n'.join(filter(None, sources))
    
    def _extract_requirements(self, text: str) -> List[str]:
        """Extract job requirements from text"""
        requirements = []
        
        # Look for requirements sections
        req_patterns = [
            r'(?:Requirements?|Qualifications?|What (?:we\'re|you\'ll) (?:looking for|need)|Must (?:have|haves?))[:\-]?\s*\n?((?:(?:\s*[•\-\*]\s*|\s*\d+[\.\)]\s*|\s*[a-z]\)\s*)[^\n]+\n?)+)',
            r'(?:Required?|Essential)[:\-]?\s*\n?((?:(?:\s*[•\-\*]\s*|\s*\d+[\.\)]\s*|\s*[a-z]\)\s*)[^\n]+\n?)+)',
            r'(?:You should have|You must have|You need)[:\-]?\s*\n?((?:(?:\s*[•\-\*]\s*|\s*\d+[\.\)]\s*|\s*[a-z]\)\s*)[^\n]+\n?)+)'
        ]
        
        for pattern in req_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                req_text = match.group(1)
                parsed_reqs = self._parse_bullet_points(req_text)
                requirements.extend(parsed_reqs)
        
        return self._clean_and_deduplicate(requirements)[:10]  # Limit to top 10
    
    def _extract_responsibilities(self, text: str) -> List[str]:
        """Extract job responsibilities from text"""
        responsibilities = []
        
        # Look for responsibility sections
        resp_patterns = [
            r'(?:Responsibilities?|Duties|What (?:you\'ll|we\'ll) do|Your role)[:\-]?\s*\n?((?:(?:\s*[•\-\*]\s*|\s*\d+[\.\)]\s*|\s*[a-z]\)\s*)[^\n]+\n?)+)',
            r'(?:You will|You\'ll)[:\-]?\s*\n?((?:(?:\s*[•\-\*]\s*|\s*\d+[\.\)]\s*|\s*[a-z]\)\s*)[^\n]+\n?)+)',
            r'(?:Day[- ]to[- ]day|Daily)[:\-]?\s*\n?((?:(?:\s*[•\-\*]\s*|\s*\d+[\.\)]\s*|\s*[a-z]\)\s*)[^\n]+\n?)+)'
        ]
        
        for pattern in resp_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                resp_text = match.group(1)
                parsed_resps = self._parse_bullet_points(resp_text)
                responsibilities.extend(parsed_resps)
        
        return self._clean_and_deduplicate(responsibilities)[:10]  # Limit to top 10
    
    def _extract_skills_mentioned(self, text: str) -> List[str]:
        """Extract technical skills mentioned in text"""
        # Common technical skills database
        tech_skills = {
            # Programming Languages
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
            'php', 'ruby', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'sql',
            
            # Web Technologies
            'react', 'angular', 'vue', 'html', 'css', 'node.js', 'express',
            'django', 'flask', 'spring', 'laravel', 'rails',
            
            # Databases
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'cassandra', 'dynamodb', 'sqlite',
            
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
            'jenkins', 'gitlab', 'github', 'ci/cd', 'devops',
            
            # Data & Analytics
            'pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn',
            'spark', 'hadoop', 'tableau', 'power bi', 'looker',
            
            # Other Technologies
            'git', 'linux', 'unix', 'api', 'rest', 'graphql', 'microservices',
            'machine learning', 'artificial intelligence', 'blockchain'
        }
        
        found_skills = []
        text_lower = text.lower()
        
        # Find exact matches
        for skill in tech_skills:
            if skill in text_lower:
                found_skills.append(skill)
        
        # Find acronyms and capitalized terms
        acronym_pattern = r'\b[A-Z]{2,}\b'
        acronyms = re.findall(acronym_pattern, text)
        found_skills.extend([a.lower() for a in acronyms if len(a) <= 6])
        
        # Find technology patterns
        tech_patterns = [
            r'\b\w+\.js\b',  # JavaScript frameworks
            r'\b\w+SQL\b',   # SQL variants
            r'\b\w+DB\b',    # Database variants
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_skills.extend([m.lower() for m in matches])
        
        return self._clean_and_deduplicate(found_skills)[:15]  # Limit to top 15
    
    def _extract_technical_keywords(self, text: str) -> List[str]:
        """Extract technical keywords and key phrases"""
        keywords = []
        
        # Technical keyword patterns
        patterns = [
            r'\b(?:experience|expertise|knowledge|proficiency|familiarity)\s+(?:with|in)\s+([^,\n.]+)',
            r'\b(?:skilled|proficient|expert)\s+(?:in|with)\s+([^,\n.]+)',
            r'\b(?:using|leveraging|implementing|working\s+with)\s+([^,\n.]+)',
            r'\b(?:minimum|at\s+least)\s+(\d+\+?\s+years?\s+[^,\n.]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cleaned = re.sub(r'\s+', ' ', match.strip())
                if len(cleaned) > 3 and len(cleaned) < 50:
                    keywords.append(cleaned)
        
        return self._clean_and_deduplicate(keywords)[:10]  # Limit to top 10
    
    def _enhance_with_openai(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance job data using OpenAI for better parsing
        
        Args:
            job_data: Parsed job data
            
        Returns:
            Enhanced job data with OpenAI improvements
        """
        if not self.config.job_matching_config.refinement_enabled:
            self.logger.debug("OpenAI enhancement disabled in configuration")
            return job_data
        
        try:
            # Create prompt for job parsing
            prompt = self._create_job_parsing_prompt(job_data)
            
            # Get OpenAI analysis using a simple text extraction approach
            enhanced_text = f"{job_data['title']} at {job_data['company']}. {job_data['summary'][:1000]}"
            openai_response = self.openai_extractor.extract_information(enhanced_text)
            
            # Parse OpenAI response - extract_information returns skills/categories format
            enhancement = {
                'skills_mentioned': openai_response.get('skills', []),
                'extracted_keywords': openai_response.get('categories', [])
            }
            
            # Merge with existing data
            enhanced_data = job_data.copy()
            enhanced_data.update(enhancement)
            
            self.logger.debug("Successfully enhanced job data with OpenAI")
            return enhanced_data
            
        except OpenAIExtractionError as e:
            self.logger.warning(f"OpenAI enhancement failed: {e}")
            return job_data  # Return original data if enhancement fails
        except Exception as e:
            self.logger.warning(f"Unexpected error in OpenAI enhancement: {e}")
            return job_data
    
    def _create_job_parsing_prompt(self, job_data: Dict[str, Any]) -> str:
        """Create prompt for OpenAI job parsing"""
        return f"""
You are an expert at parsing job descriptions. Analyze the following job posting and extract structured information.

Job Title: {job_data['title']}
Company: {job_data['company']}

Job Description:
{job_data['full_text'][:3000]}  # Limit to avoid token limits

Please extract and improve the following information. Return your response as a JSON object:

{{
    "requirements": ["list of key requirements"],
    "responsibilities": ["list of main responsibilities"],
    "skills_mentioned": ["list of technical skills and technologies"],
    "extracted_keywords": ["list of important keywords and phrases"],
    "summary": "1-2 sentence summary of the role",
    "experience_level": "junior/mid/senior/executive",
    "employment_type": "full-time/part-time/contract/freelance",
    "industry": "identified industry sector"
}}

Focus on:
- Technical skills and technologies mentioned
- Years of experience required
- Key responsibilities and duties
- Must-have vs nice-to-have requirements
- Industry-specific terminology

Return only valid JSON without additional text.
"""
    
    def _parse_openai_enhancement(self, response: str) -> Dict[str, Any]:
        """Parse OpenAI enhancement response"""
        try:
            # Clean response to ensure valid JSON
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            enhancement = json.loads(cleaned_response)
            
            # Validate and clean the enhancement
            return {
                'requirements': enhancement.get('requirements', [])[:10],
                'responsibilities': enhancement.get('responsibilities', [])[:10],
                'skills_mentioned': enhancement.get('skills_mentioned', [])[:15],
                'extracted_keywords': enhancement.get('extracted_keywords', [])[:10],
                'summary': enhancement.get('summary', '')[:500],
                'experience_level': enhancement.get('experience_level', ''),
                'employment_type': enhancement.get('employment_type', ''),
                'industry': enhancement.get('industry', '')
            }
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to parse OpenAI enhancement: {e}")
            return {}
    
    # Helper methods
    
    def _parse_bullet_points(self, text: str) -> List[str]:
        """Parse bullet point lists from text"""
        lines = text.split('\n')
        bullet_points = []
        
        for line in lines:
            line = line.strip()
            # Remove bullet point markers
            line = re.sub(r'^[\s\-\*•\d\.\)\w\)]\s*', '', line)
            if line and len(line) > 10:  # Filter out very short items
                bullet_points.append(line)
        
        return bullet_points
    
    def _clean_and_deduplicate(self, items: List[str]) -> List[str]:
        """Clean and deduplicate a list of strings"""
        seen = set()
        cleaned = []
        
        for item in items:
            item = item.strip()
            if item and item.lower() not in seen and len(item) > 2:
                cleaned.append(item)
                seen.add(item.lower())
        
        return cleaned
    
    def _is_generic_title(self, title: str) -> bool:
        """Check if title is too generic"""
        generic_terms = {
            'job', 'position', 'opening', 'opportunity', 'career',
            'apply now', 'hiring', 'wanted', 'vacancy'
        }
        return any(term in title.lower() for term in generic_terms)
    
    def _clean_job_title(self, title: str) -> str:
        """Clean and normalize job title"""
        # Remove common prefixes/suffixes
        title = re.sub(r'^(?:Job Title|Position|Role):\s*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*[-–—]\s*.*$', '', title)  # Remove everything after dash
        return title.strip()
    
    def _is_valid_company_name(self, name: str) -> bool:
        """Check if company name looks valid"""
        if len(name) < 2 or len(name) > 100:
            return False
        
        # Reject if it looks like a generic term
        generic_terms = {
            'company', 'corporation', 'business', 'enterprise',
            'organization', 'firm', 'group', 'team'
        }
        
        return name.lower() not in generic_terms
    
    def _clean_company_name(self, name: str) -> str:
        """Clean and normalize company name"""
        # Remove common suffixes
        name = re.sub(r'\s*(?:Inc\.?|LLC\.?|Corp\.?|Ltd\.?|Limited)\.?\s*$', '', name, flags=re.IGNORECASE)
        return name.strip()
    
    def _company_from_domain(self, domain: str) -> Optional[str]:
        """Extract company name from domain"""
        try:
            # Remove www. and common suffixes
            domain = re.sub(r'^www\.', '', domain)
            domain = re.sub(r'\.(com|org|net|io|co)(\.[a-z]{2})?$', '', domain)
            
            # Split on dots and take the main part
            parts = domain.split('.')
            if parts:
                main_part = parts[0]
                # Capitalize first letter
                return main_part.capitalize()
        except:
            pass
        
        return None


def create_job_extractor(config: Config) -> JobExtractor:
    """
    Factory function to create job extractor
    
    Args:
        config: Application configuration
        
    Returns:
        Configured JobExtractor instance
        
    Raises:
        JobExtractionError: If extractor creation fails
    """
    try:
        extractor = JobExtractor(config)
        logger.info("JobExtractor created successfully")
        return extractor
    except Exception as e:
        logger.error(f"Failed to create JobExtractor: {e}")
        raise JobExtractionError(f"Failed to create JobExtractor: {e}") 
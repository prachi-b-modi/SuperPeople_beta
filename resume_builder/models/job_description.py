"""
Job description data model for Resume Builder CLI
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, HttpUrl, validator
import re
from urllib.parse import urlparse


class JobDescriptionValidator(BaseModel):
    """Pydantic validator for job description data"""
    url: HttpUrl
    title: str
    company: str
    full_text: str
    requirements: List[str] = []
    skills_mentioned: List[str] = []
    responsibilities: List[str] = []
    extracted_keywords: List[str] = []
    categories: List[str] = []
    inferred_industry: Optional[str] = None
    summary: str = ""

    @validator('title', 'company', 'summary')
    def validate_text_fields(cls, v):
        """Validate text fields are not empty and reasonable length"""
        if not v or not v.strip():
            raise ValueError("Text fields cannot be empty")
        if len(v.strip()) > 1000:
            raise ValueError("Text fields cannot exceed 1000 characters")
        return v.strip()

    @validator('full_text')
    def validate_full_text(cls, v):
        """Validate full text is not empty and reasonable length"""
        if not v or not v.strip():
            raise ValueError("Full text cannot be empty")
        if len(v.strip()) < 50:
            raise ValueError("Full text must be at least 50 characters")
        if len(v.strip()) > 50000:
            raise ValueError("Full text cannot exceed 50,000 characters")
        return v.strip()

    @validator('requirements', 'skills_mentioned', 'responsibilities', 'extracted_keywords', 'categories')
    def validate_lists(cls, v):
        """Validate list fields"""
        if not isinstance(v, list):
            raise ValueError("Field must be a list")
        # Remove empty strings and duplicates while preserving order
        cleaned = []
        seen = set()
        for item in v:
            if isinstance(item, str) and item.strip() and item.strip().lower() not in seen:
                cleaned_item = item.strip()
                cleaned.append(cleaned_item)
                seen.add(cleaned_item.lower())
        
        return cleaned


@dataclass
class JobDescription:
    """
    Professional job description data model
    
    Stores extracted job posting information including requirements,
    skills, and metadata for job matching purposes.
    """
    url: str
    title: str
    company: str
    full_text: str
    requirements: List[str] = field(default_factory=list)
    skills_mentioned: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    extracted_keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    inferred_industry: Optional[str] = None
    summary: str = ""
    created_date: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate data after initialization"""
        validator = JobDescriptionValidator(
            url=self.url,
            title=self.title,
            company=self.company,
            full_text=self.full_text,
            requirements=self.requirements,
            skills_mentioned=self.skills_mentioned,
            responsibilities=self.responsibilities,
            extracted_keywords=self.extracted_keywords,
            categories=self.categories,
            inferred_industry=self.inferred_industry,
            summary=self.summary
        )
        
        # Update fields with validated/cleaned data
        self.url = str(validator.url)
        self.title = validator.title
        self.company = validator.company
        self.full_text = validator.full_text
        self.requirements = validator.requirements
        self.skills_mentioned = validator.skills_mentioned
        self.responsibilities = validator.responsibilities
        self.extracted_keywords = validator.extracted_keywords
        self.categories = validator.categories
        self.inferred_industry = validator.inferred_industry
        self.summary = validator.summary
    
    def get_domain(self) -> str:
        """Extract domain from job URL"""
        try:
            parsed = urlparse(self.url)
            return parsed.netloc.lower()
        except Exception:
            return "unknown"
    
    def get_all_keywords(self) -> List[str]:
        """Get all keywords from various fields"""
        all_keywords = []
        all_keywords.extend(self.skills_mentioned)
        all_keywords.extend(self.extracted_keywords)
        
        # Extract keywords from requirements and responsibilities
        for req in self.requirements:
            all_keywords.extend(self._extract_keywords_from_text(req))
        
        for resp in self.responsibilities:
            all_keywords.extend(self._extract_keywords_from_text(resp))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in all_keywords:
            if keyword.lower() not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword.lower())
        
        return unique_keywords
    
    def generate_search_queries(self) -> List[str]:
        """
        Generate optimized search queries for finding relevant experiences
        
        Returns multiple search strategies to find diverse relevant experiences
        """
        queries = []
        
        # Primary skills-based query
        if self.skills_mentioned:
            primary_skills = self.skills_mentioned[:5]  # Top 5 skills
            queries.append(" ".join(primary_skills))
        
        # Responsibility-based queries
        for responsibility in self.responsibilities[:3]:  # Top 3 responsibilities
            # Extract key phrases (typically 2-4 words)
            key_phrases = self._extract_key_phrases(responsibility)
            if key_phrases:
                queries.append(" ".join(key_phrases[:3]))
        
        # Requirement-based queries
        for requirement in self.requirements[:3]:  # Top 3 requirements
            key_phrases = self._extract_key_phrases(requirement)
            if key_phrases:
                queries.append(" ".join(key_phrases[:3]))
        
        # Combined high-priority terms
        if self.extracted_keywords:
            high_priority = self.extracted_keywords[:4]
            queries.append(" ".join(high_priority))
        
        # Company industry context (if recognizable)
        industry_terms = self._infer_industry_terms()
        if industry_terms:
            queries.append(" ".join(industry_terms))
        
        # Remove duplicates and empty queries
        unique_queries = []
        seen = set()
        for query in queries:
            if query and query.strip() and query.strip().lower() not in seen:
                clean_query = query.strip()
                unique_queries.append(clean_query)
                seen.add(clean_query.lower())
        
        return unique_queries[:8]  # Limit to 8 queries for efficiency
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract technical keywords from text"""
        # Common technical terms patterns
        tech_patterns = [
            r'\b[A-Z]{2,}\b',  # Acronyms (API, SQL, AWS, etc.)
            r'\b\w+\.\w+\b',   # Technologies with dots (Node.js, Vue.js)
            r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b',  # CamelCase (JavaScript, MongoDB)
            r'\b\w+[-]\w+\b',  # Hyphenated terms (Machine-Learning, Test-Driven)
        ]
        
        keywords = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)
        
        # Common programming/technical terms
        common_tech_terms = {
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'sql', 'nosql',
            'api', 'rest', 'graphql', 'microservices', 'devops', 'ci/cd',
            'machine learning', 'ai', 'data science', 'analytics', 'cloud'
        }
        
        text_lower = text.lower()
        for term in common_tech_terms:
            if term in text_lower:
                keywords.append(term)
        
        return keywords
    
    def _extract_key_phrases(self, text: str, max_phrases: int = 3) -> List[str]:
        """Extract key phrases from text (2-4 word combinations)"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'will', 'be', 'is', 'are', 'was',
            'were', 'have', 'has', 'had', 'do', 'does', 'did', 'can', 'could',
            'should', 'would', 'must', 'may', 'might'
        }
        
        # Clean and split text
        words = re.findall(r'\b\w+\b', text.lower())
        words = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Create 2-4 word phrases
        phrases = []
        for i in range(len(words)):
            for length in [2, 3, 4]:
                if i + length <= len(words):
                    phrase = ' '.join(words[i:i+length])
                    phrases.append(phrase)
        
        # Score phrases by relevance (prefer technical terms)
        scored_phrases = []
        for phrase in phrases:
            score = 0
            # Higher score for technical-sounding phrases
            if any(char.isupper() for char in phrase):
                score += 2
            if any(keyword in phrase for keyword in ['develop', 'manage', 'lead', 'implement', 'design']):
                score += 1
            if len(phrase.split()) == 3:  # Prefer 3-word phrases
                score += 1
            
            scored_phrases.append((phrase, score))
        
        # Sort by score and return top phrases
        scored_phrases.sort(key=lambda x: x[1], reverse=True)
        return [phrase for phrase, _ in scored_phrases[:max_phrases]]
    
    def _infer_industry_terms(self) -> List[str]:
        """Infer industry-related terms from company name and job description"""
        industry_keywords = {
            'fintech': ['finance', 'fintech', 'banking', 'payments', 'trading'],
            'healthtech': ['health', 'medical', 'healthcare', 'pharma', 'biotech'],
            'ecommerce': ['ecommerce', 'retail', 'marketplace', 'shopping'],
            'saas': ['saas', 'software', 'platform', 'cloud', 'enterprise'],
            'gaming': ['gaming', 'game', 'entertainment', 'media'],
            'security': ['security', 'cybersecurity', 'crypto', 'blockchain']
        }
        
        text_to_analyze = f"{self.company} {self.title} {self.summary}".lower()
        
        relevant_terms = []
        for industry, keywords in industry_keywords.items():
            if any(keyword in text_to_analyze for keyword in keywords):
                relevant_terms.extend(keywords[:2])  # Add top 2 terms
        
        return relevant_terms[:3]  # Limit to 3 terms
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'url': self.url,
            'title': self.title,
            'company': self.company,
            'full_text': self.full_text,
            'requirements': self.requirements,
            'skills_mentioned': self.skills_mentioned,
            'responsibilities': self.responsibilities,
            'extracted_keywords': self.extracted_keywords,
            'summary': self.summary,
            'created_date': self.created_date.isoformat(),
            'domain': self.get_domain(),
            'all_keywords': self.get_all_keywords()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobDescription':
        """Create instance from dictionary"""
        # Parse datetime if it's a string
        if isinstance(data.get('created_date'), str):
            data['created_date'] = datetime.fromisoformat(data['created_date'])
        
        # Remove computed fields that shouldn't be in constructor
        data.pop('domain', None)
        data.pop('all_keywords', None)
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation"""
        return f"JobDescription(company='{self.company}', title='{self.title}', skills={len(self.skills_mentioned)})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"JobDescription(url='{self.url}', company='{self.company}', "
                f"title='{self.title}', skills={len(self.skills_mentioned)}, "
                f"requirements={len(self.requirements)})") 
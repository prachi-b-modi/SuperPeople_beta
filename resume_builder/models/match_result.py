"""
Job matching result data models for Resume Builder CLI
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, validator
import json


class RefinedExperienceValidator(BaseModel):
    """Pydantic validator for refined experience data"""
    original_experience_id: str
    company: str
    role: Optional[str] = None
    accomplishments: List[str] = []
    skills: List[str] = []
    tools_technologies: List[str] = []
    relevance_score: float = 0.0
    confidence_score: float = 0.0
    keywords_matched: List[str] = []
    refinement_notes: str = ""

    @validator('original_experience_id')
    def validate_experience_id(cls, v):
        """Validate experience ID is not empty"""
        if not v or not v.strip():
            raise ValueError("Experience ID cannot be empty")
        return v.strip()

    @validator('company')
    def validate_company(cls, v):
        """Validate company name"""
        if not v or not v.strip():
            raise ValueError("Company name cannot be empty")
        return v.strip()

    @validator('accomplishments')
    def validate_accomplishments(cls, v):
        """Validate accomplishments list"""
        if not isinstance(v, list):
            raise ValueError("Accomplishments must be a list")
        if not v:
            raise ValueError("At least one accomplishment is required")
        
        cleaned = []
        for item in v:
            if isinstance(item, str) and item.strip():
                cleaned_item = item.strip()
                if len(cleaned_item) >= 10:  # Minimum length
                    cleaned.append(cleaned_item)
        
        if not cleaned:
            raise ValueError("At least one valid accomplishment is required")
        
        return cleaned

    @validator('skills', 'tools_technologies', 'keywords_matched')
    def validate_skill_lists(cls, v):
        """Validate skill and tool lists"""
        if not isinstance(v, list):
            raise ValueError("Field must be a list")
        # Clean and deduplicate
        cleaned = []
        seen = set()
        for item in v:
            if isinstance(item, str) and item.strip() and item.strip().lower() not in seen:
                cleaned_item = item.strip()
                cleaned.append(cleaned_item)
                seen.add(cleaned_item.lower())
        
        return cleaned

    @validator('relevance_score', 'confidence_score')
    def validate_scores(cls, v):
        """Validate scores are between 0.0 and 1.0"""
        if not isinstance(v, (int, float)):
            raise ValueError("Score must be a number")
        if v < 0.0 or v > 1.0:
            raise ValueError("Score must be between 0.0 and 1.0")
        return float(v)


@dataclass
class RefinedExperience:
    """
    Professional experience refined for specific job application
    
    Represents a user's experience that has been tailored and polished
    for relevance to a specific job posting.
    """
    original_experience_id: str
    company: str
    role: Optional[str] = None
    accomplishments: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    tools_technologies: List[str] = field(default_factory=list)
    relevance_score: float = 0.0
    confidence_score: float = 0.0
    keywords_matched: List[str] = field(default_factory=list)
    refinement_notes: str = ""
    
    def __post_init__(self):
        """Validate data after initialization"""
        validator = RefinedExperienceValidator(
            original_experience_id=self.original_experience_id,
            company=self.company,
            role=self.role,
            accomplishments=self.accomplishments,
            skills=self.skills,
            tools_technologies=self.tools_technologies,
            relevance_score=self.relevance_score,
            confidence_score=self.confidence_score,
            keywords_matched=self.keywords_matched,
            refinement_notes=self.refinement_notes
        )
        
        # Update fields with validated/cleaned data
        self.original_experience_id = validator.original_experience_id
        self.company = validator.company
        self.role = validator.role
        self.accomplishments = validator.accomplishments
        self.skills = validator.skills
        self.tools_technologies = validator.tools_technologies
        self.relevance_score = validator.relevance_score
        self.confidence_score = validator.confidence_score
        self.keywords_matched = validator.keywords_matched
        self.refinement_notes = validator.refinement_notes
    
    def get_all_technologies(self) -> List[str]:
        """Get combined list of skills and tools"""
        all_tech = []
        all_tech.extend(self.skills)
        all_tech.extend(self.tools_technologies)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tech = []
        for tech in all_tech:
            if tech.lower() not in seen:
                unique_tech.append(tech)
                seen.add(tech.lower())
        
        return unique_tech
    
    def get_primary_accomplishment(self) -> str:
        """Get the primary (first) accomplishment"""
        return self.accomplishments[0] if self.accomplishments else ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'original_experience_id': self.original_experience_id,
            'company': self.company,
            'role': self.role,
            'accomplishments': self.accomplishments,
            'skills': self.skills,
            'tools_technologies': self.tools_technologies,
            'relevance_score': self.relevance_score,
            'confidence_score': self.confidence_score,
            'keywords_matched': self.keywords_matched,
            'refinement_notes': self.refinement_notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RefinedExperience':
        """Create instance from dictionary"""
        return cls(
            original_experience_id=data.get('original_experience_id', ''),
            company=data.get('company', ''),
            role=data.get('role'),
            accomplishments=data.get('accomplishments', []),
            skills=data.get('skills', []),
            tools_technologies=data.get('tools_technologies', []),
            relevance_score=data.get('relevance_score', 0.0),
            confidence_score=data.get('confidence_score', 0.0),
            keywords_matched=data.get('keywords_matched', []),
            refinement_notes=data.get('refinement_notes', '')
        )
    
    def __str__(self) -> str:
        """String representation"""
        return f"RefinedExperience(score={self.relevance_score:.2f}, skills={len(self.skills)})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"RefinedExperience(id='{self.original_experience_id}', "
                f"score={self.relevance_score:.2f}, skills={len(self.skills)}, "
                f"tools={len(self.tools_technologies)})")


class JobMatchResultValidator(BaseModel):
    """Pydantic validator for job match result data"""
    job_url: str
    matched_experiences: List[Dict[str, Any]] = []
    aggregated_skills: List[str] = []
    aggregated_tools: List[str] = []
    match_score: float
    processing_metadata: Dict[str, Any] = {}

    @validator('job_url')
    def validate_job_url(cls, v):
        """Validate job URL"""
        if not v or not v.strip():
            raise ValueError("Job URL cannot be empty")
        return v.strip()

    @validator('aggregated_skills', 'aggregated_tools')
    def validate_aggregated_lists(cls, v):
        """Validate aggregated skill and tool lists"""
        if not isinstance(v, list):
            raise ValueError("Field must be a list")
        # Clean and deduplicate
        cleaned = []
        seen = set()
        for item in v:
            if isinstance(item, str) and item.strip() and item.strip().lower() not in seen:
                cleaned_item = item.strip()
                cleaned.append(cleaned_item)
                seen.add(cleaned_item.lower())
        return cleaned

    @validator('match_score')
    def validate_match_score(cls, v):
        """Validate overall match score"""
        if not isinstance(v, (int, float)):
            raise ValueError("Match score must be a number")
        if v < 0.0 or v > 1.0:
            raise ValueError("Match score must be between 0.0 and 1.0")
        return float(v)

    @validator('processing_metadata')
    def validate_metadata(cls, v):
        """Validate processing metadata"""
        if not isinstance(v, dict):
            return {}
        return v


@dataclass
class JobMatchResult:
    """
    Complete result of matching user experiences to a job posting
    
    Contains all relevant experiences refined for the specific job,
    along with aggregated skills and metadata about the matching process.
    """
    job_url: str
    matched_experiences: List[RefinedExperience] = field(default_factory=list)
    aggregated_skills: List[str] = field(default_factory=list)
    aggregated_tools: List[str] = field(default_factory=list)
    match_score: float = 0.0
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
    created_date: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate data and calculate derived fields after initialization"""
        # Convert dict experiences to RefinedExperience objects if needed
        refined_experiences = []
        for exp in self.matched_experiences:
            if isinstance(exp, dict):
                refined_experiences.append(RefinedExperience.from_dict(exp))
            elif isinstance(exp, RefinedExperience):
                refined_experiences.append(exp)
            else:
                raise ValueError(f"Invalid experience type: {type(exp)}")
        
        self.matched_experiences = refined_experiences
        
        # Validate using Pydantic
        validator = JobMatchResultValidator(
            job_url=self.job_url,
            matched_experiences=[exp.to_dict() for exp in self.matched_experiences],
            aggregated_skills=self.aggregated_skills,
            aggregated_tools=self.aggregated_tools,
            match_score=self.match_score,
            processing_metadata=self.processing_metadata
        )
        
        # Update fields with validated/cleaned data
        self.job_url = validator.job_url
        self.aggregated_skills = validator.aggregated_skills
        self.aggregated_tools = validator.aggregated_tools
        self.match_score = validator.match_score
        self.processing_metadata = validator.processing_metadata
        
        # Calculate derived fields if not provided
        if not self.aggregated_skills or not self.aggregated_tools:
            self._calculate_aggregated_technologies()
        
        if self.match_score == 0.0:
            self._calculate_overall_match_score()
    
    def _calculate_aggregated_technologies(self):
        """Calculate aggregated skills and tools from matched experiences"""
        all_skills = []
        all_tools = []
        
        for exp in self.matched_experiences:
            all_skills.extend(exp.skills)
            all_tools.extend(exp.tools_technologies)
        
        # Deduplicate while preserving order
        self.aggregated_skills = self._deduplicate_list(all_skills)
        self.aggregated_tools = self._deduplicate_list(all_tools)
    
    def _calculate_overall_match_score(self):
        """Calculate overall match score based on experience relevance scores"""
        if not self.matched_experiences:
            self.match_score = 0.0
            return
        
        # Weighted average with higher weight for top experiences
        total_score = 0.0
        total_weight = 0.0
        
        for i, exp in enumerate(self.matched_experiences):
            # Diminishing weight for lower-ranked experiences
            weight = 1.0 / (i + 1)
            total_score += exp.relevance_score * weight
            total_weight += weight
        
        self.match_score = total_score / total_weight if total_weight > 0 else 0.0
    
    def _deduplicate_list(self, items: List[str]) -> List[str]:
        """Remove duplicates while preserving order"""
        seen = set()
        unique_items = []
        for item in items:
            if item.lower() not in seen:
                unique_items.append(item)
                seen.add(item.lower())
        return unique_items
    
    def get_high_relevance_experiences(self, threshold: float = 0.7) -> List[RefinedExperience]:
        """Get experiences with high relevance scores"""
        return [exp for exp in self.matched_experiences if exp.relevance_score >= threshold]
    
    def get_top_skills(self, limit: int = 10) -> List[str]:
        """Get top aggregated skills (by frequency across experiences)"""
        skill_counts = {}
        for exp in self.matched_experiences:
            for skill in exp.skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        # Sort by frequency and return top skills
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        return [skill for skill, _ in sorted_skills[:limit]]
    
    def get_top_tools(self, limit: int = 10) -> List[str]:
        """Get top aggregated tools (by frequency across experiences)"""
        tool_counts = {}
        for exp in self.matched_experiences:
            for tool in exp.tools_technologies:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        # Sort by frequency and return top tools
        sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
        return [tool for tool, _ in sorted_tools[:limit]]
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about the match results"""
        if not self.matched_experiences:
            return {
                'total_experiences': 0,
                'high_relevance_count': 0,
                'average_relevance': 0.0,
                'total_skills': 0,
                'total_tools': 0,
                'overall_match_score': self.match_score
            }
        
        relevance_scores = [exp.relevance_score for exp in self.matched_experiences]
        high_relevance_count = len(self.get_high_relevance_experiences())
        
        return {
            'total_experiences': len(self.matched_experiences),
            'high_relevance_count': high_relevance_count,
            'average_relevance': sum(relevance_scores) / len(relevance_scores),
            'max_relevance': max(relevance_scores),
            'min_relevance': min(relevance_scores),
            'total_skills': len(self.aggregated_skills),
            'total_tools': len(self.aggregated_tools),
            'overall_match_score': self.match_score,
            'processing_time': self.processing_metadata.get('processing_time_seconds', 0),
            'api_calls_made': self.processing_metadata.get('api_calls_made', 0)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'job_url': self.job_url,
            'matched_experiences': [exp.to_dict() for exp in self.matched_experiences],
            'aggregated_skills': self.aggregated_skills,
            'aggregated_tools': self.aggregated_tools,
            'match_score': self.match_score,
            'processing_metadata': self.processing_metadata,
            'created_date': self.created_date.isoformat(),
            'summary_stats': self.get_summary_stats(),
            'top_skills': self.get_top_skills(5),
            'top_tools': self.get_top_tools(5)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobMatchResult':
        """Create instance from dictionary"""
        # Parse datetime if it's a string
        if isinstance(data.get('created_date'), str):
            data['created_date'] = datetime.fromisoformat(data['created_date'])
        
        # Remove computed fields that shouldn't be in constructor
        data.pop('summary_stats', None)
        data.pop('top_skills', None)
        data.pop('top_tools', None)
        
        return cls(**data)
    
    def save_to_file(self, file_path: str):
        """Save match results to JSON file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'JobMatchResult':
        """Load match results from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """String representation"""
        return (f"JobMatchResult(experiences={len(self.matched_experiences)}, "
                f"score={self.match_score:.2f}, skills={len(self.aggregated_skills)})")
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"JobMatchResult(url='{self.job_url}', "
                f"experiences={len(self.matched_experiences)}, "
                f"score={self.match_score:.2f}, skills={len(self.aggregated_skills)}, "
                f"tools={len(self.aggregated_tools)})") 
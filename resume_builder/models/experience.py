"""
Experience data model for Resume Builder CLI
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator, Field

from ..utils.helpers import normalize_text, ensure_list


class Experience:
    """
    Experience class compatible with job matching workflow
    
    This class provides the interface expected by ExperienceRefiner
    and other job matching components.
    """
    
    def __init__(
        self,
        id: str,
        company: str,
        text: str,
        role: Optional[str] = None,
        duration: Optional[str] = None,
        skills: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.company = company
        self.text = text
        self.role = role
        self.duration = duration
        self.skills = skills or []
        self.categories = categories or []
        self.created_at = created_at or datetime.now()
    
    @classmethod
    def from_experience_data(cls, experience_data: 'ExperienceData', experience_id: str = None) -> 'Experience':
        """Create Experience from ExperienceData"""
        return cls(
            id=experience_id or str(hash(experience_data.original_text)),
            company=experience_data.company_name,
            text=experience_data.original_text,
            role=None,  # Not available in ExperienceData
            duration=None,  # Not available in ExperienceData
            skills=experience_data.skills,
            categories=experience_data.categories,
            created_at=experience_data.created_date
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'company': self.company,
            'text': self.text,
            'role': self.role,
            'duration': self.duration,
            'skills': self.skills,
            'categories': self.categories,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class ExperienceData:
    """
    Data class for professional experience
    
    This class represents a professional experience entry with
    extracted metadata for enhanced semantic search.
    """
    original_text: str
    company_name: str
    skills: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    relevant_jobs: List[str] = field(default_factory=list)
    created_date: datetime = field(default_factory=datetime.now)
    combined_text: str = ""
    
    def __post_init__(self):
        """Post-initialization processing"""
        # Normalize and clean data
        self.original_text = normalize_text(self.original_text)
        self.company_name = normalize_text(self.company_name)
        
        # Ensure lists are properly formatted
        self.skills = [normalize_text(skill) for skill in ensure_list(self.skills) if skill.strip()]
        self.categories = [normalize_text(cat) for cat in ensure_list(self.categories) if cat.strip()]
        self.relevant_jobs = [normalize_text(job) for job in ensure_list(self.relevant_jobs) if job.strip()]
        
        # Generate combined text if not provided
        if not self.combined_text:
            self.combined_text = self.generate_combined_text()
    
    def generate_combined_text(self) -> str:
        """
        Generate enhanced text for vectorization
        
        Combines original text with extracted metadata to create
        a comprehensive text representation for semantic search.
        
        Returns:
            Combined text string
        """
        parts = [self.original_text]
        
        if self.skills:
            skills_text = f"Key skills: {', '.join(self.skills)}"
            parts.append(skills_text)
        
        if self.categories:
            categories_text = f"Categories: {', '.join(self.categories)}"
            parts.append(categories_text)
        
        if self.relevant_jobs:
            jobs_text = f"Relevant for: {', '.join(self.relevant_jobs)}"
            parts.append(jobs_text)
        
        if self.company_name:
            company_text = f"Company: {self.company_name}"
            parts.append(company_text)
        
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for storage
        
        Returns:
            Dictionary representation
        """
        return 
        {
            "original_text": self.original_text,
            "company_name": self.company_name,
            "skills": self.skills,
            "categories": self.categories,
            "relevant_jobs": self.relevant_jobs,
            "created_date": self.created_date.isoformat(),
            "combined_text": self.combined_text
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperienceData':
        """
        Create instance from dictionary
        
        Args:
            data: Dictionary data
            
        Returns:
            ExperienceData instance
        """
        # Handle datetime conversion
        if isinstance(data.get('created_date'), str):
            data['created_date'] = datetime.fromisoformat(data['created_date'])
        
        return cls(**data)
    
    def update_metadata(self, 
                       skills: Optional[List[str]] = None,
                       categories: Optional[List[str]] = None,
                       relevant_jobs: Optional[List[str]] = None) -> None:
        """
        Update extracted metadata and regenerate combined text
        
        Args:
            skills: Updated skills list
            categories: Updated categories list
            relevant_jobs: Updated relevant jobs list
        """
        if skills is not None:
            self.skills = [normalize_text(skill) for skill in ensure_list(skills) if skill.strip()]
        
        if categories is not None:
            self.categories = [normalize_text(cat) for cat in ensure_list(categories) if cat.strip()]
        
        if relevant_jobs is not None:
            self.relevant_jobs = [normalize_text(job) for job in ensure_list(relevant_jobs) if job.strip()]
        
        # Regenerate combined text
        self.combined_text = self.generate_combined_text()
    
    def add_skill(self, skill: str) -> None:
        """
        Add a skill to the skills list
        
        Args:
            skill: Skill to add
        """
        skill = normalize_text(skill)
        if skill and skill not in self.skills:
            self.skills.append(skill)
            self.combined_text = self.generate_combined_text()
    
    def add_category(self, category: str) -> None:
        """
        Add a category to the categories list
        
        Args:
            category: Category to add
        """
        category = normalize_text(category)
        if category and category not in self.categories:
            self.categories.append(category)
            self.combined_text = self.generate_combined_text()
    
    def add_relevant_job(self, job: str) -> None:
        """
        Add a relevant job to the relevant jobs list
        
        Args:
            job: Job title to add
        """
        job = normalize_text(job)
        if job and job not in self.relevant_jobs:
            self.relevant_jobs.append(job)
            self.combined_text = self.generate_combined_text()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the experience
        
        Returns:
            Summary dictionary
        """
        return 
        {
            "company": self.company_name,
            "skills_count": len(self.skills),
            "categories_count": len(self.categories),
            "relevant_jobs_count": len(self.relevant_jobs),
            "text_length": len(self.original_text),
            "created_date": self.created_date.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def __str__(self) -> str:
        """String representation"""
        return f"Experience at {self.company_name} ({len(self.skills)} skills, {len(self.categories)} categories)"
    
    def __repr__(self) -> str:
        """Developer representation"""
        return (f"ExperienceData(company='{self.company_name}', "
                f"skills={len(self.skills)}, categories={len(self.categories)}, "
                f"relevant_jobs={len(self.relevant_jobs)})")


class ExperienceValidator(BaseModel):
    """
    Pydantic model for experience validation
    """
    original_text: str = Field(..., min_length=10, max_length=10000, description="Original experience text")
    company_name: str = Field(..., min_length=1, max_length=200, description="Company name")
    skills: List[str] = Field(default_factory=list, description="List of skills")
    categories: List[str] = Field(default_factory=list, description="List of categories")
    relevant_jobs: List[str] = Field(default_factory=list, description="List of relevant job titles")
    
    @validator('original_text')
    def validate_original_text(cls, v):
        """Validate original text"""
        v = normalize_text(v)
        if len(v) < 10:
            raise ValueError("Original text must be at least 10 characters long")
        return v
    
    @validator('company_name')
    def validate_company_name(cls, v):
        """Validate company name"""
        v = normalize_text(v)
        if not v:
            raise ValueError("Company name cannot be empty")
        return v
    
    @validator('skills', 'categories', 'relevant_jobs')
    def validate_lists(cls, v):
        """Validate list fields"""
        if not isinstance(v, list):
            return []
        return [normalize_text(item) for item in v if item and normalize_text(item)]
    
    def to_experience_data(self) -> ExperienceData:
        """
        Convert to ExperienceData instance
        
        Returns:
            ExperienceData instance
        """
        return ExperienceData(
            original_text=self.original_text,
            company_name=self.company_name,
            skills=self.skills,
            categories=self.categories,
            relevant_jobs=self.relevant_jobs
        ) 
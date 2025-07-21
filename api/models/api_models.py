from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Experience models
class ExperienceBase(BaseModel):
    text: str = Field(..., description="The experience description text")
    company: str = Field(..., description="The company name")
    role: Optional[str] = Field(None, description="The job role or title")
    duration: Optional[str] = Field(None, description="The duration of the experience (e.g., 'Jan 2020 - Dec 2022')")

class ExperienceCreate(ExperienceBase):
    no_extraction: bool = Field(False, description="If true, skip AI extraction of skills and categories")

class Experience(ExperienceBase):
    id: str = Field(..., description="Unique identifier for the experience")
    skills: List[str] = Field(default_factory=list, description="List of skills extracted from the experience")
    categories: List[str] = Field(default_factory=list, description="List of categories the experience falls under")
    relevant_jobs: List[str] = Field(default_factory=list, description="List of job titles relevant to this experience")
    created_at: str = Field(..., description="Timestamp when the experience was created")

# Job models
class JobMatchRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL of the job posting to match against experiences")

class JobMatch(BaseModel):
    job_title: str = Field(..., description="Title of the job")
    company: str = Field(..., description="Company offering the job")
    matching_experiences: List[Dict[str, Any]] = Field(..., description="Experiences that match this job")
    match_score: float = Field(..., description="Overall match score")

# Utility models
class HealthStatus(BaseModel):
    database: bool = Field(..., description="Whether the database is healthy")
    extraction_service: bool = Field(..., description="Whether the extraction service is healthy")
    overall: bool = Field(..., description="Overall system health")

class DatabaseStats(BaseModel):
    experience_count: int = Field(..., description="Number of experiences in the database")
    skill_count: int = Field(..., description="Number of unique skills across all experiences")
    category_count: int = Field(..., description="Number of unique categories across all experiences")
    last_updated: str = Field(..., description="When the database was last updated")
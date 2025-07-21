from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import subprocess
import json
import logging

from api.models.api_models import JobMatchRequest, JobMatch

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/match", response_model=Dict[str, Any])
async def match_job(job_request: JobMatchRequest):
    """Match a job posting to experiences"""
    try:
        cmd = ["resume-builder", "match-job", "--url", str(job_request.url)]
        # Add JSON output flag if supported
        # cmd.append("--json")
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output
        # This is a simplified example - you would need to parse the actual output format
        # If the CLI doesn't support JSON output, you'll need to parse the text output
        
        # Mock response for now
        return {
            "job_title": "Senior Python Developer",
            "company": "Example Corp",
            "matching_experiences": [
                {
                    "id": "exp-123",
                    "company": "TechCorp",
                    "match_score": 0.85,
                    "matching_skills": ["Python", "Docker", "Microservices"]
                }
            ],
            "match_score": 0.85,
            "recommended_skills_to_add": ["Django", "FastAPI", "AWS"]
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to match job: {e.stderr}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to match job: {e.stderr}"
        )

@router.post("/extract", response_model=Dict[str, Any])
async def extract_job(job_request: JobMatchRequest):
    """Extract job details from URL"""
    try:
        cmd = ["resume-builder", "test-job-extraction", "--url", str(job_request.url)]
        # Add JSON output flag if supported
        # cmd.append("--json")
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output
        # This is a simplified example - you would need to parse the actual output format
        
        # Mock response for now
        return {
            "job_title": "Senior Python Developer",
            "company": "Example Corp",
            "location": "San Francisco, CA",
            "description": "We are looking for a Senior Python Developer...",
            "required_skills": ["Python", "Django", "FastAPI", "Docker", "AWS"],
            "extracted_at": "2023-07-21T12:00:00Z"
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract job: {e.stderr}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to extract job: {e.stderr}"
        )
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import subprocess
import json
import logging

from api.models.api_models import HealthStatus, DatabaseStats

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Check system health"""
    try:
        cmd = ["resume-builder", "health-check"]
        # Add JSON output flag if supported
        # cmd.append("--json")
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output
        # This is a simplified example - you would need to parse the actual output format
        
        # Mock response for now
        return {
            "database": True,
            "extraction_service": True,
            "overall": True
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Health check failed: {e.stderr}")
        # Even if the health check fails, we return a valid response with the status
        return {
            "database": False,
            "extraction_service": False,
            "overall": False
        }

@router.get("/stats", response_model=DatabaseStats)
async def get_stats():
    """Get database statistics"""
    try:
        cmd = ["resume-builder", "stats"]
        # Add JSON output flag if supported
        # cmd.append("--json")
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output
        # This is a simplified example - you would need to parse the actual output format
        
        # Mock response for now
        return {
            "experience_count": 5,
            "skill_count": 20,
            "category_count": 8,
            "last_updated": "2023-07-21T12:00:00Z"
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get stats: {e.stderr}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to get stats: {e.stderr}"
        )

@router.get("/config", response_model=Dict[str, Any])
async def get_config():
    """Get current configuration information"""
    try:
        cmd = ["resume-builder", "config-info"]
        # Add JSON output flag if supported
        # cmd.append("--json")
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output
        # This is a simplified example - you would need to parse the actual output format
        
        # Mock response for now
        return {
            "weaviate_url": "http://localhost:8080",
            "extraction_model": "gpt-4",
            "version": "0.1.0"
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get config: {e.stderr}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to get config: {e.stderr}"
        )
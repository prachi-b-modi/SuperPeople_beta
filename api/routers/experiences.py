from fastapi import APIRouter, HTTPException, Query, Path as FastAPIPath, status
from typing import List, Optional
import subprocess
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path as FilePath

from api.models.api_models import ExperienceBase, ExperienceCreate, Experience

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=Experience, status_code=status.HTTP_201_CREATED)
async def add_experience(experience: ExperienceCreate):
    """Add a new experience to the database"""
    try:
        # Build command
        cmd = ["resume-builder", "add-experience", 
               "--text", experience.text, 
               "--company", experience.company]
        
        if experience.role:
            cmd.extend(["--role", experience.role])
        if experience.duration:
            cmd.extend(["--duration", experience.duration])
        if experience.no_extraction:
            cmd.append("--no-extraction")
        
        # Add JSON output flag if supported
        # cmd.append("--json")
        
        # Run command and capture output
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output to get the created experience
        # This assumes the CLI tool returns the created experience as JSON or in a parseable format
        # You might need to adjust this based on actual output format
        
        # For now, we'll create a response based on the input and some mock data
        # In a production environment, you would parse the actual output from the CLI tool
        return {
            "id": str(uuid.uuid4()),
            "text": experience.text,
            "company": experience.company,
            "role": experience.role,
            "duration": experience.duration,
            "skills": ["Python", "FastAPI"],  # These would come from actual extraction
            "categories": ["Web Development"],
            "relevant_jobs": ["Software Engineer"],
            "created_at": datetime.now().isoformat()
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to add experience: {e.stderr}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to add experience: {e.stderr}"
        )

@router.get("/", response_model=List[Experience])
async def list_experiences():
    """List all experiences"""
    try:
        # Run CLI command with JSON output format
        cmd = ["resume-builder", "list-experiences", "--format", "json"]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Parse the JSON output from the CLI command
        try:
            # Log the raw output for debugging
            logger.debug(f"Raw CLI output: {result.stdout}")
            
            # Try to parse the entire output as JSON first
            try:
                cli_experiences = json.loads(result.stdout)
                logger.info(f"Successfully parsed complete JSON output with {len(cli_experiences) if isinstance(cli_experiences, list) else 1} experiences")
            except json.JSONDecodeError:
                # If that fails, try to extract JSON part from the output
                logger.warning("Complete JSON parsing failed, attempting to extract JSON portion")
                
                # Look for patterns that might indicate the start of JSON data
                json_start = result.stdout.find('[')
                json_end = result.stdout.rfind(']')
                
                if json_start >= 0 and json_end > json_start:
                    # Extract what looks like a JSON array
                    json_data = result.stdout[json_start:json_end+1]
                    
                    # Try to parse it
                    try:
                        cli_experiences = json.loads(json_data)
                        logger.info(f"Successfully parsed JSON data with {len(cli_experiences)} experiences")
                    except json.JSONDecodeError:
                        # If that fails, try a more aggressive approach to clean the output
                        logger.warning("JSON array parsing failed, attempting to clean the output")
                        # Remove ANSI color codes and other non-JSON characters
                        import re
                        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                        cleaned_data = ansi_escape.sub('', result.stdout)
                        
                        # Try to find JSON array again in cleaned data
                        json_start = cleaned_data.find('[')
                        json_end = cleaned_data.rfind(']')
                        
                        if json_start >= 0 and json_end > json_start:
                            json_data = cleaned_data[json_start:json_end+1]
                            cli_experiences = json.loads(json_data)
                            logger.info(f"Successfully parsed cleaned JSON data with {len(cli_experiences)} experiences")
                        else:
                            logger.warning("Could not find valid JSON data even after cleaning")
                            cli_experiences = []
                else:
                    logger.warning("Could not find JSON array markers in CLI output")
                    cli_experiences = []
                
            # Convert CLI experience format to API format
            experiences = []
            for exp in cli_experiences:
                experiences.append({
                    "id": exp.get("id", str(uuid.uuid4())),
                    "text": exp.get("original_text", ""),
                    "company": exp.get("company_name", ""),
                    "role": exp.get("role", None),
                    "duration": exp.get("duration", None),
                    "skills": exp.get("skills", []),
                    "categories": exp.get("categories", []),
                    "relevant_jobs": exp.get("relevant_jobs", []),
                    "created_at": exp.get("created_date", datetime.now().isoformat())
                })
            
            return experiences
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from CLI output: {e}")
            logger.debug(f"CLI output: {result.stdout}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse experiences data from CLI: {str(e)}"
            )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to list experiences: {e.stderr}")
        # Attempt to provide a fallback response with a warning
        logger.warning("Using fallback mechanism to return experiences")
        try:
            # Try to read from a backup file if available
            backup_path = FilePath("experiences_backup.json")
            if backup_path.exists():
                try:
                    with open(backup_path, 'r') as f:
                        backup_data = json.load(f)
                        
                    # Check if the backup has the expected structure
                    experiences = []
                    if isinstance(backup_data, dict) and 'experiences' in backup_data:
                        # Format where experiences are in an 'experiences' key
                        exp_list = backup_data.get('experiences', [])
                    elif isinstance(backup_data, list):
                        # Format where the file is just a list of experiences
                        exp_list = backup_data
                    else:
                        logger.warning("Backup file has unexpected format")
                        exp_list = []
                        
                    for exp in exp_list:
                        if not isinstance(exp, dict):
                            continue
                            
                        experiences.append({
                            "id": exp.get("id", str(uuid.uuid4())),
                            "text": exp.get("original_text", ""),
                            "company": exp.get("company_name", ""),
                            "role": exp.get("role", None),
                            "duration": exp.get("duration", None),
                            "skills": exp.get("skills", []),
                            "categories": exp.get("categories", []),
                            "relevant_jobs": exp.get("relevant_jobs", []),
                            "created_at": exp.get("created_date", datetime.now().isoformat())
                        })
                        
                    if experiences:
                        logger.info(f"Returned {len(experiences)} experiences from backup file")
                        return experiences
                    else:
                        logger.warning("No valid experiences found in backup file")
                except json.JSONDecodeError as json_err:
                    logger.error(f"Backup file contains invalid JSON: {json_err}")
                except Exception as backup_err:
                    logger.error(f"Error processing backup file: {backup_err}")
            else:
                # If no backup file, raise the original exception
                raise
        except Exception as fallback_error:
            logger.error(f"Fallback mechanism failed: {fallback_error}")
            # If fallback fails, raise the original exception
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Failed to list experiences: {e.stderr}"
            )

@router.get("/{experience_id}", response_model=Experience)
async def get_experience(experience_id: str = FastAPIPath(..., description="The ID of the experience to retrieve")):
    """Get a specific experience by ID"""
    try:
        # Run CLI command with JSON output format to get all experiences
        cmd = ["resume-builder", "list-experiences", "--format", "json"]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        try:
            # Log the raw output for debugging
            logger.debug(f"Raw CLI output: {result.stdout}")
            
            # Try to parse the entire output as JSON first
            try:
                cli_experiences = json.loads(result.stdout)
                logger.info(f"Successfully parsed complete JSON output with {len(cli_experiences) if isinstance(cli_experiences, list) else 1} experiences")
            except json.JSONDecodeError:
                # If that fails, try to extract JSON part from the output
                logger.warning("Complete JSON parsing failed, attempting to extract JSON portion")
                
                # Look for patterns that might indicate the start of JSON data
                json_start = result.stdout.find('[')
                json_end = result.stdout.rfind(']')
                
                if json_start >= 0 and json_end > json_start:
                    # Extract what looks like a JSON array
                    json_data = result.stdout[json_start:json_end+1]
                    
                    # Try to parse it
                    try:
                        cli_experiences = json.loads(json_data)
                        logger.info(f"Successfully parsed JSON data with {len(cli_experiences)} experiences")
                    except json.JSONDecodeError:
                        # If that fails, try a more aggressive approach to clean the output
                        logger.warning("JSON array parsing failed, attempting to clean the output")
                        # Remove ANSI color codes and other non-JSON characters
                        import re
                        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                        cleaned_data = ansi_escape.sub('', result.stdout)
                        
                        # Try to find JSON array again in cleaned data
                        json_start = cleaned_data.find('[')
                        json_end = cleaned_data.rfind(']')
                        
                        if json_start >= 0 and json_end > json_start:
                            json_data = cleaned_data[json_start:json_end+1]
                            cli_experiences = json.loads(json_data)
                            logger.info(f"Successfully parsed cleaned JSON data with {len(cli_experiences)} experiences")
                        else:
                            logger.warning("Could not find valid JSON data even after cleaning")
                            cli_experiences = []
                else:
                    logger.warning("Could not find JSON array markers in CLI output")
                    cli_experiences = []
            
            # Find the experience with the matching ID
            for exp in cli_experiences:
                # Check if this is the experience we're looking for
                # The ID might be stored in different ways depending on the CLI implementation
                exp_id = exp.get("id", None)
                
                if exp_id == experience_id or str(exp_id) == experience_id:
                    # Convert to API format
                    return {
                        "id": exp_id,
                        "text": exp.get("original_text", ""),
                        "company": exp.get("company_name", ""),
                        "role": exp.get("role", None),
                        "duration": exp.get("duration", None),
                        "skills": exp.get("skills", []),
                        "categories": exp.get("categories", []),
                        "relevant_jobs": exp.get("relevant_jobs", []),
                        "created_at": exp.get("created_date", datetime.now().isoformat())
                    }
            
            # If we get here, the experience was not found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Experience with ID {experience_id} not found"
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from CLI output: {e}")
            logger.debug(f"CLI output: {result.stdout}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse experiences data from CLI: {str(e)}"
            )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get experience: {e.stderr}")
        # Attempt to provide a fallback response with a warning
        logger.warning(f"Using fallback mechanism to return experience with ID {experience_id}")
        try:
            # Try to read from a backup file if available
            backup_path = FilePath("experiences_backup.json")
            if backup_path.exists():
                try:
                    with open(backup_path, 'r') as f:
                        backup_data = json.load(f)
                    
                    # Check if the backup has the expected structure
                    if isinstance(backup_data, dict) and 'experiences' in backup_data:
                        # Format where experiences are in an 'experiences' key
                        exp_list = backup_data.get('experiences', [])
                    elif isinstance(backup_data, list):
                        # Format where the file is just a list of experiences
                        exp_list = backup_data
                    else:
                        logger.warning("Backup file has unexpected format")
                        exp_list = []
                    
                    # Find the experience with the matching ID
                    for exp in exp_list:
                        if not isinstance(exp, dict):
                            continue
                            
                        exp_id = exp.get("id", None)
                        if exp_id == experience_id or str(exp_id) == experience_id:
                            # Convert to API format
                            logger.info(f"Found experience {experience_id} in backup file")
                            return {
                                "id": exp_id,
                                "text": exp.get("original_text", ""),
                                "company": exp.get("company_name", ""),
                                "role": exp.get("role", None),
                                "duration": exp.get("duration", None),
                                "skills": exp.get("skills", []),
                                "categories": exp.get("categories", []),
                                "relevant_jobs": exp.get("relevant_jobs", []),
                                "created_at": exp.get("created_date", datetime.now().isoformat())
                            }
                    
                    # If we get here, the experience was not found in the backup
                    logger.warning(f"Experience {experience_id} not found in backup file")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, 
                        detail=f"Experience with ID {experience_id} not found"
                    )
                except json.JSONDecodeError as json_err:
                    logger.error(f"Backup file contains invalid JSON: {json_err}")
                except Exception as backup_err:
                    logger.error(f"Error processing backup file: {backup_err}")
            else:
                # If no backup file, raise the original exception
                raise
        except Exception as fallback_error:
            logger.error(f"Fallback mechanism failed: {fallback_error}")
            # If fallback fails, raise the original exception
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Failed to get experience: {e.stderr}"
            )

@router.delete("/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(experience_id: str = FastAPIPath(..., description="The ID of the experience to delete")):
    """Delete an experience by ID"""
    try:
        # Use the delete-experience command with --no-confirm to avoid interactive prompts
        cmd = ["resume-builder", "delete-experience", "--id", experience_id, "--no-confirm"]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Return no content on success
        return None
    except subprocess.CalledProcessError as e:
        error_message = e.stderr if e.stderr else "Unknown error occurred"
        logger.error(f"Failed to delete experience: {error_message}")
        
        if "not found" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experience with ID {experience_id} not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Failed to delete experience: {error_message}"
            )

@router.get("/search/", response_model=List[Experience])
async def search_experiences(query: str = Query(..., min_length=1, description="Search query")):
    """Search experiences by query"""
    try:
        cmd = ["resume-builder", "search", "--query", query]
        # Add JSON output flag if supported
        # cmd.append("--json")
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Mock search results
        # In a real implementation, you would parse the output from the CLI tool
        if "python" in query.lower():
            return [
                {
                    "id": "exp-123",
                    "text": "Led a team of 5 developers to build a scalable microservices architecture using Python and Docker, resulting in 40% improved system performance.",
                    "company": "TechCorp",
                    "role": "Senior Developer",
                    "duration": "Jan 2020 - Dec 2022",
                    "skills": ["Python", "Docker", "Microservices", "Team Leadership"],
                    "categories": ["Backend Development", "DevOps"],
                    "relevant_jobs": ["Senior Developer", "Team Lead"],
                    "created_at": "2023-07-20T15:30:00Z"
                }
            ]
        return []
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to search experiences: {e.stderr}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to search experiences: {e.stderr}"
        )
"""
CLI commands for Resume Builder
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict
import click

from ..core.processor import create_processor
from ..core.job_extractor import create_job_extractor
from ..core.search_optimizer import create_search_optimizer
from ..core.exceptions import (
    ProcessingError, 
    WeaviateError, 
    JobExtractionError,
    ExaError
)
from ..utils.helpers import truncate_text


@click.command()
@click.option(
    '--text', 
    required=True,
    help='Professional experience description text'
)
@click.option(
    '--company', 
    required=True,
    help='Company name where the experience was gained'
)
@click.option(
    '--duration',
    help='Duration of the experience (e.g., "Jan 2020 - Dec 2021")'
)
@click.option(
    '--role',
    help='Job role or title for this experience'
)
@click.option(
    '--extract/--no-extract',
    default=True,
    help='Extract skills and metadata using OpenAI (default: enabled)'
)
@click.option(
    '--validate/--no-validate',
    default=True,
    help='Validate input data (default: enabled)'
)
@click.pass_context
def add_experience_command(ctx: click.Context, text: str, company: str, duration: str = None, role: str = None, extract: bool = True, validate: bool = True):
    """
    Add a new professional experience to your database
    
    This command processes your experience text, optionally extracts skills and metadata
    using OpenAI, and stores everything in Weaviate for future semantic search.
    
    Examples:
    
        # Add experience with automatic extraction
        resume-builder add-experience \\
            --text "Led a team of 5 developers to build a microservices architecture using Python and Docker" \\
            --company "TechCorp Inc"
        
        # Add experience without extraction  
        resume-builder add-experience \\
            --text "Managed customer relationships" \\
            --company "SalesCorp" \\
            --no-extract
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    output_helper.print_info(f"Adding experience for {company}")
    output_helper.print_info(f"Text length: {len(text)} characters")
    output_helper.print_info(f"Extraction: {'enabled' if extract else 'disabled'}")
    
    try:
        # Create and initialize processor
        with create_processor(config, output_helper) as processor:
            # Process the experience
            result = processor.process_experience(
                text=text,
                company=company,
                duration=duration,
                role=role,
                extract_metadata=extract,
                validate_input=validate
            )
            
            if result["success"]:
                output_helper.print_success(f"Successfully added experience: {result['experience_id']}")
                
                # Show extracted information if available
                if extract and result.get("extraction_results"):
                    extraction = result["extraction_results"]
                    
                    if extraction.get("skills"):
                        output_helper.print_info(f"Extracted skills: {', '.join(extraction['skills'])}")
                    
                    if extraction.get("categories"):
                        output_helper.print_info(f"Categories: {', '.join(extraction['categories'])}")
                    
                    if extraction.get("relevant_jobs"):
                        output_helper.print_info(f"Relevant jobs: {', '.join(extraction['relevant_jobs'])}")
                
                # Show processing time
                if result.get("processing_time"):
                    output_helper.print_info(f"Processing time: {result['processing_time']:.2f}s")
            
            else:
                output_helper.print_error("Failed to add experience")
                for error in result.get("errors", []):
                    output_helper.print_error(f"  • {error}")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Failed to add experience: {str(e)}")
        output_helper.print_error(f"Failed to add experience: {str(e)}")
        sys.exit(1)


@click.command()
@click.option(
    '--recreate/--no-recreate',
    default=False,
    help='Recreate the database schema if it already exists'
)
@click.pass_context
def init_db_command(ctx: click.Context, recreate: bool):
    """
    Initialize the database schema
    
    Creates the Experience collection in Weaviate with the proper schema
    for storing professional experiences with vector embeddings.
    
    Examples:
    
        # Initialize database (safe, won't overwrite existing)
        resume-builder init-db
        
        # Recreate database schema (will delete existing data)
        resume-builder init-db --recreate
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    if recreate:
        output_helper.print_warning("Recreating database schema will DELETE ALL existing data!")
        if not click.confirm("Are you sure you want to continue?"):
            output_helper.print_info("Operation cancelled")
            return
    
    try:
        # Create processor to access database
        with create_processor(config, output_helper) as processor:
            
            if recreate and processor.database.schema_exists():
                output_helper.print_info("Deleting existing schema...")
                processor.database.delete_schema()
            
            if not processor.database.schema_exists():
                output_helper.print_info("Creating database schema...")
                processor.database.create_schema()
                output_helper.print_success("Database schema created successfully")
            else:
                output_helper.print_info("Database schema already exists")
            
            # Verify schema
            output_helper.print_info("Verifying database connection...")
            if processor.database.health_check():
                output_helper.print_success("Database is healthy and ready to use")
            else:
                output_helper.print_warning("Database health check failed")
                
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        output_helper.print_error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)


@click.command()
@click.pass_context
def health_check_command(ctx: click.Context):
    """
    Check the health of all system components
    
    Verifies connectivity and status of:
    - OpenAI API connection
    - Weaviate database connection
    - Database schema existence
    
    Returns exit code 0 if all components are healthy, 1 otherwise.
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    output_helper.print_info("Performing health check...")
    
    try:
        # Create processor to check all components
        with create_processor(config, output_helper) as processor:
            health_status = processor.health_check()
            
            # Display results
            output_helper.print_json(health_status, title="Health Check Results")
            
            if health_status["overall_healthy"]:
                output_helper.print_success("All components are healthy")
                sys.exit(0)
            else:
                output_helper.print_error("Some components are unhealthy")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        output_helper.print_error(f"Health check failed: {str(e)}")
        sys.exit(1)


@click.command()
@click.option(
    '--limit',
    type=int,
    default=20,
    help='Maximum number of experiences to list (default: 20)'
)
@click.option(
    '--company',
    help='Filter by company name'
)
@click.option(
    '--format',
    type=click.Choice(['table', 'json', 'brief']),
    default='table',
    help='Output format (default: table)'
)
@click.pass_context
def list_experiences_command(ctx: click.Context, limit: int, company: Optional[str], format: str):
    """
    List stored professional experiences
    
    Display experiences from the database with optional filtering and formatting options.
    
    Examples:
    
        # List recent experiences
        resume-builder list-experiences --limit 10
        
        # Filter by company
        resume-builder list-experiences --company "TechCorp"
        
        # Output as JSON
        resume-builder list-experiences --format json
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    try:
        with create_processor(config, output_helper) as processor:
            breakpoint()
            # Get experiences
            experiences = processor.database.list_experiences(
                limit=limit,
                company_filter=company
            )
            
            if not experiences:
                output_helper.print_info("No experiences found")
                return
            
            if format == 'json':
                # Use raw=True for clean JSON output suitable for API consumption
                json_output = output_helper.print_json(experiences, title=f"Experiences ({len(experiences)} found)", raw=True)
                
            
            elif format == 'brief':
                for i, exp in enumerate(experiences, 1):
                    text_preview = truncate_text(exp.get('original_text', ''), 100)
                    output_helper.print(f"{i}. {exp.get('company_name', 'Unknown')} - {text_preview}")
            
            else:  # table format
                # Prepare data for table
                table_data = []
                for exp in experiences:
                    table_data.append({
                        "Company": exp.get('company_name', 'Unknown'),
                        "Skills": len(exp.get('skills', [])),
                        "Categories": len(exp.get('categories', [])),
                        "Text Preview": truncate_text(exp.get('original_text', ''), 60),
                        "Date": str(exp.get('created_date', ''))[:10] if exp.get('created_date') else 'Unknown'
                    })
                
                output_helper.print_table(table_data, title=f"Professional Experiences ({len(experiences)} found)")
            
            output_helper.print_info(f"Showing {len(experiences)} of {len(experiences)} experiences")
            
    except Exception as e:
        logger.error(f"Failed to list experiences: {str(e)}")
        output_helper.print_error(f"Failed to list experiences: {str(e)}")
        sys.exit(1)


@click.command()
@click.option(
    '--query',
    required=True,
    help='Search query text (e.g., job description or skill keywords)'
)
@click.option(
    '--limit',
    type=int,
    default=10,
    help='Maximum number of results to return (default: 10)'
)
@click.option(
    '--min-score',
    type=float,
    help='Minimum similarity score (0.0 to 1.0)'
)
@click.option(
    '--company',
    help='Filter results by company name'
)
@click.option(
    '--format',
    type=click.Choice(['table', 'json', 'detailed']),
    default='detailed',
    help='Output format (default: detailed)'
)
@click.pass_context
def search_experiences_command(ctx: click.Context, query: str, limit: int, min_score: Optional[float], 
                              company: Optional[str], format: str):
    """
    Search experiences using semantic similarity
    
    Find the most relevant professional experiences for a given query using
    vector similarity search. Great for finding experiences relevant to a job description.
    
    Examples:
    
        # Search for Python development experience
        resume-builder search --query "Python web development Django Flask"
        
        # Search with minimum similarity score
        resume-builder search --query "machine learning" --min-score 0.7
        
        # Search within specific company
        resume-builder search --query "leadership" --company "TechCorp"
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    output_helper.print_info(f"Searching for: '{query}'")
    
    try:
        with create_processor(config, output_helper) as processor:
            # Perform semantic search
            results = processor.database.search_experiences(
                query=query,
                limit=limit,
                min_score=min_score,
                company_filter=company
            )
            
            if not results:
                output_helper.print_info("No matching experiences found")
                return
            
            if format == 'json':
                # Use raw=True for clean JSON output suitable for API consumption
                json_output = output_helper.print_json(results, title=f"Search Results ({len(results)} found)", raw=True)
                print(json_output)
            
            elif format == 'table':
                # Prepare data for table
                table_data = []
                for result in results:
                    table_data.append({
                        "Score": f"{result.get('score', 0):.3f}",
                        "Company": result.get('company_name', 'Unknown'),
                        "Skills": ', '.join(result.get('skills', [])[:3]),  # First 3 skills
                        "Text Preview": truncate_text(result.get('original_text', ''), 80)
                    })
                
                output_helper.print_table(table_data, title=f"Search Results ({len(results)} found)")
            
            else:  # detailed format
                output_helper.print(f"\n🔍 Found {len(results)} relevant experiences:\n")
                
                for i, result in enumerate(results, 1):
                    score = result.get('score', 0)
                    company = result.get('company_name', 'Unknown')
                    skills = result.get('skills', [])
                    categories = result.get('categories', [])
                    text = result.get('original_text', '')
                    
                    output_helper.print(f"#{i} - {company} (Score: {score:.3f})")
                    output_helper.print(f"   Text: {truncate_text(text, 150)}")
                    
                    if skills:
                        output_helper.print(f"   Skills: {', '.join(skills[:5])}")
                    
                    if categories:
                        output_helper.print(f"   Categories: {', '.join(categories)}")
                    
                    output_helper.print("")  # Empty line
            
            # Show search summary
            if min_score:
                output_helper.print_info(f"Filtered by minimum score: {min_score}")
            
            if company:
                output_helper.print_info(f"Filtered by company: {company}")
                
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        output_helper.print_error(f"Search failed: {str(e)}")
        sys.exit(1)


@click.command()
@click.pass_context
def stats_command(ctx: click.Context):
    """
    Show database and usage statistics
    
    Display comprehensive statistics about your stored experiences including:
    - Total number of experiences
    - Top companies, skills, and categories
    - Database information
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    try:
        with create_processor(config, output_helper) as processor:
            stats = processor.get_statistics()
            output_helper.print_json(stats, title="Resume Builder Statistics")
            
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        output_helper.print_error(f"Failed to get statistics: {str(e)}")
        sys.exit(1)


@click.command()
@click.option(
    '--output',
    required=True,
    help='Output file path for backup'
)
@click.pass_context  
def backup_command(ctx: click.Context, output: str):
    """
    Backup all experiences to a JSON file
    
    Creates a complete backup of all your professional experiences
    that can be restored later or transferred to another system.
    
    Examples:
    
        # Backup to file
        resume-builder backup --output experiences_backup.json
        
        # Backup with timestamp
        resume-builder backup --output "backup_$(date +%Y%m%d).json"
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    output_path = Path(output)
    
    # Check if file exists
    if output_path.exists():
        if not click.confirm(f"File {output} already exists. Overwrite?"):
            output_helper.print_info("Backup cancelled")
            return
    
    try:
        with create_processor(config, output_helper) as processor:
            output_helper.print_info(f"Creating backup to {output}...")
            
            success = processor.database.backup_data(str(output_path))
            
            if success:
                output_helper.print_success(f"Backup completed: {output}")
                
                # Show file size
                file_size = output_path.stat().st_size
                output_helper.print_info(f"Backup file size: {file_size:,} bytes")
            else:
                output_helper.print_error("Backup failed")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        output_helper.print_error(f"Backup failed: {str(e)}")
        sys.exit(1)


@click.command()
@click.option(
    '--input',
    required=True,
    help='Input backup file path'
)
@click.option(
    '--confirm/--no-confirm',
    default=True,
    help='Confirm before restoring (default: enabled)'
)
@click.pass_context
def restore_command(ctx: click.Context, input: str, confirm: bool):
    """
    Restore experiences from a backup file
    
    Restores professional experiences from a previously created backup.
    This will add to existing experiences (does not replace).
    
    Examples:
    
        # Restore from backup file
        resume-builder restore --input experiences_backup.json
        
        # Restore without confirmation prompt
        resume-builder restore --input backup.json --no-confirm
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    input_path = Path(input)
    
    if not input_path.exists():
        output_helper.print_error(f"Backup file not found: {input}")
        sys.exit(1)
    
    if confirm:
        output_helper.print_warning("This will add experiences from the backup to your current database.")
        if not click.confirm("Continue with restore?"):
            output_helper.print_info("Restore cancelled")
            return
    
    try:
        with create_processor(config, output_helper) as processor:
            output_helper.print_info(f"Restoring from {input}...")
            
            success = processor.database.restore_data(str(input_path))
            
            if success:
                output_helper.print_success("Restore completed successfully")
            else:
                output_helper.print_error("Restore failed")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}")
        output_helper.print_error(f"Restore failed: {str(e)}")
        sys.exit(1)


@click.command()
@click.option(
    '--url',
    required=True,
    help='Job posting URL to extract and analyze'
)
@click.option(
    '--format',
    type=click.Choice(['json', 'detailed']),
    default='detailed',
    help='Output format (default: detailed)'
)
@click.pass_context
def test_job_extraction_command(ctx: click.Context, url: str, format: str):
    """
    Test job content extraction from URL (Sprint 2 Feature)
    
    Extract and parse job description content from a URL using Exa.ai,
    then generate optimized search queries for matching experiences.
    
    This is a test command for Sprint 2 development.
    
    Examples:
    
        # Extract job content and show details
        resume-builder test-job-extraction --url "https://company.com/job-posting"
        
        # Show results as JSON
        resume-builder test-job-extraction --url "..." --format json
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    # Check if Exa.ai is configured
    if not config.exa_config:
        output_helper.print_error("Exa.ai is not configured. Please set EXA_API_KEY in your environment.")
        output_helper.print_info("Add your Exa.ai API key to .env file: EXA_API_KEY=your_key_here")
        sys.exit(1)
    
    output_helper.print_info(f"🔍 Extracting job content from: {url}")
    
    try:
        # Create job extractor
        job_extractor = create_job_extractor(config)
        
        # Extract job description
        output_helper.print_info("📄 Extracting job description...")
        job_description = job_extractor.extract_job_description(url)
        
        # Generate search queries
        output_helper.print_info("🎯 Generating search queries...")
        search_optimizer = create_search_optimizer(
            enable_diversity=config.job_matching_config.search_diversity
        )
        search_queries = search_optimizer.generate_search_queries(job_description)
        
        if format == 'json':
            # Output everything as JSON
            result = {
                'job_description': job_description.to_dict(),
                'search_queries': search_queries
            }
            # Use raw=True for clean JSON output suitable for API consumption
            json_output = output_helper.print_json(result, title="Job Extraction Results", raw=True)
            print(json_output)
        
        else:  # detailed format
            output_helper.print_success("✅ Job extraction completed!\n")
            
            # Show job details
            output_helper.print("📋 **Job Description Details:**")
            output_helper.print(f"   Title: {job_description.title}")
            output_helper.print(f"   Company: {job_description.company}")
            output_helper.print(f"   Domain: {job_description.get_domain()}")
            output_helper.print(f"   Summary: {job_description.summary[:200]}..." if len(job_description.summary) > 200 else f"   Summary: {job_description.summary}")
            output_helper.print("")
            
            # Show extracted information
            if job_description.skills_mentioned:
                output_helper.print(f"🛠️  **Skills Mentioned ({len(job_description.skills_mentioned)}):**")
                output_helper.print(f"   {', '.join(job_description.skills_mentioned[:10])}")
                if len(job_description.skills_mentioned) > 10:
                    output_helper.print(f"   ... and {len(job_description.skills_mentioned) - 10} more")
                output_helper.print("")
            
            if job_description.requirements:
                output_helper.print(f"📝 **Requirements ({len(job_description.requirements)}):**")
                for i, req in enumerate(job_description.requirements[:5], 1):
                    output_helper.print(f"   {i}. {req[:100]}..." if len(req) > 100 else f"   {i}. {req}")
                if len(job_description.requirements) > 5:
                    output_helper.print(f"   ... and {len(job_description.requirements) - 5} more")
                output_helper.print("")
            
            if job_description.responsibilities:
                output_helper.print(f"📋 **Responsibilities ({len(job_description.responsibilities)}):**")
                for i, resp in enumerate(job_description.responsibilities[:5], 1):
                    output_helper.print(f"   {i}. {resp[:100]}..." if len(resp) > 100 else f"   {i}. {resp}")
                if len(job_description.responsibilities) > 5:
                    output_helper.print(f"   ... and {len(job_description.responsibilities) - 5} more")
                output_helper.print("")
            
            # Show search queries
            if search_queries:
                output_helper.print(f"🔍 **Generated Search Queries ({len(search_queries)}):**")
                for i, query in enumerate(search_queries, 1):
                    query_type = query.get('type', 'unknown').replace('_', ' ').title()
                    priority = query.get('priority', 0)
                    output_helper.print(f"   {i}. [{query_type}] (Priority: {priority:.1f}) \"{query['query']}\"")
                output_helper.print("")
            
            # Show all keywords
            all_keywords = job_description.get_all_keywords()
            if all_keywords:
                output_helper.print(f"🏷️  **All Keywords ({len(all_keywords)}):**")
                output_helper.print(f"   {', '.join(all_keywords[:15])}")
                if len(all_keywords) > 15:
                    output_helper.print(f"   ... and {len(all_keywords) - 15} more")
                output_helper.print("")
            
            output_helper.print_success("🎉 Ready for experience matching!")
            output_helper.print_info("💡 This job description can now be used to find relevant experiences from your database.")
    
    except JobExtractionError as e:
        output_helper.print_error(f"Job extraction failed: {str(e)}")
        sys.exit(1)
    except ExaError as e:
        output_helper.print_error(f"Exa.ai error: {str(e)}")
        output_helper.print_info("Please check your EXA_API_KEY and internet connection.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test job extraction failed: {str(e)}")
        output_helper.print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)


@click.command()
@click.option('--url', help='Job posting URL to analyze')
@click.option('--title', help='Job title (for manual input)')
@click.option('--company', help='Company name (for manual input)')
@click.option('--description', help='Job description text (for manual input)')
@click.option('--max-experiences', type=int, default=5, help='Maximum experiences to return (default: 5)')
@click.option('--min-score', type=float, default=0.3, help='Minimum relevance score (default: 0.3)')
@click.option('--refinement', type=click.Choice(['general', 'job_specific', 'skills_focused']), 
              default='job_specific', help='Type of experience refinement (default: job_specific)')
@click.option('--format', 'output_format', type=click.Choice(['detailed', 'summary', 'json']), 
              default='detailed', help='Output format (default: detailed)')
@click.option('--save', help='Save results to file (JSON format)')
@click.pass_context
def match_job_command(ctx: click.Context, url: str, title: str, company: str, description: str,
                     max_experiences: int, min_score: float, refinement: str, 
                     output_format: str, save: str):
    """
    Find and refine experiences matching a job description
    
    Extract job requirements from a URL or manual input, then find and refine
    your most relevant professional experiences with AI-powered tailoring.
    
    Examples:
    
        # Match experiences to a job URL
        resume-builder match-job --url "https://company.com/job-posting"
        
        # Manual job description input
        resume-builder match-job --title "Software Engineer" --company "TechCorp" 
        --description "We need a Python developer with React experience..."
        
        # Customize matching parameters
        resume-builder match-job --url "..." --max-experiences 10 --min-score 0.5
        
        # Save results to file
        resume-builder match-job --url "..." --save "job_match_results.json"
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    try:
        # Validate input
        if not url and not (title and company and description):
            raise click.ClickException(
                "Either --url OR (--title, --company, --description) must be provided"
            )
        
        # Initialize job matcher
        output_helper.print_info("🚀 Initializing job matcher components...")
        
        from ..core.job_matcher import create_job_matcher
        job_matcher = create_job_matcher(config)
        
        # Initialize components asynchronously  
        import asyncio
        asyncio.run(job_matcher.initialize_components())
        
        output_helper.print_info("📊 Starting job matching workflow...")
        
        # Perform job matching
        if url:
            output_helper.print_info(f"🔗 Processing job URL: {url}")
            job_match_result = job_matcher.match_job_from_url(
                job_url=url,
                refinement_type=refinement
            )
        else:
            output_helper.print_info(f"📝 Processing manual job description: {title} at {company}")
            job_match_result = job_matcher.match_job_from_description(
                job_title=title,
                company=company,
                job_description_text=description,
                refinement_type=refinement
            )
        
        # Filter by parameters
        filtered_experiences = [
            exp for exp in job_match_result.refined_experiences 
            if exp.relevance_score >= min_score
        ][:max_experiences]
        
        # Update result with filtered experiences
        job_match_result.refined_experiences = filtered_experiences
        
        output_helper.print_success(f"✅ Job matching completed! Found {len(filtered_experiences)} relevant experiences.")
        
        # Display results based on format
        _display_job_match_results(output_helper, job_match_result, output_format)
        
        # Save results if requested
        if save:
            _save_job_match_results(job_match_result, save, output_helper)
        
        # Show statistics
        stats = job_matcher.get_matching_stats()
        output_helper.print_info(f"📈 Matching efficiency: {stats['success_rate']:.1%} success rate")
        
    except Exception as e:
        logger.error(f"Job matching failed: {str(e)}")
        output_helper.print_error(f"Job matching failed: {str(e)}")
        sys.exit(1)


@click.command()
@click.option('--experience-id', help='ID of specific experience to refine')
@click.option('--company', help='Filter by company name')
@click.option('--job-title', help='Target job title for refinement')
@click.option('--job-company', help='Target job company')
@click.option('--job-skills', help='Comma-separated list of target job skills')
@click.option('--refinement-type', type=click.Choice(['general', 'job_specific', 'skills_focused']),
              default='general', help='Type of refinement (default: general)')
@click.option('--format', 'output_format', type=click.Choice(['detailed', 'json']),
              default='detailed', help='Output format (default: detailed)')
@click.pass_context
def refine_experience_command(ctx: click.Context, experience_id: str, company: str, 
                             job_title: str, job_company: str, job_skills: str,
                             refinement_type: str, output_format: str):
    """
    Refine specific experiences with AI-powered enhancement
    
    Polish raw professional experiences into compelling resume accomplishments
    with optional job-specific tailoring.
    
    Examples:
    
        # Refine specific experience by ID
        resume-builder refine-experience --experience-id "abc123"
        
        # Refine all experiences from a company
        resume-builder refine-experience --company "TechCorp"
        
        # Job-specific refinement
        resume-builder refine-experience --company "TechCorp" --job-title "Senior Developer" 
        --job-company "NewCorp" --job-skills "Python,React,AWS"
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    try:
        from ..core.experience_refiner import create_experience_refiner
        
        # Initialize components
        experience_processor = create_processor(config, output_helper)
        experience_refiner = create_experience_refiner(config)
        
        # Get experiences to refine
        with experience_processor:
            if experience_id:
                # Get specific experience by ID
                exp_dict = experience_processor.database.get_experience_by_id(experience_id)
                experiences = [_dict_to_experience(exp_dict)] if exp_dict else []
            elif company:
                # Search by company name
                exp_dicts = experience_processor.database.search_experiences(
                    query=company,
                    limit=50
                )
                # Filter by company name and convert to Experience objects
                experiences = []
                for exp_dict in exp_dicts:
                    if company.lower() in exp_dict.get('company_name', '').lower():
                        experiences.append(_dict_to_experience(exp_dict))
            else:
                raise click.ClickException("Either --experience-id or --company must be provided")
        
        if not experiences:
            output_helper.print_warning("No experiences found matching the criteria")
            return
        
        output_helper.print_info(f"🔧 Refining {len(experiences)} experience(s)...")
        
        # Create job context if provided
        job_context = None
        if job_title or job_company or job_skills:
            from ..models.job_description import JobDescription
            
            skills_list = job_skills.split(',') if job_skills else []
            skills_list = [s.strip() for s in skills_list]  # Clean whitespace
            
            full_text = f"Target position: {job_title or 'Not specified'} at {job_company or 'Target Company'}. Required skills: {', '.join(skills_list)}. This is a manual job context created for experience refinement."
            
            job_context = JobDescription(
                title=job_title or "Target Position",
                company=job_company or "Target Company", 
                url="https://manual-input.example.com",  # Valid URL format for manual input
                full_text=full_text,
                summary=f"Target position requiring: {', '.join(skills_list)}",
                skills_mentioned=skills_list,
                extracted_keywords=skills_list
            )
        
        # Refine experiences
        refined_experiences = []
        for experience in experiences:
            try:
                refined_exp = experience_refiner.refine_experience(
                    experience, job_context, refinement_type
                )
                refined_experiences.append(refined_exp)
                output_helper.print_success(f"✅ Refined: {experience.company}")
            except Exception as e:
                output_helper.print_error(f"❌ Failed to refine {experience.company}: {str(e)}")
        
        # Display results
        _display_refined_experiences(output_helper, refined_experiences, output_format)
        
        # Show refinement statistics
        stats = experience_refiner.get_refinement_stats()
        output_helper.print_info(f"📊 Refinement stats: {stats['success_rate']:.1%} success rate")
        
    except Exception as e:
        logger.error(f"Experience refinement failed: {str(e)}")
        output_helper.print_error(f"Experience refinement failed: {str(e)}")
        sys.exit(1)


@click.command()
@click.option(
    '--id',
    required=True,
    help='ID of the experience to delete'
)
@click.option(
    '--confirm/--no-confirm',
    default=True,
    help='Confirm before deleting (default: enabled)'
)
@click.pass_context
def delete_experience_command(ctx: click.Context, id: str, confirm: bool):
    """
    Delete a specific experience by ID
    
    This command removes an experience from the database permanently.
    Use with caution as this action cannot be undone.
    """
    config = ctx.obj['config']
    output_helper = ctx.obj['output_helper']
    logger = ctx.obj['logger']
    
    output_helper.print_info(f"Preparing to delete experience with ID: {id}")
    
    # Confirm deletion if required
    if confirm:
        if not click.confirm("Are you sure you want to delete this experience? This action cannot be undone."):
            output_helper.print_warning("Deletion cancelled by user")
            return
    
    try:
        # Create and initialize processor
        with create_processor(config, output_helper) as processor:
            # Delete the experience
            success = processor.database.delete_experience(id)
            
            if success:
                output_helper.print_success(f"Successfully deleted experience with ID: {id}")
            else:
                output_helper.print_error(f"Failed to delete experience with ID: {id}")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Failed to delete experience: {str(e)}")
        output_helper.print_error(f"Failed to delete experience: {str(e)}")
        sys.exit(1)


# Helper functions for displaying results

def _dict_to_experience(exp_dict: Dict) -> 'Experience':
    """Convert database dictionary to Experience object"""
    from ..models.experience import Experience
    
    return Experience(
        id=exp_dict.get('id', str(hash(exp_dict.get('original_text', '')))),
        company=exp_dict.get('company_name', 'Unknown'),
        text=exp_dict.get('original_text', ''),
        role=None,  # Not stored in current database
        duration=None,  # Not stored in current database  
        skills=exp_dict.get('skills', []),
        categories=exp_dict.get('categories', []),
        created_at=exp_dict.get('created_date')
    )

def _display_job_match_results(output_helper, job_match_result, output_format: str):
    """Display job matching results in the specified format"""
    
    if output_format == 'json':
        result_dict = {
            "job_description": {
                "title": job_match_result.job_description.title,
                "company": job_match_result.job_description.company,
                "summary": job_match_result.job_description.summary,
                "skills_mentioned": job_match_result.job_description.skills_mentioned,
                "extracted_keywords": job_match_result.job_description.extracted_keywords
            },
            "refined_experiences": [
                {
                    "company": exp.company,
                    "role": exp.role,
                    "accomplishments": exp.accomplishments,
                    "skills": exp.skills,
                    "tools_technologies": exp.tools_technologies,
                    "relevance_score": exp.relevance_score,
                    "confidence_score": exp.confidence_score
                } for exp in job_match_result.refined_experiences
            ],
            "summary": {
                "total_experiences": len(job_match_result.refined_experiences),
                "overall_match_score": job_match_result.overall_match_score,
                "aggregated_skills": job_match_result.aggregated_skills,
                "aggregated_tools": job_match_result.aggregated_tools
            }
        }
        # Use raw=True for clean JSON output suitable for API consumption
        json_output = output_helper.print_json(result_dict, title="Job Matching Results", raw=True)
        print(json_output)
    
    elif output_format == 'summary':
        # Brief summary format
        output_helper.print("\n📋 **Job Summary:**")
        output_helper.print(f"   Position: {job_match_result.job_description.title}")
        output_helper.print(f"   Company: {job_match_result.job_description.company}")
        output_helper.print(f"   Overall Match: {job_match_result.overall_match_score:.1%}")
        output_helper.print("")
        
        output_helper.print(f"\n🎯 **Top {len(job_match_result.refined_experiences)} Matching Experiences:**")
        for i, exp in enumerate(job_match_result.refined_experiences, 1):
            output_helper.print(f"   {i}. {exp.company} ({exp.role or 'Role not specified'}) - Score: {exp.relevance_score:.2f}")
        
        if job_match_result.aggregated_skills:
            output_helper.print("\n🛠️  **Key Skills Found:**")
            output_helper.print(f"   {', '.join(job_match_result.aggregated_skills[:10])}")
    
    else:  # detailed format
        output_helper.print("\n📋 **Job Description:**")
        output_helper.print(f"   Position: {job_match_result.job_description.title}")
        output_helper.print(f"   Company: {job_match_result.job_description.company}")
        output_helper.print(f"   Summary: {job_match_result.job_description.summary[:200]}...")
        output_helper.print(f"   Overall Match Score: {job_match_result.overall_match_score:.1%}")
        output_helper.print("")
        
        for i, exp in enumerate(job_match_result.refined_experiences, 1):
            output_helper.print(f"\n🏢 **Experience {i}: {exp.company}** ({exp.role or 'Role not specified'})")
            output_helper.print(f"   Relevance Score: {exp.relevance_score:.2f} | Confidence: {exp.confidence_score:.2f}")
            output_helper.print("")
            
            output_helper.print("   **Refined Accomplishments:**")
            for j, accomplishment in enumerate(exp.accomplishments, 1):
                output_helper.print(f"      {j}. {accomplishment}")
            output_helper.print("")
            
            if exp.skills:
                output_helper.print(f"   **Key Skills:** {', '.join(exp.skills[:8])}")
            
            if exp.tools_technologies:
                output_helper.print(f"   **Tools & Technologies:** {', '.join(exp.tools_technologies[:8])}")
            
            if exp.keywords_matched:
                output_helper.print(f"   **Keywords Matched:** {', '.join(exp.keywords_matched[:6])}")
            
            if exp.refinement_notes:
                output_helper.print(f"   **Notes:** {exp.refinement_notes}")
            
            output_helper.print("")  # Spacing between experiences
        
        # Show aggregated information
        if job_match_result.aggregated_skills:
            output_helper.print("\n🛠️  **All Skills Found:**")
            output_helper.print(f"   {', '.join(job_match_result.aggregated_skills)}")
        
        if job_match_result.aggregated_tools:
            output_helper.print("\n🔧 **Tools & Technologies:**")
            output_helper.print(f"   {', '.join(job_match_result.aggregated_tools)}")


def _display_refined_experiences(output_helper, refined_experiences, output_format: str):
    """Display refined experiences in the specified format"""
    
    if output_format == 'json':
        result = {
            "refined_experiences": [
                {
                    "company": exp.company,
                    "role": exp.role,
                    "accomplishments": exp.accomplishments,
                    "skills": exp.skills,
                    "tools_technologies": exp.tools_technologies,
                    "relevance_score": exp.relevance_score,
                    "confidence_score": exp.confidence_score,
                    "refinement_notes": exp.refinement_notes
                } for exp in refined_experiences
            ]
        }
        # Use raw=True for clean JSON output suitable for API consumption
        json_output = output_helper.print_json(result, title="Refined Experiences", raw=True)
        print(json_output)
    else:
        for i, refined_exp in enumerate(refined_experiences, 1):
            output_helper.print(f"\n🏢 **{refined_exp.company}** ({refined_exp.role or 'Not specified'})")
            
            output_helper.print("**Refined Accomplishments:**")
            for j, accomplishment in enumerate(refined_exp.accomplishments, 1):
                output_helper.print(f"   {j}. {accomplishment}")
            
            if refined_exp.skills:
                output_helper.print(f"**Key Skills:** {', '.join(refined_exp.skills[:10])}")
            
            if refined_exp.tools_technologies:
                output_helper.print(f"**Tools & Technologies:** {', '.join(refined_exp.tools_technologies)}")
            
            output_helper.print(f"**Relevance Score:** {refined_exp.relevance_score:.2f}")
            output_helper.print(f"**Confidence Score:** {refined_exp.confidence_score:.2f}")
            
            if refined_exp.refinement_notes:
                output_helper.print(f"**Notes:** {refined_exp.refinement_notes}")
            
            if i < len(refined_experiences):
                output_helper.print("")  # Spacing between experiences


def _save_job_match_results(job_match_result, save_path: str, output_helper):
    """Save job matching results to file"""
    import json
    from pathlib import Path
    
    try:
        result_dict = {
            "job_description": {
                "title": job_match_result.job_description.title,
                "company": job_match_result.job_description.company,
                "url": job_match_result.job_description.url,
                "summary": job_match_result.job_description.summary,
                "skills_mentioned": job_match_result.job_description.skills_mentioned,
                "extracted_keywords": job_match_result.job_description.extracted_keywords,
                "categories": job_match_result.job_description.categories,
                "inferred_industry": job_match_result.job_description.inferred_industry
            },
            "refined_experiences": [
                {
                    "original_experience_id": exp.original_experience_id,
                    "company": exp.company,
                    "role": exp.role,
                    "accomplishments": exp.accomplishments,
                    "skills": exp.skills,
                    "tools_technologies": exp.tools_technologies,
                    "relevance_score": exp.relevance_score,
                    "confidence_score": exp.confidence_score,
                    "keywords_matched": exp.keywords_matched,
                    "refinement_notes": exp.refinement_notes
                } for exp in job_match_result.refined_experiences
            ],
            "summary": {
                "total_experiences": len(job_match_result.refined_experiences),
                "overall_match_score": job_match_result.overall_match_score,
                "aggregated_skills": job_match_result.aggregated_skills,
                "aggregated_tools": job_match_result.aggregated_tools,
                "search_queries_used": job_match_result.search_queries_used,
                "matching_summary": job_match_result.matching_summary
            },
            "generated_at": job_match_result.job_description.created_at.isoformat()
        }
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        
        output_helper.print_success(f"💾 Results saved to: {save_path}")
        
        # Show file size
        file_size = Path(save_path).stat().st_size
        output_helper.print_info(f"File size: {file_size:,} bytes")
        
    except Exception as e:
        output_helper.print_error(f"Failed to save results: {str(e)}")
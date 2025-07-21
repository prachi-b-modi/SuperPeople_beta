"""
Main CLI entry point for Resume Builder
"""

import sys
from pathlib import Path
import click
from typing import Optional

from ..config.settings import load_config, Config
from ..utils.logger import setup_logging, get_logger
from ..utils.helpers import RichOutputHelper, get_missing_env_vars
from ..core.exceptions import ResumeBuilderError, ConfigurationError, EnvironmentError
from .commands import (
    add_experience_command,
    init_db_command,
    health_check_command,
    list_experiences_command,
    search_experiences_command,
    stats_command,
    backup_command,
    restore_command,
    test_job_extraction_command,
    match_job_command,
    refine_experience_command,
    delete_experience_command
)

# Global variables for CLI context
_config: Optional[Config] = None
_output_helper: Optional[RichOutputHelper] = None
_logger = None


def _setup_cli_context(config_path: str, debug: bool) -> None:
    """Setup CLI context with configuration and logging"""
    global _config, _output_helper, _logger
    
    try:
        # Load configuration
        _config = load_config(config_path)
        
        # Setup logging
        if debug:
            _config.logging.level = "DEBUG"
        
        _logger = setup_logging(_config.logging_config)
        
        # Setup output helper
        _output_helper = RichOutputHelper(enabled=_config.app_config.enable_rich_output)
        
        _logger.info(f"CLI initialized with config: {config_path}")
        
    except Exception as e:
        # Fallback output if Rich isn't available
        click.echo(f"Error: Failed to initialize CLI: {str(e)}", err=True)
        sys.exit(1)


def _check_environment() -> None:
    """Check required environment variables"""
    required_vars = ["OPENAI_API_KEY"]
    
    # Add Weaviate cloud vars if using cloud
    if _config and _config.weaviate_config.type == "cloud":
        required_vars.extend(["WEAVIATE_CLUSTER_URL", "WEAVIATE_API_KEY"])
    
    missing_vars = get_missing_env_vars(required_vars)
    
    if missing_vars:
        if _output_helper:
            _output_helper.print_error(f"Missing required environment variables: {', '.join(missing_vars)}")
            _output_helper.print_info("Please set these variables or update your configuration file.")
        else:
            click.echo(f"Error: Missing environment variables: {', '.join(missing_vars)}", err=True)
        
        raise EnvironmentError(missing_vars)


@click.group()
@click.option(
    '--config', 
    default=None,
    help='Path to configuration file (default: use built-in config)'
)
@click.option(
    '--debug/--no-debug',
    default=False,
    help='Enable debug logging'
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[str], debug: bool):
    """
    Resume Builder CLI - Manage your professional experiences with AI-powered extraction and semantic search
    
    This tool helps you store and organize your professional experiences using OpenAI for
    information extraction and Weaviate for vector storage and semantic search.
    
    Examples:
    
        # Add a new experience
        resume-builder add-experience --text "Led a team of developers..." --company "TechCorp"
        
        # Initialize database
        resume-builder init-db
        
        # List all experiences
        resume-builder list-experiences
        
        # Search experiences
        resume-builder search --query "Python development"
    """
    # Ensure object exists for subcommands
    ctx.ensure_object(dict)
    
    # Determine config path
    if config is None:
        # Use default config from package
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    else:
        config_path = Path(config)
    
    if not config_path.exists():
        click.echo(f"Error: Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    
    # Setup CLI context
    _setup_cli_context(str(config_path), debug)
    
    # Store in context for subcommands
    ctx.obj['config'] = _config
    ctx.obj['output_helper'] = _output_helper
    ctx.obj['logger'] = _logger
    
    # Check environment variables
    try:
        _check_environment()
    except EnvironmentError:
        sys.exit(1)


# Add subcommands
cli.add_command(add_experience_command, name="add-experience")
cli.add_command(init_db_command, name="init-db")
cli.add_command(health_check_command, name="health-check")
cli.add_command(list_experiences_command, name="list-experiences")
cli.add_command(search_experiences_command, name="search")
cli.add_command(stats_command, name="stats")
cli.add_command(backup_command, name="backup")
cli.add_command(restore_command, name="restore")
cli.add_command(test_job_extraction_command, name="test-job-extraction")
cli.add_command(match_job_command, name="match-job")
cli.add_command(refine_experience_command, name="refine-experience")
cli.add_command(delete_experience_command, name="delete-experience")


@cli.command()
@click.pass_context
def version(ctx: click.Context):
    """Show version information"""
    output_helper = ctx.obj['output_helper']
    
    from .. import __version__, __author__, __description__
    
    version_info = {
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "config_path": str(_config.config_path) if _config else "Unknown",
        "database_type": _config.weaviate_config.type if _config else "Unknown"
    }
    
    # Version info is typically viewed by humans, so we keep the formatted output
    output_helper.print_json(version_info, title="Resume Builder CLI - Version Information")


@cli.command()
@click.pass_context
def config_info(ctx: click.Context):
    """Show current configuration"""
    output_helper = ctx.obj['output_helper']
    config = ctx.obj['config']
    
    # Create safe config info (without sensitive data)
    config_info = {
        "config_file": str(config.config_path),
        "openai": {
            "model": config.openai_config.model,
            "temperature": config.openai_config.extraction_temperature,
            "max_retries": config.openai_config.max_retries,
            "api_key_set": bool(config.openai_config.api_key)
        },
        "exa": {
            "configured": bool(config.exa_config),
            "api_key_set": bool(config.exa_config and config.exa_config.api_key) if config.exa_config else False,
            "base_url": config.exa_config.base_url if config.exa_config else None,
            "timeout": config.exa_config.timeout if config.exa_config else None,
            "max_retries": config.exa_config.max_retries if config.exa_config else None
        } if config.exa_config else {"configured": False},
        "job_matching": {
            "max_experiences": config.job_matching_config.max_experiences_to_match,
            "min_relevance_score": config.job_matching_config.min_relevance_score,
            "search_diversity": config.job_matching_config.search_diversity,
            "refinement_enabled": config.job_matching_config.refinement_enabled,
            "caching_enabled": config.job_matching_config.enable_caching
        },
        "weaviate": {
            "type": config.weaviate_config.type,
            "collection_name": config.weaviate_config.collection.name,
            "vectorizer": config.weaviate_config.collection.vectorizer
        },
        "logging": {
            "level": config.logging_config.level,
            "file": config.logging_config.file
        },
        "app": {
            "retry_attempts": config.app_config.retry_attempts,
            "rich_output": config.app_config.enable_rich_output
        }
    }
    
    # Config info is typically viewed by humans, so we keep the formatted output
    output_helper.print_json(config_info, title="Current Configuration")


def handle_cli_error(func):
    """Decorator to handle CLI errors gracefully"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ResumeBuilderError as e:
            if _output_helper:
                _output_helper.print_error(f"Resume Builder Error: {str(e)}")
            else:
                click.echo(f"Error: {str(e)}", err=True)
            sys.exit(1)
        except KeyboardInterrupt:
            if _output_helper:
                _output_helper.print_warning("Operation cancelled by user")
            else:
                click.echo("Operation cancelled", err=True)
            sys.exit(130)
        except Exception as e:
            if _logger:
                _logger.exception("Unexpected error in CLI")
            
            if _output_helper:
                _output_helper.print_error(f"Unexpected error: {str(e)}")
                _output_helper.print_info("Use --debug for more details")
            else:
                click.echo(f"Unexpected error: {str(e)}", err=True)
            sys.exit(1)
    
    return wrapper


# Apply error handling to the main CLI group
cli = handle_cli_error(cli)


def main():
    """Main entry point for the CLI"""
    cli()


if __name__ == "__main__":
    main()
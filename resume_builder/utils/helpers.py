"""
General utility functions for Resume Builder CLI
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table


def format_datetime(dt: datetime, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime object to string
    
    Args:
        dt: Datetime object
        format_string: Format string
        
    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_string)


def parse_datetime(dt_string: str, format_string: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse datetime string to datetime object
    
    Args:
        dt_string: Datetime string
        format_string: Format string
        
    Returns:
        Parsed datetime object
    """
    return datetime.strptime(dt_string, format_string)


def safe_json_loads(json_string: str) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON string
    
    Args:
        json_string: JSON string to parse
        
    Returns:
        Parsed JSON or None if invalid
    """
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return None


def safe_json_dumps(data: Any, indent: int = 2) -> str:
    """
    Safely serialize data to JSON string
    
    Args:
        data: Data to serialize
        indent: JSON indentation
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(data, indent=indent, default=str)
    except (TypeError, ValueError):
        return "{}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def normalize_text(text: str) -> str:
    """
    Normalize text for processing
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    # Remove extra whitespace
    text = " ".join(text.split())
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def ensure_list(value: Union[str, List[str]]) -> List[str]:
    """
    Ensure value is a list
    
    Args:
        value: String or list of strings
        
    Returns:
        List of strings
    """
    if isinstance(value, str):
        return [value]
    elif isinstance(value, list):
        return value
    else:
        return []


def create_file_backup(file_path: Union[str, Path], suffix: str = ".bak") -> Path:
    """
    Create a backup of a file
    
    Args:
        file_path: Path to file to backup
        suffix: Backup file suffix
        
    Returns:
        Path to backup file
    """
    original_path = Path(file_path)
    backup_path = original_path.with_suffix(original_path.suffix + suffix)
    
    if original_path.exists():
        import shutil
        shutil.copy2(original_path, backup_path)
    
    return backup_path


class RichOutputHelper:
    """Helper class for Rich console output"""
    
    def __init__(self, enabled: bool = True):
        """
        Initialize Rich output helper
        
        Args:
            enabled: Whether Rich output is enabled
        """
        self.enabled = enabled
        self.console = Console() if enabled else None
    
    def print(self, *args, **kwargs):
        """Print with Rich formatting if enabled"""
        if self.enabled and self.console:
            self.console.print(*args, **kwargs)
        else:
            print(*args)
    
    def print_json(self, data: Dict[str, Any], title: str = "JSON Data", raw: bool = False) -> str:
        """Return JSON data as string
        
        Args:
            data: Data to convert to JSON
            title: Title for the JSON (used only for formatted display)
            raw: If True, return raw JSON without formatting (for API consumption)
            
        Returns:
            JSON string representation of the data
        """
        json_str = safe_json_dumps(data)
        
        if raw:
            # Return raw JSON without any formatting or decorations
            return json_str
            
        # For non-raw mode, still display formatted output but also return the JSON
        if self.enabled and self.console:
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
            panel = Panel(syntax, title=title, expand=False)
            self.console.print(panel)
        else:
            print(f"\n{title}:")
            print(json_str)
            
        return json_str
    
    def print_table(self, data: List[Dict[str, Any]], title: str = "Data Table"):
        """Print data as a table"""
        if not data:
            self.print("No data to display")
            return
        
        if self.enabled and self.console:
            table = Table(title=title)
            
            # Add columns
            for key in data[0].keys():
                table.add_column(key.replace("_", " ").title())
            
            # Add rows
            for row in data:
                table.add_row(*[str(value) for value in row.values()])
            
            self.console.print(table)
        else:
            print(f"\n{title}:")
            for i, row in enumerate(data):
                print(f"Row {i + 1}:")
                for key, value in row.items():
                    print(f"  {key}: {value}")
                print()
    
    def print_success(self, message: str):
        """Print success message"""
        if self.enabled and self.console:
            self.console.print(f"✅ {message}", style="bold green")
        else:
            print(f"SUCCESS: {message}")
    
    def print_error(self, message: str):
        """Print error message"""
        if self.enabled and self.console:
            self.console.print(f"❌ {message}", style="bold red")
        else:
            print(f"ERROR: {message}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        if self.enabled and self.console:
            self.console.print(f"⚠️ {message}", style="bold yellow")
        else:
            print(f"WARNING: {message}")
    
    def print_info(self, message: str):
        """Print info message"""
        if self.enabled and self.console:
            self.console.print(f"ℹ️ {message}", style="bold blue")
        else:
            print(f"INFO: {message}")


def validate_environment_variables(required_vars: List[str]) -> Dict[str, Optional[str]]:
    """
    Validate that required environment variables are set
    
    Args:
        required_vars: List of required environment variable names
        
    Returns:
        Dictionary mapping variable names to values (None if not set)
    """
    import os
    return {var: os.getenv(var) for var in required_vars}


def get_missing_env_vars(required_vars: List[str]) -> List[str]:
    """
    Get list of missing environment variables
    
    Args:
        required_vars: List of required environment variable names
        
    Returns:
        List of missing variable names
    """
    env_vars = validate_environment_variables(required_vars)
    return [var for var, value in env_vars.items() if value is None]
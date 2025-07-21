"""
Logging utilities for Resume Builder CLI
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from rich.logging import RichHandler

from ..config.settings import LoggingConfig


def setup_logging(config: LoggingConfig, name: str = "resume_builder") -> logging.Logger:
    """
    Set up logging configuration
    
    Args:
        config: Logging configuration
        name: Logger name
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set log level
    level = getattr(logging, config.level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(config.format)
    
    # Set up handlers
    if config.file:
        # File handler
        file_path = Path(config.file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        # Console handler with Rich formatting
        console_handler = RichHandler(
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger


def get_logger(name: str = "resume_builder") -> logging.Logger:
    """
    Get logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class ContextualLogger:
    """Logger with contextual information"""
    
    def __init__(self, logger: logging.Logger, context: Optional[dict] = None):
        """
        Initialize contextual logger
        
        Args:
            logger: Base logger
            context: Additional context to include in logs
        """
        self.logger = logger
        self.context = context or {}
    
    def _format_message(self, msg: str) -> str:
        """Format message with context"""
        if self.context:
            context_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
            return f"[{context_str}] {msg}"
        return msg
    
    def debug(self, msg: str, **kwargs):
        """Log debug message"""
        self.logger.debug(self._format_message(msg), **kwargs)
    
    def info(self, msg: str, **kwargs):
        """Log info message"""
        self.logger.info(self._format_message(msg), **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """Log warning message"""
        self.logger.warning(self._format_message(msg), **kwargs)
    
    def error(self, msg: str, **kwargs):
        """Log error message"""
        self.logger.error(self._format_message(msg), **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """Log critical message"""
        self.logger.critical(self._format_message(msg), **kwargs)
    
    def exception(self, msg: str, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(self._format_message(msg), **kwargs)
    
    def with_context(self, **context) -> 'ContextualLogger':
        """Create a new logger with additional context"""
        new_context = {**self.context, **context}
        return ContextualLogger(self.logger, new_context) 
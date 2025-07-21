"""
Custom exceptions for Resume Builder CLI
"""


class ResumeBuilderError(Exception):
    """Base exception for Resume Builder CLI"""
    pass


class ConfigurationError(ResumeBuilderError):
    """Raised when there's a configuration error"""
    pass


class OpenAIError(ResumeBuilderError):
    """Base exception for OpenAI-related errors"""
    pass


class OpenAIAPIError(OpenAIError):
    """Raised when OpenAI API call fails"""
    pass


class OpenAIRateLimitError(OpenAIError):
    """Raised when OpenAI rate limit is exceeded"""
    pass


class OpenAIExtractionError(OpenAIError):
    """Raised when OpenAI extraction fails or returns invalid data"""
    pass


class WeaviateError(ResumeBuilderError):
    """Base exception for Weaviate-related errors"""
    pass


class WeaviateConnectionError(WeaviateError):
    """Raised when unable to connect to Weaviate"""
    pass


class WeaviateSchemaError(WeaviateError):
    """Raised when there's a schema-related error"""
    pass


class WeaviateDataError(WeaviateError):
    """Raised when there's a data operation error"""
    pass


class ValidationError(ResumeBuilderError):
    """Raised when data validation fails"""
    pass


class ProcessingError(ResumeBuilderError):
    """Raised when data processing fails"""
    pass


class ExaError(ResumeBuilderError):
    """Base exception for Exa.ai-related errors"""
    pass


class ExaAPIError(ExaError):
    """Raised when Exa.ai API call fails"""
    pass


class ExaRateLimitError(ExaError):
    """Raised when Exa.ai rate limit is exceeded"""
    pass


class ExaContentExtractionError(ExaError):
    """Raised when content extraction from URL fails"""
    pass


class JobMatchingError(ResumeBuilderError):
    """Base exception for job matching errors"""
    pass


class URLValidationError(JobMatchingError):
    """Raised when URL validation fails"""
    pass


class JobExtractionError(JobMatchingError):
    """Raised when job description extraction fails"""
    pass


class ExperienceRefinementError(JobMatchingError):
    """Raised when experience refinement fails"""
    pass


class OpenAIIntegrationError(ResumeBuilderError):
    """Raised when OpenAI API integration fails"""
    pass


class ValidationError(ResumeBuilderError):
    """Raised when data validation fails"""
    pass


class ContentExtractionError(ResumeBuilderError):
    """Raised when content extraction fails"""
    pass


class CLIError(ResumeBuilderError):
    """Raised when there's a CLI-related error"""
    pass


class EnvironmentError(ResumeBuilderError):
    """Raised when required environment variables are missing"""
    
    def __init__(self, missing_vars: list):
        """
        Initialize with missing environment variables
        
        Args:
            missing_vars: List of missing variable names
        """
        self.missing_vars = missing_vars
        super().__init__(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )


class RetryExhaustedError(ResumeBuilderError):
    """Raised when retry attempts are exhausted"""
    
    def __init__(self, operation: str, attempts: int, last_error: Exception = None):
        """
        Initialize with retry information
        
        Args:
            operation: Name of the operation that failed
            attempts: Number of attempts made
            last_error: The last error that occurred
        """
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error
        
        message = f"Operation '{operation}' failed after {attempts} attempts"
        if last_error:
            message += f". Last error: {str(last_error)}"
        
        super().__init__(message) 
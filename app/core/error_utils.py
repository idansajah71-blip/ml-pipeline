import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SENSITIVE_PATTERNS = [
    (r'password[=:]\s*\S+', 'password=***'),
    (r'secret[=:]\s*\S+', 'secret=***'),
    (r'token[=:]\s*\S+', 'token=***'),
    (r'key[=:]\s*\S+', 'key=***'),
    (r'credentials?[=:]\s*\S+', 'credentials=***'),
    (r'authorization[=:]\s*\S+', 'authorization=***'),
    (r'Bearer\s+\S+', 'Bearer ***'),
    (r'postgresql://[^\s]+', 'postgresql://***'),
    (r'redis://[^\s]+', 'redis://***'),
    (r'mysql://[^\s]+', 'mysql://***'),
    (r'mongodb://[^\s]+', 'mongodb://***'),
    (r'\/[a-zA-Z]:\\[^\s]+', '***'),
    (r'\/home\/[^\s]+', '***'),
    (r'\/var\/[^\s]+', '***'),
    (r'\/etc\/[^\s]+', '***'),
    (r'File "([^"]+)"', 'File "***"'),
    (r'line \d+', 'line ***'),
]

SAFE_ERROR_MESSAGES = {
    'ValueError': 'Invalid input provided',
    'KeyError': 'Required field missing',
    'TypeError': 'Invalid data type',
    'FileNotFoundError': 'Resource not found',
    'PermissionError': 'Access denied',
    'ConnectionError': 'Service temporarily unavailable',
    'TimeoutError': 'Operation timed out',
    'MemoryError': 'Insufficient memory',
    'OSError': 'System error occurred',
    'ImportError': 'Required dependency missing',
    'ModuleNotFoundError': 'Required dependency missing',
}


def sanitize_error_message(error: Exception, include_type: bool = False) -> str:
    """
    Sanitize exception message to prevent internal detail leakage.
    
    Args:
        error: The exception to sanitize
        include_type: Whether to include exception type in output
        
    Returns:
        Sanitized error message safe for client response
    """
    error_type = type(error).__name__

    if error_type in SAFE_ERROR_MESSAGES:
        base_message = SAFE_ERROR_MESSAGES[error_type]
    else:
        base_message = "An unexpected error occurred"

    raw_message = str(error)

    if not raw_message:
        return base_message

    sanitized = raw_message

    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    if len(sanitized) > 200:
        sanitized = sanitized[:200] + "..."

    if include_type:
        return f"{base_message} ({error_type})"

    return base_message


def log_error(error: Exception, context: Optional[str] = None, exc_info: bool = True):
    """
    Log error with full details for internal debugging.
    
    Args:
        error: The exception to log
        context: Additional context about where the error occurred
        exc_info: Whether to include stack trace
    """
    if context:
        logger.error(f"{context}: {error}", exc_info=exc_info)
    else:
        logger.error(f"Error: {error}", exc_info=exc_info)


def sanitize_validation_error(error: Exception) -> str:
    """
    Sanitize validation errors while keeping useful user feedback.
    
    Args:
        error: The validation error to sanitize
        
    Returns:
        Sanitized message with actionable feedback
    """
    error_type = type(error).__name__
    raw_message = str(error)

    if error_type == 'ValidationError':
        return "Invalid input. Please check your data and try again."

    if 'null' in raw_message.lower() or 'none' in raw_message.lower():
        return "A required field is missing. Please fill in all required fields."

    if 'out of range' in raw_message.lower():
        return "One or more values are outside the acceptable range."

    if 'invalid' in raw_message.lower():
        return "One or more fields contain invalid data. Please check your input."

    return "Validation failed. Please check your input and try again."

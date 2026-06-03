"""
Environment Variable Validation Utility

Validates required environment variables at Django startup.
Fails fast with clear error messages if .env is misconfigured.
"""
import os
import logging
from decouple import config

logger = logging.getLogger(__name__)

# Required environment variables for email functionality
REQUIRED_EMAIL_VARS = [
    'EMAIL_HOST',
    'EMAIL_PORT',
    'EMAIL_HOST_USER',
    'EMAIL_HOST_PASSWORD',
    'FRONTEND_URL',
]

# Optional but recommended environment variables
OPTIONAL_VARS = [
    'DEFAULT_FROM_EMAIL',
    'SECRET_KEY',
    'MONGO_URI',
    'MONGO_DB_NAME',
]


def validate_email_config():
    """
    Validate email configuration environment variables.
    
    Returns:
        tuple: (is_valid: bool, missing_vars: list, errors: list)
    """
    missing_vars = []
    errors = []
    
    for var in REQUIRED_EMAIL_VARS:
        value = config(var, default=None)
        if not value:
            missing_vars.append(var)
            errors.append(f"Missing required environment variable: {var}")
    
    # Validate EMAIL_PORT is numeric
    email_port = config('EMAIL_PORT', default=None)
    if email_port:
        try:
            int(email_port)
        except (ValueError, TypeError):
            errors.append(f"EMAIL_PORT must be a valid integer, got: {email_port}")
    
    # Validate EMAIL_HOST_USER is a valid email format (basic check)
    email_user = config('EMAIL_HOST_USER', default=None)
    if email_user and '@' not in email_user:
        errors.append(f"EMAIL_HOST_USER should be a valid email address, got: {email_user}")
    
    is_valid = len(missing_vars) == 0 and len(errors) == 0
    
    return is_valid, missing_vars, errors


def validate_all_config():
    """
    Validate all critical environment variables.
    
    Raises:
        RuntimeError: If required environment variables are missing or invalid.
    """
    is_valid, missing_vars, errors = validate_email_config()
    
    if not is_valid:
        error_message = "Environment configuration validation failed:\n"
        if missing_vars:
            error_message += f"  Missing variables: {', '.join(missing_vars)}\n"
        if errors:
            error_message += "  Errors:\n"
            for error in errors:
                error_message += f"    - {error}\n"
        error_message += "\nPlease check your .env file and ensure all required variables are set."
        
        logger.error(error_message)
        raise RuntimeError(error_message)
    
    logger.info("✅ Environment configuration validation passed")


def get_client_ip(request):
    """
    Extract client IP address from request.
    
    Args:
        request: Django request object
        
    Returns:
        str: Client IP address or None
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """
    Extract user agent from request.
    
    Args:
        request: Django request object
        
    Returns:
        str: User agent string or empty string
    """
    return request.META.get('HTTP_USER_AGENT', '')[:255]  # Limit to 255 chars


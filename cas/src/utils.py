# Utility functions for Config as a Service

import json
from datetime import datetime
from typing import Any, Dict, Optional

def validate_json_string(value: str) -> bool:
    """Validate if a string is valid JSON"""
    try:
        json.loads(value)
        return True
    except (json.JSONDecodeError, TypeError):
        return False

def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO string"""
    if dt is None:
        return None
    return dt.isoformat() + 'Z'

def sanitize_input(value: Any) -> str:
    """Sanitize input by converting to string and stripping whitespace"""
    if value is None:
        return ''
    return str(value).strip()

def validate_environment(env: str) -> bool:
    """Validate environment string"""
    valid_envs = ['dev', 'development', 'staging', 'prod', 'production']
    return env.lower() in valid_envs

def validate_config_type(config_type: str) -> bool:
    """Validate configuration type"""
    valid_types = ['application', 'infrastructure']
    return config_type.lower() in valid_types

def create_error_response(message: str, status_code: int = 400) -> tuple:
    """Create standardized error response"""
    return {'message': message}, status_code

def create_success_response(data: Dict[str, Any], message: str = 'Success') -> tuple:
    """Create standardized success response"""
    response = {'message': message}
    response.update(data)
    return response, 200

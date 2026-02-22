"""Input validation utilities."""
import re
from typing import Optional
from datetime import datetime

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number format (Indian format)."""
    # Remove spaces and dashes
    phone = re.sub(r'[\s-]', '', phone)
    # Check for valid Indian phone number
    pattern = r'^(\+91|91)?[6-9]\d{9}$'
    return bool(re.match(pattern, phone))

def validate_abha_number(abha: str) -> bool:
    """Validate ABHA number format (14 digits: XX-XXXX-XXXX-XXXX)."""
    pattern = r'^\d{2}-\d{4}-\d{4}-\d{4}$'
    return bool(re.match(pattern, abha))

def validate_date_format(date_str: str, format: str = '%Y-%m-%d') -> bool:
    """Validate date string format."""
    try:
        datetime.strptime(date_str, format)
        return True
    except ValueError:
        return False

def sanitize_string(value: str, max_length: int = 500) -> str:
    """Sanitize string input."""
    if not value:
        return ''
    # Remove leading/trailing whitespace
    value = value.strip()
    # Truncate to max length
    return value[:max_length]

def validate_password_strength(password: str) -> dict:
    """Check password strength and return validation result."""
    result = {
        'valid': True,
        'errors': []
    }
    
    if len(password) < 8:
        result['valid'] = False
        result['errors'].append('Password must be at least 8 characters long')
    
    if not re.search(r'[A-Z]', password):
        result['valid'] = False
        result['errors'].append('Password must contain at least one uppercase letter')
    
    if not re.search(r'[a-z]', password):
        result['valid'] = False
        result['errors'].append('Password must contain at least one lowercase letter')
    
    if not re.search(r'\d', password):
        result['valid'] = False
        result['errors'].append('Password must contain at least one digit')
    
    return result

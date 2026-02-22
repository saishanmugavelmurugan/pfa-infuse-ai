"""Common helper functions."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import re

def get_utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)

def format_datetime(dt: datetime, format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Format datetime to string."""
    return dt.strftime(format)

def parse_datetime(date_str: str, format: str = '%Y-%m-%d') -> Optional[datetime]:
    """Parse datetime string."""
    try:
        return datetime.strptime(date_str, format)
    except ValueError:
        return None

def clean_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values from dictionary."""
    return {k: v for k, v in data.items() if v is not None}

def paginate_list(items: List[Any], page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """Paginate a list of items."""
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        'items': items[start:end],
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page
    }

def generate_patient_number() -> str:
    """Generate a unique patient number."""
    import random
    return f"PAT-{random.randint(100000, 999999)}"

def generate_invoice_number() -> str:
    """Generate a unique invoice number."""
    import random
    from datetime import datetime
    prefix = datetime.now().strftime('%Y%m')
    return f"INV-{prefix}-{random.randint(10000, 99999)}"

def mask_sensitive_data(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive data like phone numbers or IDs."""
    if not value or len(value) <= visible_chars:
        return value
    return '*' * (len(value) - visible_chars) + value[-visible_chars:]

def calculate_age(date_of_birth: datetime) -> int:
    """Calculate age from date of birth."""
    today = datetime.now()
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text

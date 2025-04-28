# sanitizer.py
"""Provides functions to sanitize user input, removing potentially harmful content.

Aims to mitigate risks like Cross-Site Scripting (XSS) and basic SQL injection patterns.
Uses libraries like `bleach` for robust HTML sanitization.
"""

import re
import bleach
from typing import Dict, Any

def sanitize_input(input_string: str) -> str:
    """Sanitizes a string by removing HTML, potential SQL keywords, and script tags.

    Uses bleach for primary HTML cleaning and regex for additional patterns.
    Note: This provides basic protection and might not cover all attack vectors.
    Use prepared statements for database interactions for proper SQL injection prevention.

    Args:
        input_string (str): The raw input string to sanitize.

    Returns:
        str: The sanitized string.
    """
    if not isinstance(input_string, str):
        # Return non-string inputs as-is or handle as appropriate
        return input_string
        
    # 1. Use bleach to remove unwanted HTML tags and attributes.
    #    Configure `bleach.clean` with allowed tags/attributes if specific HTML is needed.
    #    Default cleans all standard tags.
    cleaned = bleach.clean(input_string)
    
    # 2. Remove common SQL injection keywords (case-insensitive).
    #    WARNING: This is a basic regex approach and NOT a substitute for parameterized queries!
    #    It primarily aims to reduce obvious attempts in non-database contexts.
    cleaned = re.sub(r'\b(AND|OR|UNION|SELECT|INSERT|UPDATE|DELETE|DROP)\b', '', cleaned, flags=re.IGNORECASE)
    
    # 3. Remove script tags (already handled by bleach, but as an extra layer).
    cleaned = re.sub(r'<script.*?>.*?</script>', '', cleaned, flags=re.IGNORECASE|re.DOTALL)
    
    # 4. Remove common event handler attributes (like onclick, onload) to prevent XSS.
    #    Bleach also handles many of these, but this adds explicit removal.
    cleaned = re.sub(r'\bon\w+\s*=.*?(?=\s|>)', '', cleaned, flags=re.IGNORECASE)
    
    # 5. Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def sanitize_dict(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitizes string values within a dictionary.

    Iterates through dictionary items. If a value is a string, it applies 
    `sanitize_input`. Other types are left unchanged.

    Args:
        input_dict (Dict[str, Any]): The dictionary to sanitize.

    Returns:
        Dict[str, Any]: The dictionary with its string values sanitized.
    """
    if not isinstance(input_dict, dict):
        return input_dict # Return non-dicts as-is
        
    return {k: sanitize_input(v) if isinstance(v, str) else v for k, v in input_dict.items()}
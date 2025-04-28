# validators.py
"""Input validation functions for the business development scenario data.

Provides functions to check the format, content, and validity of user inputs
before they are processed or used to configure the AI system.
"""

import re
from typing import List, Dict

def validate_company_name(name: str) -> bool:
    """Validates the company name.
    
    Ensures the name is not empty and within a reasonable length.

    Args:
        name (str): The company name to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    # Simple check: non-empty and max length
    return bool(name) and len(name) <= 100

def validate_website(website: str) -> bool:
    """Validates a website URL using a regex pattern.

    Allows common formats including http, https, ftp, localhost, and IP addresses.
    Also attempts to validate URLs starting with 'www.' by prepending 'http://'.

    Args:
        website (str): The website URL to validate.

    Returns:
        bool: True if the URL matches the pattern, False otherwise.
    """
    # Regex for common URL patterns (including http, https, ftp, domain, localhost, IP)
    pattern = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    # Handle cases where user might just type www.example.com
    if not website.startswith(("http://", "https://", "ftp://")) and website.startswith("www."):
        website = "http://" + website  # Prepend protocol for validation logic

    return bool(pattern.match(website))

def validate_product(product: Dict[str, str]) -> bool:
    """Validates the product dictionary structure and content.

    Checks if it's a dictionary with 'name' and 'description' keys,
    and if the values are strings within reasonable length limits.

    Args:
        product (Dict[str, str]): The product dictionary.

    Returns:
        bool: True if the structure and content are valid, False otherwise.
    """
    return (
        isinstance(product, dict) and
        'name' in product and
        'description' in product and
        isinstance(product.get('name'), str) and
        isinstance(product.get('description'), str) and
        bool(product.get('name')) and # Ensure non-empty
        bool(product.get('description')) and # Ensure non-empty
        len(product.get('name', '')) <= 100 and
        len(product.get('description', '')) <= 500
    )

def validate_industry(industry: str) -> bool:
    """Validates if the industry is one of the predefined allowed values.

    Args:
        industry (str): The industry string to validate.

    Returns:
        bool: True if the industry is in the allowed list, False otherwise.
    """
    # Use a predefined list for controlled vocabulary
    valid_industries = ["Food Industry", "Technology", "Dairy", "Healthcare"]
    return industry in valid_industries

def validate_country(country: str) -> bool:
    """Validates the target country name.

    Ensures the name is not empty and within a reasonable length. 
    Note: This is a basic check; a production system might use a
    validated list of countries.

    Args:
        country (str): The country name to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    # Simple check: non-empty and max length
    # TODO: Consider integrating a library like `pycountry` for robust validation.
    return bool(country) and len(country) <= 100

def validate_goals(goals: List[str]) -> bool:
    """Validates that the goals list contains only allowed values and is not empty.

    Args:
        goals (List[str]): The list of goals to validate.

    Returns:
        bool: True if all goals are valid and the list is not empty, False otherwise.
    """
    valid_goals = ["Market Entry", "Product Adaptation", "Regulatory Compliance", "Competitive Positioning"]
    # Check if it's a list, not empty, and all items are in the valid list
    return isinstance(goals, list) and len(goals) > 0 and all(goal in valid_goals for goal in goals)

def validate_input(data: Dict) -> List[str]:
    """Performs comprehensive validation of all input fields.

    Calls individual validation functions for each field in the input data dictionary.

    Args:
        data (Dict): A dictionary containing all the input fields 
                     (e.g., 'company_name', 'company_website', etc.).

    Returns:
        List[str]: A list of error messages. If the list is empty, validation passed.
    """
    errors = []
    
    # Validate each field using its specific function, appending errors if validation fails
    if not validate_company_name(data.get('company_name', '')):
        errors.append("Invalid or missing company name (max 100 chars).")
    
    if not validate_website(data.get('company_website', '')):
        errors.append("Invalid website URL format.")
    
    if not validate_product(data.get('product', {})):
        errors.append("Invalid product information (must have non-empty name (<=100 chars) and description (<=500 chars)).")
    
    if not validate_industry(data.get('industry', '')):
        errors.append(f"Invalid industry selected. Choose from: {', '.join(["Food Industry", "Technology", "Dairy", "Healthcare"])}")
    
    if not validate_country(data.get('target_country', '')):
        errors.append("Invalid or missing target country (max 100 chars).")
    
    # Handle potential non-list input for goals gracefully
    goals_input = data.get('goals', [])
    if not isinstance(goals_input, list):
        errors.append("Goals must be provided as a list.")
    elif not validate_goals(goals_input):
        errors.append(f"Invalid or missing goals selected. Choose at least one from: {', '.join(["Market Entry", "Product Adaptation", "Regulatory Compliance", "Competitive Positioning"])}")
    
    return errors

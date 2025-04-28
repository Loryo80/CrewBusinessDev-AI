class Config:
    """Represents the configuration for a business development scenario.

    Stores and validates all necessary inputs required to define the context 
    for the AI agent crews, such as company details, product information, 
    target market, and strategic goals.

    Attributes:
        company_name (str): The name of the company.
        company_website (str): The company's official website URL.
        product (dict): A dictionary containing the product's 'name' and 'description'.
        industry (str): The industry the company operates in.
        target_country (str): The country targeted for business development.
        goals (tuple[str]): A tuple of strategic goals for the initiative 
                             (e.g., 'Market Entry', 'Product Adaptation').
    """
    def __init__(self, company_name, company_website, product, industry, target_country, goals):
        """Initializes the Config object with validation.
        
        Args:
            company_name (str): The name of the company.
            company_website (str): The company's website.
            product (dict): Dictionary with 'name' and 'description'.
            industry (str): Company's industry.
            target_country (str): Target country name.
            goals (list[str] | tuple[str]): List or tuple of strategic goals.
            
        Raises:
            ValueError: If any input fails validation (e.g., empty string, 
                      invalid product format, no goals).
        """
        self.company_name = self.validate_string(company_name, "Company Name")
        self.company_website = self.validate_string(company_website, "Company Website")
        self.product = self.validate_product(product)
        self.industry = self.validate_string(industry, "Industry")
        self.target_country = self.validate_string(target_country, "Target Country")
        self.goals = self.validate_goals(goals)

    @staticmethod
    def validate_string(value, field_name):
        """Validates that a value is a non-empty string.

        Args:
            value (any): The value to validate.
            field_name (str): The name of the field being validated (for error messages).

        Returns:
            str: The validated and stripped string.

        Raises:
            ValueError: If the value is not a string or is empty/whitespace only.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def validate_product(product):
        """Validates the product dictionary format and its contents.

        Args:
            product (any): The value to validate as the product dictionary.

        Returns:
            dict: The validated product dictionary with stripped string values.

        Raises:
            ValueError: If 'product' is not a dict or lacks 'name'/'description',
                      or if name/description are invalid strings.
        """
        if not isinstance(product, dict) or 'name' not in product or 'description' not in product:
            raise ValueError("Product must be a dictionary with 'name' and 'description' keys")
        # Reuse string validation for product name and description
        return {
            'name': Config.validate_string(product['name'], "Product Name"),
            'description': Config.validate_string(product['description'], "Product Description")
        }

    @staticmethod
    def validate_goals(goals):
        """Validates that goals is a non-empty list/tuple of valid goal strings.

        Args:
            goals (any): The value to validate.

        Returns:
            tuple[str]: A tuple containing only the valid, recognized goals.
                      Filters out any unrecognized goal strings.

        Raises:
            ValueError: If goals is not a list/tuple or is empty.
        """
        valid_goals = ["Market Entry", "Product Adaptation", "Regulatory Compliance", "Competitive Positioning"]
        if not isinstance(goals, (list, tuple)) or len(goals) == 0:
            raise ValueError("Goals must be a non-empty list or tuple")
        # Filter to include only known valid goals and return as an immutable tuple
        return tuple(goal for goal in goals if goal in valid_goals)

    def to_dict(self):
        """Converts the configuration object to a dictionary.

        Useful for serialization (e.g., JSON) or formatting task descriptions.

        Returns:
            dict: A dictionary representation of the configuration.
        """
        return {
            "company_name": self.company_name,
            "company_website": self.company_website,
            "product": self.product,
            "industry": self.industry,
            "target_country": self.target_country,
            # Convert goals back to list for broader compatibility (e.g., JSON)
            "goals": list(self.goals)
        }

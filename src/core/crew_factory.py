import json
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, WebsiteSearchTool
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
import logging
from functools import lru_cache
import os
from dotenv import load_dotenv
from typing import Dict, Any, List, Tuple, Optional, TYPE_CHECKING, ForwardRef

# Use TYPE_CHECKING to satisfy static type checkers for the Config import
# while still allowing the runtime fallback.
if TYPE_CHECKING:
    from ..config import Config
else:
    # Define a forward reference for Config
    Config = ForwardRef('Config')

# Assuming Config class is available (e.g., from src.config import Config)
try:
    from ..config import Config
except ImportError:
    # Fallback for potential direct script execution or different structure
    logger = logging.getLogger(__name__)
    logger.warning("Could not perform relative import of Config. Assuming it's available elsewhere.")
    # Config remains a ForwardRef in this case

# Load environment variables from .env file
load_dotenv()

# Load API Keys and Model Names from environment variables
# These are essential for initializing LLM connections.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

MODEL_MINI = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini") # Allow override via env
MODEL_FLASH = os.getenv("GOOGLE_MODEL_NAME", "gemini-1.5-flash") # Allow override via env
MODEL_MISTRAL_LARGE = os.getenv("MISTRAL_MODEL_NAME", "mistral-large-latest") # Allow override via env


# Validate that essential API keys are loaded
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY is not set in the environment variables")
if not SERPER_API_KEY:
    raise ValueError("SERPER_API_KEY is not set in the environment variables")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set in the environment variables")

logger = logging.getLogger(__name__)

class CrewFactory:
    """Factory class for creating CrewAI Agents, Tasks, and Crews.

    Handles the initialization of language models (LLMs) from different providers
    (OpenAI, Google, Mistral) and equips agents with necessary tools.
    Provides methods to assemble specialized crews for various business 
    development functions.

    Attributes:
        config (Config): The configuration object defining the scenario.
        openai_api_key (str): API key for OpenAI.
        mistral_api_key (str): API key for Mistral AI.
        serper_api_key (str): API key for SerperDevTool.
        google_api_key (str): API key for Google Generative AI.
        llm_mini (ChatOpenAI): Initialized OpenAI LLM instance.
        llm_flash (ChatGoogleGenerativeAI): Initialized Google LLM instance.
        llm_mistral_large (ChatMistralAI): Initialized Mistral LLM instance.
        search_tool (SerperDevTool): Tool for general web searches.
        web_tool (WebsiteSearchTool): Tool for searching specific websites.
    """
    
    def __init__(self, config: 'Config'):
        """Initializes the CrewFactory with configuration and LLMs.

        Args:
            config (Config): The configuration object.

        Raises:
            TypeError: If config is None.
            ValueError: If any required API key is missing in environment variables.
        """
        # Runtime check remains necessary because type hints aren't enforced at runtime
        if config is None:
            raise TypeError("Configuration object must be provided.")
        self.config = config
        
        # Store API keys locally (consider if needed beyond LLM init)
        self.openai_api_key = OPENAI_API_KEY
        self.mistral_api_key = MISTRAL_API_KEY
        self.serper_api_key = SERPER_API_KEY
        self.google_api_key = GOOGLE_API_KEY
        
        # Initialize LLM clients using loaded keys and model names
        # Temperature is set to 0 for more deterministic outputs, suitable for analysis tasks.
        self.llm_mini = ChatOpenAI(temperature=0, model=MODEL_MINI, api_key=self.openai_api_key)
        self.llm_flash = ChatGoogleGenerativeAI(model=MODEL_FLASH, api_key=self.google_api_key)
        self.llm_mistral_large = ChatMistralAI(model=MODEL_MISTRAL_LARGE, api_key=self.mistral_api_key)
        
        # Initialize tools shared by agents
        self.search_tool = SerperDevTool(api_key=self.serper_api_key)
        self.web_tool = WebsiteSearchTool()
        
        logger.info(f"CrewFactory initialized with LLMs: OpenAI ('{MODEL_MINI}'), Google ('{MODEL_FLASH}'), Mistral ('{MODEL_MISTRAL_LARGE}')")

    @lru_cache(maxsize=32)
    def create_agent(self, role: str, goal: str, backstory: str, llm_choice: str = "openai") -> Agent:
        """Creates a CrewAI Agent with specified parameters and selected LLM.

        Uses LRU cache to avoid recreating identical agents unnecessarily.

        Args:
            role (str): The role of the agent (e.g., 'Market Researcher').
            goal (str): The primary objective of the agent.
            backstory (str): The background or persona of the agent.
            llm_choice (str): The LLM to use ('openai', 'google', 'mistral'). 
                              Defaults to 'openai'.

        Returns:
            Agent: An initialized CrewAI Agent instance.
        
        Raises:
            ValueError: If an invalid llm_choice is provided.
            Exception: Propagates exceptions from Agent initialization.
        """
        logger.debug(f"Creating agent: Role='{role}', LLM='{llm_choice}'")
        try:
            # Select the appropriate LLM instance based on choice
            selected_llm = None
            if llm_choice == "openai":
                selected_llm = self.llm_mini
            elif llm_choice == "google":
                selected_llm = self.llm_flash
            elif llm_choice == "mistral":
                selected_llm = self.llm_mistral_large
            else:
                raise ValueError(f"Invalid llm_choice: '{llm_choice}'. Must be 'openai', 'google', or 'mistral'.")

            return Agent(
                role=role,
                goal=goal,
                backstory=backstory,
                tools=[self.search_tool, self.web_tool], # Provide shared tools
                verbose=True, # Enable detailed logging from the agent
                llm=selected_llm # Assign the chosen LLM
            )
        except Exception as e:
            logger.error(f"Error creating agent '{role}': {str(e)}", exc_info=True)
            raise

    def create_task(self, description: str, agent: Agent, expected_output: str = "") -> Task:
        """Creates a CrewAI Task assigned to a specific agent.

        Formats the task description using the project configuration.

        Args:
            description (str): The template string for the task description. 
                               It should contain placeholders matching keys in 
                               `config.to_dict()` (e.g., '{product[name]}').
            agent (Agent): The agent responsible for executing this task.
            expected_output (str, optional): A description of the desired output format.
                                            Defaults to "".

        Returns:
            Task: An initialized CrewAI Task instance.
        
        Raises:
            Exception: Propagates exceptions from Task initialization.
        """
        logger.debug(f"Creating task for agent '{agent.role}': {description[:50]}...")
        try:
            # Format the description string with values from the config dictionary
            formatted_description = description.format(**self.config.to_dict())
            return Task(
                description=formatted_description,
                agent=agent,
                expected_output=expected_output
            )
        except KeyError as e:
            logger.error(f"Missing key in config for task description formatting: {e}. Description: '{description}'")
            raise ValueError(f"Task description formatting failed. Missing key: {e}") from e
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}", exc_info=True)
            raise

    @lru_cache(maxsize=16)
    def create_crew(self, name: str, agents: Tuple[Agent], tasks: Tuple[Task], manager_llm_choice: str = "openai") -> Crew:
        """Creates a CrewAI Crew with specified agents, tasks, and manager LLM.
        
        Uses a hierarchical process and allows selection of the manager LLM.
        Uses LRU cache to potentially reuse identical crew configurations.

        Args:
            name (str): A name for the crew (for identification/logging).
            agents (Tuple[Agent]): A tuple of Agent instances in the crew.
            tasks (Tuple[Task]): A tuple of Task instances assigned to the crew.
            manager_llm_choice (str): The LLM for the hierarchical manager 
                                      ('openai', 'google', 'mistral'). Defaults to 'openai'.

        Returns:
            Crew: An initialized CrewAI Crew instance.
        
        Raises:
            ValueError: If an invalid manager_llm_choice is provided.
            Exception: Propagates exceptions from Crew initialization.
        """
        logger.debug(f"Creating crew: Name='{name}', Manager LLM='{manager_llm_choice}'")
        try:
            # Select the appropriate manager LLM instance
            selected_manager_llm = None
            if manager_llm_choice == "openai":
                selected_manager_llm = self.llm_mini
            elif manager_llm_choice == "google":
                selected_manager_llm = self.llm_flash
            elif manager_llm_choice == "mistral":
                selected_manager_llm = self.llm_mistral_large
            else:
                raise ValueError(f"Invalid manager_llm_choice: '{manager_llm_choice}'. Must be 'openai', 'google', or 'mistral'.")

            # Ensure agents and tasks are tuples for immutability/caching
            agents_tuple = tuple(agents) if isinstance(agents, list) else agents
            tasks_tuple = tuple(tasks) if isinstance(tasks, list) else tasks

            return Crew(
                agents=agents_tuple, 
                tasks=tasks_tuple,
                process=Process.hierarchical, # Use hierarchical process for manager oversight
                manager_llm=selected_manager_llm, # Assign the chosen manager LLM
                verbose=True # Enable detailed logging from the crew
            )
        except Exception as e:
            logger.error(f"Error creating crew '{name}': {str(e)}", exc_info=True)
            raise

    # --- Methods to create specific, predefined crews --- 
    # These methods assemble standard agents and tasks for common business functions.
    # They currently default to using the 'openai' LLM choice passed to create_agent/create_crew.
    # They could be modified to accept an `llm_choice` parameter if needed.

    def create_market_research_crew(self) -> Crew:
        """Creates a crew focused on market research."""
        logger.info("Creating Market Research Crew")
        researcher = self.create_agent(
            role="Market Researcher",
            goal=f"Conduct comprehensive market research for {self.config.product['name']} in {self.config.target_country}",
            backstory=f"You are a highly experienced market researcher specializing in the {self.config.industry} sector, with deep knowledge of the {self.config.target_country} market dynamics. Your goal is to provide actionable insights."
        )
        tasks = [
            self.create_task("Analyze the current market size, historical growth, and future potential for products like {product[name]} in {target_country}. Identify key market drivers and barriers.", researcher, "Detailed report on market size, growth projections, drivers, and barriers."),
            self.create_task("Identify the top 3-5 direct and indirect competitors for {product[name]} in {target_country}. Analyze their market share, strengths, weaknesses, and pricing strategies.", researcher, "Competitor analysis report including market share, SWOT, and pricing."),
            self.create_task("Determine target consumer demographics, preferences, purchasing behaviors, and key trends related to {product[name]} within {target_country}.", researcher, "Consumer profile and trends report.")
        ]
        tasks.extend(self.create_goal_specific_tasks(researcher, "Market Research"))
        # Defaulting manager LLM to openai, change `manager_llm_choice` if needed
        return self.create_crew("Market Research", (researcher,), tuple(tasks))

    def create_regulatory_compliance_crew(self) -> Crew:
        """Creates a crew focused on regulatory compliance."""
        logger.info("Creating Regulatory Compliance Crew")
        compliance_officer = self.create_agent(
            role="Regulatory Compliance Officer",
            goal=f"Ensure full regulatory compliance for the import and sale of {self.config.product['name']} in {self.config.target_country}",
            backstory=f"You are a meticulous regulatory expert specializing in the {self.config.industry} industry for the {self.config.target_country} region. Your focus is identifying all requirements and potential hurdles."
        )
        tasks = [
            self.create_task("Identify and list all relevant import regulations, product standards, labeling requirements, and certifications needed for {product[name]} in {target_country}.", compliance_officer, "Comprehensive list of regulations, standards, and certification requirements."),
            self.create_task("Outline the necessary steps and documentation required to achieve compliance for {product[name]} in {target_country}. Estimate timelines and potential costs.", compliance_officer, "Compliance roadmap including steps, documents, estimated timelines, and costs."),
            self.create_task("Conduct a risk assessment identifying potential compliance challenges and penalties for non-compliance regarding {product[name]} in {target_country}.", compliance_officer, "Compliance risk assessment report.")
        ]
        tasks.extend(self.create_goal_specific_tasks(compliance_officer, "Regulatory Compliance"))
        return self.create_crew("Regulatory Compliance", (compliance_officer,), tuple(tasks))

    def create_supply_chain_crew(self) -> Crew:
        """Creates a crew focused on supply chain management."""
        logger.info("Creating Supply Chain Crew")
        supply_chain_manager = self.create_agent(
            role="Supply Chain Manager",
            goal=f"Design an optimized and resilient supply chain strategy for {self.config.product['name']} entering {self.config.target_country}",
            backstory=f"You are a seasoned supply chain professional with expertise in international logistics for the {self.config.industry} sector, particularly within {self.config.target_country}."
        )
        tasks = [
            self.create_task("Identify and evaluate potential suppliers, manufacturers, and distribution partners for {product[name]} within or serving {target_country}. Assess their reliability and cost-effectiveness.", supply_chain_manager, "List of potential partners with evaluation criteria and recommendations."),
            self.create_task("Develop optimal logistics, warehousing, and transportation strategies for getting {product[name]} into and distributed within {target_country}. Consider customs and import processes.", supply_chain_manager, "Logistics and distribution plan including modes, routes, and customs considerations."),
            self.create_task("Assess inventory management needs, demand forecasting challenges, and necessary infrastructure for {product[name]} in {target_country}.", supply_chain_manager, "Inventory management and forecasting assessment.")
        ]
        tasks.extend(self.create_goal_specific_tasks(supply_chain_manager, "Supply Chain"))
        return self.create_crew("Supply Chain", (supply_chain_manager,), tuple(tasks))

    def create_sales_marketing_crew(self) -> Crew:
        """Creates a crew focused on sales and marketing strategy."""
        logger.info("Creating Sales and Marketing Crew")
        marketing_specialist = self.create_agent(
            role="Marketing Specialist",
            goal=f"Develop effective marketing strategies to build brand awareness and generate demand for {self.config.product['name']} in {self.config.target_country}",
            backstory=f"You are a creative and data-driven marketing expert with proven success in launching {self.config.industry} products in {self.config.target_country}."
        )
        sales_manager = self.create_agent(
            role="Sales Manager",
            goal=f"Develop actionable sales strategies and identify channels to effectively sell {self.config.product['name']} in {self.config.target_country}",
            backstory=f"You are a results-oriented sales leader with experience building sales channels for {self.config.industry} products in {self.config.target_country}."
        )
        tasks = [
            self.create_task("Develop a comprehensive marketing plan for {product[name]} tailored to {target_country}, including target audience, messaging, channel mix (digital, traditional), and budget recommendations.", marketing_specialist, "Detailed marketing plan document."),
            self.create_task("Create a sales strategy outlining target customer segments, sales channels (direct, distributors, online), sales team structure (if applicable), and key performance indicators (KPIs) for {product[name]} in {target_country}.", sales_manager, "Sales strategy document."),
            self.create_task("Identify key customer segments, appropriate marketing channels, and effective messaging strategies for {product[name]} within {target_country}.", marketing_specialist, "Customer segmentation and channel analysis report."),
            self.create_task("Analyze competitor pricing and recommend optimal pricing strategies (including MSRP, wholesale, promotional) for {product[name]} in {target_country}.", sales_manager, "Pricing strategy analysis and recommendations.")
        ]
        tasks.extend(self.create_goal_specific_tasks([marketing_specialist, sales_manager], "Sales and Marketing"))
        return self.create_crew("Sales and Marketing", (marketing_specialist, sales_manager), tuple(tasks))

    def create_implementation_launch_crew(self) -> Crew:
        """Creates a crew focused on implementation and launch planning."""
        logger.info("Creating Implementation and Launch Crew")
        project_manager = self.create_agent(
            role="Project Manager",
            goal=f"Develop and oversee a detailed plan for the successful implementation and launch of {self.config.product['name']} in {self.config.target_country}",
            backstory=f"You are an organized and proactive project manager experienced in coordinating complex international product launches within the {self.config.industry} industry, specifically for the {self.config.target_country} market."
        )
        tasks = [
            self.create_task("Develop a detailed, phased implementation plan covering all aspects (operations, marketing, sales, legal) required to launch {product[name]} in {target_country}. Include key milestones and dependencies.", project_manager, "Comprehensive implementation plan with phases, milestones, and dependencies."),
            self.create_task("Identify potential operational, market, and financial risks associated with the launch of {product[name]} in {target_country}. Propose mitigation strategies for each identified risk.", project_manager, "Risk assessment matrix with mitigation strategies."),
            self.create_task("Create a realistic project timeline with specific deadlines for key launch activities for {product[name]} in {target_country}.", project_manager, "Detailed launch timeline (e.g., Gantt chart description)." ),
            self.create_task("Outline the necessary coordination points and communication plan between different internal teams ({e.g., supply_chain, marketing, sales}) and external partners for a smooth launch.", project_manager, "Inter-team coordination and communication plan.")
        ]
        tasks.extend(self.create_goal_specific_tasks(project_manager, "Implementation and Launch"))
        return self.create_crew("Implementation and Launch", (project_manager,), tuple(tasks))

    def create_goal_specific_tasks(self, agents: Agent | List[Agent], crew_name: str) -> List[Task]:
        """Creates additional tasks based on the high-level goals defined in the config.

        Maps predefined goal-related tasks to specific crews.

        Args:
            agents (Agent | List[Agent]): The agent(s) within the crew who might 
                                          be suitable for these tasks. If a list, 
                                          the first agent is usually assigned.
            crew_name (str): The name of the crew these tasks belong to.

        Returns:
            List[Task]: A list of Task objects specific to the configured goals 
                       for this crew.
        """
        # If multiple agents, pick the first one for goal tasks (can be refined)
        primary_agent = agents[0] if isinstance(agents, list) else agents
        
        # Mapping from high-level goals to specific task descriptions relevant to certain crews
        goal_task_definitions = {
            "Market Entry": {
                "Market Research": "Specifically analyze market entry barriers (e.g., tariffs, quotas, cultural barriers) and facilitators (e.g., trade agreements, existing infrastructure) for {product[name]} in {target_country}.",
                "Implementation and Launch": "Develop a detailed market entry strategy outlining the chosen approach (e.g., direct export, joint venture, local subsidiary), rationale, and key steps for {product[name]} in {target_country}."
            },
            "Product Adaptation": {
                "Market Research": "Identify specific product adaptations (features, packaging, formulation) needed for {product[name]} to meet consumer preferences and regulations in {target_country}.",
                "Supply Chain": "Assess the supply chain implications and feasibility of required product adaptations for {product[name]} for the {target_country} market."
            },
            "Regulatory Compliance": {
                # This goal is often covered by the main tasks of the Regulatory Compliance crew
                "Regulatory Compliance": "Provide a final checklist confirming all key regulatory requirements identified for {product[name]} in {target_country} have been addressed or planned for."
            },
            "Competitive Positioning": {
                "Market Research": "Analyze the competitive landscape to identify unique selling propositions (USPs) for {product[name]} against key competitors in {target_country}.",
                "Sales and Marketing": "Develop a clear competitive positioning statement and strategy for {product[name]} based on market analysis and identified USPs for the {target_country} market."
            }
        }
        
        tasks = []
        # Iterate through the goals set in the configuration for this run
        if self.config and self.config.goals: # Check if config and goals exist
             for goal in self.config.goals:
                 # Check if the current goal has a defined task for this specific crew
                 if goal in goal_task_definitions and crew_name in goal_task_definitions[goal]:
                     task_description = goal_task_definitions[goal][crew_name]
                     logger.debug(f"Creating goal-specific task for Goal='{goal}', Crew='{crew_name}'")
                     # Create the task and assign it to the primary agent of the crew
                     tasks.append(self.create_task(task_description, primary_agent))
        else:
             logger.warning("Cannot create goal-specific tasks: Config or config.goals is missing.")
        return tasks

class EnhancedCrewFactory(CrewFactory):
    """Extends CrewFactory with additional validation and utility methods.

    Adds configuration validation and methods for summarizing and modifying crews.
    """
    def __init__(self, config: 'Config'):
        """Initializes the EnhancedCrewFactory and validates the config."""
        super().__init__(config)
        # Perform validation specific to the enhanced factory
        self.validate_config()
        logger.info("EnhancedCrewFactory initialized and config validated.")

    def validate_config(self):
        """Performs basic validation on the provided configuration object.

        Ensures required fields exist and that goals are provided correctly.
        
        Raises:
            ValueError: If configuration is missing required fields or goals are invalid.
        """
        logger.debug("Validating configuration...")
        if self.config is None: # Check if config was successfully passed from base
             raise ValueError("EnhancedCrewFactory cannot validate a None configuration.")

        required_fields = ['company_name', 'product', 'industry', 'target_country', 'goals']
        missing_fields = [field for field in required_fields if not hasattr(self.config, field) or getattr(self.config, field) is None]
        if missing_fields:
            raise ValueError(f"Config is missing required fields: {', '.join(missing_fields)}")
        
        if not isinstance(self.config.product, dict) or not self.config.product.get('name') or not self.config.product.get('description'):
             raise ValueError("Config product must be a dictionary with non-empty 'name' and 'description'.")

        if not isinstance(self.config.goals, tuple) or len(self.config.goals) == 0:
            raise ValueError("Config must include at least one goal, provided as a tuple.")
        logger.debug("Configuration validation passed.")

    def generate_crew_summary(self) -> Dict[str, Dict[str, Tuple[str]]]:
        """Generates a summary of all standard crews, their agents, and tasks.

        Returns:
            Dict[str, Dict[str, Tuple[str]]]: A dictionary where keys are crew names.
                                                Values are dicts with 'agents' (tuple of roles) 
                                                and 'tasks' (tuple of descriptions).
        """
        summary = {}
        standard_crew_names = [
            "Market Research", 
            "Regulatory Compliance", 
            "Supply Chain", 
            "Sales and Marketing", 
            "Implementation and Launch"
        ]
        for crew_name in standard_crew_names:
            try:
                # Create the crew to inspect its structure
                # Note: This uses default LLM settings for inspection
                crew = self.create_crew_by_name(crew_name)
                summary[crew_name] = {
                    # Extract agent roles as a tuple of strings
                    "agents": tuple(agent.role for agent in crew.agents),
                    # Extract task descriptions as a tuple of strings
                    "tasks": tuple(task.description for task in crew.tasks)
                }
            except Exception as e:
                logger.error(f"Error generating summary for crew '{crew_name}': {e}")
                summary[crew_name] = {"error": str(e)} # Include error in summary
        return summary

    def add_custom_task(self, crew_name: str, task_description: str, agent_role: Optional[str] = None):
        """Adds a custom task to an existing crew configuration.

        NOTE: This method currently modifies the crew *instance* returned by 
        `create_crew_by_name`. If caching is active in `create_crew`, subsequent calls
        for the same crew might return the cached, unmodified version. 
        This modification is transient for the current workflow.
        Consider implications if crew instances need to be persistently modified.

        Args:
            crew_name (str): The name of the crew to add the task to.
            task_description (str): The description of the new custom task.
            agent_role (Optional[str]): The role of the agent to assign the task to.
                                        If None, assigns to the first agent in the crew.

        Returns:
            Crew: The modified crew instance with the added task (and potentially reordered tasks).
        
        Raises:
            ValueError: If the specified crew_name is invalid.
        """
        logger.info(f"Adding custom task to crew '{crew_name}': {task_description[:50]}...")
        # Retrieve the crew instance (potentially cached)
        crew = self.create_crew_by_name(crew_name)
        
        # Find the target agent or default to the first one
        target_agent = None
        if agent_role:
            target_agent = next((agent for agent in crew.agents if agent.role == agent_role), None)
        if not target_agent:
             if not crew.agents: # Handle case where crew somehow has no agents
                 logger.error(f"Cannot add task: Crew '{crew_name}' has no agents.")
                 # Or raise an error? Depending on desired behavior.
                 return crew # Return unmodified crew
             target_agent = crew.agents[0]
             if agent_role:
                 logger.warning(f"Agent role '{agent_role}' not found in crew '{crew_name}'. Assigning task to default agent '{target_agent.role}'.")
        
        # Create the new task instance (doesn't need config formatting here)
        new_task = Task(description=task_description, agent=target_agent)
        
        # Append the new task (modifies the tasks list of this crew instance)
        crew.tasks = tuple(list(crew.tasks) + [new_task])
        logger.debug(f"Task added to crew '{crew_name}'. Total tasks: {len(crew.tasks)}")
        
        # Re-prioritize tasks including the new one
        return self.prioritize_tasks(crew)

    def prioritize_tasks(self, crew: Crew) -> Crew:
        """Sorts tasks within a crew based on goal relevance (simple heuristic).

        Attempts to place tasks related to configured goals before general tasks.

        Args:
            crew (Crew): The crew instance whose tasks need sorting.

        Returns:
            Crew: The same crew instance with its `tasks` attribute potentially reordered.
        """
        logger.debug(f"Prioritizing tasks for crew '{crew.name if hasattr(crew, 'name') else 'Unnamed'}'")
        # Define the order: goals first, then a placeholder for general tasks
        if self.config and self.config.goals: # Ensure config and goals are available
             priority_order = list(self.config.goals) + ["General"] # Ensure goals is a list here
        else:
             logger.warning("Cannot prioritize tasks: Config or config.goals is missing. Using default task order.")
             return crew # Return unsorted if no goals

        # Sort tasks based on the index of the first matching goal found in the description
        # Lower index means higher priority. Tasks not matching any goal get the 'General' priority.
        try:
             # Ensure task.description is a string before calling lower()
             crew.tasks = tuple(sorted(crew.tasks,
                                       key=lambda task: next((i for i, goal in enumerate(priority_order)
                                                            if isinstance(task.description, str) and goal.lower() in task.description.lower()),
                                                           len(priority_order)))) # Assign lowest priority if no goal matches or description not string
             logger.debug("Task prioritization complete.")
        except Exception as e:
             logger.error(f"Error during task prioritization for crew '{crew.name if hasattr(crew, 'name') else 'Unnamed'}': {e}", exc_info=True)
             # Return crew with original task order in case of error
        return crew

    def export_to_json(self) -> str:
        """Exports the summary of standard crew structures to a JSON string.

        Uses the `generate_crew_summary` method.

        Returns:
            str: A JSON string representing the standard crew structures, or a JSON
                 object containing an error message if summary generation failed.
        """
        logger.info("Exporting crew structure summary to JSON")
        try:
            # Generate the summary dictionary
            export_data = self.generate_crew_summary()
            
            # Convert the summary data to a JSON string with indentation
            return json.dumps(export_data, indent=2)
        except Exception as e:
            logger.error(f"Error exporting crew summary to JSON: {str(e)}", exc_info=True)
            # Return a JSON object indicating the error
            return json.dumps({"error": f"Failed to export crew summary: {str(e)}"}) 

    def create_crew_by_name(self, crew_name: str) -> Crew:
        """Helper method to retrieve a specific standard crew instance by its name.

        Args:
            crew_name (str): The name of the standard crew to create.

        Returns:
            Crew: The initialized crew instance.
        
        Raises:
            ValueError: If the crew_name is not recognized.
        """
        # Mapping from crew names to their creation methods
        crew_methods = {
            "Market Research": self.create_market_research_crew,
            "Regulatory Compliance": self.create_regulatory_compliance_crew,
            "Supply Chain": self.create_supply_chain_crew,
            "Sales and Marketing": self.create_sales_marketing_crew,
            "Implementation and Launch": self.create_implementation_launch_crew
        }
        
        if crew_name not in crew_methods:
            logger.error(f"Attempted to create unknown crew name: {crew_name}")
            raise ValueError(f"Unknown crew name: {crew_name}. Valid names are: {list(crew_methods.keys())}")
        
        logger.debug(f"Calling creation method for crew: {crew_name}")
        # Call the corresponding creation method
        return crew_methods[crew_name]()

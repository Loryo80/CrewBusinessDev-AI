import json
import os
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional, TYPE_CHECKING, ForwardRef
from pydantic import BaseModel

# Use TYPE_CHECKING for conditional imports
if TYPE_CHECKING:
    from ..config import Config
else:
    # Define a forward reference for Config
    Config = ForwardRef('Config')

# Attempt runtime import of Config
try:
    from ..config import Config
except ImportError:
    # Fallback for potential direct script execution or different structure
    logger = logging.getLogger(__name__)
    logger.warning("Could not perform relative import of Config. Assuming it's available elsewhere.")
    # Config remains a ForwardRef in this case

logger = logging.getLogger(__name__)

# Pydantic models for potential structured output (currently unused but good practice)
class TaskOutput(BaseModel):
    """Represents the structured output of a single task within a crew."""
    description: Optional[str] = None
    raw: str
    # Add other relevant fields if tasks produce structured data

class CrewOutput(BaseModel):
    """Represents the structured output of an entire crew execution."""
    raw: str # Overall summary or final output
    tasks_output: Optional[List[TaskOutput]] = None
    token_usage: Optional[Dict[str, int]] = None # Optional: track token usage
    # Add other relevant fields from crew results


class ReportManager:
    """Handles saving and retrieving crew execution reports as JSON files.

    Organizes reports in a structured directory based on the configuration 
    (company, product, country).
    
    Attributes:
        config (Config): The configuration object for the current run.
        base_path (Path): The root directory for saving reports for this config.
        logger (logging.Logger): Logger instance for this class.
    """
    def __init__(self, config: 'Config'):
        """Initializes the ReportManager.

        Args:
            config (Config): The configuration object.
        
        Raises:
            TypeError: If config is None or not provided.
        """
        if config is None:
            raise TypeError("Configuration object must be provided.")
        self.config = config
        # Calculate path relative to project root (assuming src/core structure)
        # This assumes the script is run from the project root or PYTHONPATH is set correctly.
        project_root = Path(__file__).resolve().parent.parent.parent 
        self.base_path = project_root / f"reports/{self.config.company_name}/{self.config.product['name']}/{self.config.target_country}".replace(" ", "_").lower()
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"ReportManager initialized. Base path: {self.base_path}")

    def _json_serializable(self, obj: Any) -> Any:
        """Helper function to make objects JSON serializable.

        Handles datetime objects and objects with __dict__.
        Converts other non-serializable types to string.
        
        Args:
            obj: The object to serialize.
            
        Returns:
            A JSON-serializable representation of the object.
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        # Attempt to serialize Pydantic models or objects with __dict__
        if hasattr(obj, 'model_dump'): # Check for Pydantic v2
             return obj.model_dump()
        elif hasattr(obj, 'dict'): # Check for Pydantic v1
             return obj.dict()
        elif hasattr(obj, '__dict__'):
             return obj.__dict__
        try:
            # Check if it's directly serializable
            json.dumps(obj)
            return obj
        except TypeError:
             # Fallback: convert to string if not serializable
             return str(obj)

    def save_report(self, crew_name: str, data: Any) -> Path:
        """Saves the provided data as a JSON report.

        Creates necessary directories and handles JSON serialization for common types.

        Args:
            crew_name (str): The name of the crew (used in the filename).
            data (Any): The data payload to save (typically the result from crew.kickoff).

        Returns:
            Path: The absolute path to the saved report file.
        
        Raises:
            IOError: If there is an error writing the file.
            TypeError: If data serialization fails unexpectedly.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{crew_name}_{timestamp}.json"
        file_path = self.base_path / file_name
        
        self.logger.info(f"Attempting to save report to: {file_path}")
        
        # Ensure the target directory exists
        try:
             os.makedirs(file_path.parent, exist_ok=True)
        except OSError as e:
             self.logger.error(f"Error creating directory {file_path.parent}: {e}")
             raise IOError(f"Could not create report directory: {file_path.parent}") from e

        # Prepare data for JSON serialization using the helper
        # If data is already a dict, use it; otherwise, try to serialize
        serializable_data = data if isinstance(data, dict) else self._json_serializable(data)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Use the helper function as the default serializer
                json.dump(serializable_data, f, indent=2, ensure_ascii=False, default=self._json_serializable)
            
            self.logger.info(f"Report saved successfully: {file_path}")
            # Avoid logging potentially huge report content unless necessary (debug level)
            # self.logger.debug(f"Report content: {json.dumps(serializable_data, indent=2, default=self._json_serializable)}")
            
            return file_path.resolve() # Return absolute path
        except IOError as e:
            self.logger.error(f"Error saving report file {file_path}: {e}")
            raise
        except TypeError as e:
            self.logger.error(f"Error serializing report data for {file_path}: {e}")
            # Optionally log the problematic data structure (carefully, might be large/sensitive)
            # self.logger.debug(f"Problematic data structure: {data}")
            raise

    def list_reports(self) -> List[str]:
        """Lists the names of saved JSON reports in the base directory.

        Returns:
            List[str]: A list of report filenames (e.g., 'Market_Research_20231027_103000.json').
                       Returns an empty list if the directory doesn't exist or has no reports.
        """
        if not self.base_path.exists():
            self.logger.warning(f"Report directory not found: {self.base_path}")
            return []
        try:
             # Ensure directory exists before listing
             self.base_path.mkdir(parents=True, exist_ok=True)
             reports = [f.name for f in self.base_path.glob("*.json")]
             self.logger.info(f"Found {len(reports)} reports in {self.base_path}")
             return reports
        except OSError as e:
            self.logger.error(f"Error accessing report directory {self.base_path}: {e}")
            return []

    def get_report_content(self, report_name: str) -> Optional[Dict[str, Any]]:
        """Loads and parses the content of a specific JSON report file.

        Args:
            report_name (str): The filename of the report to load.

        Returns:
            Optional[Dict[str, Any]]: The parsed content of the report as a dictionary,
                                     or None if the file doesn't exist or cannot be parsed.
        """
        file_path = self.base_path / report_name
        self.logger.info(f"Attempting to load report: {file_path}")
        if file_path.exists() and file_path.is_file():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    self.logger.info(f"Successfully loaded report: {report_name}")
                    return content
            except json.JSONDecodeError as e:
                self.logger.error(f"Error decoding JSON from {report_name}: {e}")
                return None
            except IOError as e:
                 self.logger.error(f"Error reading report file {report_name}: {e}")
                 return None
            except Exception as e:
                 self.logger.error(f"Unexpected error loading report {report_name}: {e}")
                 return None
        else:
             self.logger.warning(f"Report file not found or is not a file: {file_path}")
             return None

# --- GoalSpecificReportManager (Potentially Deprecated or Refactored) --- 
# This class adds goal-specific logic on top of the basic ReportManager.
# Consider if this logic is better placed elsewhere (e.g., in the Metrics class or app logic)
# depending on how goal-specific summaries are used.

class GoalSpecificReportManager(ReportManager):
    """Extends ReportManager to add functionality specific to goal-based analysis.

    Provides methods to generate summaries filtered by the configured goals.
    NOTE: The utility of this class depends on the specific analysis required.
          Consider if goal-specific processing is better handled closer to where
          the results are consumed (e.g., in the UI or Metrics calculation).
    """
    def __init__(self, config: 'Config'):
        """Initializes the GoalSpecificReportManager.

        Args:
            config (Config): The configuration object.
        """
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.logger.info("GoalSpecificReportManager initialized.")

    def generate_goal_specific_summary(self) -> Dict[str, Dict[str, Any]]:
        """Creates a summary dictionary containing report info relevant to each goal.
        
        Iterates through all saved reports, extracts information potentially
        relevant to each configured goal using `extract_goal_relevant_info`,
        and organizes it by goal.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary where keys are goal names.
                                         Each value is another dictionary mapping
                                         report filenames to the extracted relevant info.
        """
        summary = {goal: {} for goal in self.config.goals}
        self.logger.info(f"Generating goal-specific summary for goals: {self.config.goals}")
        report_list = self.list_reports()
        self.logger.debug(f"Found reports: {report_list}")
        
        for report_name in report_list:
            content = self.get_report_content(report_name)
            if content:
                for goal in self.config.goals:
                    self.logger.debug(f"Extracting info for goal '{goal}' from report '{report_name}'")
                    relevant_info = self.extract_goal_relevant_info(content, goal)
                    if relevant_info:
                        self.logger.debug(f"Found relevant info for goal '{goal}': {relevant_info}")
                        summary[goal][report_name] = relevant_info
                    # else:
                        # self.logger.debug(f"No relevant info found for goal '{goal}'.")
            # else:
                # self.logger.warning(f"Could not get content for report '{report_name}'.")
                
        self.logger.info("Goal-specific summary generation complete.")
        return summary

    def extract_goal_relevant_info(self, content: Dict[str, Any], goal: str) -> Optional[Dict[str, Any]]:
        """Recursively searches a dictionary for keys or string values containing the goal name.

        This is a simple heuristic to find potentially relevant parts of a report.
        It performs a case-insensitive search.

        Args:
            content (Dict[str, Any]): The dictionary (report content) to search within.
            goal (str): The goal name to search for.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the found relevant key-value pairs,
                                     or None if nothing relevant is found.
        """
        relevant_info = {}
        goal_lower = goal.lower()
        
        if isinstance(content, dict):
            for key, value in content.items():
                key_lower = key.lower()
                # Check if goal is in the key or string value
                if goal_lower in key_lower or (isinstance(value, str) and goal_lower in value.lower()):
                    relevant_info[key] = value
                # Recursively search in nested dictionaries
                elif isinstance(value, dict):
                    nested_info = self.extract_goal_relevant_info(value, goal)
                    if nested_info:
                        relevant_info[key] = nested_info
                # Optionally, search within lists of strings or dicts (can be slow)
                # elif isinstance(value, list):
                #    list_info = []
                #    for item in value:
                #        if isinstance(item, str) and goal_lower in item.lower():
                #            list_info.append(item)
                #        elif isinstance(item, dict):
                #            nested_list_info = self.extract_goal_relevant_info(item, goal)
                #            if nested_list_info:
                #                list_info.append(nested_list_info)
                #    if list_info:
                #        relevant_info[key] = list_info
                        
        # Return the dictionary only if it contains relevant info
        return relevant_info if relevant_info else None

    # Note: The methods below seem to duplicate functionality or have unclear purpose
    # compared to the base ReportManager and the goal summary logic above.
    # Consider refactoring or removing if they are not actively used or needed.

    # def generate_report(self, task: str, data: Dict[str, Any]) -> Dict[str, Any]:
    #     """Creates a basic report structure (duplicate of structure used elsewhere?)."""
    #     self.logger.warning("generate_report method called - ensure this structure is intended.")
    #     return {
    #         "task": task,
    #         "timestamp": datetime.now().isoformat(),
    #         "data": data
    #     }

    # def save_and_summarize_report(self, task: str, data: Dict[str, Any]) -> Dict[str, Any]:
    #     """Saves a report and generates a simple text summary (potentially redundant)."""
    #     self.logger.warning("save_and_summarize_report method called - review necessity.")
    #     report = self.generate_report(task, data) # Uses the potentially duplicated structure
    #     file_path = self.save_report(task, report) # Saves using the base class method
    #     summary = self.generate_summary(report) # Generates a simple text summary
    #     return {
    #         "file_path": str(file_path),
    #         "summary": summary
    #     }

    # def generate_summary(self, report: Dict[str, Any]) -> str:
    #     """Generates a very basic textual summary of a report dictionary."""
    #     task = report.get("task", "Unknown task")
    #     timestamp = report.get("timestamp", "Unknown time")
    #     data_keys = list(report.get("data", {}).keys())
    #     return f"Report for {task} generated at {timestamp}. Contains data on: {', '.join(data_keys)}"

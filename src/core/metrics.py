import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GoalBasedMetrics:
    """Tracks progress towards predefined business goals based on crew results.

    Initializes a structure to hold metrics relevant to specific goals 
    (e.g., Market Entry, Product Adaptation). Updates these metrics based on
    the output received from different agent crews.

    Attributes:
        goals (tuple[str]): The list of strategic goals defined in the Config.
        metrics (Dict[str, Dict[str, Any]]): A nested dictionary storing 
                                             metric names and their current values, 
                                             organized by goal.
    """
    def __init__(self, config):
        """Initializes the metrics tracker based on the configuration.

        Args:
            config (Config): The configuration object containing the goals.
        """
        # Store the goals from the configuration
        self.goals = config.goals
        # Initialize the metrics dictionary based on the configured goals
        self.metrics = self.initialize_metrics()

    def initialize_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Sets up the initial structure for metrics based on known goals.

        Defines specific sub-metrics expected for each recognized goal.

        Returns:
            Dict[str, Dict[str, Any]]: An initialized dictionary where each goal 
                                         maps to a dictionary of its specific 
                                         metrics set to initial values (usually 0).
        """
        metrics = {}
        for goal in self.goals:
            # Define default sub-metrics for each known goal type
            if goal == "Market Entry":
                metrics[goal] = {"market_penetration": 0, "brand_recognition": 0}
            elif goal == "Product Adaptation":
                metrics[goal] = {"localization_score": 0, "customer_satisfaction": 0}
            elif goal == "Regulatory Compliance":
                metrics[goal] = {"compliance_rate": 0, "risk_assessment": 0}
            elif goal == "Competitive Positioning":
                metrics[goal] = {"market_share": 0, "competitive_advantage": 0}
            else:
                # Log a warning if a goal from config doesn't have predefined metrics
                logger.warning(f"Unknown goal: {goal}. No specific metrics initialized.")
                metrics[goal] = {} # Initialize with an empty dict for unknown goals
        return metrics

    def update_metrics(self, crew_name: str, result: Dict[str, Any]):
        """Updates the metrics based on the results from a crew execution.

        Attempts to parse the result dictionary, looking for keys that match
        the configured goals and sub-keys that match the initialized metrics.

        Args:
            crew_name (str): The name of the crew that produced the result (for logging).
            result (Dict[str, Any]): The dictionary output from a crew's `kickoff` method.
                                     Expected to potentially contain goal names as keys.
        """
        try:
            logger.info(f"Updating metrics for crew: {crew_name} based on goals: {self.goals}")
            
            # Iterate through the configured goals for this run
            for goal in self.goals:
                # Check if the crew result contains data relevant to this goal
                if goal in result and goal in self.metrics:
                    goal_data = result[goal]
                    # Check if the goal data is a dictionary (expected case)
                    if isinstance(goal_data, dict):
                        for metric, value in goal_data.items():
                            # Update only if the metric is recognized for this goal
                            if metric in self.metrics[goal]:
                                self.metrics[goal][metric] = value
                                logger.debug(f"Updated metric {goal}/{metric} to {value}")
                            else:
                                logger.warning(f"Unrecognized metric '{metric}' for goal '{goal}' in results.")
                    # Handle cases where result[goal] might be a list of dicts (less common)
                    elif isinstance(goal_data, list):
                        for item in goal_data:
                            if isinstance(item, dict):
                                for metric, value in item.items():
                                    if metric in self.metrics[goal]:
                                        self.metrics[goal][metric] = value
                                        logger.debug(f"Updated metric {goal}/{metric} to {value} from list item")
                                    else:
                                        logger.warning(f"Unrecognized metric '{metric}' for goal '{goal}' in list item.")
                    else:
                         logger.warning(f"Unexpected data type for goal '{goal}' in results: {type(goal_data)}")
                # else:
                    # logger.debug(f"Goal '{goal}' not found in crew result keys or not initialized.")

        except Exception as e:
            # Log any errors during the metrics update process
            logger.error(f"Error updating metrics from crew '{crew_name}': {str(e)}", exc_info=True)

    def get_goal_progress(self) -> Dict[str, float]:
        """Calculates a simple progress score for each goal.

        Averages the current values of the sub-metrics for each goal.
        Assumes metrics are numerical and higher values indicate progress.
        This is a basic heuristic for demonstration.

        Returns:
            Dict[str, float]: A dictionary mapping each goal to its calculated 
                              progress score (0-100 scale assumed, but depends on metric values).
        """
        progress = {}
        for goal, goal_metrics in self.metrics.items():
            # Calculate average progress only if metrics exist for the goal
            if goal_metrics and isinstance(goal_metrics, dict):
                # Filter out non-numeric values before averaging
                numeric_values = [v for v in goal_metrics.values() if isinstance(v, (int, float))]
                if numeric_values:
                     progress[goal] = sum(numeric_values) / len(numeric_values)
                else:
                     progress[goal] = 0.0 # No numeric metrics to average
            else:
                progress[goal] = 0.0 # No metrics defined or invalid format
        return progress

    def reset_metrics(self):
        """Resets all metrics back to their initial values."""
        logger.info("Resetting metrics.")
        self.metrics = self.initialize_metrics()

    def generate_summary(self) -> Dict[str, Dict[str, Any]]:
        """Provides a summary of the current state of all metrics.

        Returns:
            Dict[str, Dict[str, Any]]: The current metrics dictionary.
        """
        return {goal: self.metrics.get(goal, {}) for goal in self.goals}
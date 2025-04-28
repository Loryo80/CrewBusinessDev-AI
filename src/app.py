# app.py
"""Main Streamlit application file for the International Business Development Tool.

Handles the user interface, input collection, configuration management, 
crew execution initiation, report display, and basic authentication.
"""

import streamlit as st
import json
import os
import logging
import logging.config
import traceback
from datetime import datetime
from io import BytesIO
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# --- Project Module Imports ---
# Use absolute imports based on the src directory structure
try:
    from .config import Config
    from .core.crew_factory import EnhancedCrewFactory
    from .core.report_manager import ReportManager # Use base ReportManager for saving/loading
    from .core.metrics import GoalBasedMetrics
    from .utils.sanitizer import sanitize_input, sanitize_dict
    from .auth import login_required
    from .utils.validators import validate_input
except ImportError as e:
    # Provide more context if imports fail, which might happen if not run as a module
    st.error(f"Import Error: {e}. Please ensure the application is run as a module (e.g., `streamlit run src/app.py`) from the project root directory.")
    st.stop()
# ----------------------------- #

# --- Setup --- #

# Load logging configuration (adjust path relative to this file within src)
try:
    # Assuming logging_config.ini is in the parent directory of src
    project_root_for_logging = Path(__file__).resolve().parent.parent
    logging.config.fileConfig(project_root_for_logging / 'logging_config.ini')
    logger = logging.getLogger(__name__)
    logger.info("Logging configured.")
except Exception as log_e:
    # Fallback basic logging if config file fails
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load logging config from file: {log_e}. Using basic logging.")

# Load environment variables from .env file
load_dotenv()

# Check for essential API Keys (redundant with crew_factory check, but good for early feedback)
# Note: No need to load keys here if only used within CrewFactory
# REQUIRED_KEYS = ["OPENAI_API_KEY", "MISTRAL_API_KEY", "SERPER_API_KEY", "GOOGLE_API_KEY"]
# missing_keys = [key for key in REQUIRED_KEYS if not os.getenv(key)]
# if missing_keys:
#     logger.error(f"Missing environment variables: {', '.join(missing_keys)}")
#     st.error(f"Application startup failed: Missing required API key(s) in .env file: {', '.join(missing_keys)}. Please refer to README.md.")
#     st.stop()

# --- Pydantic Models for Structure (Optional) ---
# These mirror the ones in report_manager.py, useful if data needs validation here.
# Consider consolidating these into a shared types module.
class TaskOutput(BaseModel):
    """Structure for individual task output within a report."""
    description: Optional[str] = None
    raw: str

class CrewOutput(BaseModel):
    """Structure for the main data part of a saved report."""
    raw: str
    tasks_output: Optional[List[TaskOutput]] = None
    token_usage: Optional[Dict[str, int]] = None

# --- Core Application Logic --- #

@login_required
def run_business_development(config: Config) -> Tuple[Optional[ReportManager], Optional[GoalBasedMetrics], Optional[EnhancedCrewFactory]]:
    """Orchestrates the execution of all relevant business development crews.

    Initializes the factory, report manager, and metrics tracker.
    Creates and runs each predefined crew sequentially.
    Saves reports and updates metrics after each crew execution.
    Displays initial and final crew structures.

    Args:
        config (Config): The validated configuration object for the scenario.

    Returns:
        Tuple containing the ReportManager, GoalBasedMetrics, and EnhancedCrewFactory 
        instances used in the run, or (None, None, None) if a critical error occurs.
    """
    logger.info(f"Starting business development run for {config.company_name} targeting {config.target_country}")
    progress_bar = st.progress(0, text="Initializing...")
    status_text = st.empty()

    try:
        # 1. Initialization
        status_text.text("Initializing Crew Factory, Report Manager, and Metrics...")
        factory = EnhancedCrewFactory(config)
        # Use the base ReportManager here, GoalSpecific features seem less relevant for the core run
        report_manager = ReportManager(config)
        metrics = GoalBasedMetrics(config)
        progress_bar.progress(10)

        # Ensure report directory exists (ReportManager constructor handles this)
        # os.makedirs(report_manager.base_path, exist_ok=True)

        # 2. Display Initial Structure (Optional Debug/Info)
        status_text.text("Displaying Initial Crew Setup...")
        with st.expander("View Initial Crew Structure (JSON)"):
            try:
                initial_structure = factory.export_to_json()
                st.json(json.loads(initial_structure)) # Parse string to dict for st.json
            except json.JSONDecodeError as json_error:
                st.error(f"Error parsing initial crew structure JSON: {str(json_error)}")
                logger.error(f"JSON parsing error in initial structure: {str(json_error)}")
                logger.debug(f"Raw JSON data: {factory.export_to_json()}")
            except Exception as e:
                st.error(f"An unexpected error occurred displaying initial structure: {str(e)}")
                logger.error(f"Unexpected error in initial JSON display: {str(e)}", exc_info=True)
        progress_bar.progress(15)

        # --- Custom Task Addition (Consider placing this before crew creation) --- #
        # This section currently allows adding tasks AFTER crews might be cached.
        # For dynamic task addition to influence the run, it should happen *before*
        # `create_crew_by_name` is potentially called and cached.
        # This might require refactoring how crews are created or managed if dynamic addition
        # during a run is a core feature.
        st.subheader("Add Custom Tasks (Experimental)")
        crew_names = ["Market Research", "Regulatory Compliance", "Supply Chain", "Sales and Marketing", "Implementation and Launch"]
        selected_crew_for_task = st.selectbox("Select crew to add task to:", crew_names, key="custom_task_crew_select")
        custom_task_description = st.text_input("Enter custom task description:", key="custom_task_desc")
        # Optional: Select agent role if crew has multiple agents
        # agent_role_for_task = st.text_input("Assign to agent role (optional):", key="custom_task_agent")
        
        if st.button("Add Custom Task", key="add_custom_task_btn"):
            if custom_task_description:
                try:
                    # This modifies a potentially cached crew instance; see method docstring
                    factory.add_custom_task(selected_crew_for_task, custom_task_description) #, agent_role=agent_role_for_task)
                    st.success(f"Custom task tentatively added to {selected_crew_for_task} crew for this run. View Final Structure below.")
                    logger.info(f"Custom task added to {selected_crew_for_task} via UI.")
                    # Refresh the final structure view if needed after modification
                except Exception as e:
                    st.error(f"Error adding custom task: {str(e)}")
                    logger.error(f"Error adding custom task: {str(e)}", exc_info=True)
            else:
                st.warning("Please enter a task description.")
        # ----------------------------------------------------------------------------- #

        # 3. Crew Creation
        status_text.text("Creating Agent Crews...")
        crews_to_run = []
        try:
            # Define the standard crews to run in sequence
            standard_crews = [
                ("Market Research", factory.create_market_research_crew),
                ("Regulatory Compliance", factory.create_regulatory_compliance_crew),
                ("Supply Chain", factory.create_supply_chain_crew),
                ("Sales and Marketing", factory.create_sales_marketing_crew),
                ("Implementation and Launch", factory.create_implementation_launch_crew)
            ]
            for name, creator_func in standard_crews:
                 crews_to_run.append(creator_func()) # Create each crew instance
            logger.info(f"Successfully created {len(crews_to_run)} crews.")
            progress_bar.progress(25)
        except Exception as e:
            st.error(f"An error occurred while creating crews: {str(e)}")
            logger.error(f"Error creating crews: {str(e)}", exc_info=True)
            return None, None, None # Critical error, cannot proceed

        # 4. Crew Execution Loop
        total_crews = len(crews_to_run)
        for i, crew in enumerate(crews_to_run):
            crew_display_name = crew.name if hasattr(crew, 'name') else f"Crew {i+1}"
            status_text.text(f"Running Crew {i+1}/{total_crews}: {crew_display_name}...")
            logger.info(f"Kicking off crew: {crew_display_name}")
            
            with st.spinner(f"Running {crew_display_name}..."):
                try:
                    # Execute the crew's tasks
                    # TODO: Consider making this async for better UI responsiveness
                    result = crew.kickoff()
                    logger.info(f"Crew {crew_display_name} finished successfully.")
                    
                    # Save the raw result as a report
                    report_file = report_manager.save_report(crew_display_name, result)
                    logger.info(f"Report saved for {crew_display_name} at {report_file}")
                    
                    # Update metrics based on the result (assuming result is dict)
                    if isinstance(result, dict):
                        metrics.update_metrics(crew_display_name, result)
                        logger.info(f"Metrics updated based on {crew_display_name} results.")
                    else:
                         logger.warning(f"Crew {crew_display_name} result was not a dict. Type: {type(result)}. Skipping metrics update.")
                         
                except Exception as e:
                    st.error(f"An error occurred during {crew_display_name} execution: {str(e)}")
                    logger.error(f"Execution error in crew {crew_display_name}: {str(e)}", exc_info=True)
                    # Decide whether to stop the whole process or continue with next crew
                    # For now, we stop the run on any crew execution error.
                    status_text.text(f"Error during {crew_display_name} execution. Aborting run.")
                    progress_bar.progress(int((i + 1) / total_crews * 70) + 25) # Update progress partially
                    return None, None, None 
            
            # Update progress bar after each crew completes
            progress_value = int(((i + 1) / total_crews) * 70) + 25 # Scale progress between 25% and 95%
            progress_bar.progress(progress_value)

        # 5. Completion & Final Structure
        status_text.text("Business development analysis complete!")
        st.success("All crews completed their tasks successfully!")
        progress_bar.progress(100)

        with st.expander("View Final Crew Structure (JSON) - Includes Custom Tasks Added This Run"):
            try:
                # Note: This shows the structure AFTER potential modifications by add_custom_task
                final_structure = factory.export_to_json()
                st.json(json.loads(final_structure))
            except json.JSONDecodeError as json_error:
                st.error(f"Error parsing final crew structure JSON: {str(json_error)}")
                logger.error(f"JSON parsing error in final structure: {str(json_error)}")
            except Exception as e:
                st.error(f"An unexpected error occurred displaying final structure: {str(e)}")
                logger.error(f"Unexpected error in final JSON display: {str(e)}", exc_info=True)

        return report_manager, metrics, factory
        
    except Exception as e:
        # Catch-all for errors during the overall process
        logger.error(f"An unexpected error occurred during the business development run: {str(e)}", exc_info=True)
        st.error(f"A critical error occurred: {str(e)}")
        status_text.text("Run failed due to an unexpected error.")
        # Log detailed traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        progress_bar.progress(100) # Indicate completion, even if failed
        return None, None, None

# --- Report Loading and Display --- #

def load_report(file_path: Path) -> Optional[Dict[str, Any]]:
    """Loads and parses a JSON report file.

    Args:
        file_path (Path): The path to the JSON report file.

    Returns:
        Optional[Dict[str, Any]]: The loaded report data as a dictionary, 
                                 or None if loading fails.
    """
    logger.info(f"Attempting to load report from: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
            logger.info(f"Successfully loaded report: {file_path.name}")
            return report_data
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON from {file_path.name}: {str(e)}")
        logger.error(f"JSON decode error for {file_path}: {str(e)}")
    except IOError as e:
        st.error(f"Error reading file {file_path.name}: {str(e)}")
        logger.error(f"IOError reading {file_path}: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected error occurred loading {file_path.name}: {str(e)}")
        logger.error(f"Unexpected error loading {file_path}: {str(e)}", exc_info=True)
    return None

def display_report(report_data: Dict[str, Any]):
    """Displays the contents of a loaded report in Streamlit.

    Formats the display to show overall summary, detailed task outputs,
    and token usage if available. Handles potentially missing keys.

    Args:
        report_data (Dict[str, Any]): The report data dictionary.
    """
    if not report_data or not isinstance(report_data, dict):
        st.error("Invalid or empty report data provided.")
        logger.warning("Attempted to display invalid report data.")
        return

    # Use crew name from filename (if available) or default
    # This part assumes the report structure might differ - adjust as needed.
    report_title = report_data.get('crew_name', report_data.get('task', 'Unknown Report')) 
    st.subheader(f"Displaying Report: {report_title}")
    timestamp = report_data.get('timestamp', 'Timestamp not available')
    st.caption(f"Generated: {timestamp}")

    # CrewAI results often nested under a key like 'result' or directly
    # We need to handle potential variations in structure based on crew.kickoff() output format.
    # Let's assume the core content might be in a 'data' key if generated by `generate_task_report`,
    # or directly in the root if saved from `crew.kickoff()`.
    
    main_content = report_data.get('data', report_data) # Look in 'data' first, then root

    if isinstance(main_content, str):
         # If the main content is just a string, display it directly
         st.subheader("Overall Output")
         st.markdown(main_content)
         logger.info("Displayed simple string report content.")

    elif isinstance(main_content, dict):
        logger.info("Displaying structured dictionary report content.")
        # Display overall summary / raw output
        st.subheader("Overall Summary / Raw Output")
        raw_output = main_content.get('raw', 'No raw output provided.')
        if isinstance(raw_output, str):
             st.markdown(raw_output) # Use markdown for better formatting potential
        else:
             st.json(raw_output) # Display as JSON if not a string

        # Display individual task outputs if present
        tasks_output = main_content.get('tasks_output')
        if tasks_output and isinstance(tasks_output, list):
            st.subheader("Detailed Task Outputs")
            if not tasks_output:
                 st.write("No detailed task outputs available in this report.")
            else:
                 for i, task_output_data in enumerate(tasks_output):
                     if isinstance(task_output_data, dict):
                          # Try to parse with Pydantic for structure, fallback to dict access
                          try:
                               task_output = TaskOutput(**task_output_data)
                               expander_title = task_output.description or f"Task {i+1}"
                               with st.expander(expander_title):
                                   st.markdown(task_output.raw)
                          except Exception:
                               # Fallback if structure doesn't match TaskOutput model
                               expander_title = task_output_data.get('description', f"Task {i+1} (raw dict)")
                               with st.expander(expander_title):
                                   st.markdown(task_output_data.get('raw', 'No raw output found in task dict.'))
                                   # Optionally display the full task dict for debugging
                                   # st.json(task_output_data)
                     else:
                          st.warning(f"Task output item {i+1} is not a dictionary: {type(task_output_data)}")
        else:
            st.write("No detailed task outputs found in this report structure.")

        # Display token usage if available
        token_usage = main_content.get('token_usage')
        if token_usage:
            st.subheader("Token Usage")
            st.json(token_usage)
        else:
             st.write("Token usage data not found in this report.")
    else:
        # Handle cases where the main content is neither string nor dict
        st.error("Report data is not in a recognized format (expected string or dictionary).")
        st.json(main_content) # Display raw content as JSON for inspection
        logger.warning(f"Displayed unrecognized report content type: {type(main_content)}")

def list_available_reports(config: Config) -> List[str]:
    """Lists available JSON report files for the given configuration.

    Args:
        config (Config): The configuration object.

    Returns:
        List[str]: A list of report filenames found in the specific directory 
                   for this configuration. Returns empty list if directory 
                   doesn't exist or contains no reports.
    """
    if not config or not config.company_name or not config.product or not config.target_country:
        logger.warning("Attempted to list reports with incomplete config.")
        return [] # Cannot determine path without full config
        
    try:
        # Construct the expected path based on the config
        # Use the same logic as ReportManager initialization
        project_root = Path(__file__).resolve().parent.parent
        base_path = project_root / f"reports/{config.company_name}/{config.product['name']}/{config.target_country}".replace(" ", "_").lower()
        
        logger.info(f"Checking for reports in: {base_path}")
        if not base_path.exists() or not base_path.is_dir():
            logger.info("Report directory does not exist.")
            return []
            
        # List only .json files
        reports = [f.name for f in base_path.glob("*.json") if f.is_file()]
        logger.info(f"Found {len(reports)} reports.")
        return sorted(reports, reverse=True) # Sort newest first
    except Exception as e:
        logger.error(f"Error listing reports for config {config.to_dict()}: {e}", exc_info=True)
        st.error(f"Error accessing report directory: {e}")
        return []

# --- Streamlit UI Main Function --- #

@login_required # Apply the login decorator to the main function
def main():
    """Defines the main Streamlit user interface and application flow."""
    st.set_page_config(page_title="International Business Development AI", layout="wide")
    st.title("🌍 International Business Development AI Assistant")
    st.caption("Leveraging CrewAI agents for strategic planning")

    # --- Input Section --- #
    st.sidebar.header("Scenario Configuration")
    company_name = sanitize_input(st.sidebar.text_input("Company Name", key="company_name_input", help="Your company's name."))
    company_website = sanitize_input(st.sidebar.text_input("Company Website", key="website_input", help="Your company's primary website (e.g., https://www.example.com)."))
    product_name = sanitize_input(st.sidebar.text_input("Product/Service Name", key="product_name_input", help="The name of the product or service."))
    product_description = sanitize_input(st.sidebar.text_area("Product/Service Description", key="product_desc_input", height=100, help="Briefly describe the product/service and its value proposition."))
    industry_options = ["Food Industry", "Technology", "Dairy", "Healthcare", "Finance", "Manufacturing", "Retail", "Other"] # Expanded options
    industry = st.sidebar.selectbox("Industry", industry_options, key="industry_select", help="Select the most relevant industry.")
    target_country = sanitize_input(st.sidebar.text_input("Target Country", key="country_input", help="The country you want to analyze for market entry."))
    goal_options = ["Market Entry", "Product Adaptation", "Regulatory Compliance", "Competitive Positioning"]
    goals = st.sidebar.multiselect("Strategic Goals", goal_options, key="goals_multiselect", help="Select the primary objectives for this analysis.")

    # Store inputs temporarily for validation
    input_data = {
        'company_name': company_name,
        'company_website': company_website,
        'product': {"name": product_name, "description": product_description},
        'industry': industry,
        'target_country': target_country,
        'goals': goals
    }

    # --- Action Buttons & Workflow --- #
    st.sidebar.divider()
    run_button = st.sidebar.button("🚀 Start Full Analysis", key="start_button", use_container_width=True, help="Run all agent crews based on the configuration.")
    # Removed "Generate Reports" button as it seemed redundant with the main run

    st.header("Analysis Execution & Results")

    # Validate inputs before proceeding
    validation_errors = validate_input(input_data)
    config = None
    if not validation_errors:
        try:
            # If validation passes, create the Config object
            config = Config(
                company_name=company_name,
                company_website=company_website,
                product=sanitize_dict({"name": product_name, "description": product_description}),
                industry=industry,
                target_country=target_country,
                goals=tuple(goals) # Config expects tuple
            )
            logger.info(f"Configuration created successfully: {config.to_dict()}")
        except ValueError as ve:
            # Catch validation errors during Config instantiation (double check)
            validation_errors.append(f"Configuration Error: {str(ve)}")
            logger.error(f"Config object creation failed: {str(ve)}", exc_info=True)
        except Exception as config_e:
            validation_errors.append(f"Unexpected error creating config: {str(config_e)}")
            logger.error(f"Unexpected error during Config creation: {str(config_e)}", exc_info=True)
    
    # Display validation errors if any
    if validation_errors:
        st.error("Please correct the following configuration issues:")
        for error in validation_errors:
            st.warning(f"- {error}")
        # Disable run button indirectly by not proceeding if config is None
        # run_button = False # This doesn't work as expected with Streamlit's flow

    # --- Execute Analysis --- #
    if run_button and config:
        logger.info("'Start Full Analysis' button clicked with valid config.")
        with st.container(): # Group execution output
             report_manager, metrics, factory = run_business_development(config)
             
             if report_manager and metrics and factory:
                 st.success("✅ Full analysis completed successfully!")
                 # Display final metrics
                 st.subheader("📊 Final Goal Progress (Heuristic)")
                 st.json(metrics.get_goal_progress())
                 # Store results in session state if needed for later use
                 st.session_state['last_run_metrics'] = metrics.get_goal_progress()
                 st.session_state['last_run_config'] = config # Store config too
             else:
                 st.error("❌ Analysis run encountered errors. Please check logs.")
    elif run_button and not config:
         st.error("Cannot start analysis due to configuration errors listed above.")
         logger.warning("'Start Full Analysis' button clicked, but config is invalid or None.")

    # --- Report Loading Section --- #
    st.divider()
    st.header("📂 Load & View Reports")

    # Use config from current inputs if valid, otherwise try loading from session state
    config_for_reports = config # Use current valid config if available
    if not config_for_reports and 'last_run_config' in st.session_state:
        config_for_reports = st.session_state['last_run_config']
        st.info("Using configuration from last successful run to list reports.")

    if config_for_reports:
        available_reports = list_available_reports(config_for_reports)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if available_reports:
                selected_report_name = st.selectbox(
                    "Select a saved report to load:", 
                    available_reports, 
                    key="report_select",
                    help="Reports are named [CrewName]_[Timestamp].json"
                )
            else:
                st.info("No reports found for the current configuration. Run an analysis first.")
                selected_report_name = None
        with col2:
            load_report_button = st.button("Load Selected Report", key="load_report_btn", disabled=not selected_report_name, use_container_width=True)

        if load_report_button and selected_report_name:
            logger.info(f"'Load Selected Report' button clicked for: {selected_report_name}")
            # Construct the full path using the same logic as ReportManager
            try:
                 project_root = Path(__file__).resolve().parent.parent
                 report_path = project_root / f"reports/{config_for_reports.company_name}/{config_for_reports.product['name']}/{config_for_reports.target_country}".replace(" ", "_").lower() / selected_report_name
                 
                 report_data = load_report(report_path)
                 if report_data:
                     display_report(report_data)
                 # Error handling is done within load_report
            except Exception as load_e:
                 st.error(f"Error constructing path or loading report: {load_e}")
                 logger.error(f"Error during report loading button action: {load_e}", exc_info=True)

    else:
        st.warning("Enter a valid configuration in the sidebar to list or load reports.")

    # --- Manual Path Option (Less Ideal) --- #
    # with st.expander("Load Report by Full Path"):
    #     manual_report_path_input = st.text_input("Enter full path to a report JSON file:", key="manual_path_input")
    #     if st.button("Load from Path", key="load_path_btn"):
    #         if manual_report_path_input:
    #             file_path = Path(manual_report_path_input)
    #             if file_path.exists() and file_path.is_file() and file_path.suffix == '.json':
    #                 logger.info(f"Attempting to load manual path: {file_path}")
    #                 report_data = load_report(file_path)
    #                 if report_data:
    #                     display_report(report_data)
    #             else:
    #                 st.error(f"Invalid path or not a JSON file: {file_path}")
    #         else:
    #             st.warning("Please enter a file path.")

# --- Helper for Generating Single Report (If needed standalone) --- #
# This function seems less relevant now that the main run executes all crews.
# Kept here for reference but might be removable.
def generate_task_report(task_name: str, config: Config) -> Dict[str, Any]:
    """Generates a report for a single specified task/crew.

    Creates the necessary crew based on the task name and runs it.
    Intended for generating individual reports on demand (less used now).

    Args:
        task_name (str): The name of the task/crew to run 
                         (e.g., "Market Research").
        config (Config): The configuration object.

    Returns:
        Dict[str, Any]: A dictionary containing the report data or an error message.
    """
    logger.info(f"Generating standalone report for task: {task_name}")
    try:
        factory = EnhancedCrewFactory(config)
        crew = None

        # Map task name to crew creation method
        crew_methods = {
            "Market Research": factory.create_market_research_crew,
            "Regulatory Compliance": factory.create_regulatory_compliance_crew,
            "Supply Chain Management": factory.create_supply_chain_crew,
            "Sales and Marketing": factory.create_sales_marketing_crew,
            "Implementation and Launch": factory.create_implementation_launch_crew
        }

        if task_name in crew_methods:
            crew = crew_methods[task_name]()
        else:
            logger.error(f"Unknown task name provided for standalone report generation: {task_name}")
            return {"error": f"Unknown task '{task_name}'"}

        if crew:
            logger.info(f"Kicking off crew for task '{task_name}'")
            result = crew.kickoff() # Consider adding error handling around kickoff
            report_data = {
                "task": task_name, # Or use crew.name?
                "timestamp": datetime.utcnow().isoformat(),
                "data": result
            }
            logger.info(f"Successfully generated report data for task '{task_name}'")
            return report_data
        else:
            # Should not happen if task_name is valid, but as a safeguard
            logger.error(f"Crew object was None for task '{task_name}' despite valid mapping.")
            return {"error": f"Unable to create crew for task '{task_name}'"}
            
    except Exception as e:
        logger.error(f"Error generating standalone report for {task_name}: {str(e)}", exc_info=True)
        return {"error": f"Error generating report for {task_name}: {str(e)}"}

# --- Application Entry Point --- #
if __name__ == "__main__":
    logger.info("Starting Streamlit application.")
    main()
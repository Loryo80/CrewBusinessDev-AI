# International Business Development AI Assistant

**Project Goal:** To demonstrate advanced AI architecture principles using a multi-agent system (CrewAI) for complex international business development planning, showcasing integration with multiple leading Large Language Models (LLMs).

This Streamlit application leverages CrewAI agents to assist with various aspects of international business development planning, simulating a collaborative team of AI specialists.

## AI Architecture & Key Features

This project serves as a portfolio piece demonstrating key competencies relevant to an **AI Architect** role:

*   **Multi-Agent System (CrewAI):**
    *   Employs a sophisticated multi-agent framework (`CrewAI`) where specialized AI agents (e.g., Market Researcher, Regulatory Compliance Officer) collaborate to achieve complex goals.
    *   Utilizes a **hierarchical process** where a manager agent oversees the workflow and synthesizes findings from specialized agents, mimicking real-world team dynamics.
    *   Demonstrates dynamic task allocation and collaboration between agents.

*   **Multi-LLM Integration & Flexibility:**
    *   **Configured for Multiple Leading LLMs:** The system is architected to integrate seamlessly with various state-of-the-art LLMs via LangChain. It is currently configured with:
        *   **Mistral AI (`mistral-large-latest`)**
        *   **OpenAI (`gpt-4o-mini`)**
        *   **Google (`gemini-1.5-flash`)**
    *   This demonstrates the ability to design systems that are LLM-agnostic, allowing for strategic selection based on performance, cost, or specific task requirements.
    *   The underlying `CrewFactory` allows selecting the LLM for agents and the crew manager (defaults to OpenAI currently).

*   **Modular & Scalable Design:**
    *   Source code is organized into logical modules (`src/core`, `src/utils`) promoting maintainability, testability, and ease of extension.
    *   Leverages Python best practices, including clear separation of concerns (UI in `app.py`, core logic in `core/`, utilities in `utils/`).

*   **Configuration-Driven Planning:**
    *   Utilizes a central `Config` object (`src/config.py`) to define the business scenario (company, product, target country, goals), making the system adaptable to different inputs without code changes.

*   **Agent Tooling & Grounding:**
    *   Agents are equipped with external tools (`SerperDevTool` for web search, `WebsiteSearchTool`) to ground their analysis in real-time information, enhancing the reliability and relevance of their outputs.

*   **Structured Reporting & Metrics:**
    *   Generates structured JSON reports for each crew's execution (`src/core/report_manager.py`).
    *   Includes a basic metrics system (`src/core/metrics.py`) to track progress against high-level business goals.

*   **Robust Development Practices:**
    *   Uses environment variables (`python-dotenv`) for API key management.
    *   Includes basic input validation (`src/utils/validators.py`) and sanitization (`src/utils/sanitizer.py`).
    *   Configured logging (`logging_config.ini`) for monitoring and debugging.

## Technology Stack

*   **Core Framework:** Python 3.10+
*   **Multi-Agent System:** CrewAI
*   **LLM Integration:** LangChain
*   **Configured LLMs:** Mistral AI, OpenAI, Google Generative AI
*   **Web UI:** Streamlit
*   **Agent Tools:** SerperDevTool, WebsiteSearchTool
*   **Dependencies:** See `requirements.txt`

## Project Structure

```
CrewBusinessDev-officiel/
├── .env                 # Local environment variables (API Keys)
├── .env.example         # Example environment variable structure
├── .gitignore           # Standard Python/IDE gitignore
├── logging_config.ini   # Logging configuration
├── README.md            # This file
├── requirements.txt     # Python dependencies
├── src/                  # Source code directory
│   ├── __init__.py
│   ├── app.py            # Streamlit UI/Application Entrypoint
│   ├── auth.py           # Basic authentication
│   ├── config.py         # Business scenario configuration class
│   ├── core/             # Core AI logic (Agents, Crews, Reports)
│   │   ├── __init__.py
│   │   ├── crew_factory.py # Defines Agents, Tasks, Crews, LLM config
│   │   ├── metrics.py      # Goal tracking logic
│   │   └── report_manager.py # Report saving/management
│   ├── utils/            # Utility functions
│   │   ├── __init__.py
│   │   ├── sanitizer.py    # Input sanitization
│   │   └── validators.py   # Input validation
│   
└── reports/             # Output reports (created at runtime, gitignored)
└── CrewBusinessDev/      # Python Virtual Environment (gitignored)
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd CrewBusinessDev-officiel
    ```

2.  **Create and activate a virtual environment:** (Recommended)
    ```bash
    python -m venv CrewBusinessDev
    # Windows: CrewBusinessDev\Scripts\activate
    # macOS/Linux: source CrewBusinessDev/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    *   Copy `env.example.txt` to a new file named `.env`.
    *   **Important:** Rename `env.example.txt` to `.env`.
    *   Open the `.env` file and add your actual API keys:
    ```dotenv
    # .env
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
    SERPER_API_KEY="YOUR_SERPER_API_KEY"
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    MISTRAL_API_KEY="YOUR_MISTRAL_API_KEY"
    ```

## Running the Application

Ensure your virtual environment is activated and the `.env` file is populated.

```bash
streamlit run src/app.py
```

Navigate to the URL provided by Streamlit (usually `http://localhost:8501`).

## Environment Variables Required

*   `OPENAI_API_KEY`: For OpenAI models (e.g., GPT-4o-mini).
*   `SERPER_API_KEY`: For the SerperDevTool search functionality.
*   `GOOGLE_API_KEY`: For Google Generative AI models (e.g., Gemini-1.5-flash).
*   `MISTRAL_API_KEY`: For Mistral AI models (e.g., mistral-large-latest). 

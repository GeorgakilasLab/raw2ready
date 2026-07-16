# Architecture Overview

This section describes the layout, data flows, and structural components of **raw2ready**.

---

## High-Level Architecture

The framework consists of a NiceGUI-based single-page application (SPA) front-end, a Python-based calculation and data manipulation layer, and an AI multi-agent orchestrator.

```
                  +--------------------------------+
                  |      NiceGUI Web Interface     |
                  |           (run_app.py)          |
                  +--------------------------------+
                                  |
            +---------------------+---------------------+
            |                                           |
            v                                           v
+-----------------------+                   +-----------------------+
|    Frontend Pages     |                   |    AI Chat Interface  |
|    (src/gui/ folder)  |                   | (src/gui/llm_gui.py)  |
+-----------------------+                   +-----------------------+
            |                                           |
            v                                           v
+-----------------------+                   +-----------------------+
|   Core Business Logic |                   |   Agent Orchestrator  |
|   (src/core/ folder)  |                   |  (src/agents/ folder) |
+-----------------------+                   +-----------------------+
            |                                           |
            +---------------------+---------------------+
                                  |
                                  v
                    +---------------------------+
                    |    Local LLM (Ollama)     |
                    +---------------------------+
```

---

## 1. Frontend & State Management

*   **Entry Point (`run_app.py`)**: Boots the NiceGUI server, registers routes, sets up global logger configurations, and initializes runtime directories.
*   **State Management**: Utilizes NiceGUI's `app.storage.general` to cache loaded Pandas DataFrames, active files, and parsing configurations across page loads and refreshes.
*   **GUI Pages (`src/gui/` folder)**:
    *   `main_page.py`: Sidebar layout, tab routing, and master configuration loader.
    *   `load_gui.py`: Data ingestion interface.
    *   `calculate_gui.py` / `merge_gui.py` / `metadata_gui.py` / `plot_gui.py`: Individual feature views.

---

## 2. Analytical Tools & Business Logic (`src/core/` and `src/utils/` folders)

*   **`src/utils/tools.py`**: Shared utility tasks (loading configs, parsing raw datasets, cleaning and transforming dataframes).
*   **`src/core/auto_visualizer.py` & `src/core/forecast_engine.py`**: Plotly visualization and linear regression modeling.
*   **`src/core/report_generator.py` & `src/core/smart_recommendations.py`**: Generating dataset summaries and scanning columns for statistical quality recommendations.

---

## 3. Multi-Agent AI System (`src/agents/` folder)

Conversations and research queries are handled by specialized local agents orchestrated by `src/agents/agent_orchestrator.py`:

*   **Data Analyst Agent (`data_analyst.py`)**: Runs queries against the active dataset.
*   **Microorganism Router (`microorganism_router.py`)**: Classifies user queries to route them to biological search agents if needed.
*   **BacDive Explorer (`bacdive_explorer.py`)**: Fetches biological details from the BacDive database.
*   **Crossref Explorer (`crossref_explorer.py`) & Literature Reviewer (`literature_reviewer.py`)**: Fetches paper DOI references, publishers, and publication years via Crossref metadata search.
*   **Internet Explorer (`internet_explorer.py`)**: Integrates web queries using DuckDuckGo Search (`ddgs`).
*   **Master Summarizer (`master_summarizer.py`)**: Synthesizes responses from multiple backend agents.

# raw2ready

**raw2ready** is an enterprise AI-powered data cleaning, merging, and analytics platform designed specifically for bioreactor and bioprocess datasets. Built on top of Python and NiceGUI, it provides an interactive web-based user interface to transform raw, noisy, or disconnected bioreactor CSV/Excel export logs into clean, unified, and ready-to-analyze datasets.

---

## Key Features

*   **Interactive Data Loader**: Upload, preview, and validate CSV and Excel bioreactor logs.
*   **Intelligent Parser**: Parse complex, multi-header spreadsheets, normalize units of measure, and convert timestamp formats automatically.
*   **Robust Data Merger**: Merge multiple files using row-wise concatenation or column-wise join logic on timestamps or custom keys.
*   **Custom Expression Evaluator**: Safely calculate new metrics and parameters from existing columns using mathematical formulas.
*   **Visual Exploration & Forecasting**: Build time-series plots, correlation matrices, and perform linear-regression-based forecasting.
*   **Multi-Agent AI Copilot**: Talk to specialized local LLM agents (powered by Ollama/Llama3) to query datasets, extract experimental protocols, and search biological databases like BacDive and Crossref.
*   **Automated Quality Reporting**: Generate comprehensive data quality, outlier detection, and correlation reports.

---

## Getting Started

To get started, follow these steps:

1.  **[Installation](installation.md)**: Set up the Python Conda environment and install the required dependencies.
2.  **[Usage Guide](usage.md)**: Learn how to launch the server and step through the data parsing and merging workflows.
3.  **[Architecture](architecture.md)**: Explore the architectural design of the NiceGUI pages, helper modules, and multi-agent backend.

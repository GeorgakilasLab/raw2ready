# raw2ready

**raw2ready** is a locally deployed, open-source web app for the harmonization, processing, visualization, semantic annotation, and intelligent exploration of bioprocess data.

The framework automates the transformation of heterogeneous raw data files originating from bioprocess-related devices (e.g., bioreactors, gas analyzers) into standardized, machine-readable datasets through a modular and extensible architecture. It provides an interactive web-based graphical user interface that enables users to perform data curation, preprocessing, visualization, and AI-assisted exploration directly through the browser.

---

## Key Features

- Raw data parsing and harmonization.
- Time-series synchronization and dataset merging.
- Dynamic calculation of user-defined variables.
- Interactive visualization.
- Metadata annotation using [MIFE](https://doi.org/10.1093/gigascience/giag038).
- Agentic AI assisted exploration of data, experimental conditions, microbial information ([BacDive](https://bacdive.dsmz.de/)) and literature ([CrossRef](https://www.crossref.org/), [DuckDuckGo](https://duckduckgo.com/)).

---

## Getting Started

To get started, follow these steps:

1.  **[Installation](installation.md)**: Set up the Python Conda environment and install the required dependencies.
2.  **[Usage Guide](usage.md)**: Learn how to launch the server and step through the data parsing and merging workflows.
3.  **[Architecture](architecture.md)**: Explore the architectural design of the NiceGUI pages, helper modules, and multi-agent backend.

# Module Usage Guide

This guide walks you through the functionality of each module in the **raw2ready** application.

---

## 1. Dashboard Module

The **Dashboard** module acts as the home portal of the application. It displays high-level statistics of the loaded bioprocess datasets, including:
- Total number of loaded files
- Combined total row count
- Combined total column count
- The filename of the last loaded dataset
- A dynamic, sortable **Loaded Datasets Matrix** table displaying the file names, row/column dimensions, and their memory footprints in megabytes (MB).

### Interface & Overview
![Dashboard Overview Placeholder](assets/images/placeholder_dashboard_overview.png)
*Placeholder: High-level dashboard statistics cards and the loaded dataset matrix.*

---

## 2. Load Module

The **Load** module allows users to import, preview, clean, and validate raw experimental files. It parses raw sheets from Sartorius bioreactors, BioLectorXT devices, gas analyzers, and generic CSV/Excel data files. Users can inspect the raw data structure, verify datatypes, perform basic cleaning operations (e.g., removing duplicates, deleting columns, removing empty rows), and cache the cleaned data.

### Dataset Upload & Select
![Load Upload Placeholder](assets/images/placeholder_load_upload.png)
*Placeholder: The upload area and dataset selector menu.*

### Tabular Preview & Data Cleaning
![Load Preview Placeholder](assets/images/placeholder_load_preview.png)
*Placeholder: Tabular data grid showing the parsed contents and data cleaning action panel.*

---

## 3. Merge Module

The **Merge** module enables users to combine distinct datasets. It supports:
- **Row-wise (Concatenation)**: Append rows of datasets with similar schemas (e.g., repeating runs).
- **Column-wise (Join/Merge)**: Combine different parameter measurements (e.g., offline glucose measurements and online bioreactor logs) by matching timestamps or specific keys.

### Merge Type & Dataset Selection
![Merge Configuration Placeholder](assets/images/placeholder_merge_config.png)
*Placeholder: Selecting row-wise vs column-wise merging and choosing target datasets.*

### Keys Mapping & Alignment Output
![Merge Alignment Placeholder](assets/images/placeholder_merge_alignment.png)
*Placeholder: Map alignment columns, select merge key, and preview the resulting merged dataframe.*

---

## 4. Calculate Module

The **Calculate** module provides a safe math expression evaluator to compute new derived bioprocess parameters. Users can select any active dataset, specify python/numpy formulas (e.g. `log(Biomass_1) * Temp`), define column aliases, and execute calculations across specific filtered ranges of data. The resulting calculated column is added to the dataset and saved back to the session cache.

### Custom Formula Calculation
![Calculate Formula Placeholder](assets/images/placeholder_calculate_formula.png)
*Placeholder: Formula input field, variable alias mappings, and target column configuration panel.*

---

## 5. Plot Module

The **Plot** module offers visual exploration of time-series bioprocess logs and correlation analyses. It renders interactive charts to visualize data trends, correlation matrices to examine connections between parameters, and simple regression lines to forecast future data behavior.

### Time-Series Visualization & Correlation Matrix
![Plot Chart Placeholder](assets/images/placeholder_plot_chart.png)
*Placeholder: Line chart visualization of parameters vs elapsed time and correlation heatmaps.*

---

## 6. Metadata Module

The **Metadata** module builds fermentation experiment metadata schemas following the ISA/MIM structure ([MIFE](https://doi.org/10.1093/gigascience/giag038) standard). It enables tracking investigations, studies, observation units, samples, and assays. Users can define study designs, configure factors, add sample characteristics, register assays, and export/import standard JSON metadata protocols.

### Investigation Setup
![Metadata Investigation Placeholder](assets/images/placeholder_metadata_investigation.png)
*Placeholder: Form inputs for describing investigations.*

### Study Definition
![Metadata Study Placeholder](assets/images/placeholder_metadata_study.png)
*Placeholder: Form inputs for study metadata and protocols.*

### Observation Units Configuration
![Metadata Observation Placeholder](assets/images/placeholder_metadata_observation.png)
*Placeholder: Describing bioreactors, replicates, and experimental groups.*

### Samples Tracking
![Metadata Samples Placeholder](assets/images/placeholder_metadata_samples.png)
*Placeholder: Registering extracted samples, timestamps, and properties.*

### Assays Registration & MIFE Export
![Metadata Assays Placeholder](assets/images/placeholder_metadata_assays.png)
*Placeholder: Selecting measurement types, instruments, and exporting the final schema.*

---

## 7. LLM Module

The **LLM (Large Language Model) Dataset** module provides a local chatbot assistant. Users can ask questions about their datasets in natural language (e.g. *"What is the max pH value?"*), retrieve protocols, and enable multi-agent systems to search literature (CrossRef), biological repositories (BacDive), or the internet (DuckDuckGo).

### Agent Chatbot Interface
![LLM Chat Placeholder](assets/images/placeholder_llm_chat.png)
*Placeholder: Natural language chat interface with agent toggle panels.*

It currently supports the following agents: data analysis (loaded data), experimental conditions (loaded metadata based on [MIFE](https://doi.org/10.1093/gigascience/giag038) standard), literature search ([CrossRef](https://www.crossref.org/)), microbial information ([BacDive](https://bacdive.dsmz.de/)), and general web search ([DuckDuckGo](https://duckduckgo.com/)).

---

## 8. Help Module

The **Help** module acts as an interactive user manual. It lists keyboard shortcuts, explains layout elements, and offers quick guides to solve common parsing or merging issues.

### Help & Documentation Portal
![Help Guide Placeholder](assets/images/placeholder_help_guide.png)
*Placeholder: FAQ guide, documentation indexes, and support references.*

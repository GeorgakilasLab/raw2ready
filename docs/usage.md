# Usage Guide

This guide walks you through the core workflows of the **raw2ready** NiceGUI web application.

---

## 1. Loading Datasets

Navigate to the **Load** tab:
*   **Select / Upload Files**: Choose from pre-loaded examples or upload your raw Excel/CSV bioreactor files.
*   **Preview**: View the dataset structure, sheet names, and raw contents in the interactive table preview.

---

## 2. Parsing and Normalizing

Navigate to the **Parse** tab:
*   Identify column headers and configure row parsing offsets.
*   Define units of measure and perform unit conversion or normalization (e.g. converting temperatures to Kelvin/Celsius, scaling biomass, etc.).
*   Verify the parsed output in the preview before saving.

---

## 3. Merging Datasets

Navigate to the **Merge** tab:
*   **Row-wise (Concatenation)**: Combine datasets that share similar columns but cover different time intervals.
*   **Column-wise (Join/Merge)**: Combine distinct variables (e.g., pH readings and feed rate logs) matching them on timestamps or a shared index.
*   Select the merge keys, review the alignment, and export the resulting unified dataset.

---

## 4. Custom Calculations

Navigate to the **Calculate** tab:
*   Select the active dataset.
*   Input a custom python/numpy mathematical expression (e.g., `log(Biomass_1) * Temp`).
*   Name your target column and select column aliases.
*   Click **Calculate** to apply the formula across the selected filtered rows and view/export the updated dataset.

---

## 5. Visualizing & Forecasting

Navigate to the **Plot** tab:
*   Create dynamic line charts of variables plotted against elapsed run time.
*   Check correlations between variables using the interactive visualizer.
*   Run linear-regression-based projections to forecast future values.

---

## 6. AI Agent Copilot

Navigate to the **LLM Chat** tab:
*   **Data Queries**: Ask natural language questions about your active dataset (e.g. *"What was the average temperature during the first 3 hours?"*).
*   **Agent Toggles**: Enable specific helper agents:
    *   **Literature Reviewer**: Searches literature sources (Crossref) for relevant bioprocess studies.
    *   **BacDive Explorer**: Retrieves taxonomic and physiological metadata for specific microorganisms.
    *   **Internet Explorer**: Fetches web search results to supplement queries.

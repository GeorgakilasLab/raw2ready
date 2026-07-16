# Installation Guide

Follow these steps to set up your development environment and launch the **raw2ready** application.

---

## 1. Prerequisites

Ensure you have the following installed on your system:
*   [Miniconda](https://docs.anaconda.com/miniconda/) or Anaconda.
*   [Ollama](https://ollama.com/) (optional, required for local AI capabilities).

---

## 2. Set Up the Conda Environment

Initialize and configure the environment using the provided `conda.yml`:

```bash
# Clone the repository
git clone https://github.com/GeorgakilasLab/raw2ready.git
cd raw2ready

# Create the conda environment
conda env create -f conda.yml

# Activate the environment
conda activate raw2ready
```

If you modify or update dependencies, you can manually reinstall them:
```bash
pip install -r requirements.txt
```

---

## 3. Set Up Ollama (For AI Agents)

The web application leverages local LLM instances via Ollama:

1.  Start the Ollama server:
    ```bash
    ollama serve
    ```
2.  Pull the default model (Llama 3):
    ```bash
    ollama pull llama3
    ```

---

## 4. Run the Web Application

With the environment activated and Ollama running, launch the raw2ready web server:

```bash
python run_app.py
```

Open your browser and navigate to `http://localhost:8081`.

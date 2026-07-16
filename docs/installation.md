# Installation Guide

Follow these steps to set up your environment and launch the **raw2ready** application.

## Manual Deployment (Conda)

You can deploy raw2ready manually using Conda (requires installation of miniconda - see [installation](docs/installation.md)). This creates an isolated virtual environment and installs all dependencies specified in the `conda.yml` configuration.

### 1. Clone the Repository

Download and extract the repository manually, or clone it using Git.

```bash
git clone https://github.com/GeorgakilasLab/raw2ready.git
cd raw2ready
```

### 2. Create the Conda Environment

Run the following command in the root of the project to create the `raw2ready` Conda environment:

```bash
conda env create -f conda.yml
```

### 3. Activate the Environment

Once the environment has been successfully created, activate it using:

```bash
conda activate raw2ready
```

### 4. Launch the Web Application

To start the raw2ready web interface, run the entry script:

```bash
python run_app.py
```

Then, open your browser and navigate to:

```text
http://localhost:8081
```

### 5. Optional: Install Ollama

raw2ready supports Agentic AI assisted exploration of data, experimental conditions, microbial information and literature using local Large Language Models via *Ollama*.

To install Ollama, run the following command from a directory in which you want to download it:

```bash
cd ~
mkdir ollama
cd ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
```

## Containerized Deployment (Docker)

Coming soon...

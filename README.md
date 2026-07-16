# raw2ready

## Table of Contents

1. [Introduction](#1-introduction)
2. [Deployment](#2-deployment)
3. [Containerized Deployment (Docker)](#3-containerized-deployment-docker)
4. [Troubleshooting](#4-troubleshooting)
5. [Support](#5-support)

# 1. Introduction

*raw2ready* is a locally deployed, open-source web app for the harmonization, processing, visualization, semantic annotation, and intelligent exploration of bioprocess data.

The framework automates the transformation of heterogeneous raw data files originating from bioprocess-related devices (e.g., bioreactors, gas analyzers) into standardized, machine-readable datasets through a modular and extensible architecture. It provides an interactive web-based graphical user interface that enables users to perform data curation, preprocessing, visualization, and AI-assisted exploration directly through the browser.

The framework supports:

- Raw data parsing and harmonization
- Time-series synchronization and dataset merging
- Dynamic calculation of user-defined variables
- Interactive visualization
- Metadata annotation using [MIFE](https://doi.org/10.1093/gigascience/giag038)
- Agentic AI assisted exploration of data, experimental conditions, microbial information ([BacDive](https://bacdive.dsmz.de/)) and literature ([CrossRef](https://www.crossref.org/), [DuckDuckGo](https://duckduckgo.com/)).

## Currently Supported Data Formats

- Sartorius formatted MS Excel files
- BioLectorXT formatted MS Excel files
- Gas analyzer formatted text files
- Generic text (csv, tsv etc) or MS Excel files with tabular data

# 2. Deployment

The framework has been tested on Linux environments (Ubuntu, Mint) and Windows via WSL.

## Development Deployment (Conda)

For development purposes, raw2ready can be deployed using Conda. This creates an isolated virtual environment and installs all dependencies specified in the `conda.yml` configuration.

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

# 3. Containerized Deployment (Docker)

Coming soon...

# 4. Troubleshooting

## Common Issues

### The files of my equipment are not recognized

Verify that the equipment is currently supported.

Contact us for support in adding support for your equipment.

### Ollama model unavailable

Verify Ollama installation:

```bash
ollama list
```

If the required models are not available, download them:

```bash
ollama pull [MODEL_NAME] # e.g. llama3
```

# 5. Support

## Getting Help

GitHub Issues:

https://github.com/GeorgakilasLab/raw2ready/-/issues

Email Support:

ggeorgakilas@athenarc.gr
antoniades000michael@gmail.com

## Citing raw2ready

If you use raw2ready in your research, please cite:

`Coming soon...`

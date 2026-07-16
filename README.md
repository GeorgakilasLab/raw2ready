# raw2ready

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Directory Structure](#3-directory-structure)
4. [Command Line Interface](#4-command-line-interface)
5. [Web-Based Interface](#5-web-based-interface)
6. [Data Types](#6-data-types)
7. [Configuration Files](#7-configuration-files)
8. [Usage Examples](#8-usage-examples)
9. [Troubleshooting](#9-troubleshooting)
10. [Support](#10-support)

---

# 1. Introduction

*raw2ready* is a Python framework for the harmonization, processing, visualization, semantic annotation, and intelligent exploration of fermentation data produced by industrial biotechnology equipment.

The framework automates the transformation of heterogeneous raw data files originating from fermentation devices (e.g., bioreactors, gas analyzers, spectroscopic instruments, and sensors) into standardized, machine-readable datasets through a modular and extensible architecture.

In addition to its command-line functionality, raw2ready provides an interactive web-based graphical user interface implemented using *NiceGUI*, enabling users to perform data curation, preprocessing, visualization, and AI-assisted exploration workflows directly through the browser.

The framework supports the complete experimental data lifecycle, including:

- Raw data parsing and harmonization
- Time-series synchronization and dataset merging
- Dynamic calculation of derived variables
- Statistical analysis and interactive visualization
- Metadata annotation using MIFE
- AI-assisted exploration using Large Language Models (LLMs)

Furthermore, raw2ready integrates a multi-agent framework capable of combining information from experimental datasets, metadata, microbial repositories, scientific literature, and external web resources in order to support evidence-based reasoning over fermentation experiments.

---

## Key Features

- Modular architecture
- Fully local deployment
- Interactive NiceGUI web interface
- Standardized data organization
- Multi-source time-series integration
- Dynamic formula execution
- Statistical analysis and visualization
- Metadata annotation using MIFE
- Multi-agent LLM framework
- BacDive microbial knowledge integration
- Crossref literature retrieval
- Internet-assisted knowledge exploration
- Runtime memory management
- Comprehensive logging and traceability

---

## Currently Supported Equipment

- Sartorius bioreactors
- BioLectorXT systems
- Gas analyzers
- Generic CSV datasets
- Microsoft Excel datasets

---

# 2. Installation

## Prerequisites

The framework has been tested on:

- Python *3.10*
- Python *3.11*

Requirements:

- Python 3.10 or higher
- Linux, macOS, or Windows
- WSL recommended for Windows users
- Optional: Ollama for local LLM execution

---

## Dependencies

The complete list of dependencies can be found in:

text
requirements.txt

Main dependencies include:

text
nicegui
pandas
numpy
scipy
scikit-learn
matplotlib
plotly
pyyaml
requests
beautifulsoup4
bacdive
crossrefapi
nltk
spacy
transformers
sentence-transformers
torch
ollama

---

## Setup

Download and extract the repository manually, or clone it using Git.

### Clone the repository

git clone https://gitlab.com/bioindustry4.0/raw2ready.git
cd raw2ready

or

git clone -b features/mikeantonbranch \
https://gitlab.com/arc3972240/bioindustry/raw2ready.git

cd raw2ready

---

### Create a virtual environment

python3 -m venv raw2ready
source raw2ready/bin/activate

---

### Install required packages

pip3 install --upgrade pip
pip3 install -r requirements.txt

---

### Install SpaCy English model

python3 -m spacy download en_core_web_sm

---

### Download required NLTK resources

Start Python:

python3

Execute:

import nltk

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('averaged_perceptron_tagger')
nltk.download('vader_lexicon')

exit()

---

## Development Deployment (Conda)

For development purposes, raw2ready can be deployed using Conda. This creates an isolated virtual environment and installs all dependencies specified in the `conda.yml` configuration.

### 1. Create the Conda Environment

Run the following command in the root of the project to create the `raw2ready` Conda environment:

```bash
conda env create -f conda.yml
```

### 2. Activate the Environment

Once the environment has been successfully created, activate it using:

```bash
conda activate raw2ready
```

### 3. Download Required Language Models & Resources

Download the required SpaCy model and NLTK resource packages within the activated Conda environment:

```bash
python3 -m spacy download en_core_web_sm
python3 -c "import nltk; nltk.download(['punkt', 'stopwords', 'wordnet', 'omw-1.4', 'averaged_perceptron_tagger', 'vader_lexicon', 'punkt_tab'])"
```

### 4. Launch the Web Application

To start the NiceGUI web interface, run the entry script:

```bash
python run_app.py
```

Then, open your browser and navigate to:

```text
http://localhost:8080
```

---

## Optional: Install Ollama

raw2ready supports fully local Large Language Models through *Ollama*.

Install Ollama:

curl -fsSL https://ollama.com/install.sh | sh

Download the recommended model:

ollama pull llama3

---

## Verify Installation

### Command-line interface

python3 raw2ready.py --help

### NiceGUI application

python3 run_app.py

Open your browser and navigate to:

text
http://localhost:8080

---

# 3. Directory Structure

## Key Components

- raw2ready.py : Main command-line executable
- run_app.py : NiceGUI application entry point
- modules/ : Core data processing modules
- lib/ : Utility and helper functions
- gui/ : NiceGUI user interface components
- agents/ : LLM and multi-agent implementations
- tools/ : Shared services and utilities
- examples/ : Example configuration files
- logs/ : Agent execution logs

## Complete Structure

text
raw2ready/
├── raw2ready.py
├── run_app.py
├── modules/
├── lib/
├── gui/
├── agents/
├── tools/
├── examples/
├── assets/
├── logs/
├── config/
├── requirements.txt
└── README.md

---

# 4. Command Line Interface

## Global Syntax

python raw2ready.py [module] [options]

## Available Modules

### Parse Module

Parses raw equipment files and transforms them into standardized datasets.

python raw2ready.py parse [options]

Options:

text
-cf, --config_file FILE

---

### Merge Module

Synchronizes and merges heterogeneous time-series datasets.

python raw2ready.py merge [options]

Options:

text
-cf, --config_file FILE

---

### Calculate Module

Calculates derived variables based on user-defined formulas.

python raw2ready.py calculate [options]

Options:

text
-cf, --config_file FILE

---

# 5. Web-Based Interface

The NiceGUI interface provides browser-based access to all framework functionality.

Available modules include:

- Dashboard
- Load
- Merge
- Calculate
- Plot
- Metadata Annotation
- BacDive Explorer
- Crossref Explorer
- Internet Explorer
- Multi-Agent Copilot
- Statistical Analysis

Launch the interface:

python3 run_app.py

Open:

text
http://localhost:8080

---

# 6. Data Types

raw2ready currently supports:

- CSV files
- Excel files (.xlsx)
- Sartorius sensor exports
- Sartorius gas analyzer exports
- BioLectorXT exports
- Raman measurements
- Time-series datasets
- MIFE metadata files

---

# 7. Configuration Files

All command-line modules operate using JSON configuration files.

Example:

{
    "output directory": "/path/to/output",
    "experiment name": "Experiment_01",
    "equipment": "Sartorius"
}

Configuration files define:

- input files
- output locations
- merge parameters
- calculation parameters
- equipment-specific settings

Example configuration files are available under:

text
examples/

---

# 8. Usage Examples

## Parse raw files

python raw2ready.py parse \
-cf examples/config_file_template.Sartorius.json

## Merge datasets

python raw2ready.py merge \
-cf examples/config_file_template.Sartorius.json

## Calculate new variables

python raw2ready.py calculate \
-cf examples/config_file_template.Sartorius.json

## Launch NiceGUI

python run_app.py

---

# 9. Troubleshooting

## Common Issues

### Equipment not recognized

Verify that the equipment is currently supported.

### Missing Python package

Install missing dependencies:

pip3 install -r requirements.txt

### Ollama model unavailable

Verify Ollama installation:

ollama list

Download required models:

ollama pull llama3

### NiceGUI not accessible

Verify that port *8080* is available.

---

# 10. Support

## Getting Help

GitLab Issues:

https://gitlab.com/arc3972240/bioindustry/raw2ready/-/issues

Email Support:

ggeorgakilas@athenarc.gr
antoniades000michael@gmail.com

---

## Citing raw2ready

If you use raw2ready in your research, please cite:

text
=======
# raw2ready

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Directory Structure](#3-directory-structure)
4. [Command Line Interface](#4-command-line-interface)
5. [Web-Based Interface](#5-web-based-interface)
6. [Data Types](#6-data-types)
7. [Configuration Files](#7-configuration-files)
8. [Usage Examples](#8-usage-examples)
9. [Troubleshooting](#9-troubleshooting)
10. [Support](#10-support)

---

# 1. Introduction

*raw2ready* is a Python framework for the harmonization, processing, visualization, semantic annotation, and intelligent exploration of fermentation data produced by industrial biotechnology equipment.

The framework automates the transformation of heterogeneous raw data files originating from fermentation devices (e.g., bioreactors, gas analyzers, spectroscopic instruments, and sensors) into standardized, machine-readable datasets through a modular and extensible architecture.

In addition to its command-line functionality, raw2ready provides an interactive web-based graphical user interface implemented using *NiceGUI*, enabling users to perform data curation, preprocessing, visualization, and AI-assisted exploration workflows directly through the browser.

The framework supports the complete experimental data lifecycle, including:

- Raw data parsing and harmonization
- Time-series synchronization and dataset merging
- Dynamic calculation of derived variables
- Statistical analysis and interactive visualization
- Metadata annotation using MIFE
- AI-assisted exploration using Large Language Models (LLMs)

Furthermore, raw2ready integrates a multi-agent framework capable of combining information from experimental datasets, metadata, microbial repositories, scientific literature, and external web resources in order to support evidence-based reasoning over fermentation experiments.

---

## Key Features

- Modular architecture
- Fully local deployment
- Interactive NiceGUI web interface
- Standardized data organization
- Multi-source time-series integration
- Dynamic formula execution
- Statistical analysis and visualization
- Metadata annotation using MIFE
- Multi-agent LLM framework
- BacDive microbial knowledge integration
- Crossref literature retrieval
- Internet-assisted knowledge exploration
- Runtime memory management
- Comprehensive logging and traceability

---

## Currently Supported Equipment

- Sartorius bioreactors
- BioLectorXT systems
- Gas analyzers
- Generic CSV datasets
- Microsoft Excel datasets

---

# 2. Installation

## Prerequisites

The framework has been tested on:

- Python *3.10*
- Python *3.11*

Requirements:

- Python 3.10 or higher
- Linux, macOS, or Windows
- WSL recommended for Windows users
- Optional: Ollama for local LLM execution

---

## Dependencies

The complete list of dependencies can be found in:

text
requirements.txt

Main dependencies include:

text
nicegui
pandas
numpy
scipy
scikit-learn
matplotlib
plotly
pyyaml
requests
beautifulsoup4
bacdive
crossrefapi
nltk
spacy
transformers
sentence-transformers
torch
ollama

---

## Setup

Download and extract the repository manually, or clone it using Git.

### Clone the repository

git clone https://gitlab.com/bioindustry4.0/raw2ready.git
cd raw2ready

or

git clone -b features/mikeantonbranch \
https://gitlab.com/arc3972240/bioindustry/raw2ready.git

cd raw2ready

---

### Create a virtual environment

python3 -m venv raw2ready
source raw2ready/bin/activate

---

### Install required packages

pip3 install --upgrade pip
pip3 install -r requirements.txt

---

### Install SpaCy English model

python3 -m spacy download en_core_web_sm

---

### Download required NLTK resources

Start Python:

python3

Execute:

import nltk

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('averaged_perceptron_tagger')
nltk.download('vader_lexicon')

exit()

---

## Optional: Install Ollama

raw2ready supports fully local Large Language Models through *Ollama*.

Install Ollama:

curl -fsSL https://ollama.com/install.sh | sh

Download the recommended model:

ollama pull llama3

---

## Verify Installation

### Command-line interface

python3 raw2ready.py --help

### NiceGUI application

python3 run_app.py

Open your browser and navigate to:

text
http://localhost:8080

---

# 3. Directory Structure

## Key Components

- raw2ready.py : Main command-line executable
- run_app.py : NiceGUI application entry point
- modules/ : Core data processing modules
- lib/ : Utility and helper functions
- gui/ : NiceGUI user interface components
- agents/ : LLM and multi-agent implementations
- tools/ : Shared services and utilities
- examples/ : Example configuration files
- logs/ : Agent execution logs

## Complete Structure

text
raw2ready/
├── raw2ready.py
├── run_app.py
├── modules/
├── lib/
├── gui/
├── agents/
├── tools/
├── examples/
├── assets/
├── logs/
├── config/
├── requirements.txt
└── README.md

---

# 4. Command Line Interface

## Global Syntax

python raw2ready.py [module] [options]

## Available Modules

### Parse Module

Parses raw equipment files and transforms them into standardized datasets.

python raw2ready.py parse [options]

Options:

text
-cf, --config_file FILE

---

### Merge Module

Synchronizes and merges heterogeneous time-series datasets.

python raw2ready.py merge [options]

Options:

text
-cf, --config_file FILE

---

### Calculate Module

Calculates derived variables based on user-defined formulas.

python raw2ready.py calculate [options]

Options:

text
-cf, --config_file FILE

---

# 5. Web-Based Interface

The NiceGUI interface provides browser-based access to all framework functionality.

Available modules include:

- Dashboard
- Load
- Merge
- Calculate
- Plot
- Metadata Annotation
- BacDive Explorer
- Crossref Explorer
- Internet Explorer
- Multi-Agent Copilot
- Statistical Analysis

Launch the interface:

python3 run_app.py

Open:

text
http://localhost:8080

---

# 6. Data Types

raw2ready currently supports:

- CSV files
- Excel files (.xlsx)
- Sartorius sensor exports
- Sartorius gas analyzer exports
- BioLectorXT exports
- Raman measurements
- Time-series datasets
- MIFE metadata files

---

# 7. Configuration Files

All command-line modules operate using JSON configuration files.

Example:

{
    "output directory": "/path/to/output",
    "experiment name": "Experiment_01",
    "equipment": "Sartorius"
}

Configuration files define:

- input files
- output locations
- merge parameters
- calculation parameters
- equipment-specific settings

Example configuration files are available under:

text
examples/

---

# 8. Usage Examples

## Parse raw files

python raw2ready.py parse \
-cf examples/config_file_template.Sartorius.json

## Merge datasets

python raw2ready.py merge \
-cf examples/config_file_template.Sartorius.json

## Calculate new variables

python raw2ready.py calculate \
-cf examples/config_file_template.Sartorius.json

## Launch NiceGUI

python run_app.py

---

# 9. Troubleshooting

## Common Issues

### Equipment not recognized

Verify that the equipment is currently supported.

### Missing Python package

Install missing dependencies:

pip3 install -r requirements.txt

### Ollama model unavailable

Verify Ollama installation:

ollama list

Download required models:

ollama pull llama3

### NiceGUI not accessible

Verify that port *8080* is available.

---

# 10. Support

## Getting Help

GitLab Issues:

https://gitlab.com/arc3972240/bioindustry/raw2ready/-/issues

Email Support:

ggeorgakilas@athenarc.gr
antoniades000michael@gmail.com

---

## Citing raw2ready

If you use raw2ready in your research, please cite:

text
>>>>>>> 2b89b4a (Changes for version 1)
Citation information coming soon.
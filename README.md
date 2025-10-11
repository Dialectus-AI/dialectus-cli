# Dialectus CLI

Command-line interface for the Dialectus AI debate system.

## Overview

The Dialectus CLI provides a rich, interactive command-line interface for managing AI debates. Built with Rich for beautiful terminal output and comprehensive debate management features.

<img src="https://github.com/user-attachments/assets/fc031506-feef-4cb1-9f30-e1eb513b06a6" width=50% height=50% alt="CLI">

## Features

- **Interactive Debate Creation** - Rich prompts for setting up debates
- **Real-time Progress Tracking** - Live progress bars and status updates  
- **Comprehensive Output** - Detailed debate transcripts and judge results
- **Model Management** - Easy configuration of AI models and providers
- **Format Support** - Multiple debate formats (Oxford, Parliamentary, Socratic)
- **Export Options** - Save transcripts in various formats

## Installation

### From PyPI (coming soon)
```bash
pip install dialectus-cli
```

### From Source
```bash
git clone https://github.com/psarno/dialectus-cli.git
cd dialectus-cli
pip install -r requirements.txt
```

## Quick Start

1. Run a debate with default settings:
```bash
python cli.py
```

2. Configure AI models:
```bash
python cli.py --configure
```

3. Use specific debate format:
```bash
python cli.py --format oxford --topic "Should AI be regulated?"
```

## Usage

```bash
python cli.py [OPTIONS]

Options:
  --topic TEXT        Debate topic
  --format TEXT       Debate format (oxford, parliamentary, socratic)
  --rounds INT        Number of debate rounds
  --configure        Configure AI models and settings
  --help             Show help and exit
```

## Configuration

The CLI uses a `debate_config.json` file for settings. You can generate this interactively:

```bash
python cli.py --configure
```

## Development

This repository was extracted from the original AI-Debate monolith to create a focused, installable CLI tool.

## Dependencies

- `rich` - Beautiful terminal output and interactive prompts
- `click` - Command-line interface framework
- `pydantic` - Data validation and settings management
- `httpx` - HTTP client for API communication

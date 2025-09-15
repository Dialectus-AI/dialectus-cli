# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Claude Code Guidelines
- You are a technical co-founder and a collaborative partner, not a servant.
- Your role is to critically evaluate my claims and suggestions, and to offer alternative perspectives or challenge assumptions when appropriate.
- Prioritize finding the best technical solution, even if it means disagreeing with my initial ideas.
Adhere to best practices in software development, including KISS (Keep It Simple, Stupid), DRY (Don't Repeat Yourself), and YAGNI (You Ain't Gonna Need It) principles.
- Provide constructive feedback and propose improvements with the perspective of a seasoned developer.
- Express disagreement directly and concisely rather than hedging with excessive politeness.

## Overview

Dialectus CLI is a command-line interface for AI debate orchestration. It's a Python application that facilitates structured debates between AI models using various providers (Ollama, OpenRouter) with configurable judging systems.

## Architecture

### Core Components

- **cli.py**: Main CLI entry point using Click framework with Rich for terminal UI
- **config/settings.py**: Pydantic-based configuration system with validation
- **models/**: Model management system supporting multiple providers
- **Configuration**: JSON-based config system with example template

### Key Design Patterns

- **Provider abstraction**: Support for multiple AI model providers (Ollama, OpenRouter)
- **Debate engine**: Modular system for different debate formats (Oxford, Parliamentary, Socratic)
- **Judge system**: AI-based evaluation with configurable criteria
- **Transcript management**: Automatic saving and retrieval of debate records

### Configuration System

The application uses `debate_config.json` for configuration:
- Debate settings (topic, format, time limits)
- Model configurations with provider-specific settings
- Judging criteria and methods
- System settings (transcript storage, logging)

## Development Commands

### Installation and Setup
```bash
# Install from source
pip install -r requirements.txt

# Run the CLI directly
python cli.py

# Install as package (development)
pip install -e .
```

### Running the Application
```bash
# Start a debate with default config
python cli.py debate

# Start with specific topic and format
python cli.py debate --topic "Should AI be regulated?" --format oxford

# Configure models and settings
python cli.py --configure

# List available Ollama models
python cli.py list-models

# View saved transcripts
python cli.py transcripts
```

### Configuration
```bash
# Generate default config from example
cp debate_config.example.json debate_config.json

# Use custom config file
python cli.py --config custom_config.json debate
```

## Project Structure

- Root CLI application with direct imports from local modules
- No test framework currently configured
- Uses pip-compile for dependency management (requirements.in → requirements.txt)
- Entry point defined in setup.py for console script installation

## Dependencies

Core dependencies managed in requirements.in:
- **rich**: Terminal UI and formatting
- **click**: CLI framework
- **pydantic**: Configuration validation
- **openai**: AI model interaction
- **pyyaml**: Configuration file handling
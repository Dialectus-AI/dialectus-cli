# Dialectus CLI

Command-line interface for the Dialectus AI debate system.

## Overview

The Dialectus CLI is a modern, API-first command-line client for managing AI debates. It communicates with the Dialectus Engine backend via REST API and WebSocket connections, providing a rich terminal interface for debate orchestration with full ensemble judging support.

## Features

- **🤖 Ensemble Judging** - Support for single or multiple AI judges with automatic method detection
- **🌐 API-First Architecture** - Uses same backend endpoints as the web interface
- **📊 Real-time Streaming** - Live debate updates via WebSocket connections
- **🎨 Rich Terminal UI** - Beautiful output with progress bars and formatted displays
- **⚙️ Flexible Configuration** - JSON-based configuration with strict validation
- **📋 Multiple Formats** - Support for Oxford, Parliamentary, and Socratic debate formats
- **💾 Transcript Management** - Automatic saving and viewing of debate transcripts
- **🔍 Model Discovery** - List available AI models from the backend

## Installation

### Prerequisites

Make sure the Dialectus Engine backend is running on `http://localhost:8000` (default).

### From Source
```bash
git clone https://github.com/psarno/dialectus-cli.git
cd dialectus-cli
pip install -r requirements.txt
```

## Quick Start

1. **Copy example configuration:**
```bash
cp debate_config.example.json debate_config.json
```

2. **List available models:**
```bash
python cli.py list-models
```

3. **Run a debate:**
```bash
python cli.py debate --topic "Should AI be regulated?"
```

4. **View saved transcripts:**
```bash
python cli.py transcripts
```

## Usage

### Commands

```bash
python cli.py [OPTIONS] COMMAND [ARGS]...

Commands:
  debate       Start a debate between AI models
  list-models  List available models from the API
  transcripts  List saved debate transcripts

Options:
  -c, --config PATH               Configuration file path (default: debate_config.json)
  --log-level [DEBUG|INFO|WARNING|ERROR]
  --help                          Show this message and exit
```

### Debate Options

```bash
python cli.py debate [OPTIONS]

Options:
  -t, --topic TEXT                Debate topic
  -f, --format [parliamentary|oxford|socratic]  Debate format
  -r, --rounds INTEGER            Number of rounds
  -i, --interactive               Interactive mode with pauses
```

## Configuration

### Basic Configuration

Create a `debate_config.json` file:

```json
{
  "debate": {
    "topic": "Should artificial intelligence be regulated?",
    "format": "oxford",
    "time_per_turn": 120,
    "word_limit": 200
  },
  "models": {
    "model_a": {
      "name": "qwen2.5:7b",
      "provider": "ollama",
      "personality": "analytical",
      "max_tokens": 300,
      "temperature": 0.7
    },
    "model_b": {
      "name": "openai/gpt-4o-mini",
      "provider": "openrouter",
      "personality": "passionate",
      "max_tokens": 300,
      "temperature": 0.8
    }
  },
  "judging": {
    "judge_models": ["openthinker:7b"],
    "judge_provider": "ollama",
    "criteria": ["logic", "evidence", "persuasiveness"]
  },
  "system": {
    "api_base_url": "http://localhost:8000",
    "save_transcripts": true,
    "transcript_dir": "transcripts",
    "log_level": "INFO"
  }
}
```

### Judging Configuration

The CLI automatically determines judging method based on the `judge_models` array:

- **No Judging:** `"judge_models": []`
- **Single Judge:** `"judge_models": ["openthinker:7b"]`
- **Ensemble Judging:** `"judge_models": ["judge1", "judge2", "judge3"]`

#### Single Judge Example
```json
{
  "judging": {
    "judge_models": ["openthinker:7b"],
    "judge_provider": "ollama",
    "criteria": ["logic", "evidence", "persuasiveness"]
  }
}
```

#### Ensemble Judge Example
```json
{
  "judging": {
    "judge_models": ["openthinker:7b", "llama3.2:3b", "qwen2.5:3b"],
    "judge_provider": "ollama",
    "criteria": ["logic", "evidence", "persuasiveness"]
  }
}
```

See `debate_config.example.json` and `debate_config.ensemble.example.json` for complete examples.

### Model Providers

The CLI supports multiple AI model providers:

- **Ollama** - Local models (`provider: "ollama"`)
- **OpenRouter** - Cloud models (`provider: "openrouter"`)
- **OpenAI** - Direct OpenAI API (`provider: "openai"`)

Model names should match the backend's available models (check with `python cli.py list-models`).

## Architecture

The CLI is designed as a thin API client that communicates with the Dialectus Engine:

- **REST API** - Debate creation, model listing, transcript retrieval
- **WebSocket** - Real-time debate streaming and updates
- **JSON Configuration** - Strict validation with Pydantic models
- **Rich Display** - Terminal UI with progress indicators and formatted output

This ensures the CLI stays in sync with the web frontend and benefits from all backend improvements.

## Example Output

```
Debate Setup
┌─────────────────────────────────────────────┐
│ Topic: Should AI be regulated?              │
│ Format: Oxford                              │
│ Time per turn: 120s                         │
│ Word limit: 200                             │
│                                             │
│ Participants:                               │
│ - model_a: qwen2.5:7b (analytical)         │
│ - model_b: gpt-4o-mini (passionate)        │
│                                             │
│ Judging: Ensemble: 3 judges                │
└─────────────────────────────────────────────┘

🏆 WINNER: qwen2.5:7b
Margin: 7.2/10.0
Ensemble Decision (3 judges)
```

## Development

This CLI was refactored from the original monolithic structure to be a standalone API client. It focuses on:

- **Zero code duplication** with the backend
- **API-first design** for consistency with web frontend
- **Strict typing** with no backwards compatibility
- **Modern Python practices** with async/await and Pydantic

## Dependencies

- `httpx` - Modern HTTP client for API communication
- `websockets` - WebSocket client for real-time streaming
- `pydantic` - Data validation and configuration management
- `rich` - Beautiful terminal output and formatting
- `click` - Command-line interface framework
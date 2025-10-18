<img src="https://raw.githubusercontent.com/dialectus-ai/dialectus-engine/main/assets/logo.png" alt="Dialectus CLI" width="350">

# Dialectus CLI

Command-line interface for the Dialectus AI debate system. Run AI debates locally with Ollama or cloud models via OpenRouter.

<img src="https://github.com/user-attachments/assets/fba4d1f8-9561-4971-a2fa-ec24f01865a8" alt="CLI" width=700>

## Installation

```bash
pip install dialectus-cli
```

### From Source

```bash
git clone https://github.com/Dialectus-AI/dialectus-cli
cd dialectus-cli
uv sync --all-extras
```

## Requirements

- **Python 3.13+**
- **uv** (recommended): Fast Python package manager - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Ollama** (if using local models): Running at `http://localhost:11434`
- **OpenRouter API key** (if using cloud models): Set via environment variable

### Environment Variables

```bash
# Linux/macOS
export OPENROUTER_API_KEY="your-key-here"

# Windows PowerShell
$env:OPENROUTER_API_KEY="your-key-here"

# Windows CMD
set OPENROUTER_API_KEY=your-key-here
```

## Quick Start

After installation, the `dialectus` command is available:

```bash
# Copy example config
cp debate_config.example.json debate_config.json

# Edit with your preferred models and API keys
nano debate_config.json  # or your favorite editor

# Run a debate
dialectus debate
```

## Configuration

Edit `debate_config.json` to configure:
- **Models**: Debate participants (Ollama or OpenRouter)
- **Judging**: AI judge models and evaluation criteria
- **System**: Ollama/OpenRouter settings

## Commands

All commands work identically across platforms:

### Start a Debate
```bash
uv run dialectus debate
uv run dialectus debate --topic "Should AI be regulated?"
uv run dialectus debate --format oxford
uv run dialectus debate --interactive
```

### List Available Models
```bash
uv run dialectus list-models
```

### View Saved Transcripts
```bash
uv run dialectus transcripts
uv run dialectus transcripts --limit 50
```

## Database

Transcripts are saved to SQLite database at `~/.dialectus/debates.db`

## Architecture

```
CLI → DebateRunner → DebateEngine → Rich Console
           ↓
    SQLite Database
```

- **No API layer** - Imports engine directly
- **Local-first** - Runs completely offline with Ollama
- **SQLite storage** - Simple, portable database

## Development

### Contributing

```bash
# Clone and install in editable mode
git clone https://github.com/Dialectus-AI/dialectus-cli
cd dialectus-cli
uv sync --all-extras

# Type checking
uv run pyright dialectus/

# Build package
uv run python -m build
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_database.py

# Run with coverage
uv run pytest --cov=dialectus
```

All tests should pass with zero warnings.

### Dev Tooling

CI runs Ruff for linting/formatting, Pyright for type checking, and Pytest for the test suite. Dependencies are managed via `pyproject.toml` and automatically synced with uv:

```bash
# Install/update dependencies
uv sync --all-extras

# Add new dependency
uv add package-name

# Add new dev dependency
uv add --dev package-name
```

## License

MIT (open source)

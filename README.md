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
pip install -e ".[dev]"
```

## Requirements

- **Python 3.13+**
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
dialectus debate
dialectus debate --topic "Should AI be regulated?"
dialectus debate --format oxford
dialectus debate --interactive
```

### List Available Models
```bash
dialectus list-models
```

### View Saved Transcripts
```bash
dialectus transcripts
dialectus transcripts --limit 50
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
pip install -e ".[dev]"

# Type checking
pyright dialectus/

# Build package
python -m build
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_database.py

# Run with coverage
pytest --cov=dialectus
```

All tests should pass with zero warnings.

### Dev Tooling

CI runs Ruff for linting/formatting, Pyright for type checking, and Pytest for the test suite. Keep those tools (and the supporting build utilities) in sync by compiling `dev-requirements.in`:

```bash
pip install pip-tools
pip-compile dev-requirements.in
pip-sync dev-requirements.txt
```

## License

MIT (open source)

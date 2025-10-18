<img src="https://raw.githubusercontent.com/dialectus-ai/dialectus-engine/main/assets/logo.png" alt="Dialectus CLI" width="350">

# Dialectus CLI

Command-line interface for the Dialectus AI debate system. Run AI debates locally with Ollama or cloud models via OpenRouter.

<img src="https://github.com/user-attachments/assets/fba4d1f8-9561-4971-a2fa-ec24f01865a8" alt="CLI" width=700>

## Installation

### From PyPI

**Using uv (recommended):**
```bash
uv pip install dialectus-cli
```

**Using pip:**
```bash
pip install dialectus-cli
```

### From Source

**Using uv (recommended, faster):**
```bash
# Clone the repository
git clone https://github.com/Dialectus-AI/dialectus-cli
cd dialectus-cli

# Install in development mode with all dev dependencies
uv sync

# Or install without dev dependencies
uv pip install -e .
```

**Using pip:**
```bash
# Clone the repository
git clone https://github.com/Dialectus-AI/dialectus-cli
cd dialectus-cli

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Requirements

- **Python 3.12+**
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

### Running Tests and Type Checking

**Using uv (recommended):**
```bash
# Run tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=dialectus

# Type check with Pyright
uv run pyright

# Lint with ruff
uv run ruff check .

# Format with ruff
uv run ruff format .
```

**Using pip:**
```bash
# Ensure dev dependencies are installed
pip install -e ".[dev]"

# Run tests
pytest

# Type check with Pyright
pyright

# Lint and format
ruff check .
ruff format .
```

### Building Distribution

**Using uv:**
```bash
# Build wheel and sdist
uv build

# Install locally from wheel
uv pip install dist/dialectus_cli-*.whl
```

**Using pip:**
```bash
# Build wheel and sdist
python -m build

# Install locally
pip install dist/dialectus_cli-*.whl
```

### Managing Dependencies

**Using uv:**
```bash
# Add a new dependency
# 1. Edit pyproject.toml [project.dependencies] section
# 2. Update lock file and sync environment:
uv lock && uv sync

# Upgrade all dependencies (within version constraints)
uv lock --upgrade

# Upgrade specific package
uv lock --upgrade-package rich

# Add dev dependency
# 1. Edit pyproject.toml [project.optional-dependencies.dev]
# 2. Run:
uv sync
```

**Using pip:**
```bash
# Add a new dependency
# 1. Edit pyproject.toml dependencies
# 2. Reinstall:
pip install -e ".[dev]"
```

### Why uv?

- **10-100x faster** than pip for installs and resolution
- **Reproducible builds** via `uv.lock` (cross-platform, includes hashes)
- **Python 3.14 ready** - Takes advantage of free-threading for even better performance
- **Single source of truth** - Dependencies in `pyproject.toml`, lock file auto-generated
- **Compatible** - `pip` still works perfectly with `pyproject.toml`

## License

MIT (open source)

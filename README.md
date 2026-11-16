<img width="500" height="117" alt="dialectus-logo-horz" src="https://github.com/user-attachments/assets/438b8963-0652-4886-acd1-5c197040c606" />

# Dialectus CLI

Command-line interface for the Dialectus AI debate system. Run AI debates locally with Ollama or cloud models via OpenRouter, Anthropic, or OpenAI.

> **Related Project:** This CLI uses the [dialectus-engine](https://github.com/dialectus-ai/dialectus-engine) library for all debate orchestration. Check out the engine repository for the core debate logic, API documentation, and library usage examples.

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
- **API keys** (if using cloud models): Set via environment variables
  - **OpenAI**: For GPT models
  - **Anthropic**: For Claude models
  - **OpenRouter**: One key for hundreds of models from Anthropic, OpenAI, Google, Meta, and more

### Environment Variables

```bash
# Linux/macOS
export OPENAI_API_KEY="sk-your-openai-key"
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export OPENROUTER_API_KEY="sk-or-v1-..."

# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-openai-key"
$env:ANTHROPIC_API_KEY="sk-ant-api03-..."
$env:OPENROUTER_API_KEY="sk-or-v1-..."

# Windows CMD
set OPENAI_API_KEY=sk-your-openai-key
set ANTHROPIC_API_KEY=sk-ant-api03-...
set OPENROUTER_API_KEY=sk-or-v1-...
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
- **Models**: Debate participants (Ollama, OpenRouter, Anthropic, or OpenAI)
  - **Ollama** (local): `"provider": "ollama"`, `"name": "llama3.2:3b"`
  - **OpenRouter** (cloud): `"provider": "openrouter"`, `"name": "anthropic/claude-haiku-5.5"`
  - **Anthropic** (direct): `"provider": "anthropic"`, `"name": "claude-haiku-5-5"`
  - **OpenAI** (direct): `"provider": "openai"`, `"name": "gpt-4.1-mini"`
- **Judging**: AI judge models and evaluation criteria
  - Use a single judge: `"judge_models": ["openthinker:7b"]`
  - Use ensemble judging with multiple judges: `"judge_models": ["openthinker:7b", "llama3.2:3b", "qwen2.5:3b"]`
  - The engine aggregates multiple judges using majority voting with consensus analysis
- **System**: Provider settings (Ollama/OpenRouter/Anthropic/OpenAI), topic generation, logging

## Commands

All commands work identically across platforms. After a PyPI install, run `dialectus ...` directly; from a source checkout, prefix with `uv run` as shown below.

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

## Provider Setup

### OpenAI (GPT Models)

**Use OpenAI's native API for GPT models:**

1. **Get an API key**: Create one at [platform.openai.com](https://platform.openai.com/)

2. **Set your API key** (choose one method):

   **Environment variable (recommended):**
   ```bash
   export OPENAI_API_KEY="sk-your-openai-key"
   ```

   **Or in `debate_config.json`:**
   ```json
   {
     "system": {
       "openai": {
         "api_key": "sk-your-openai-key",
         "base_url": "https://api.openai.com/v1",
         "max_retries": 3,
         "timeout": 60
       }
     }
   }
   ```

3. **Configure models** using OpenAI model IDs:
   ```json
   {
     "models": {
       "model_a": {
         "name": "gpt-4.1-mini",
         "provider": "openai",
         "personality": "analytical",
         "max_tokens": 300,
         "temperature": 0.7
       }
     }
   }
   ```

Any model ID your OpenAI account can access will work. See [OpenAI's model documentation](https://platform.openai.com/docs/models) for the current lineup. Examples: `gpt-4.1`, `gpt-4.1-mini`, `gpt-4o`.

### Anthropic (Claude Models)

**Direct access to Claude models with official Anthropic API:**

1. **Get an API key**: Sign up at [console.anthropic.com](https://console.anthropic.com/)

2. **Set your API key** (choose one method):

   **Environment variable (recommended):**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-api03-..."
   ```

   **Or in `debate_config.json`:**
   ```json
   {
     "system": {
       "anthropic": {
         "api_key": "sk-ant-api03-...",
         "base_url": "https://api.anthropic.com/v1",
         "max_retries": 3,
         "timeout": 60
       }
     }
   }
   ```

3. **Configure models** using official model names:
   ```json
   {
     "models": {
       "model_a": {
         "name": "claude-haiku-5-5",
         "provider": "anthropic",
         "personality": "analytical",
         "max_tokens": 300,
         "temperature": 0.7
       }
     }
   }
   ```

**Choosing a model:** use any model ID your Anthropic account can access. See [Anthropic's model documentation](https://docs.anthropic.com/en/docs/models-overview) for the current lineup. The older Claude 3 and 3.5 models have been retired, so old configs that name them will need updating.

Cost tracking for direct Anthropic and OpenAI models relies on a built-in pricing catalog that may not include the newest models. OpenRouter reports real per-request costs.

### OpenRouter

**One API key for hundreds of models from Anthropic, OpenAI, Google, Meta, and more:**

1. **Get an API key**: Sign up at [openrouter.ai](https://openrouter.ai/)

2. **Set your API key**:
   ```bash
   export OPENROUTER_API_KEY="sk-or-v1-..."
   ```

3. **Configure models** using OpenRouter's naming:
   ```json
   {
     "models": {
       "model_a": {
         "name": "anthropic/claude-haiku-5.5",
         "provider": "openrouter",
         "personality": "analytical",
         "max_tokens": 300,
         "temperature": 0.7
       }
     }
   }
   ```

   Browse model IDs at [openrouter.ai/models](https://openrouter.ai/models), or run `dialectus list-models`. Variants with a `:batch` suffix only accept OpenRouter's batch API and fail on chat requests, so don't configure them.

### Ollama (Local Models)

**Run models locally without any API keys:**

1. **Install Ollama**: Download from [ollama.com](https://ollama.com/)

2. **Pull models**:
   ```bash
   ollama pull llama3.2:3b
   ollama pull qwen2.5:7b
   ```

3. **Configure**:
   ```json
   {
     "models": {
       "model_a": {
         "name": "llama3.2:3b",
         "provider": "ollama",
         "personality": "analytical",
         "max_tokens": 300,
         "temperature": 0.7
       }
     },
     "system": {
       "ollama_base_url": "http://localhost:11434"
     }
   }
   ```

## Architecture

```
CLI → DebateRunner → DebateEngine → Rich Console
           ↓
    SQLite Database
```

- **No API layer** - Imports [dialectus-engine](https://github.com/dialectus-ai/dialectus-engine) directly as a Python library
- **Local-first** - Runs completely offline with Ollama
- **SQLite storage** - Simple, portable database

For more details on the core engine implementation, see the [dialectus-engine repository](https://github.com/dialectus-ai/dialectus-engine).

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
- **Single source of truth** - Dependencies in `pyproject.toml`, lock file auto-generated
- **Compatible** - `pip` still works perfectly with `pyproject.toml`

## License

MIT (open source)

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Style

- You are a technical co-founder and collaborative partner, not a servant. 🤗
- Your role is to critically evaluate my claims and suggestions, and to offer alternative perspectives or challenge assumptions when appropriate.
- Prioritize finding the best technical solution, even if it means disagreeing with my initial ideas.
- Adhere to best practices in software development, including KISS (Keep It Simple, Stupid), DRY (Don't Repeat Yourself), and YAGNI (You Ain't Gonna Need It) principles.
- Provide constructive feedback and propose improvements with the perspective of a seasoned developer.
- Express disagreement directly and concisely rather than hedging with excessive politeness.

## Project Overview

**Dialectus CLI** is a lightweight, API-first command-line client for the Dialectus AI debate system. This is a Python terminal application that communicates with the dialectus-engine backend via REST API and WebSocket connections.

Key characteristics:
- **Zero code duplication** - No debate logic, just API calls
- **API-first design** - Uses same backend endpoints as dialectus-web frontend
- **Rich terminal UI** - Beautiful output with progress bars and formatted displays
- **Strict typing** - Pydantic models for configuration and API contracts
- **Modern async** - httpx and websockets for non-blocking I/O

This is one of three repositories in the Dialectus ecosystem:
- **dialectus-cli** (this repo) - Python CLI client
- **dialectus-engine** - Python/FastAPI backend (REST API + WebSocket)
- **dialectus-web** - TypeScript/Vite frontend SPA

## Code Quality Standards

**This project has a HIGH bar.** The developer has 30 years of professional software engineering experience and expects:

### Python Standards
- **Python 3.13** with modern type annotations
- **Pyright standard mode** (not strict, but still rigorous)
- **No legacy typing** - Use `list[str]`, `dict[str, int]`, `X | None` instead of `List`, `Dict`, `Optional`
- **Avoid `Any`** - Use proper type annotations with generics, protocols, and unions
- **Pydantic v2** - Use `model_dump()` not deprecated `dict()` for serialization
- **Modern async/await** - Proper async context managers and generators
- **No unused imports or variables** - Keep the codebase clean
- **Type-safe dict access** - Use `.get()` or explicit checks for optional keys
- **Collections from built-ins** - `from typing import TYPE_CHECKING` for circular imports only

### Pre-Commit Requirements
**CRITICAL**: Before ANY commit or code completion:
1. Check type annotations with Pyright in standard mode
2. Run the CLI to ensure no runtime errors (`python cli.py --help`)
3. Test core commands (`list-models`, `debate`) if modifying API client
4. Ensure config JSON examples are valid

### Project Conventions
- **Pydantic for config** - All configuration via Pydantic models with validation
- **Rich for output** - Use Rich Console for all user-facing output (not print())
- **Click for CLI** - Declarative command structure with type-checked options
- **API client abstraction** - Single ApiClient class for all backend communication
- **JSON configuration** - Human-editable config files with strict validation

## Development Commands

```bash
# Run CLI commands directly
python cli.py --help
python cli.py list-models
python cli.py debate --topic "Should AI be regulated?"
python cli.py transcripts

# Install dependencies
pip install -r requirements.txt

# Recompile dependencies after editing requirements.in
pip-compile requirements.in

# Install as editable package (optional)
pip install -e .

# Run with custom config
python cli.py --config custom_config.json debate

# Enable debug logging
python cli.py --log-level DEBUG debate
```

## Architecture

### Technology Stack
- **Python 3.13** with modern type hints (`X | None`, `list[T]`, `dict[K, V]`)
- **Click** for CLI framework with decorators and type-checked options
- **Rich** for beautiful terminal UI (tables, panels, progress bars)
- **httpx** for async HTTP client (REST API calls)
- **websockets** for WebSocket client (real-time debate streaming)
- **Pydantic v2** for data validation and settings management

### Core Structure
```
dialectus-cli/
├── cli.py                       # Main CLI entry point with Click commands
├── api_client.py                # ApiClient class for backend communication
├── config.py                    # Pydantic config models (AppConfig, ModelConfig)
├── setup.py                     # Package setup for console script installation
├── requirements.in              # Minimal dependency specifications
├── requirements.txt             # Locked dependencies via pip-compile
├── debate_config.example.json   # Example configuration (single judge)
├── debate_config.ensemble.example.json  # Example with ensemble judges
├── debate_config.json           # User's actual config (gitignored)
├── pyrightconfig.json           # Pyright type checker configuration
└── transcripts/                 # Local debate transcript storage
    └── *.json                   # Saved debate transcripts (timestamped)
```

### Key Design Decisions

**API-First Architecture**: This CLI is intentionally thin. All debate logic, model management, and judging happens in the backend (dialectus-engine). The CLI just:
1. Loads config from JSON
2. Calls `/v1/debates` API endpoint to create debate
3. Opens WebSocket to `/v1/ws/debate/{id}` for real-time streaming
4. Displays results in Rich terminal UI

**Zero Code Duplication**: Unlike many CLIs that duplicate backend logic, this one trusts the backend completely. This ensures:
- CLI stays in sync with web frontend automatically
- Backend improvements benefit CLI instantly
- No drift between CLI and web behavior
- Smaller codebase (just ~1000 lines total)

**Pydantic Configuration**: JSON config files use same Pydantic models as backend for consistency. Config validation happens at parse time with clear error messages.

**Rich Terminal UI**: All output via Rich Console provides:
- Colored, formatted text
- Progress spinners for API calls
- Tables for model lists
- Panels for debate setup
- Real-time streaming display

## Multi-Repository Context

When working across repositories, you can add them to the Claude Code session:
```bash
claude-code --add-dir ../dialectus-engine --add-dir ../dialectus-web dialectus-cli
```

### Backend Integration (dialectus-engine)
The CLI communicates with the Python FastAPI backend via:
- **REST API** at `http://localhost:8000/v1` (configurable via `system.api_base_url`)
  - `GET /v1/models` - Available AI models
  - `POST /v1/debates` - Create and start debate
- **WebSocket** at `ws://localhost:8000/v1/ws/debate/{id}` for real-time streaming
  - Streams `new_message` events with debate turns
  - Streams `judge_decision` event when judging completes
  - Streams `debate_completed` event when finished

### Frontend Relationship (dialectus-web)
The CLI and web frontend are **parallel clients** of the same backend:
- Both use identical API endpoints
- Both receive same WebSocket message format
- Both interpret same debate formats and judge results
- Backend enforces all business logic for both

## Configuration System

### Configuration Files
- `debate_config.json` - User's active configuration (gitignored)
- `debate_config.example.json` - Example with single judge
- `debate_config.ensemble.example.json` - Example with ensemble judges (3+ judges)

### Configuration Structure
```json
{
  "debate": {
    "topic": "Should AI be regulated?",
    "format": "oxford",           // "oxford", "parliamentary", "socratic"
    "time_per_turn": 120,          // Seconds per turn (informational)
    "word_limit": 200              // Word limit per turn
  },
  "models": {
    "model_a": {
      "name": "qwen2.5:7b",        // Backend model name
      "provider": "ollama",         // "ollama" or "openrouter"
      "personality": "analytical",  // Personality style
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
    "judge_models": ["openthinker:7b"],  // Empty for no judge, 1 for single, 3+ for ensemble
    "judge_provider": "ollama",
    "criteria": ["logic", "evidence", "persuasiveness"]
  },
  "system": {
    "api_base_url": "http://localhost:8000",
    "log_level": "INFO",
    "http_timeout_local": 120.0,   // Longer timeout for local Ollama models
    "http_timeout_remote": 30.0,   // Shorter timeout for cloud models
    "websocket_timeout": 60.0
  }
}
```

### Pydantic Config Models
- `AppConfig` - Top-level config container
- `DebateConfig` - Debate settings (topic, format, word_limit)
- `ModelConfig` - Per-model config (name, provider, temperature)
- `JudgingConfig` - Judge settings (judge_models, criteria)
- `SystemConfig` - System settings (api_base_url, timeouts)

## CLI Commands

### Main Commands

**`debate`** - Start a debate between AI models
```bash
python cli.py debate [OPTIONS]

Options:
  -t, --topic TEXT                Debate topic (overrides config)
  -f, --format [parliamentary|oxford|socratic]  Debate format (overrides config)
  -i, --interactive               Interactive mode with pauses between phases
```

**`list-models`** - List available models from the backend
```bash
python cli.py list-models
```

**`transcripts`** - List saved debate transcripts
```bash
python cli.py transcripts [OPTIONS]

Options:
  --detail               Show full transcript content (default: metadata only)
  --limit INTEGER        Number of transcripts to show (default: 10)
```

### Global Options
```bash
python cli.py [OPTIONS] COMMAND

Options:
  -c, --config PATH               Configuration file path (default: debate_config.json)
  --log-level [DEBUG|INFO|WARNING|ERROR]  Logging level
  --help                          Show help message
```

## API Client Architecture

### ApiClient Class
Located in `api_client.py`, this class handles all backend communication:

**HTTP Methods** (via httpx.AsyncClient):
- `get_models() -> list[str]` - Fetch available models
- `create_debate(setup: DebateSetupRequest) -> DebateResponse` - Create debate
- `close() -> None` - Close HTTP client

**WebSocket Methods** (via websockets):
- `stream_debate(debate_id: str, handler: DebateStreamHandler) -> None` - Stream debate events

**Smart Timeout Handling**:
- Detects if config uses Ollama models → uses `http_timeout_local` (120s default)
- Detects if config uses only cloud models → uses `http_timeout_remote` (30s default)
- Reason: Local Ollama inference can be slow, cloud APIs are fast

### DebateStreamHandler Protocol
Callback interface for WebSocket event handling:
```python
class DebateStreamHandler(Protocol):
    async def on_message(self, speaker_id: str, content: str, is_chunk: bool) -> None:
        """Handle debate message chunks."""
        ...

    async def on_judge_decision(self, decision: dict[str, Any]) -> None:
        """Handle judge decision."""
        ...

    async def on_debate_complete(self, summary: dict[str, Any]) -> None:
        """Handle debate completion."""
        ...

    async def on_error(self, error: str) -> None:
        """Handle errors."""
        ...
```

### Pydantic Request/Response Models
- `DebateSetupRequest` - Matches backend `/v1/debates` POST body
- `DebateResponse` - Backend response with `id`, `status`, `config`
- `FullModelConfig` - Complete model config for API (name, provider, personality, etc.)

## Real-Time Streaming

### WebSocket Flow
1. CLI calls `POST /v1/debates` → receives `debate_id`
2. CLI connects to `ws://localhost:8000/v1/ws/debate/{debate_id}`
3. Backend executes debate asynchronously, streaming events:
   - `{"type": "new_message", "speaker_id": "model_a", "content": "...", "is_chunk": true}`
   - `{"type": "judge_decision", "winner_id": "model_a", "margin": 7.2, ...}`
   - `{"type": "debate_completed", "status": "completed", ...}`
4. CLI displays events in real-time via Rich terminal UI
5. CLI saves transcript to `transcripts/YYYYMMDD_HHMMSS_debate.json`

### Display Features
- **Spinner** during API calls (model fetching, debate creation)
- **Live chunks** streaming for debate messages (character by character)
- **Tables** for model listings
- **Panels** for debate setup and results
- **Colors** for different speakers and judge verdicts

## File Organization

### Naming Conventions
- **Modules**: `snake_case.py` (e.g., `api_client.py`, `config.py`)
- **Classes**: `PascalCase` (e.g., `ApiClient`, `AppConfig`)
- **Functions**: `snake_case` (e.g., `setup_logging`, `get_default_config`)
- **Constants**: `UPPER_SNAKE_CASE` for module-level constants
- **Click commands**: `snake_case` (e.g., `@cli.command()` for `list_models`)

### Import Conventions
```python
# Standard library
import asyncio
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

# Third-party
import click
import httpx
import websockets
from rich.console import Console
from pydantic import BaseModel, Field

# Local modules (absolute imports preferred, no relative imports needed)
from config import AppConfig, get_default_config
from api_client import ApiClient, DebateSetupRequest
```

## Common Patterns

### Click Command with Context
```python
@cli.command()
@click.option("--topic", "-t", help="Debate topic")
@click.pass_context
def debate(ctx: click.Context, topic: str | None) -> None:
    """Start a debate."""
    config: AppConfig = ctx.obj["config"]

    # Override config with CLI options if provided
    if topic:
        config.debate.topic = topic

    # Run async function
    try:
        asyncio.run(_run_debate_async(config))
    except Exception as e:
        _display_error(e)
        raise SystemExit(1)
```

### Rich Terminal Output
```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Panel for structured info
console.print(Panel(
    "[bold cyan]Debate Setup[/bold cyan]\n"
    f"Topic: {config.debate.topic}\n"
    f"Format: {config.debate.format}",
    border_style="blue"
))

# Table for data
table = Table(title="Available Models")
table.add_column("Model Name", style="cyan")
table.add_column("Provider", style="magenta")
for model in models:
    table.add_row(model.name, model.provider)
console.print(table)
```

### Async API Client Usage
```python
async def _run_debate_async(config: AppConfig) -> None:
    """Run debate with proper resource cleanup."""
    client = ApiClient(config.system.api_base_url)

    try:
        # Create debate via REST
        setup = DebateSetupRequest(
            topic=config.debate.topic,
            format=config.debate.format,
            models={...},
            judge_models=config.judging.judge_models
        )
        response = await client.create_debate(setup)

        # Stream debate via WebSocket
        handler = DebateDisplayHandler(console)
        await client.stream_debate(response.id, handler)

    finally:
        await client.close()
```

### Pydantic Config Loading
```python
def get_default_config() -> AppConfig:
    """Load and validate configuration."""
    config_path = Path("debate_config.json")

    if not config_path.exists():
        raise FileNotFoundError(
            "debate_config.json not found. "
            "Copy debate_config.example.json to get started."
        )

    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    return AppConfig(**config_data)  # Pydantic validation
```

## Testing & Development

### Local Development
1. Ensure backend is running: `cd ../dialectus-engine && python main.py --web`
2. Run CLI: `python cli.py list-models` to verify connection
3. Run debate: `python cli.py debate`
4. Check logs: `python cli.py --log-level DEBUG debate`

### Testing Against Backend
The CLI should work against:
- **Local backend**: `http://localhost:8000` (default)
- **Production backend**: `https://dialectus.ai` (set `system.api_base_url` in config)

No mocking or test harness needed - this CLI is a pure API client.

### Common Issues
- **Connection refused** - Backend not running on `api_base_url`
- **WebSocket timeout** - Increase `system.websocket_timeout` in config
- **HTTP timeout** - Increase `http_timeout_local` for slow local models
- **Empty model list** - Backend has no models configured or can't reach Ollama
- **Invalid config** - Pydantic will show validation errors with field names

## Package Installation

The CLI can be installed as a console script via `setup.py`:

```bash
# Install in development mode
pip install -e .

# Run via console script
dialectus debate --topic "Should AI be regulated?"

# Uninstall
pip uninstall dialectus-cli
```

Entry point defined in `setup.py`:
```python
entry_points={
    "console_scripts": [
        "dialectus=cli:main",  # Calls main() in cli.py
    ],
}
```

## Performance Considerations

### Async I/O
All network operations are async to avoid blocking:
- HTTP requests via `httpx.AsyncClient`
- WebSocket streaming via `websockets.connect()`
- Concurrent operations where possible (e.g., spinner + API call)

### Resource Cleanup
Always use proper async context managers:
```python
async with httpx.AsyncClient() as client:
    # Client auto-closes on exit
    ...

async with websockets.connect(uri) as websocket:
    # WebSocket auto-closes on exit
    ...
```

### Timeout Configuration
Smart timeout handling based on model providers:
- Local models (Ollama): 120s default - slow inference
- Cloud models (OpenRouter): 30s default - fast APIs
- WebSocket: 60s default - allows for long-running debates

## Dependencies

Minimal dependencies managed via `requirements.in`:
```
httpx>=0.25.0      # Modern async HTTP client
websockets>=15.0.1 # WebSocket client
pydantic>=2.0.0    # Data validation and settings
rich>=13.0.0       # Terminal UI
click>=8.0.0       # CLI framework
```

All pinned versions in `requirements.txt` via `pip-compile` for reproducibility.

## Security Considerations

- **No API keys in code** - Backend handles all auth with OpenRouter/Ollama
- **No user auth** - CLI is for local/development use
- **WebSocket security** - Uses same domain as HTTP API (no CORS issues)
- **Config validation** - Pydantic prevents malformed configs
- **Type safety** - Pyright catches type errors at development time

## Future Enhancements

- **Interactive config editor** - TUI for editing debate_config.json
- **Transcript replay** - Play back saved debates in terminal
- **Model comparison mode** - Run same debate with different model combinations
- **Export formats** - Save transcripts as Markdown, HTML, PDF
- **Statistics dashboard** - Show debate history, win rates, model performance
- **Batch mode** - Run multiple debates from CSV/YAML input
- **Authentication** - Support backend user accounts when available
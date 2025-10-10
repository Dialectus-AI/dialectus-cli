# Dialectus CLI

Command-line interface for the Dialectus AI debate system. This CLI imports the `dialectus-engine` wheel directly and runs debates locally.

## Quick Start

### Linux/macOS/Git Bash
```bash
# 1. Build and install the engine wheel
./build-engine.sh

# 2. Copy the example config
cp debate_config.example.json debate_config.json

# 3. Edit config with your models and API keys (if using OpenRouter)
nano debate_config.json

# 4. Run a debate
python cli.py debate
```

### Windows (PowerShell)
```powershell
# 1. Build and install the engine wheel
.\build-engine.ps1

# 2. Copy the example config
Copy-Item debate_config.example.json debate_config.json

# 3. Edit config with your models and API keys (if using OpenRouter)
notepad debate_config.json

# 4. Run a debate
python cli.py debate
```

### Windows (CMD)
```cmd
REM 1. Build and install the engine wheel
build-engine.bat

REM 2. Copy the example config
copy debate_config.example.json debate_config.json

REM 3. Edit config with your models and API keys (if using OpenRouter)
notepad debate_config.json

REM 4. Run a debate
python cli.py debate
```

## Requirements

- **Python 3.13+**
- **Ollama** (if using local models): Running at `http://localhost:11434`
- **OpenRouter API key** (if using cloud models): Set via environment variable

### Environment Variables

**Linux/macOS:**
```bash
export OPENROUTER_API_KEY="your-key-here"
```

**Windows (PowerShell):**
```powershell
$env:OPENROUTER_API_KEY="your-key-here"
```

**Windows (CMD):**
```cmd
set OPENROUTER_API_KEY=your-key-here
```

## Installation

### Linux/macOS/Git Bash
```bash
# Install dependencies
pip install -r requirements.txt

# Build and install engine wheel
./build-engine.sh
```

### Windows (PowerShell)
```powershell
# Install dependencies
pip install -r requirements.txt

# Build and install engine wheel
.\build-engine.ps1
```

### Windows (CMD)
```cmd
REM Install dependencies
pip install -r requirements.txt

REM Build and install engine wheel
build-engine.bat
```

## Configuration

Edit `debate_config.json` to configure:
- **Models**: Debate participants (Ollama or OpenRouter)
- **Judging**: AI judge models and evaluation criteria
- **System**: Ollama/OpenRouter settings

## Commands

All commands work identically across platforms (Linux/macOS/Windows):

### Start a Debate
```bash
python cli.py debate
python cli.py debate --topic "Should AI be regulated?"
python cli.py debate --format oxford
python cli.py debate --interactive
```

### List Available Models
```bash
python cli.py list-models
```

### View Saved Transcripts
```bash
python cli.py transcripts
python cli.py transcripts --limit 50
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

### Rebuilding the Engine

When the engine code changes:

**Linux/macOS/Git Bash:**
```bash
./build-engine.sh
```

**Windows (PowerShell):**
```powershell
.\build-engine.ps1
```

**Windows (CMD):**
```cmd
build-engine.bat
```

### Type Checking
```bash
pyright cli.py
```

## License

MIT (open source)

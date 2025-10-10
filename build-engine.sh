#!/usr/bin/env bash
# build-engine.sh
# Build dialectus-engine wheel and install it into the CLI venv

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function step() {
    echo -e "\n${CYAN}[STEP]${NC} $1"
}

function success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

function error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${YELLOW}==================================================${NC}"
echo -e "${YELLOW}  Dialectus CLI - Engine Build Script${NC}"
echo -e "${YELLOW}==================================================${NC}"

# Paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLI_DIR="$SCRIPT_DIR"
ENGINE_DIR="$(dirname "$CLI_DIR")/dialectus-engine"
DEPS_DIR="$CLI_DIR/deps"

# Step 1: Verify dialectus-engine exists
step "Verifying dialectus-engine directory..."
if [ ! -d "$ENGINE_DIR" ]; then
    error "dialectus-engine directory not found at: $ENGINE_DIR"
    exit 1
fi
success "Found dialectus-engine at: $ENGINE_DIR"

# Step 2: Build the wheel
step "Building dialectus-engine wheel..."
cd "$ENGINE_DIR"

# Clean old builds
for pattern in build dist "*.egg-info"; do
    if compgen -G "$pattern" > /dev/null 2>&1; then
        rm -rf $pattern
        success "Cleaned: $pattern"
    fi
done

# Build wheel
python -m build --wheel
if [ $? -ne 0 ]; then
    error "Wheel build failed"
    exit 1
fi
success "Wheel built successfully"

# Step 3: Find the latest wheel
step "Locating wheel file..."
WHEEL_FILE=$(ls -t dist/*.whl 2>/dev/null | head -n1)
if [ -z "$WHEEL_FILE" ]; then
    error "No wheel file found in dist/"
    exit 1
fi
success "Found wheel: $(basename "$WHEEL_FILE")"

# Step 4: Create deps directory if needed
if [ ! -d "$DEPS_DIR" ]; then
    mkdir -p "$DEPS_DIR"
    success "Created deps directory"
fi

# Step 5: Copy wheel to deps
step "Copying wheel to deps/..."
cp "$WHEEL_FILE" "$DEPS_DIR/"
success "Copied to: $DEPS_DIR/$(basename "$WHEEL_FILE")"

# Step 6: Install the wheel
step "Installing wheel with pip (into venv)..."
cd "$CLI_DIR"

# Activate venv and install
source venv/Scripts/activate
pip install --force-reinstall "$DEPS_DIR/$(basename "$WHEEL_FILE")"
if [ $? -ne 0 ]; then
    error "Pip install failed"
    exit 1
fi
success "Wheel installed successfully into venv"

echo -e "\n${GREEN}==================================================${NC}"
echo -e "${GREEN}  Build Complete!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "You can now run: ${CYAN}python cli.py --help${NC}\n"

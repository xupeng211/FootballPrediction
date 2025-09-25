#!/bin/bash
# Setup CI enforcement hooks

set -e

echo "🔧 Setting up CI enforcement hooks..."

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Check if we're in project root
if [ ! -f "pyproject.toml" ] && [ ! -f "requirements.txt" ]; then
    echo "❌ Not in project root directory"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Copy pre-push hook
echo "📋 Installing pre-push hook..."
cp .git/hooks/pre-push .git/hooks/pre-push.bak 2>/dev/null || true

# Create the pre-push hook
cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
# Pre-push hook for CI enforcement
set -e

echo "🔍 Running pre-push CI checks..."

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] && [ ! -f "requirements.txt" ]; then
    print_error "Not in project root directory"
    exit 1
fi

# Run make prepush if available
if command -v make &> /dev/null && [ -f "Makefile" ]; then
    echo "📋 Running 'make prepush'..."
    if make prepush; then
        print_status "Pre-push checks passed"
    else
        print_error "Pre-push checks failed"
        exit 1
    fi
else
    echo "📋 Running manual CI checks..."

    # Run unit tests
    if USE_LOCAL_DB=false pytest tests/unit/ --cov=src --cov-report=term-missing --cov-fail-under=60 --tb=short; then
        print_status "Tests passed"
    else
        print_error "Tests failed"
        exit 1
    fi

    # Run linting
    if flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics; then
        print_status "Lint checks passed"
    else
        print_error "Lint checks failed"
        exit 1
    fi
fi

print_status "All pre-push checks passed! 🚀"
exit 0
EOF

# Make the hook executable
chmod +x .git/hooks/pre-push

# Create pre-commit hook for additional safety
echo "📋 Installing pre-commit hook..."
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for basic checks

echo "🔍 Running pre-commit checks..."

# Run black formatting if available
if command -v black &> /dev/null; then
    echo "🎨 Running black formatter..."
    black --check . || {
        echo "💡 Code needs formatting. Run: black ."
        echo "   Or commit with --no-verify to skip"
        exit 1
    }
fi

# Run isort if available
if command -v isort &> /dev/null; then
    echo "📚 Running isort..."
    isort --check-only . || {
        echo "💡 Imports need sorting. Run: isort ."
        echo "   Or commit with --no-verify to skip"
        exit 1
    }
fi

echo "✅ Pre-commit checks passed!"
EOF

chmod +x .git/hooks/pre-commit

# Install pre-commit configuration if pre-commit is available
if command -v pre-commit &> /dev/null; then
    echo "📋 Installing pre-commit configuration..."
    cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile, black]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=127, --extend-ignore=E203,W503]

  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: bash -c 'USE_LOCAL_DB=false pytest tests/unit/ --cov=src --cov-report=term-missing --cov-fail-under=60'
        language: system
        pass_filenames: false
        always_run: true
EOF

    pre-commit install
    print_status "Pre-commit hooks installed"
fi

print_status "CI enforcement hooks installed successfully!"
echo ""
echo "🚀 CI enforcement is now active:"
echo "   • Pre-commit: Code formatting and basic checks"
echo "   • Pre-push: Full CI validation"
echo ""
echo "💡 To skip hooks:"
echo "   • Commit: git commit --no-verify"
echo "   • Push: git push --no-verify"
echo ""
echo "🔧 To test hooks:"
echo "   • Pre-commit: Run 'pre-commit run --all-files'"
echo "   • Pre-push: Run 'make prepush'"
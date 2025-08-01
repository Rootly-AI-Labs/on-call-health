#!/bin/bash

# Pre-commit check script for frontend
# This script runs type checking and linting before allowing commits

echo "🔍 Running pre-commit checks..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to frontend directory
cd "$(dirname "$0")"

# Run TypeScript type checking
echo "📘 Running TypeScript type check..."
npx tsc --noEmit
TYPE_CHECK_EXIT_CODE=$?

if [ $TYPE_CHECK_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}❌ TypeScript type check failed!${NC}"
    echo "Please fix the type errors before committing."
    exit 1
else
    echo -e "${GREEN}✅ TypeScript type check passed${NC}"
fi

# Run ESLint
echo "🔍 Running ESLint..."
npm run lint
LINT_EXIT_CODE=$?

if [ $LINT_EXIT_CODE -ne 0 ]; then
    # Check if there are actual errors (not just warnings)
    npm run lint 2>&1 | grep -E "Error:" > /dev/null
    HAS_ERRORS=$?
    
    if [ $HAS_ERRORS -eq 0 ]; then
        echo -e "${RED}❌ ESLint found errors!${NC}"
        echo "Please fix the ESLint errors before committing."
        echo "Tip: Run 'npm run lint' to see all issues."
        exit 1
    else
        echo -e "${YELLOW}⚠️  ESLint found only warnings${NC}"
        echo "Consider fixing the warnings, but they won't block your commit."
    fi
else
    echo -e "${GREEN}✅ ESLint check passed${NC}"
fi

echo -e "${GREEN}✨ All pre-commit checks passed!${NC}"
exit 0
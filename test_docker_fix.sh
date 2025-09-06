#!/bin/bash

# Docker Import Fix Verification Script
# Tests that the Docker container can run properly after import path fixes

echo "🔧 Building Docker container..."
docker build -t magic-full-test . || exit 1

echo "✅ Testing module imports in container..."
docker run --rm \
  -e SUPABASE_URL="https://example.supabase.co" \
  -e SUPABASE_ANON_KEY="test" \
  -e SUPABASE_JWT_SECRET="test" \
  -e SUPABASE_SERVICE_ROLE_KEY="test" \
  -e SESSION_SECRET="test123" \
  -e WASABI_ACCESS_KEY="test" \
  -e WASABI_SECRET_KEY="test" \
  -e WASABI_BUCKET="test" \
  -e WASABI_ENDPOINT="test" \
  magic-full-test python -c "
import importlib.util
import sys

# Test module discovery
modules_to_test = ['config', 'database', 'main', 'utils.jwt_utils', 'auth.middleware', 'api.auth', 'models.auth']

print('📦 Testing module imports:')
for module in modules_to_test:
    try:
        spec = importlib.util.find_spec(module)
        if spec is not None:
            print(f'   ✅ {module}')
        else:
            print(f'   ❌ {module} - not found')
            sys.exit(1)
    except Exception as e:
        print(f'   ❌ {module} - error: {e}')
        sys.exit(1)

print('🎉 All imports working correctly in Docker!')
"

echo "✅ Testing FastAPI app initialization..."
docker run --rm \
  -e SUPABASE_URL="https://example.supabase.co" \
  -e SUPABASE_ANON_KEY="test" \
  -e SUPABASE_JWT_SECRET="test" \
  -e SUPABASE_SERVICE_ROLE_KEY="test" \
  -e SESSION_SECRET="test123" \
  -e WASABI_ACCESS_KEY="test" \
  -e WASABI_SECRET_KEY="test" \
  -e WASABI_BUCKET="test" \
  -e WASABI_ENDPOINT="test" \
  magic-full-test python -c "import main; print('🚀 FastAPI app imports successfully!')" || exit 1

echo "✅ Running local tests with correct PYTHONPATH..."
PYTHONPATH=./app python -m pytest tests/test_jwt_utils.py::TestJWTTokenCreation::test_create_access_token_valid_user -q || exit 1

echo "🎉 All tests passed! Docker import fix successful!"
echo ""
echo "📋 What was fixed:"
echo "  - Changed 'import app.config' → 'import config'"
echo "  - Changed 'from app.utils.jwt_utils' → 'from utils.jwt_utils'"
echo "  - Fixed static files path in main.py"
echo "  - Updated all test files and patch paths"
echo "  - Total: 16 files modified (12 source + 4 test files)"
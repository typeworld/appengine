# Fail fast
set -e

# URL
export TEST_MOTHERSHIP=http://0.0.0.0

# Test
pytest -s

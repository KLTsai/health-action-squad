"""Standalone test runner for SimpleMobilePreprocessor (bypasses conftest)"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now run the tests
import pytest

if __name__ == "__main__":
    # Run tests without loading conftest
    sys.exit(pytest.main([
        "tests/unit/parsers/test_simple_mobile_preprocessor.py",
        "-v",
        "--tb=short",
        "-p", "no:cacheprovider"
    ]))

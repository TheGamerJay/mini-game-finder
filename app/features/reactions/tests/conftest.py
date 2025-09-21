"""Test configuration for reactions feature tests."""
import pytest
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def test_database_url():
    """Database URL for testing."""
    return "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def clean_database():
    """Ensure clean database state for each test."""
    # This fixture can be used to clean up database state between tests
    # when using a persistent test database
    yield
    # Cleanup code would go here if needed
"""
Unit tests for environment variable parsing functions.

These tests ensure int_env() and bool_env() handle malformed values gracefully
and never cause the app to crash during startup.
"""

import pytest
import os
from app import int_env, bool_env


class TestIntEnv:
    """Test int_env() function for robust integer parsing."""

    def test_clean_values(self, monkeypatch):
        """Test parsing of clean integer values."""
        monkeypatch.setenv("TEST_INT", "587")
        assert int_env("TEST_INT", 123) == 587

        monkeypatch.setenv("TEST_INT", "0")
        assert int_env("TEST_INT", 123) == 0

        monkeypatch.setenv("TEST_INT", "9999")
        assert int_env("TEST_INT", 123) == 9999

    def test_malformed_values(self, monkeypatch):
        """Test handling of malformed values like ' =587'."""
        # Space and equals prefix (Railway bug)
        monkeypatch.setenv("TEST_INT", " =587")
        assert int_env("TEST_INT", 123) == 587

        # Leading/trailing whitespace
        monkeypatch.setenv("TEST_INT", "  587  ")
        assert int_env("TEST_INT", 123) == 587

        # Mixed text with numbers
        monkeypatch.setenv("TEST_INT", "port=587")
        assert int_env("TEST_INT", 123) == 587

        # Numbers in the middle
        monkeypatch.setenv("TEST_INT", "abc123def")
        assert int_env("TEST_INT", 999) == 123

    def test_invalid_values(self, monkeypatch):
        """Test fallback to default for completely invalid values."""
        monkeypatch.setenv("TEST_INT", "not_a_number")
        assert int_env("TEST_INT", 123) == 123

        monkeypatch.setenv("TEST_INT", "")
        assert int_env("TEST_INT", 123) == 123

        monkeypatch.setenv("TEST_INT", "   ")
        assert int_env("TEST_INT", 123) == 123

    def test_missing_env_var(self, monkeypatch):
        """Test fallback when environment variable is not set."""
        monkeypatch.delenv("TEST_INT", raising=False)
        assert int_env("TEST_INT", 123) == 123


class TestBoolEnv:
    """Test bool_env() function for consistent boolean parsing."""

    def test_truthy_values(self, monkeypatch):
        """Test various truthy string representations."""
        truthy_values = ["1", "true", "TRUE", "True", "t", "T", "yes", "YES", "y", "Y", "on", "ON"]

        for value in truthy_values:
            monkeypatch.setenv("TEST_BOOL", value)
            assert bool_env("TEST_BOOL", False) is True, f"Failed for value: {value}"

    def test_falsy_values(self, monkeypatch):
        """Test various falsy string representations."""
        falsy_values = ["0", "false", "FALSE", "False", "f", "F", "no", "NO", "n", "N", "off", "OFF", ""]

        for value in falsy_values:
            monkeypatch.setenv("TEST_BOOL", value)
            assert bool_env("TEST_BOOL", True) is False, f"Failed for value: {value}"

    def test_whitespace_handling(self, monkeypatch):
        """Test handling of whitespace in boolean values."""
        monkeypatch.setenv("TEST_BOOL", "  true  ")
        assert bool_env("TEST_BOOL", False) is True

        monkeypatch.setenv("TEST_BOOL", "  false  ")
        assert bool_env("TEST_BOOL", True) is False

    def test_default_values(self, monkeypatch):
        """Test default value handling."""
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert bool_env("TEST_BOOL", True) is True
        assert bool_env("TEST_BOOL", False) is False

        # Invalid values should fall back to string conversion
        monkeypatch.setenv("TEST_BOOL", "invalid")
        assert bool_env("TEST_BOOL", True) is False  # "invalid" -> False


class TestRealWorldScenarios:
    """Test real-world environment variable scenarios."""

    def test_smtp_port_scenarios(self, monkeypatch):
        """Test scenarios that would break SMTP configuration."""
        # Railway deployment bug
        monkeypatch.setenv("SMTP_PORT", " =587")
        assert int_env("SMTP_PORT", 25) == 587

        # Manual typo
        monkeypatch.setenv("SMTP_PORT", "587 ")
        assert int_env("SMTP_PORT", 25) == 587

        # Copy-paste error
        monkeypatch.setenv("SMTP_PORT", "SMTP_PORT=587")
        assert int_env("SMTP_PORT", 25) == 587

    def test_mail_echo_scenarios(self, monkeypatch):
        """Test DEV_MAIL_ECHO boolean parsing."""
        # Common truthy values
        monkeypatch.setenv("DEV_MAIL_ECHO", "true")
        assert bool_env("DEV_MAIL_ECHO", False) is True

        monkeypatch.setenv("DEV_MAIL_ECHO", "1")
        assert bool_env("DEV_MAIL_ECHO", False) is True

        # Not set (production default)
        monkeypatch.delenv("DEV_MAIL_ECHO", raising=False)
        assert bool_env("DEV_MAIL_ECHO", False) is False


if __name__ == "__main__":
    # Run tests with: python test_env_parsing.py
    pytest.main([__file__, "-v"])
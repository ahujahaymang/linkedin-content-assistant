"""Unit tests for configuration loading and validation."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from linkedin_content_assistant.config import (
    AppConfig,
    LLMConfig,
    SafetyConfig,
    SystemConfig,
    TelegramConfig,
    load_config,
)


class TestSystemConfig:
    """Test SystemConfig validation."""

    def test_valid_environment(self):
        """Test valid environment values."""
        for env in ["development", "staging", "production"]:
            config = SystemConfig(environment=env)
            assert config.environment == env

    def test_invalid_environment(self):
        """Test invalid environment raises ValueError."""
        with pytest.raises(ValueError, match="Invalid environment"):
            SystemConfig(environment="invalid")

    def test_valid_log_level(self):
        """Test valid log level values."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = SystemConfig(log_level=level)
            assert config.log_level == level

    def test_log_level_case_insensitive(self):
        """Test log level is case insensitive."""
        config = SystemConfig(log_level="info")
        assert config.log_level == "INFO"

    def test_invalid_log_level(self):
        """Test invalid log level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid log_level"):
            SystemConfig(log_level="INVALID")


class TestLLMConfig:
    """Test LLMConfig validation."""

    def test_valid_temperature_range(self):
        """Test temperature validation for content generation."""
        # Valid range: 0.7-0.8
        config = LLMConfig(
            primary_provider="bedrock_claude",
            primary_model="test-model",
            temperature=0.75,
        )
        assert config.temperature == 0.75

    def test_temperature_below_range(self):
        """Test temperature below recommended range raises ValueError."""
        with pytest.raises(ValueError, match="outside recommended range"):
            LLMConfig(
                primary_provider="bedrock_claude",
                primary_model="test-model",
                temperature=0.5,
            )

    def test_temperature_above_range(self):
        """Test temperature above recommended range raises ValueError."""
        with pytest.raises(ValueError, match="outside recommended range"):
            LLMConfig(
                primary_provider="bedrock_claude",
                primary_model="test-model",
                temperature=0.9,
            )

    def test_invalid_provider(self):
        """Test invalid provider raises ValueError."""
        with pytest.raises(ValueError, match="Invalid primary_provider"):
            LLMConfig(
                primary_provider="invalid_provider",
                primary_model="test-model",
                temperature=0.75,
            )


class TestSafetyConfig:
    """Test SafetyConfig validation."""

    def test_default_safety_settings(self):
        """Test default safety settings are secure."""
        config = SafetyConfig()
        assert config.require_manual_posting is True
        assert config.store_linkedin_credentials is False

    def test_cannot_enable_credential_storage(self):
        """Test that credential storage cannot be enabled."""
        with pytest.raises(ValueError, match="store_linkedin_credentials must be False"):
            SafetyConfig(store_linkedin_credentials=True)

    def test_cannot_disable_manual_posting(self):
        """Test that manual posting requirement cannot be disabled."""
        with pytest.raises(ValueError, match="require_manual_posting must be True"):
            SafetyConfig(require_manual_posting=False)


class TestTelegramConfig:
    """Test TelegramConfig validation."""

    def test_valid_parse_mode(self):
        """Test valid parse mode values."""
        for mode in ["HTML", "Markdown"]:
            config = TelegramConfig(
                bot_token="test_token",
                chat_id="test_chat",
                parse_mode=mode,
            )
            assert config.parse_mode == mode

    def test_invalid_parse_mode(self):
        """Test invalid parse mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid parse_mode"):
            TelegramConfig(
                bot_token="test_token",
                chat_id="test_chat",
                parse_mode="INVALID",
            )

    def test_enabled_requires_credentials(self):
        """Test that enabled Telegram requires credentials."""
        with pytest.raises(ValueError, match="bot_token is not set"):
            TelegramConfig(
                enabled=True,
                bot_token="${TELEGRAM_BOT_TOKEN}",
                chat_id="test_chat",
            )

        with pytest.raises(ValueError, match="chat_id is not set"):
            TelegramConfig(
                enabled=True,
                bot_token="test_token",
                chat_id="${TELEGRAM_CHAT_ID}",
            )


class TestConfigLoading:
    """Test configuration loading from YAML."""

    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_data = {
            "system": {
                "environment": "production",
                "log_level": "INFO",
                "data_dir": "./data",
            },
            "profiles": {
                "directory": "./profiles",
                "auto_load": True,
            },
            "memory": {
                "storage_type": "json",
                "directory": "./data/memory",
                "retention_days": 90,
            },
            "scheduler": {
                "enabled": True,
                "check_interval": 60,
                "max_concurrent_jobs": 1,
            },
            "llm": {
                "primary_provider": "bedrock_claude",
                "primary_model": "anthropic.claude-3-sonnet-20240229-v1:0",
                "fallback_enabled": True,
                "temperature": 0.75,
                "max_tokens": 2000,
                "timeout": 60,
            },
            "telegram": {
                "enabled": True,
                "bot_token": "test_bot_token",
                "chat_id": "test_chat_id",
                "parse_mode": "HTML",
            },
            "feed_scanner": {
                "enabled": True,
                "max_posts_per_session": 50,
                "delay_between_reads": 3,
                "scan_interval_hours": 6,
            },
            "web_scraper": {
                "enabled": True,
                "sources": ["https://news.ycombinator.com"],
                "request_timeout": 30,
                "rate_limit_delay": 5,
            },
            "trend_monitor": {
                "enabled": True,
                "aggregation_window_hours": 24,
                "min_frequency": 2,
                "max_trends": 10,
            },
            "safety": {
                "max_posts_per_day": 1,
                "require_manual_posting": True,
                "store_linkedin_credentials": False,
            },
            "monitoring": {
                "health_check_enabled": True,
                "daily_summary_time": "23:59",
            },
            "logging": {
                "log_file": "./logs/test.log",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = load_config(config_path)
            assert config.system.environment == "production"
            assert config.llm.temperature == 0.75
            assert config.telegram.bot_token == "test_bot_token"
            assert config.safety.require_manual_posting is True
        finally:
            os.unlink(config_path)

    def test_load_config_with_env_substitution(self):
        """Test environment variable substitution in config."""
        os.environ["TEST_BOT_TOKEN"] = "my_secret_token"
        os.environ["TEST_CHAT_ID"] = "12345"

        config_data = {
            "system": {"environment": "production"},
            "llm": {
                "primary_provider": "bedrock_claude",
                "primary_model": "test-model",
                "temperature": 0.75,
            },
            "telegram": {
                "enabled": True,
                "bot_token": "${TEST_BOT_TOKEN}",
                "chat_id": "${TEST_CHAT_ID}",
            },
            "safety": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = load_config(config_path)
            assert config.telegram.bot_token == "my_secret_token"
            assert config.telegram.chat_id == "12345"
        finally:
            os.unlink(config_path)
            del os.environ["TEST_BOT_TOKEN"]
            del os.environ["TEST_CHAT_ID"]

    def test_load_config_file_not_found(self):
        """Test loading non-existent config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name

        try:
            with pytest.raises(ValueError, match="Failed to parse YAML"):
                load_config(config_path)
        finally:
            os.unlink(config_path)

    def test_load_empty_config(self):
        """Test loading empty config file raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            config_path = f.name

        try:
            with pytest.raises(ValueError, match="Configuration file is empty"):
                load_config(config_path)
        finally:
            os.unlink(config_path)

    def test_validation_failure(self):
        """Test configuration validation failure."""
        config_data = {
            "system": {"environment": "invalid_env"},  # Invalid environment
            "llm": {
                "primary_provider": "bedrock_claude",
                "primary_model": "test-model",
                "temperature": 0.75,
            },
            "telegram": {
                "bot_token": "test",
                "chat_id": "test",
            },
            "safety": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                load_config(config_path)
        finally:
            os.unlink(config_path)


class TestAppConfig:
    """Test AppConfig cross-field validation."""

    def test_creates_missing_directories(self):
        """Test that missing directories are created during validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            profiles_dir = Path(tmpdir) / "profiles"
            memory_dir = Path(tmpdir) / "memory"
            log_dir = Path(tmpdir) / "logs"

            config = AppConfig(
                system=SystemConfig(data_dir=str(data_dir)),
                profiles={"directory": str(profiles_dir)},
                memory={"directory": str(memory_dir)},
                llm={
                    "primary_provider": "bedrock_claude",
                    "primary_model": "test-model",
                    "temperature": 0.75,
                },
                telegram={
                    "bot_token": "test",
                    "chat_id": "test",
                },
                logging={"log_file": str(log_dir / "test.log")},
            )

            assert data_dir.exists()
            assert profiles_dir.exists()
            assert memory_dir.exists()
            assert log_dir.exists()

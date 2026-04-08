"""Integration test for configuration loading from example file."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from linkedin_content_assistant.config import load_config


class TestConfigIntegration:
    """Integration tests for configuration loading."""

    def test_load_example_config_with_env_vars(self):
        """Test loading the example config file with environment variables set."""
        # Set required environment variables
        os.environ["TELEGRAM_BOT_TOKEN"] = "test_bot_token_12345"
        os.environ["TELEGRAM_CHAT_ID"] = "test_chat_id_67890"

        # Copy example config to temporary location
        example_config = Path("config/config.yaml.example")
        assert example_config.exists(), "Example config file not found"

        with tempfile.TemporaryDirectory() as tmpdir:
            test_config = Path(tmpdir) / "config.yaml"
            shutil.copy(example_config, test_config)

            try:
                # Load configuration
                config = load_config(str(test_config))

                # Verify system configuration
                assert config.system.environment == "production"
                assert config.system.log_level == "INFO"
                assert config.system.data_dir == "./data"

                # Verify profiles configuration
                assert config.profiles.directory == "./profiles"
                assert config.profiles.auto_load is True

                # Verify memory configuration
                assert config.memory.storage_type == "json"
                assert config.memory.directory == "./data/memory"
                assert config.memory.retention_days == 90

                # Verify scheduler configuration
                assert config.scheduler.enabled is True
                assert config.scheduler.check_interval == 60
                assert config.scheduler.max_concurrent_jobs == 1

                # Verify LLM configuration
                assert config.llm.primary_provider == "bedrock_claude"
                assert config.llm.primary_model == "anthropic.claude-3-sonnet-20240229-v1:0"
                assert config.llm.fallback_enabled is True
                assert config.llm.temperature == 0.75
                assert 0.7 <= config.llm.temperature <= 0.8  # Verify in valid range
                assert config.llm.max_tokens == 2000
                assert config.llm.timeout == 60

                # Verify Telegram configuration with env var substitution
                assert config.telegram.enabled is True
                assert config.telegram.bot_token == "test_bot_token_12345"
                assert config.telegram.chat_id == "test_chat_id_67890"
                assert config.telegram.parse_mode == "HTML"
                assert config.telegram.retry_attempts == 3
                assert config.telegram.retry_delay == 5

                # Verify feed scanner configuration
                assert config.feed_scanner.enabled is True
                assert config.feed_scanner.max_posts_per_session == 50
                assert config.feed_scanner.delay_between_reads == 3
                assert config.feed_scanner.scan_interval_hours == 6
                assert config.feed_scanner.rate_limit_pause == 3600

                # Verify web scraper configuration
                assert config.web_scraper.enabled is True
                assert len(config.web_scraper.sources) == 2
                assert "https://news.ycombinator.com" in config.web_scraper.sources
                assert config.web_scraper.request_timeout == 30
                assert config.web_scraper.rate_limit_delay == 5
                assert config.web_scraper.respect_robots_txt is True
                assert config.web_scraper.max_retries == 3

                # Verify trend monitor configuration
                assert config.trend_monitor.enabled is True
                assert config.trend_monitor.aggregation_window_hours == 24
                assert config.trend_monitor.min_frequency == 2
                assert config.trend_monitor.max_trends == 10

                # Verify safety configuration
                assert config.safety.max_posts_per_day == 1
                assert config.safety.require_manual_posting is True
                assert config.safety.store_linkedin_credentials is False
                assert config.safety.enable_rate_limiting is True
                assert config.safety.exponential_backoff_base == 2
                assert config.safety.max_backoff_seconds == 300

                # Verify monitoring configuration
                assert config.monitoring.health_check_enabled is True
                assert config.monitoring.health_check_interval == 300
                assert config.monitoring.metrics_enabled is True
                assert config.monitoring.alert_on_critical_errors is True
                assert config.monitoring.daily_summary_enabled is True
                assert config.monitoring.daily_summary_time == "23:59"

                # Verify logging configuration
                assert config.logging.log_file == "./logs/linkedin_content_assistant.log"
                assert config.logging.max_file_size_mb == 100
                assert config.logging.backup_count == 5
                assert config.logging.include_stack_traces is True

            finally:
                # Clean up environment variables
                del os.environ["TELEGRAM_BOT_TOKEN"]
                del os.environ["TELEGRAM_CHAT_ID"]

    def test_example_config_fails_without_env_vars(self):
        """Test that example config fails validation without required env vars."""
        # Ensure env vars are not set
        if "TELEGRAM_BOT_TOKEN" in os.environ:
            del os.environ["TELEGRAM_BOT_TOKEN"]
        if "TELEGRAM_CHAT_ID" in os.environ:
            del os.environ["TELEGRAM_CHAT_ID"]

        example_config = Path("config/config.yaml.example")
        assert example_config.exists(), "Example config file not found"

        with tempfile.TemporaryDirectory() as tmpdir:
            test_config = Path(tmpdir) / "config.yaml"
            shutil.copy(example_config, test_config)

            # Should fail because Telegram credentials are not set
            with pytest.raises(ValueError, match="bot_token is not set"):
                load_config(str(test_config))

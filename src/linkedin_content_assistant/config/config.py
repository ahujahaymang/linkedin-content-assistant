"""Configuration system for LinkedIn Content Assistant.

This module provides configuration loading from YAML files and environment variables,
with comprehensive validation and fail-fast error handling.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SystemConfig(BaseModel):
    """System-wide configuration."""

    environment: str = Field(
        default="production",
        description="Environment: development, staging, or production",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )
    data_dir: str = Field(
        default="./data",
        description="Base directory for data storage",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        valid_envs = {"development", "staging", "production"}
        if v not in valid_envs:
            raise ValueError(
                f"Invalid environment '{v}'. Must be one of: {', '.join(valid_envs)}"
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level value."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(
                f"Invalid log_level '{v}'. Must be one of: {', '.join(valid_levels)}"
            )
        return v.upper()


class ProfilesConfig(BaseModel):
    """Profile management configuration."""

    directory: str = Field(
        default="./profiles",
        description="Directory containing profile YAML files",
    )
    auto_load: bool = Field(
        default=True,
        description="Automatically load all profiles on startup",
    )


class MemoryConfig(BaseModel):
    """Memory store configuration."""

    storage_type: str = Field(
        default="json",
        description="Storage backend: json, sqlite, or postgresql",
    )
    directory: str = Field(
        default="./data/memory",
        description="Directory for memory storage files",
    )
    retention_days: int = Field(
        default=90,
        ge=1,
        description="Number of days to retain post history",
    )
    backup_enabled: bool = Field(
        default=False,
        description="Enable automatic backups",
    )
    backup_interval_hours: int = Field(
        default=24,
        ge=1,
        description="Hours between automatic backups",
    )

    @field_validator("storage_type")
    @classmethod
    def validate_storage_type(cls, v: str) -> str:
        """Validate storage type."""
        valid_types = {"json", "sqlite", "postgresql"}
        if v not in valid_types:
            raise ValueError(
                f"Invalid storage_type '{v}'. Must be one of: {', '.join(valid_types)}"
            )
        return v


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable the scheduler",
    )
    check_interval: int = Field(
        default=60,
        ge=1,
        description="Seconds between scheduler checks",
    )
    max_concurrent_jobs: int = Field(
        default=1,
        ge=1,
        description="Maximum concurrent generation jobs",
    )


class LLMProviderConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = Field(
        description="Provider name: bedrock_claude, openai, or anthropic",
    )
    model: str = Field(
        description="Model identifier",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for the provider (if required)",
    )
    region: Optional[str] = Field(
        default=None,
        description="AWS region for Bedrock (if applicable)",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider name."""
        valid_providers = {"bedrock_claude", "openai", "anthropic"}
        if v not in valid_providers:
            raise ValueError(
                f"Invalid provider '{v}'. Must be one of: {', '.join(valid_providers)}"
            )
        return v


class LLMConfig(BaseModel):
    """LLM configuration."""

    primary_provider: str = Field(
        description="Primary LLM provider",
    )
    primary_model: str = Field(
        description="Primary model identifier",
    )
    fallback_enabled: bool = Field(
        default=True,
        description="Enable fallback to secondary providers",
    )
    fallback_providers: List[LLMProviderConfig] = Field(
        default_factory=list,
        description="Fallback provider configurations",
    )
    temperature: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Temperature for content generation",
    )
    max_tokens: int = Field(
        default=2000,
        ge=1,
        description="Maximum tokens per request",
    )
    timeout: int = Field(
        default=60,
        ge=1,
        description="Request timeout in seconds",
    )

    @field_validator("primary_provider")
    @classmethod
    def validate_primary_provider(cls, v: str) -> str:
        """Validate primary provider."""
        valid_providers = {"bedrock_claude", "openai", "anthropic"}
        if v not in valid_providers:
            raise ValueError(
                f"Invalid primary_provider '{v}'. Must be one of: {', '.join(valid_providers)}"
            )
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is in creative range for content generation."""
        if not (0.7 <= v <= 0.8):
            raise ValueError(
                f"Temperature {v} is outside recommended range [0.7, 0.8] for content generation"
            )
        return v


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable Telegram delivery",
    )
    bot_token: str = Field(
        description="Telegram bot token",
    )
    chat_id: str = Field(
        description="Telegram chat ID for delivery",
    )
    parse_mode: str = Field(
        default="HTML",
        description="Message parse mode: HTML or Markdown",
    )
    retry_attempts: int = Field(
        default=3,
        ge=1,
        description="Number of retry attempts for failed deliveries",
    )
    retry_delay: int = Field(
        default=5,
        ge=1,
        description="Initial retry delay in seconds (exponential backoff)",
    )

    @field_validator("parse_mode")
    @classmethod
    def validate_parse_mode(cls, v: str) -> str:
        """Validate parse mode."""
        valid_modes = {"HTML", "Markdown"}
        if v not in valid_modes:
            raise ValueError(
                f"Invalid parse_mode '{v}'. Must be one of: {', '.join(valid_modes)}"
            )
        return v

    @model_validator(mode="after")
    def validate_credentials(self) -> "TelegramConfig":
        """Validate Telegram credentials are provided if enabled."""
        if self.enabled:
            if not self.bot_token or self.bot_token.startswith("${"):
                raise ValueError(
                    "Telegram is enabled but bot_token is not set. "
                    "Set TELEGRAM_BOT_TOKEN environment variable."
                )
            if not self.chat_id or self.chat_id.startswith("${"):
                raise ValueError(
                    "Telegram is enabled but chat_id is not set. "
                    "Set TELEGRAM_CHAT_ID environment variable."
                )
        return self


class FeedScannerConfig(BaseModel):
    """LinkedIn feed scanner configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable feed scanning",
    )
    max_posts_per_session: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum posts to scan per session",
    )
    delay_between_reads: int = Field(
        default=3,
        ge=1,
        description="Seconds between reading posts (human-like behavior)",
    )
    scan_interval_hours: int = Field(
        default=6,
        ge=1,
        description="Hours between feed scans",
    )
    rate_limit_pause: int = Field(
        default=3600,
        ge=3600,
        description="Seconds to pause if rate limited (minimum 1 hour)",
    )


class WebScraperConfig(BaseModel):
    """Web scraper configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable web scraping",
    )
    sources: List[str] = Field(
        default_factory=list,
        description="List of web sources to scrape",
    )
    request_timeout: int = Field(
        default=30,
        ge=1,
        description="Request timeout in seconds",
    )
    rate_limit_delay: int = Field(
        default=5,
        ge=1,
        description="Minimum delay between requests in seconds",
    )
    respect_robots_txt: bool = Field(
        default=True,
        description="Respect robots.txt directives",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        description="Maximum retry attempts",
    )
    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; LinkedInContentAssistant/0.1)",
        description="User agent string",
    )

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: List[str]) -> List[str]:
        """Validate source URLs."""
        if not v:
            return v
        for source in v:
            if not source.startswith(("http://", "https://")):
                raise ValueError(f"Invalid source URL '{source}'. Must start with http:// or https://")
        return v


class TrendMonitorConfig(BaseModel):
    """Trend monitoring configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable trend monitoring",
    )
    aggregation_window_hours: int = Field(
        default=24,
        ge=1,
        description="Hours to aggregate trends over",
    )
    min_frequency: int = Field(
        default=2,
        ge=1,
        description="Minimum occurrences to be considered trending",
    )
    max_trends: int = Field(
        default=10,
        ge=1,
        description="Maximum trends to track",
    )


class SafetyConfig(BaseModel):
    """Safety and rate limiting configuration."""

    max_posts_per_day: int = Field(
        default=1,
        ge=1,
        description="Maximum posts per day per profile",
    )
    require_manual_posting: bool = Field(
        default=True,
        description="Require manual posting (no automation)",
    )
    store_linkedin_credentials: bool = Field(
        default=False,
        description="Store LinkedIn credentials (should be False)",
    )
    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable rate limiting",
    )
    exponential_backoff_base: int = Field(
        default=2,
        ge=2,
        description="Base for exponential backoff",
    )
    max_backoff_seconds: int = Field(
        default=300,
        ge=1,
        description="Maximum backoff time in seconds",
    )

    @model_validator(mode="after")
    def validate_safety_settings(self) -> "SafetyConfig":
        """Validate safety settings."""
        if self.store_linkedin_credentials:
            raise ValueError(
                "store_linkedin_credentials must be False for safety. "
                "This system does not support storing LinkedIn credentials."
            )
        if not self.require_manual_posting:
            raise ValueError(
                "require_manual_posting must be True for safety. "
                "This system requires manual posting to avoid automation risks."
            )
        return self


class MonitoringConfig(BaseModel):
    """Monitoring and health check configuration."""

    health_check_enabled: bool = Field(
        default=True,
        description="Enable health checks",
    )
    health_check_interval: int = Field(
        default=300,
        ge=1,
        description="Seconds between health checks",
    )
    metrics_enabled: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
    alert_on_critical_errors: bool = Field(
        default=True,
        description="Send alerts for critical errors",
    )
    daily_summary_enabled: bool = Field(
        default=True,
        description="Generate daily summary reports",
    )
    daily_summary_time: str = Field(
        default="23:59",
        description="Time to generate daily summary (HH:MM)",
    )

    @field_validator("daily_summary_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format."""
        if not re.match(r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", v):
            raise ValueError(
                f"Invalid time format '{v}'. Must be HH:MM (24-hour format)"
            )
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""

    log_file: str = Field(
        default="./logs/linkedin_content_assistant.log",
        description="Path to log file",
    )
    max_file_size_mb: int = Field(
        default=100,
        ge=1,
        description="Maximum log file size in MB",
    )
    backup_count: int = Field(
        default=5,
        ge=1,
        description="Number of backup log files to keep",
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    include_stack_traces: bool = Field(
        default=True,
        description="Include stack traces in error logs",
    )


class AppConfig(BaseSettings):
    """Main application configuration.
    
    Loads configuration from YAML file and environment variables.
    Environment variables override YAML values.
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    system: SystemConfig = Field(default_factory=SystemConfig)
    profiles: ProfilesConfig = Field(default_factory=ProfilesConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    llm: LLMConfig
    telegram: TelegramConfig
    feed_scanner: FeedScannerConfig = Field(default_factory=FeedScannerConfig)
    web_scraper: WebScraperConfig = Field(default_factory=WebScraperConfig)
    trend_monitor: TrendMonitorConfig = Field(default_factory=TrendMonitorConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @model_validator(mode="after")
    def validate_config(self) -> "AppConfig":
        """Perform cross-field validation."""
        # Validate directories exist or can be created
        dirs_to_check = [
            self.system.data_dir,
            self.profiles.directory,
            self.memory.directory,
        ]
        
        for dir_path in dirs_to_check:
            path = Path(dir_path)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    raise ValueError(
                        f"Cannot create directory '{dir_path}': {e}"
                    )
        
        # Validate log directory
        log_path = Path(self.logging.log_file)
        log_dir = log_path.parent
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(
                    f"Cannot create log directory '{log_dir}': {e}"
                )
        
        return self


def _substitute_env_vars(data: Any) -> Any:
    """Recursively substitute environment variables in configuration data.
    
    Supports ${VAR_NAME} syntax in strings.
    """
    if isinstance(data, dict):
        return {key: _substitute_env_vars(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_substitute_env_vars(item) for item in data]
    elif isinstance(data, str):
        # Match ${VAR_NAME} pattern
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, data)
        result = data
        for var_name in matches:
            env_value = os.environ.get(var_name)
            if env_value is None:
                # Leave as-is if environment variable not set
                continue
            result = result.replace(f"${{{var_name}}}", env_value)
        return result
    else:
        return data


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from YAML file and environment variables.
    
    Args:
        config_path: Path to YAML configuration file. If None, looks for:
                    - ./config.yaml
                    - ./config/config.yaml
                    - ~/.linkedin_content_assistant/config.yaml
    
    Returns:
        AppConfig: Validated configuration object
    
    Raises:
        FileNotFoundError: If no configuration file is found
        ValueError: If configuration is invalid
        yaml.YAMLError: If YAML parsing fails
    """
    # Load environment variables from .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
    
    # Determine config file path
    if config_path is None:
        search_paths = [
            Path("./config.yaml"),
            Path("./config/config.yaml"),
            Path.home() / ".linkedin_content_assistant" / "config.yaml",
        ]
        
        config_file = None
        for path in search_paths:
            if path.exists():
                config_file = path
                break
        
        if config_file is None:
            raise FileNotFoundError(
                f"Configuration file not found. Searched: {', '.join(str(p) for p in search_paths)}"
            )
    else:
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    # Load YAML file
    try:
        with open(config_file, "r") as f:
            yaml_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML configuration: {e}")
    except Exception as e:
        raise ValueError(f"Failed to read configuration file: {e}")
    
    if not yaml_data:
        raise ValueError("Configuration file is empty")
    
    # Substitute environment variables
    yaml_data = _substitute_env_vars(yaml_data)
    
    # Create and validate configuration
    try:
        config = AppConfig(**yaml_data)
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")
    
    return config

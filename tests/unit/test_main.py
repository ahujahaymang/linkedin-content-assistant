"""Unit tests for main application entry point."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from linkedin_content_assistant.main import (
    setup_logging,
    initialize_components,
    _create_llm_config
)
from linkedin_content_assistant.config.config import AppConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=AppConfig)
    
    # System config
    config.system = Mock()
    config.system.environment = "development"
    config.system.log_level = "INFO"
    config.system.data_dir = "./data"
    
    # Profiles config
    config.profiles = Mock()
    config.profiles.directory = "./profiles"
    config.profiles.auto_load = True
    
    # Memory config
    config.memory = Mock()
    config.memory.storage_type = "json"
    config.memory.directory = "./data/memory"
    config.memory.retention_days = 90
    
    # Scheduler config
    config.scheduler = Mock()
    config.scheduler.enabled = True
    config.scheduler.check_interval = 60
    config.scheduler.max_concurrent_jobs = 1
    
    # LLM config
    config.llm = Mock()
    config.llm.primary_provider = "bedrock_claude"
    config.llm.primary_model = "anthropic.claude-3-sonnet-20240229-v1:0"
    config.llm.fallback_enabled = True
    config.llm.fallback_providers = []
    config.llm.temperature = 0.75
    config.llm.max_tokens = 2000
    config.llm.timeout = 60
    
    # Logging config
    config.logging = Mock()
    config.logging.log_file = "./logs/test.log"
    config.logging.max_file_size_mb = 100
    config.logging.backup_count = 5
    config.logging.format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    config.logging.include_stack_traces = True
    
    return config


def test_create_llm_config(mock_config):
    """Test LLM config creation from AppConfig."""
    llm_config = _create_llm_config(mock_config)
    
    assert llm_config is not None
    assert llm_config.primary_provider.model == "anthropic.claude-3-sonnet-20240229-v1:0"
    assert llm_config.enable_fallback == True
    assert llm_config.primary_provider.temperature == 0.75
    assert llm_config.primary_provider.max_tokens == 2000
    assert llm_config.primary_provider.timeout == 60


def test_setup_logging_creates_log_directory(mock_config, tmp_path):
    """Test that setup_logging creates log directory if it doesn't exist."""
    log_file = tmp_path / "logs" / "test.log"
    mock_config.logging.log_file = str(log_file)
    
    setup_logging(mock_config)
    
    assert log_file.parent.exists()


def test_setup_logging_configures_handlers(mock_config, tmp_path):
    """Test that setup_logging configures console and file handlers."""
    log_file = tmp_path / "logs" / "test.log"
    mock_config.logging.log_file = str(log_file)
    
    setup_logging(mock_config)
    
    import logging
    root_logger = logging.getLogger()
    
    # Should have at least 2 handlers (console + file)
    assert len(root_logger.handlers) >= 2


@patch('linkedin_content_assistant.main.ProfileManager')
@patch('linkedin_content_assistant.main.create_memory_store')
@patch('linkedin_content_assistant.main.LLMFactory')
@patch('linkedin_content_assistant.main.ContentStrategyAgent')
@patch('linkedin_content_assistant.main.DraftingAgent')
@patch('linkedin_content_assistant.main.ContentOrchestrator')
def test_initialize_components_success(
    mock_orchestrator_class,
    mock_drafting_class,
    mock_strategy_class,
    mock_llm_factory_class,
    mock_memory_store_func,
    mock_profile_manager_class,
    mock_config
):
    """Test successful component initialization."""
    # Setup mocks
    mock_profile_manager = Mock()
    mock_profile_manager.list_profiles.return_value = ["test-profile"]
    mock_profile_manager_class.return_value = mock_profile_manager
    
    mock_memory_store = Mock()
    mock_memory_store_func.return_value = mock_memory_store
    
    mock_llm_factory = Mock()
    mock_llm_factory.health_check.return_value = {"provider1": True}
    mock_llm_factory_class.return_value = mock_llm_factory
    
    mock_strategy_agent = Mock()
    mock_strategy_class.return_value = mock_strategy_agent
    
    mock_drafting_agent = Mock()
    mock_drafting_class.return_value = mock_drafting_agent
    
    mock_orchestrator = Mock()
    mock_orchestrator_class.return_value = mock_orchestrator
    
    # Call initialize_components
    profile_manager, memory_store, llm_factory, orchestrator = initialize_components(mock_config)
    
    # Verify components were created
    assert profile_manager == mock_profile_manager
    assert memory_store == mock_memory_store
    assert llm_factory == mock_llm_factory
    assert orchestrator == mock_orchestrator
    
    # Verify ProfileManager was initialized with correct directory
    mock_profile_manager_class.assert_called_once_with(profiles_dir=mock_config.profiles.directory)
    
    # Verify MemoryStore was created with correct parameters
    mock_memory_store_func.assert_called_once()
    
    # Verify LLMFactory health check was called
    mock_llm_factory.health_check.assert_called_once()


@patch('linkedin_content_assistant.main.ProfileManager')
@patch('linkedin_content_assistant.main.create_memory_store')
@patch('linkedin_content_assistant.main.LLMFactory')
def test_initialize_components_fails_with_no_healthy_providers(
    mock_llm_factory_class,
    mock_memory_store_func,
    mock_profile_manager_class,
    mock_config
):
    """Test that initialization fails when no LLM providers are healthy."""
    # Setup mocks
    mock_profile_manager = Mock()
    mock_profile_manager.list_profiles.return_value = []
    mock_profile_manager_class.return_value = mock_profile_manager
    
    mock_memory_store = Mock()
    mock_memory_store_func.return_value = mock_memory_store
    
    mock_llm_factory = Mock()
    mock_llm_factory.health_check.return_value = {"provider1": False}  # No healthy providers
    mock_llm_factory_class.return_value = mock_llm_factory
    
    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="No healthy LLM providers available"):
        initialize_components(mock_config)


def test_main_module_can_be_imported():
    """Test that the main module can be imported without errors."""
    import linkedin_content_assistant.main
    
    assert hasattr(linkedin_content_assistant.main, 'main')
    assert hasattr(linkedin_content_assistant.main, 'setup_logging')
    assert hasattr(linkedin_content_assistant.main, 'initialize_components')
    assert hasattr(linkedin_content_assistant.main, 'generate_once')
    assert hasattr(linkedin_content_assistant.main, 'health_check')

"""Main application entry point for LinkedIn Content Assistant.

This module provides the main entry point for the LinkedIn Content Assistant MVP.
It handles:
- Configuration loading and validation
- Component initialization (ProfileManager, MemoryStore, LLMFactory, Agents, Orchestrator)
- Logging setup
- CLI commands (start, generate-once, health-check)
- Graceful shutdown handling
"""

import argparse
import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config.config import load_config, AppConfig
from .profiles.manager import ProfileManager
from .memory.store import create_memory_store
from .llm.factory import LLMFactory
from .llm.config import LLMConfig, ProviderConfig
from .llm.base import LLMProvider
from .agents.content_strategy import ContentStrategyAgent
from .agents.drafting import DraftingAgent
from .orchestration.orchestrator import ContentOrchestrator


# Global shutdown flag
shutdown_requested = False


def setup_logging(config: AppConfig) -> None:
    """Set up logging based on configuration.
    
    Args:
        config: Application configuration
    """
    # Create log directory if it doesn't exist
    log_file = Path(config.logging.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    log_level = getattr(logging, config.system.log_level.upper())
    
    # Create formatters
    formatter = logging.Formatter(config.logging.format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # File handler with rotation
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        config.logging.log_file,
        maxBytes=config.logging.max_file_size_mb * 1024 * 1024,
        backupCount=config.logging.backup_count
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("LinkedIn Content Assistant Starting")
    logger.info(f"Environment: {config.system.environment}")
    logger.info(f"Log Level: {config.system.log_level}")
    logger.info(f"Log File: {config.logging.log_file}")
    logger.info("=" * 80)


async def initialize_components(config: AppConfig) -> tuple:
    """Initialize all application components.
    
    Args:
        config: Application configuration
        
    Returns:
        Tuple of (profile_manager, memory_store, llm_factory, orchestrator)
        
    Raises:
        Exception: If component initialization fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize ProfileManager
        logger.info("Initializing ProfileManager...")
        profile_manager = ProfileManager(profiles_dir=config.profiles.directory)
        profiles = profile_manager.list_profiles()
        logger.info(f"ProfileManager initialized with {len(profiles)} profile(s): {', '.join(profiles) if profiles else 'none'}")
        
        # Initialize MemoryStore
        logger.info("Initializing MemoryStore...")
        # Map config storage_type to actual store implementation
        store_type_map = {
            "json": "in_memory",  # JSON is implemented as in-memory with persistence
            "sqlite": "in_memory",  # Future: will be separate implementation
            "postgresql": "in_memory"  # Future: will be separate implementation
        }
        actual_store_type = store_type_map.get(config.memory.storage_type, "in_memory")
        
        memory_store = create_memory_store(
            store_type=actual_store_type,
            persistence_file=str(Path(config.memory.directory) / "events.json")
        )
        logger.info(f"MemoryStore initialized (type: {config.memory.storage_type})")
        
        # Initialize LLMFactory
        logger.info("Initializing LLMFactory...")
        llm_config = _create_llm_config(config)
        llm_factory = LLMFactory(llm_config)
        
        # Verify LLM health
        health_status = llm_factory.health_check()
        healthy_providers = [k for k, v in health_status.items() if v]
        if not healthy_providers:
            raise RuntimeError("No healthy LLM providers available")
        logger.info(f"LLMFactory initialized with {len(healthy_providers)} healthy provider(s)")
        
        # Initialize Agents
        logger.info("Initializing Content Agents...")
        content_strategy_agent = ContentStrategyAgent(llm_factory)
        drafting_agent = DraftingAgent(llm_factory)
        logger.info("Content Agents initialized")
        
        # Initialize Telegram Bot (if enabled)
        telegram_bot = None
        try:
            logger.info(f"Checking Telegram configuration: enabled={config.telegram.enabled}")
            if config.telegram.enabled:
                logger.info("Initializing Telegram Bot...")
                from linkedin_content_assistant.delivery.telegram_bot import TelegramBot
                telegram_bot = TelegramBot(config.telegram)
                # Connect to Telegram
                try:
                    await telegram_bot.connect()
                    logger.info("Telegram Bot connected successfully")
                except Exception as e:
                    logger.warning(f"Failed to connect Telegram Bot: {e}", exc_info=True)
                    telegram_bot = None
            else:
                logger.info("Telegram delivery disabled in configuration")
        except Exception as e:
            logger.error(f"Error during Telegram bot initialization: {e}", exc_info=True)
            telegram_bot = None
        
        # Initialize ContentOrchestrator
        logger.info("Initializing ContentOrchestrator...")
        orchestrator = ContentOrchestrator(
            profile_manager=profile_manager,
            memory_store=memory_store,
            content_strategy_agent=content_strategy_agent,
            drafting_agent=drafting_agent,
            trend_monitor=None,  # Stub for MVP
            telegram_bot=telegram_bot
        )
        logger.info("ContentOrchestrator initialized")
        
        logger.info("All components initialized successfully")
        return profile_manager, memory_store, llm_factory, orchestrator
        
    except Exception as e:
        logger.error(f"Component initialization failed: {e}", exc_info=True)
        raise


def _create_llm_config(config: AppConfig) -> LLMConfig:
    """Create LLMConfig from AppConfig.
    
    Args:
        config: Application configuration
        
    Returns:
        LLMConfig instance
    """
    import os
    
    # Get API keys from environment
    openai_api_key = os.getenv('OPENAI_API_KEY')
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    
    # Parse primary provider
    primary_provider_type = LLMProvider(config.llm.primary_provider)
    primary_api_key = None
    primary_region = None
    
    if primary_provider_type == LLMProvider.OPENAI:
        primary_api_key = openai_api_key
    elif primary_provider_type == LLMProvider.ANTHROPIC:
        primary_api_key = anthropic_api_key
    elif primary_provider_type == LLMProvider.BEDROCK_CLAUDE:
        primary_region = aws_region
    
    primary_provider = ProviderConfig(
        provider=primary_provider_type,
        model=config.llm.primary_model,
        api_key=primary_api_key,
        region=primary_region,
        max_tokens=config.llm.max_tokens,
        temperature=config.llm.temperature,
        timeout=config.llm.timeout,
        retry_attempts=3,
        retry_delay=5
    )
    
    # Parse fallback providers
    fallback_providers = []
    for fb_config in config.llm.fallback_providers:
        fb_provider_type = LLMProvider(fb_config.provider)
        fb_api_key = fb_config.api_key
        fb_region = fb_config.region
        
        # Load from environment if not specified in config
        if not fb_api_key:
            if fb_provider_type == LLMProvider.OPENAI:
                fb_api_key = openai_api_key
            elif fb_provider_type == LLMProvider.ANTHROPIC:
                fb_api_key = anthropic_api_key
        
        if not fb_region and fb_provider_type == LLMProvider.BEDROCK_CLAUDE:
            fb_region = aws_region
        
        fallback_providers.append(ProviderConfig(
            provider=fb_provider_type,
            model=fb_config.model,
            api_key=fb_api_key,
            region=fb_region,
            max_tokens=config.llm.max_tokens,
            temperature=config.llm.temperature,
            timeout=config.llm.timeout,
            retry_attempts=3,
            retry_delay=5
        ))
    
    return LLMConfig(
        primary_provider=primary_provider,
        fallback_providers=fallback_providers,
        enable_fallback=config.llm.fallback_enabled,
        fallback_on_errors=["rate_limit", "authentication", "model_not_found"]
    )


async def generate_once(orchestrator: ContentOrchestrator, profile_id: str) -> None:
    """Generate a single post for testing (one-time generation).
    
    Args:
        orchestrator: Content orchestrator instance
        profile_id: Profile identifier
    """
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting one-time generation for profile: {profile_id}")
    logger.info("=" * 80)
    
    try:
        result = await orchestrator.generate_daily_post(profile_id)
        
        if result.success:
            logger.info("✓ Post generation successful!")
            logger.info(f"  Options generated: {result.options_generated}")
            logger.info(f"  Delivery status: {result.delivery_status}")
            
            if result.post_draft:
                logger.info("\n" + "=" * 80)
                logger.info("GENERATED POST:")
                logger.info("=" * 80)
                logger.info(result.post_draft.content)
                logger.info("\nHashtags: " + " ".join(result.post_draft.hashtags))
                logger.info(f"Length: {result.post_draft.estimated_length} characters")
                if result.post_draft.call_to_action:
                    logger.info(f"CTA: {result.post_draft.call_to_action}")
                logger.info("=" * 80)
        else:
            logger.error(f"✗ Post generation failed: {result.error}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"One-time generation failed: {e}", exc_info=True)
        sys.exit(1)


async def health_check(
    profile_manager: ProfileManager,
    memory_store,
    llm_factory: LLMFactory
) -> bool:
    """Perform health check on all components.
    
    Args:
        profile_manager: Profile manager instance
        memory_store: Memory store instance
        llm_factory: LLM factory instance
        
    Returns:
        True if all components are healthy, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    logger.info("Performing health check...")
    logger.info("=" * 80)
    
    all_healthy = True
    
    # Check ProfileManager
    try:
        profiles = profile_manager.list_profiles()
        logger.info(f"✓ ProfileManager: OK ({len(profiles)} profile(s))")
    except Exception as e:
        logger.error(f"✗ ProfileManager: FAILED - {e}")
        all_healthy = False
    
    # Check MemoryStore
    try:
        # Try to query events
        test_events = memory_store.get_events(
            profile_id="test",
            event_type="test",
            limit=1
        )
        logger.info("✓ MemoryStore: OK")
    except Exception as e:
        logger.error(f"✗ MemoryStore: FAILED - {e}")
        all_healthy = False
    
    # Check LLMFactory
    try:
        health_status = llm_factory.health_check()
        healthy_count = sum(1 for v in health_status.values() if v)
        total_count = len(health_status)
        
        if healthy_count > 0:
            logger.info(f"✓ LLMFactory: OK ({healthy_count}/{total_count} provider(s) healthy)")
            for provider, is_healthy in health_status.items():
                status = "✓" if is_healthy else "✗"
                logger.info(f"  {status} {provider}")
        else:
            logger.error("✗ LLMFactory: FAILED - No healthy providers")
            all_healthy = False
    except Exception as e:
        logger.error(f"✗ LLMFactory: FAILED - {e}")
        all_healthy = False
    
    logger.info("=" * 80)
    
    if all_healthy:
        logger.info("Health check: ALL SYSTEMS OPERATIONAL")
    else:
        logger.error("Health check: SOME SYSTEMS FAILED")
    
    return all_healthy


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger = logging.getLogger(__name__)
    
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
    shutdown_requested = True


async def start_scheduler(
    orchestrator: ContentOrchestrator,
    profile_manager: ProfileManager,
    config: AppConfig
) -> None:
    """Start the scheduler for daily content generation.
    
    Args:
        orchestrator: Content orchestrator instance
        profile_manager: Profile manager instance
        config: Application configuration
    """
    logger = logging.getLogger(__name__)
    
    if not config.scheduler.enabled:
        logger.warning("Scheduler is disabled in configuration")
        return
    
    logger.info("Starting scheduler...")
    logger.info(f"Check interval: {config.scheduler.check_interval} seconds")
    logger.info(f"Max concurrent jobs: {config.scheduler.max_concurrent_jobs}")
    
    # Get all enabled profiles
    profiles = profile_manager.list_profiles()
    if not profiles:
        logger.warning("No profiles found - scheduler will wait for profiles to be added")
    else:
        logger.info(f"Monitoring {len(profiles)} profile(s): {', '.join(profiles)}")
    
    logger.info("Scheduler started. Press Ctrl+C to stop.")
    logger.info("=" * 80)
    
    # Main scheduler loop
    while not shutdown_requested:
        try:
            # Refresh profile list
            profiles = profile_manager.list_profiles()
            
            # For MVP, we'll just log that we're checking
            # Full scheduler implementation will be in Task 11
            logger.debug(f"Scheduler check: {len(profiles)} profile(s) active")
            
            # Sleep for check interval
            await asyncio.sleep(config.scheduler.check_interval)
            
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
            await asyncio.sleep(config.scheduler.check_interval)
    
    logger.info("Scheduler stopped")


async def async_main(args: argparse.Namespace) -> int:
    """Async main function.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger = logging.getLogger(__name__)
    orchestrator = None
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config(args.config)
        logger.info("Configuration loaded successfully")
        
        # Initialize components
        profile_manager, memory_store, llm_factory, orchestrator = await initialize_components(config)
        
        # Execute command
        if args.command == "start":
            # Start scheduler mode
            await start_scheduler(orchestrator, profile_manager, config)
            return 0
            
        elif args.command == "generate-once":
            # One-time generation for testing
            if not args.profile:
                logger.error("--profile is required for generate-once command")
                return 1
            
            await generate_once(orchestrator, args.profile)
            return 0
            
        elif args.command == "health-check":
            # Health check
            is_healthy = await health_check(profile_manager, memory_store, llm_factory)
            return 0 if is_healthy else 1
            
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        return 1
    finally:
        # Cleanup telegram bot connection
        if orchestrator and orchestrator.telegram_bot:
            try:
                await orchestrator.telegram_bot.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting telegram bot: {e}")


def main() -> int:
    """Main entry point for the application.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="LinkedIn Content Assistant - AI-powered content generation for LinkedIn",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  start           Start the application in scheduler mode (continuous operation)
  generate-once   Generate a single post for testing (requires --profile)
  health-check    Check health of all components

Examples:
  # Start the application
  python3 -m linkedin_content_assistant.main start

  # Generate a single post for testing
  python3 -m linkedin_content_assistant.main generate-once --profile my-profile

  # Check system health
  python3 -m linkedin_content_assistant.main health-check

  # Use custom config file
  python3 -m linkedin_content_assistant.main start --config /path/to/config.yaml
        """
    )
    
    parser.add_argument(
        "command",
        choices=["start", "generate-once", "health-check"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file (default: searches standard locations)"
    )
    
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Profile ID (required for generate-once command)"
    )
    
    args = parser.parse_args()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize logging early (before config load) with basic setup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        # Load config first to set up proper logging
        config = load_config(args.config)
        
        # Set up proper logging based on config
        setup_logging(config)
        
        # Run async main
        exit_code = asyncio.run(async_main(args))
        return exit_code
        
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("\nPlease create a configuration file. See config/config.yaml.example for reference.", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"ERROR: Configuration validation failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        logging.getLogger(__name__).error("Fatal error", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

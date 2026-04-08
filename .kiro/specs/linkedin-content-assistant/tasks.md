# Implementation Plan: LinkedIn Content Assistant

## Overview

This implementation plan builds the LinkedIn Content Assistant, a safe content generation system that creates authentic LinkedIn posts and delivers them via Telegram for manual posting. The system leverages proven components from AIManager/linkedin_ai_manager while adding new capabilities for style learning, web scraping, and simplified daily content generation.

The implementation follows a component-by-component approach, starting with project setup and component reuse, then building new components, and finally integrating everything into a cohesive system. Each task includes property-based tests to validate correctness properties from the design document.

## Tasks

- [x] 1. Project setup and infrastructure
  - Create Python project structure in PersonalPOC/linkedInblogger/
  - Set up virtual environment and install dependencies (pydantic, aiohttp, python-telegram-bot, boto3, openai, anthropic, beautifulsoup4, pyyaml, pytest, hypothesis)
  - Create directory structure: src/, tests/, profiles/, data/memory/, config/
  - Set up pytest configuration with hypothesis integration
  - Create .env.example file with required environment variables
  - Create requirements.txt with all dependencies
  - _Requirements: 15.1-15.7_

- [ ] 2. Copy and adapt reusable components from AIManager
  - [x] 2.1 Copy Profile Store components
    - Copy AIManager/linkedin_ai_manager/profiles/ to src/linkedin_content_assistant/profiles/
    - Verify ProfileConfig, IdentityConfig, BehaviorConfig models are intact
    - Test profile YAML serialization/deserialization
    - _Requirements: 1.1, 1.4, 15.1_
  
  - [x] 2.2 Write property tests for Profile Store
    - **Property 1: Profile Data Round-Trip Preservation**
    - **Validates: Requirements 1.1, 1.4**
    - **Property 2: Profile Data Validation Rejects Invalid Input**
    - **Validates: Requirements 1.2**
    - **Property 3: Profile Version Increment on Update**
    - **Validates: Requirements 1.3**
    - **Property 4: Multiple Profile Independence**
    - **Validates: Requirements 1.5**
  
  - [x] 2.3 Copy Memory Store components
    - Copy AIManager/linkedin_ai_manager/memory/ to src/linkedin_content_assistant/memory/
    - Verify MemoryStore, MemoryEvent models work correctly
    - Test event storage and querying functionality
    - _Requirements: 11.1-11.7, 15.2_
  
  - [x] 2.4 Copy LLM integration components
    - Copy AIManager/linkedin_ai_manager/llm/ to src/linkedin_content_assistant/llm/
    - Verify LLMFactory, LLMConfig, provider implementations
    - Test provider routing and fallback logic
    - _Requirements: 10.1-10.7, 15.3_
  
  - [~] 2.5 Write property tests for LLM integration
    - **Property 34: LLM Provider Fallback**
    - **Validates: Requirements 10.3**
    - **Property 35: Provider Failure Logging**
    - **Validates: Requirements 10.4**
    - **Property 36: Token Usage Tracking**
    - **Validates: Requirements 10.5**
    - **Property 37: Temperature Configuration**
    - **Validates: Requirements 10.6**
  
  - [x] 2.6 Copy Content Strategy Agent
    - Copy AIManager/linkedin_ai_manager/agents/content_strategy.py to src/linkedin_content_assistant/agents/
    - Copy base agent classes from agents/base.py
    - Verify agent execution and output validation
    - _Requirements: 9.1-9.6, 15.5_
  
  - [~] 2.7 Write property tests for Content Strategy Agent
    - **Property 30: Post Option Uniqueness**
    - **Validates: Requirements 9.2**
    - **Property 31: Best Option Selection by Score**
    - **Validates: Requirements 9.4**
    - **Property 32: All Options Storage**
    - **Validates: Requirements 9.5**
    - **Property 33: Angle Repetition Avoidance**
    - **Validates: Requirements 9.6**
  
  - [x] 2.8 Copy Drafting Agent
    - Copy AIManager/linkedin_ai_manager/agents/drafting.py to src/linkedin_content_assistant/agents/
    - Verify drafting output format and validation
    - Test style matching and formatting capabilities
    - _Requirements: 3.1-3.7, 15.5_
  
  - [~] 2.9 Write property tests for Drafting Agent
    - **Property 9: Post Length Constraint**
    - **Validates: Requirements 3.4**
    - **Property 10: Hashtag Count Constraint**
    - **Validates: Requirements 3.5**
    - **Property 12: Call-to-Action Presence**
    - **Validates: Requirements 3.7**
    - **Property 13: AI Phrase Blacklist Enforcement**
    - **Validates: Requirements 4.3**

- [~] 3. Checkpoint - Verify reused components
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Adapt Feed Scanner for read-only operation
  - [~] 4.1 Copy and modify Feed Scanner
    - Copy AIManager/linkedin_ai_manager/agents/feed_scanner.py to src/linkedin_content_assistant/agents/
    - Remove all comment generation functionality
    - Remove all write operations to LinkedIn
    - Add rate limiting (max 50 posts per session)
    - Add human-like delays between reads (3 seconds minimum)
    - Implement trending topic extraction and storage
    - _Requirements: 5.1-5.7, 15.6_
  
  - [~] 4.2 Write property tests for Feed Scanner
    - **Property 16: Feed Scanner Read-Only Constraint**
    - **Validates: Requirements 5.1, 8.1**
    - **Property 17: High-Engagement Post Identification**
    - **Validates: Requirements 5.2**
    - **Property 18: Trending Topic Storage Completeness**
    - **Validates: Requirements 5.5**
    - **Property 19: Domain Relevance Filtering**
    - **Validates: Requirements 5.6, 6.3**
    - **Property 48: Feed Scan Post Limit**
    - **Validates: Requirements 13.1**
    - **Property 49: Feed Read Delays**
    - **Validates: Requirements 13.2**
    - **Property 53: LinkedIn Rate Limit Pause**
    - **Validates: Requirements 13.7**
  
  - [~] 4.3 Write unit tests for Feed Scanner
    - Test read-only HTTP operations (mock HTTP calls)
    - Test post limit enforcement with various feed sizes
    - Test high-engagement identification with sample data
    - Test rate limit handling with simulated 429 responses
    - _Requirements: 5.1-5.7_

- [ ] 5. Build Style Learner component
  - [~] 5.1 Implement Style Learner core functionality
    - Create src/linkedin_content_assistant/style_learner/learner.py
    - Implement analyze_posts() method with LLM integration
    - Implement extract_vocabulary_patterns() for style classification
    - Implement identify_hook_patterns() for high-engagement hooks
    - Implement analyze_emoji_usage() for emoji pattern detection
    - Implement update_profile_behavior() to persist learned patterns
    - Create StyleAnalysis, VocabularyPatterns, EmojiPatterns data models
    - _Requirements: 2.1-2.6_
  
  - [~] 5.2 Write property tests for Style Learner
    - **Property 5: Style Learning Pattern Extraction**
    - **Validates: Requirements 2.1**
    - **Property 6: High-Engagement Hook Identification**
    - **Validates: Requirements 2.2**
    - **Property 7: Emoji Pattern Analysis**
    - **Validates: Requirements 2.3**
    - **Property 8: Style Pattern Persistence**
    - **Validates: Requirements 2.5**
    - **Property 14: Sentence Length Variance**
    - **Validates: Requirements 4.5**
    - **Property 15: Emoji Placement Consistency**
    - **Validates: Requirements 4.6**
  
  - [~] 5.3 Write unit tests for Style Learner
    - Test vocabulary pattern extraction with known samples
    - Test emoji frequency classification with various post sets
    - Test hook pattern identification with engagement metrics
    - Test behavior config updates with mock profile store
    - Test handling of empty or malformed posts
    - _Requirements: 2.1-2.6_

- [ ] 6. Build Web Scraper component
  - [~] 6.1 Implement Web Scraper core functionality
    - Create src/linkedin_content_assistant/web_scraper/scraper.py
    - Implement scrape_sources() with aiohttp for async requests
    - Implement extract_article_data() with BeautifulSoup parsing
    - Implement filter_by_relevance() for domain matching
    - Implement identify_cross_source_trends() for trend detection
    - Implement respect_rate_limits() with exponential backoff
    - Create ScraperConfig, NewsItem data models
    - Add robots.txt checking functionality
    - _Requirements: 6.1-6.7_
  
  - [~] 6.2 Write property tests for Web Scraper
    - **Property 20: Web Scraper Rate Limit Respect**
    - **Validates: Requirements 6.7, 10.7, 13.5**
    - **Property 21: News Item Storage with Attribution**
    - **Validates: Requirements 6.4**
    - **Property 22: Cross-Source Trend Detection**
    - **Validates: Requirements 6.5**
    - **Property 50: Robots.txt Respect**
    - **Validates: Requirements 13.3**
  
  - [~] 6.3 Write unit tests for Web Scraper
    - Test robots.txt checking with mock responses
    - Test rate limit detection and exponential backoff
    - Test article data extraction with sample HTML
    - Test cross-source trend detection with mock articles
    - Test timeout handling with slow responses
    - _Requirements: 6.1-6.7_

- [ ] 7. Build Trend Monitor component
  - [~] 7.1 Implement Trend Monitor core functionality
    - Create src/linkedin_content_assistant/trend_monitor/monitor.py
    - Implement get_trending_topics() to query memory store
    - Implement combine_sources() to merge LinkedIn and web trends
    - Implement rank_by_relevance() with scoring algorithm
    - Implement filter_by_domains() for profile-specific filtering
    - Create TrendData data model
    - _Requirements: 5.7, 6.6_
  
  - [~] 7.2 Write property tests for Trend Monitor
    - **Property 23: Trend Aggregation Completeness**
    - **Validates: Requirements 6.6**
  
  - [~] 7.3 Write unit tests for Trend Monitor
    - Test trend aggregation from multiple sources
    - Test relevance ranking with various profiles
    - Test domain filtering with specific keywords
    - Test handling of empty trend data
    - _Requirements: 5.7, 6.6_

- [~] 8. Checkpoint - Verify new components
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Adapt Telegram Bot for delivery-only mode
  - [~] 9.1 Copy and simplify Telegram Bot
    - Copy AIManager/linkedin_ai_manager/ui/telegram_bot.py to src/linkedin_content_assistant/delivery/
    - Remove approval workflow functionality
    - Simplify to delivery-only mode
    - Implement send_post_draft() with copy-paste optimized formatting
    - Implement send_alert() for error notifications
    - Implement handle_user_feedback() for /posted and /skip commands
    - Add manual posting instructions to message format
    - _Requirements: 7.1-7.7, 8.3, 15.4_
  
  - [~] 9.2 Write property tests for Telegram Bot
    - **Property 24: Telegram Message Formatting Completeness**
    - **Validates: Requirements 7.2, 7.3**
    - **Property 25: Telegram Delivery Retry Logic**
    - **Validates: Requirements 7.6**
    - **Property 26: Delivery Logging Completeness**
    - **Validates: Requirements 7.7**
    - **Property 28: Manual Posting Instructions Presence**
    - **Validates: Requirements 8.3**
  
  - [~] 9.3 Write unit tests for Telegram Bot
    - Test message formatting with various post types
    - Test retry logic with simulated failures
    - Test delivery logging with mock memory store
    - Test user feedback handling (/posted, /skip commands)
    - _Requirements: 7.1-7.7_

- [ ] 10. Build Content Orchestrator component
  - [x] 10.1 Implement Content Orchestrator core functionality
    - Create src/linkedin_content_assistant/orchestration/orchestrator.py
    - Implement generate_daily_post() workflow method
    - Implement check_generation_limit() to enforce 1 post/day
    - Implement select_best_option() for option selection logic
    - Implement deliver_to_telegram() for delivery coordination
    - Create DailyPostResult data model
    - Wire together: TrendMonitor → ContentStrategy → Drafting → Telegram
    - _Requirements: 3.1-3.7, 8.4-8.6, 13.4_
  
  - [~] 10.2 Write property tests for Content Orchestrator
    - **Property 11: Theme Repetition Avoidance**
    - **Validates: Requirements 3.6**
    - **Property 27: No LinkedIn Credential Storage**
    - **Validates: Requirements 8.2**
    - **Property 29: Draft Status Tracking**
    - **Validates: Requirements 8.5, 11.2**
    - **Property 51: Daily Post Generation Limit**
    - **Validates: Requirements 13.4**
  
  - [~] 10.3 Write unit tests for Content Orchestrator
    - Test daily generation workflow with mocked components
    - Test generation limit enforcement (1/day)
    - Test option selection logic with various scores
    - Test error recovery paths with component failures
    - _Requirements: 3.1-3.7, 8.4-8.6_

- [ ] 11. Build Daily Scheduler component
  - [~] 11.1 Adapt and implement Daily Scheduler
    - Copy AIManager/linkedin_ai_manager/scheduler/ to src/linkedin_content_assistant/scheduler/
    - Simplify to daily-only scheduling (remove comment monitoring)
    - Implement posting window support with start/end hours
    - Implement skip days functionality (weekends, holidays)
    - Enforce 1 post per day limit
    - Create SchedulerConfig data model
    - _Requirements: 3.1, 12.1-12.4, 15.7_
  
  - [~] 11.2 Write property tests for Daily Scheduler
    - **Property 43: Posting Window Configuration Support**
    - **Validates: Requirements 12.1**
    - **Property 44: Multiple Posting Windows Support**
    - **Validates: Requirements 12.3**
    - **Property 45: Skip Days Enforcement**
    - **Validates: Requirements 12.4**
  
  - [~] 11.3 Write unit tests for Daily Scheduler
    - Test posting window triggering with various times
    - Test skip days enforcement with different configurations
    - Test multiple posting windows per day
    - Test scheduler start/stop functionality
    - _Requirements: 12.1-12.4_

- [ ] 12. Build configuration management
  - [x] 12.1 Implement configuration system
    - Create src/linkedin_content_assistant/config/config.py
    - Implement configuration loading from YAML and environment variables
    - Implement configuration validation on startup
    - Create system-wide configuration data model
    - Add support for profiles, memory, scheduler, LLM, Telegram, feed scanner, web scraper sections
    - Create config.yaml.example with all configuration options
    - _Requirements: 12.5-12.7_
  
  - [~] 12.2 Write property tests for configuration
    - **Property 46: Configuration Loading**
    - **Validates: Requirements 12.5**
    - **Property 47: Configuration Validation on Startup**
    - **Validates: Requirements 12.6, 12.7**
  
  - [~] 12.3 Write unit tests for configuration
    - Test valid configuration loading from YAML
    - Test environment variable override
    - Test invalid configuration rejection
    - Test missing required fields detection
    - _Requirements: 12.5-12.7_

- [~] 13. Checkpoint - Verify orchestration and configuration
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Build monitoring and health checks
  - [~] 14.1 Implement monitoring components
    - Create src/linkedin_content_assistant/monitoring/health.py for health checks
    - Create src/linkedin_content_assistant/monitoring/logger.py for error logging
    - Create src/linkedin_content_assistant/monitoring/metrics.py for tracking
    - Implement health check endpoint reporting component status
    - Implement error logging with stack traces
    - Implement LLM token usage and cost tracking
    - Implement Telegram delivery success rate tracking
    - Implement content generation success rate tracking
    - Implement daily summary statistics logging
    - _Requirements: 14.1-14.7_
  
  - [~] 14.2 Write property tests for monitoring
    - **Property 38: Post Draft Storage Completeness**
    - **Validates: Requirements 11.1**
    - **Property 39: Engagement Metrics Storage**
    - **Validates: Requirements 11.3**
    - **Property 40: Post History Query by Criteria**
    - **Validates: Requirements 11.4**
    - **Property 41: Post History Retrieval for Repetition Avoidance**
    - **Validates: Requirements 11.6**
    - **Property 42: History Export Completeness**
    - **Validates: Requirements 11.7**
    - **Property 52: Rate Limit Logging**
    - **Validates: Requirements 13.6**
    - **Property 54: Error Logging with Stack Traces**
    - **Validates: Requirements 14.2**
    - **Property 55: LLM Token Usage Reporting**
    - **Validates: Requirements 14.3**
    - **Property 56: Telegram Delivery Success Rate Tracking**
    - **Validates: Requirements 14.4**
    - **Property 57: Critical Error Alerting**
    - **Validates: Requirements 14.5**
    - **Property 58: Content Generation Success Rate Tracking**
    - **Validates: Requirements 14.6**
    - **Property 59: Daily Summary Logging**
    - **Validates: Requirements 14.7**
  
  - [~] 14.3 Write unit tests for monitoring
    - Test health check endpoint with various component states
    - Test error logging with sample exceptions
    - Test token usage tracking with mock LLM calls
    - Test delivery success rate calculation
    - Test critical error alerting with mock Telegram
    - _Requirements: 14.1-14.7_

- [ ] 15. Build main application entry point
  - [x] 15.1 Implement main application
    - Create src/linkedin_content_assistant/main.py
    - Implement application initialization and startup
    - Wire all components together (orchestrator, scheduler, monitoring)
    - Implement graceful shutdown handling
    - Add command-line interface for manual operations
    - Add support for one-time generation (testing mode)
    - _Requirements: 12.5-12.7, 14.1_
  
  - [~] 15.2 Write integration tests for main application
    - Test full application startup and shutdown
    - Test configuration loading and validation
    - Test component initialization order
    - Test graceful error handling on startup failures
    - _Requirements: 12.5-12.7_

- [ ] 16. Build error handling and resilience
  - [~] 16.1 Implement error handling patterns
    - Create src/linkedin_content_assistant/errors/handlers.py
    - Implement circuit breaker for external services
    - Implement graceful degradation logic
    - Implement timeout configuration for all external calls
    - Add retry logic with exponential backoff for all external APIs
    - Implement error recovery workflows (LLM failure, Telegram failure, rate limits)
    - _Requirements: 10.3, 13.5-13.7_
  
  - [~] 16.2 Write unit tests for error handling
    - Test circuit breaker state transitions
    - Test graceful degradation scenarios
    - Test timeout enforcement with slow operations
    - Test retry logic with various failure patterns
    - Test error recovery workflows
    - _Requirements: 10.3, 13.5-13.7_

- [~] 17. Checkpoint - Verify complete system
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 18. Create sample profiles and documentation
  - [x] 18.1 Create sample profile configurations
    - Create profiles/example-senior-engineer.yaml with complete profile
    - Create profiles/example-tech-lead.yaml with different style
    - Document profile configuration options in profiles/README.md
    - _Requirements: 1.1-1.5_
  
  - [~] 18.2 Create user documentation
    - Create README.md with project overview and setup instructions
    - Create CONFIGURATION.md with detailed configuration guide
    - Create USAGE.md with usage examples and workflows
    - Document manual posting workflow
    - Document style learning process
    - Document troubleshooting common issues
    - _Requirements: 8.3-8.6_

- [ ] 19. Integration testing and end-to-end workflows
  - [~] 19.1 Write end-to-end integration tests
    - Test profile creation → style learning → content generation → delivery workflow
    - Test feed scanning → trend detection → content generation workflow
    - Test web scraping → trend aggregation → content generation workflow
    - Test configuration loading → scheduler start → daily generation trigger workflow
    - Test error recovery across component boundaries
    - _Requirements: 3.1-3.7, 5.1-5.7, 6.1-6.7, 7.1-7.7_
  
  - [~] 19.2 Write property-based integration tests
    - Test system behavior with randomly generated profiles
    - Test system behavior with randomly generated post history
    - Test system behavior with randomly generated trends
    - Verify all 59 correctness properties hold in integrated system
    - _Requirements: All requirements_

- [~] 20. Final checkpoint and deployment preparation
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all 59 correctness properties are tested
  - Review code quality and documentation completeness
  - Create deployment checklist

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at major milestones
- Property tests validate universal correctness properties (59 total)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- Component reuse from AIManager reduces implementation effort significantly
- Python is the implementation language (evident from design document code examples)
- All external API calls must implement rate limiting and exponential backoff
- No LinkedIn credentials should ever be stored in the system
- Manual posting workflow is enforced through Telegram delivery only

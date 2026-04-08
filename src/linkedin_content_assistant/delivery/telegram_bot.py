"""Telegram bot for LinkedIn Content Assistant delivery.

This module implements Telegram Bot API integration for delivering
post drafts to users for manual posting to LinkedIn.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp

from linkedin_content_assistant.agents.drafting import LinkedInPost
from linkedin_content_assistant.config.config import TelegramConfig

logger = logging.getLogger(__name__)


@dataclass
class FeedbackData:
    """User feedback data from Telegram."""
    
    approval_id: str
    action: str  # "posted" or "skipped"
    user_id: str
    username: str
    timestamp: str
    reason: Optional[str] = None


class TelegramBot:
    """
    Telegram Bot for delivering LinkedIn post drafts.
    
    Sends post drafts to user via Telegram with copy-paste optimized
    formatting and manual posting instructions.
    """
    
    def __init__(self, config: TelegramConfig):
        """
        Initialize Telegram bot.
        
        Args:
            config: Telegram configuration
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._connected = False
        self.logger = logging.getLogger(__name__)
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate Telegram configuration."""
        if not self.config.enabled:
            return
        
        if not self.config.bot_token:
            raise ValueError("bot_token is required for Telegram integration")
        
        if not self.config.chat_id:
            raise ValueError("chat_id is required for Telegram integration")
        
        # Validate bot token format
        if ':' not in self.config.bot_token or len(self.config.bot_token) < 20:
            raise ValueError("bot_token must be in format: 123456789:ABCdef...")
    
    @property
    def is_connected(self) -> bool:
        """Check if bot is connected."""
        return self._connected
    
    async def connect(self) -> bool:
        """
        Connect to Telegram Bot API.
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If connection fails
        """
        if not self.config.enabled:
            self.logger.info("Telegram integration disabled")
            return False
        
        try:
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Test API connection
            await self._test_api_connection()
            
            self._connected = True
            self.logger.info("Connected to Telegram Bot API")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Telegram API: {e}")
            if self.session:
                await self.session.close()
                self.session = None
            raise ConnectionError(f"Telegram connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from Telegram Bot API."""
        if self.session:
            await self.session.close()
            self.session = None
        
        self._connected = False
        self.logger.info("Disconnected from Telegram Bot API")
    
    async def send_post_draft(
        self,
        post: LinkedInPost,
        profile_id: str
    ) -> bool:
        """
        Send a post draft via Telegram.
        
        Args:
            post: The LinkedIn post to deliver
            profile_id: Profile ID for tracking
            
        Returns:
            True if message sent successfully
            
        Raises:
            RuntimeError: If bot not connected or message sending fails
        """
        if not self.is_connected:
            raise RuntimeError("Telegram bot not connected")
        
        try:
            # Format the post content message (copyable)
            post_message = self._format_post_content(post)
            
            # Format the metadata message (separate)
            metadata_message = self._format_metadata(post, profile_id)
            
            # Send post content first
            success1 = await self._send_message_with_retry(
                self.config.chat_id,
                post_message
            )
            
            if not success1:
                self.logger.error(f"Failed to send post content for profile {profile_id}")
                return False
            
            # Send metadata second
            success2 = await self._send_message_with_retry(
                self.config.chat_id,
                metadata_message
            )
            
            if success2:
                self.logger.info(f"Sent post draft for profile {profile_id}")
            else:
                self.logger.warning(f"Post sent but metadata failed for profile {profile_id}")
            
            return success1 and success2
            
        except Exception as e:
            self.logger.error(f"Error sending post draft: {e}")
            raise RuntimeError(f"Failed to send Telegram message: {e}")
    
    async def send_alert(self, message: str) -> bool:
        """
        Send an alert message via Telegram.
        
        Args:
            message: Alert message to send
            
        Returns:
            True if message sent successfully
        """
        if not self.is_connected:
            self.logger.warning("Cannot send alert: Telegram bot not connected")
            return False
        
        try:
            alert_text = f"🚨 <b>Alert</b>\n\n{message}"
            return await self._send_message_with_retry(
                self.config.chat_id,
                alert_text
            )
        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
            return False
    
    async def handle_user_feedback(self, update: Dict[str, Any]) -> Optional[FeedbackData]:
        """
        Handle incoming Telegram updates for user feedback.
        
        Args:
            update: Update payload from Telegram
            
        Returns:
            Processed feedback data or None
        """
        try:
            # Handle text message
            if "message" in update:
                return await self._handle_text_message(update["message"])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error handling Telegram feedback: {e}")
            return None
    
    def _format_post_content(self, post: LinkedInPost) -> str:
        """
        Format post content for copy-paste to LinkedIn.
        
        Args:
            post: LinkedIn post to format
            
        Returns:
            Formatted post content (copyable)
        """
        # Post content (check if hashtags are already included)
        content = post.content.strip()
        
        # Check if content already ends with hashtags
        has_hashtags_in_content = any(tag in content for tag in post.hashtags) if post.hashtags else False
        
        message = f"{content}\n\n"
        
        # Only add hashtags if they're not already in the content
        if post.hashtags and not has_hashtags_in_content:
            hashtags_str = ' '.join(post.hashtags)
            message += f"{hashtags_str}"
        
        return message.strip()
    
    def _format_metadata(self, post: LinkedInPost, profile_id: str) -> str:
        """
        Format metadata and instructions (separate message).
        
        Args:
            post: LinkedIn post
            profile_id: Profile ID
            
        Returns:
            Formatted metadata message
        """
        message = "📊 <b>Post Metadata</b>\n\n"
        
        # Extract tone from tone_analysis if available
        tone = post.tone_analysis.get("formality", "professional") if post.tone_analysis else "professional"
        message += f"• Tone: {tone.title()}\n"
        message += f"• Length: {post.estimated_length} chars\n"
        
        # Call to action if present
        if post.call_to_action:
            message += f"• CTA: {post.call_to_action}\n"
        
        # Timestamp and profile
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message += f"• Generated: {timestamp}\n"
        message += f"• Profile: {profile_id}\n"
        
        # Instructions section
        message += "\n💡 <b>Actions:</b>\n"
        message += "• Reply /posted after posting to LinkedIn\n"
        message += "• Reply /skip to skip this draft"
        
        return message
    
    async def _test_api_connection(self) -> None:
        """Test connection to Telegram Bot API."""
        url = f"https://api.telegram.org/bot{self.config.bot_token}/getMe"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                raise ConnectionError(f"API test failed: {response.status}")
            
            data = await response.json()
            if not data.get('ok'):
                raise ConnectionError(
                    f"Bot API error: {data.get('description', 'Unknown error')}"
                )
    
    async def _send_message_with_retry(
        self,
        chat_id: str,
        text: str
    ) -> bool:
        """
        Send message with exponential backoff retry.
        
        Args:
            chat_id: Chat ID to send to
            text: Message text
            
        Returns:
            True if message sent successfully
        """
        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        
        message_data = {
            "chat_id": chat_id,
            "text": self._truncate_for_telegram(text),
            "parse_mode": self.config.parse_mode
        }
        
        for attempt in range(self.config.retry_attempts):
            try:
                async with self.session.post(url, json=message_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            return True
                        else:
                            self.logger.error(
                                f"Telegram API error: {data.get('description', 'Unknown error')}"
                            )
                    else:
                        error_text = await response.text()
                        self.logger.error(
                            f"Telegram HTTP error {response.status}: {error_text}"
                        )
                
                # Exponential backoff
                if attempt < self.config.retry_attempts - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                self.logger.error(
                    f"Error sending Telegram message (attempt {attempt + 1}): {e}"
                )
                if attempt < self.config.retry_attempts - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
        
        return False
    
    async def _handle_text_message(
        self,
        message: Dict[str, Any]
    ) -> Optional[FeedbackData]:
        """Handle text message feedback."""
        text = message.get("text", "").strip().lower()
        user = message.get("from", {})
        
        # Handle /posted command
        if text == "/posted":
            return FeedbackData(
                approval_id="",  # Will be filled by orchestrator
                action="posted",
                user_id=str(user.get("id", "")),
                username=user.get("username", "Unknown"),
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Handle /skip command
        elif text == "/skip" or text.startswith("/skip "):
            reason = text[6:].strip() if len(text) > 6 else None
            return FeedbackData(
                approval_id="",
                action="skipped",
                user_id=str(user.get("id", "")),
                username=user.get("username", "Unknown"),
                timestamp=datetime.utcnow().isoformat(),
                reason=reason
            )
        
        return None
    
    def _truncate_for_telegram(self, text: str, max_length: int = 4096) -> str:
        """Truncate text to Telegram message limits."""
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length - 3] + "..."
        return truncated
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Health check results
        """
        health = {
            "telegram_connected": self.is_connected,
            "chat_id": self.config.chat_id if self.config.enabled else None,
            "enabled": self.config.enabled
        }
        
        # Test API if connected
        if self.is_connected:
            try:
                await self._test_api_connection()
                health["api_test"] = "passed"
            except Exception as e:
                health["api_test"] = f"failed: {e}"
        
        return health

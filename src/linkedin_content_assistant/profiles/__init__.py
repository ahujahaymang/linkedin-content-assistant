"""Profile management module."""

from .manager import ProfileManager
from .models import (
    ProfileConfig,
    IdentityConfig,
    BehaviorConfig,
    ProfileValidationError,
    SeniorityLevel,
    PostingWindow
)
from .multi_profile_manager import MultiProfileManager, ProfileIsolationError

__all__ = [
    'ProfileManager',
    'ProfileConfig', 
    'IdentityConfig',
    'BehaviorConfig',
    'ProfileValidationError',
    'SeniorityLevel',
    'PostingWindow',
    'MultiProfileManager',
    'ProfileIsolationError'
]

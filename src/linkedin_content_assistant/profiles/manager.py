"""Profile configuration manager with versioning and rollback support."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import ValidationError

from .models import ProfileConfig, ProfileValidationError


class ProfileManager:
    """Manages profile configurations with versioning and rollback capabilities."""
    
    def __init__(self, profiles_dir: str = "./profiles"):
        """Initialize profile manager with profiles directory."""
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        self.active_dir = self.profiles_dir / "active"
        self.versions_dir = self.profiles_dir / "versions"
        self.backups_dir = self.profiles_dir / "backups"
        
        for directory in [self.active_dir, self.versions_dir, self.backups_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _get_profile_path(self, profile_id: str) -> Path:
        """Get the path to the active profile file."""
        return self.active_dir / f"{profile_id}.yaml"
    
    def _get_version_path(self, profile_id: str, version: int) -> Path:
        """Get the path to a specific version of a profile."""
        return self.versions_dir / profile_id / f"v{version}.yaml"
    
    def _get_backup_path(self, profile_id: str, timestamp: datetime) -> Path:
        """Get the path to a backup file."""
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return self.backups_dir / profile_id / f"backup_{timestamp_str}.yaml"
    
    def _get_version_history_path(self, profile_id: str) -> Path:
        """Get the path to the version history file."""
        return self.versions_dir / profile_id / "history.json"
    
    def load_profile(self, profile_id: str) -> ProfileConfig:
        """Load the active profile configuration."""
        profile_path = self._get_profile_path(profile_id)
        
        if not profile_path.exists():
            raise ProfileValidationError(f"Profile '{profile_id}' not found")
        
        try:
            return ProfileConfig.from_yaml_file(profile_path)
        except Exception as e:
            raise ProfileValidationError(f"Failed to load profile '{profile_id}': {e}")
    
    def save_profile(self, profile: ProfileConfig, create_backup: bool = True) -> None:
        """Save profile configuration with optional backup."""
        profile_path = self._get_profile_path(profile.profile_id)
        
        # Create backup of existing profile if it exists
        if create_backup and profile_path.exists():
            try:
                existing_profile = ProfileConfig.from_yaml_file(profile_path)
                backup_path = self._get_backup_path(profile.profile_id, existing_profile.last_updated)
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(profile_path, backup_path)
            except Exception as e:
                # Log warning but don't fail the save operation
                print(f"Warning: Failed to create backup for {profile.profile_id}: {e}")
        
        # Save the new profile
        try:
            profile.save_to_file(profile_path)
        except Exception as e:
            raise ProfileValidationError(f"Failed to save profile '{profile.profile_id}': {e}")
    
    def create_profile(self, profile: ProfileConfig) -> None:
        """Create a new profile configuration."""
        profile_path = self._get_profile_path(profile.profile_id)
        
        if profile_path.exists():
            raise ProfileValidationError(f"Profile '{profile.profile_id}' already exists")
        
        # Ensure this is version 1 for new profiles
        profile.version = 1
        profile.created_at = datetime.utcnow()
        profile.last_updated = datetime.utcnow()
        
        # Save the profile
        self.save_profile(profile, create_backup=False)
        
        # Initialize version history
        self._save_version_history(profile.profile_id, [{
            'version': 1,
            'timestamp': profile.created_at.isoformat(),
            'action': 'created',
            'description': 'Initial profile creation'
        }])
    
    def update_profile(self, profile_id: str, updates: Dict, description: str = "Profile update") -> ProfileConfig:
        """Update profile with versioning support."""
        # Load current profile
        current_profile = self.load_profile(profile_id)
        
        # Validate that only modifiable fields are being updated
        for field_path in updates.keys():
            if not current_profile.can_modify_field(field_path):
                raise ProfileValidationError(f"Field '{field_path}' is immutable and cannot be modified")
        
        # Create new version
        new_profile = current_profile.increment_version()
        
        # Apply updates
        try:
            # Handle nested updates (e.g., behavior.active_topics)
            profile_dict = new_profile.model_dump()
            for field_path, value in updates.items():
                self._set_nested_field(profile_dict, field_path, value)
            
            # Create new profile instance with updates
            new_profile = ProfileConfig(**profile_dict)
            
        except ValidationError as e:
            raise ProfileValidationError(f"Validation failed for profile update: {e}")
        
        # Save versioned profile
        self._save_version(current_profile)
        self.save_profile(new_profile)
        
        # Update version history
        history = self._load_version_history(profile_id)
        history.append({
            'version': new_profile.version,
            'timestamp': new_profile.last_updated.isoformat(),
            'action': 'updated',
            'description': description,
            'changes': list(updates.keys())
        })
        self._save_version_history(profile_id, history)
        
        return new_profile
    
    def rollback_profile(self, profile_id: str, target_version: int) -> ProfileConfig:
        """Rollback profile to a specific version."""
        # Load target version
        version_path = self._get_version_path(profile_id, target_version)
        if not version_path.exists():
            raise ProfileValidationError(f"Version {target_version} not found for profile '{profile_id}'")
        
        try:
            target_profile = ProfileConfig.from_yaml_file(version_path)
        except Exception as e:
            raise ProfileValidationError(f"Failed to load version {target_version}: {e}")
        
        # Load current profile for backup and get current version
        current_version = 1
        try:
            current_profile = self.load_profile(profile_id)
            current_version = current_profile.version
            self._save_version(current_profile)
        except Exception:
            pass  # Current profile might not exist
        
        # Create new version based on target but with incremented version from current
        rolled_back_profile = target_profile.model_copy(deep=True)
        rolled_back_profile.version = current_version + 1
        rolled_back_profile.last_updated = datetime.utcnow()
        
        # Save rolled back profile
        self.save_profile(rolled_back_profile)
        
        # Update version history
        history = self._load_version_history(profile_id)
        history.append({
            'version': rolled_back_profile.version,
            'timestamp': rolled_back_profile.last_updated.isoformat(),
            'action': 'rollback',
            'description': f'Rolled back to version {target_version}',
            'target_version': target_version
        })
        self._save_version_history(profile_id, history)
        
        return rolled_back_profile
    
    def list_profiles(self) -> List[str]:
        """List all available profile IDs."""
        profile_files = self.active_dir.glob("*.yaml")
        return [f.stem for f in profile_files]
    
    def get_version_history(self, profile_id: str) -> List[Dict]:
        """Get version history for a profile."""
        return self._load_version_history(profile_id)
    
    def list_versions(self, profile_id: str) -> List[int]:
        """List all available versions for a profile."""
        version_dir = self.versions_dir / profile_id
        if not version_dir.exists():
            return []
        
        version_files = version_dir.glob("v*.yaml")
        versions = []
        for f in version_files:
            try:
                version_num = int(f.stem[1:])  # Remove 'v' prefix
                versions.append(version_num)
            except ValueError:
                continue
        
        return sorted(versions)
    
    def delete_profile(self, profile_id: str, create_backup: bool = True) -> None:
        """Delete a profile with optional backup."""
        profile_path = self._get_profile_path(profile_id)
        
        if not profile_path.exists():
            raise ProfileValidationError(f"Profile '{profile_id}' not found")
        
        if create_backup:
            # Create final backup
            backup_path = self._get_backup_path(profile_id, datetime.utcnow())
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(profile_path, backup_path)
        
        # Remove active profile
        profile_path.unlink()
        
        # Optionally remove version history (keep for audit trail)
        # version_dir = self.versions_dir / profile_id
        # if version_dir.exists():
        #     shutil.rmtree(version_dir)
    
    def validate_profile(self, profile: ProfileConfig) -> Tuple[bool, List[str]]:
        """Validate profile configuration and return validation results."""
        errors = []
        
        try:
            # Pydantic validation happens automatically during model creation
            # Additional custom validations can be added here
            
            # Check for required fields
            if not profile.identity.headline.strip():
                errors.append("Identity headline cannot be empty")
            
            if not profile.identity.primary_domains:
                errors.append("At least one primary domain is required")
            
            if not profile.identity.target_audience.strip():
                errors.append("Target audience cannot be empty")
            
            # Validate posting windows
            for i, window in enumerate(profile.behavior.posting_windows):
                if window.start_hour >= window.end_hour:
                    errors.append(f"Posting window {i+1}: end hour must be after start hour")
            
            return len(errors) == 0, errors
            
        except ValidationError as e:
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error['loc'])
                errors.append(f"{field}: {error['msg']}")
            
            return False, errors
    
    def _save_version(self, profile: ProfileConfig) -> None:
        """Save a profile version to the versions directory."""
        version_path = self._get_version_path(profile.profile_id, profile.version)
        version_path.parent.mkdir(parents=True, exist_ok=True)
        profile.save_to_file(version_path)
    
    def _load_version_history(self, profile_id: str) -> List[Dict]:
        """Load version history for a profile."""
        history_path = self._get_version_history_path(profile_id)
        
        if not history_path.exists():
            return []
        
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_version_history(self, profile_id: str, history: List[Dict]) -> None:
        """Save version history for a profile."""
        history_path = self._get_version_history_path(profile_id)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, default=str)
    
    def _set_nested_field(self, data: Dict, field_path: str, value) -> None:
        """Set a nested field value using dot notation."""
        keys = field_path.split('.')
        current = data
        
        # Navigate to the parent of the target field
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the final value
        current[keys[-1]] = value

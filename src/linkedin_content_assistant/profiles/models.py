"""Profile configuration models and validation."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
import yaml
from pathlib import Path


class SeniorityLevel(str, Enum):
    """Professional seniority levels."""
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    DIRECTOR = "director"
    VP = "vp"
    C_LEVEL = "c_level"


class PostingWindow(BaseModel):
    """Time window for posting content."""
    start_hour: int = Field(..., ge=0, le=23, description="Start hour (0-23)")
    end_hour: int = Field(..., ge=0, le=23, description="End hour (0-23)")
    
    @field_validator('end_hour')
    @classmethod
    def end_after_start(cls, v, info):
        if info.data and 'start_hour' in info.data and v <= info.data['start_hour']:
            raise ValueError('end_hour must be greater than start_hour')
        return v


class IdentityConfig(BaseModel):
    """Immutable identity configuration that defines core professional identity."""
    
    headline: str = Field(..., min_length=1, max_length=220, description="LinkedIn headline")
    seniority: SeniorityLevel = Field(..., description="Professional seniority level")
    primary_domains: List[str] = Field(..., min_length=1, max_length=5, description="Core expertise domains")
    target_audience: str = Field(..., min_length=1, description="Primary target audience")
    excluded_topics: List[str] = Field(default_factory=list, description="Topics to avoid")
    positioning: str = Field(..., min_length=1, description="Professional positioning statement")
    
    @field_validator('primary_domains')
    @classmethod
    def validate_domains(cls, v):
        if not v:
            raise ValueError('At least one primary domain is required')
        return [domain.strip() for domain in v if domain.strip()]
    
    @field_validator('excluded_topics')
    @classmethod
    def validate_excluded_topics(cls, v):
        return [topic.strip() for topic in v if topic.strip()]


class BehaviorConfig(BaseModel):
    """Adaptive behavior configuration that can evolve based on engagement."""
    
    active_topics: List[str] = Field(default_factory=list, description="Currently active topics")
    hook_patterns: List[str] = Field(default_factory=list, description="Preferred content hook patterns")
    posting_windows: List[PostingWindow] = Field(default_factory=list, description="Preferred posting time windows")
    emoji_frequency: str = Field(default="moderate", pattern="^(none|low|moderate|high)$", description="Emoji usage frequency")
    comment_depth: str = Field(default="detailed", pattern="^(brief|moderate|detailed)$", description="Comment detail level")
    vocabulary_bias: str = Field(default="professional", pattern="^(casual|professional|technical|academic)$", description="Vocabulary style preference")
    engagement_style: str = Field(default="thoughtful", pattern="^(reactive|thoughtful|proactive)$", description="Engagement approach")
    
    @field_validator('active_topics')
    @classmethod
    def validate_active_topics(cls, v):
        return [topic.strip() for topic in v if topic.strip()]
    
    @field_validator('hook_patterns')
    @classmethod
    def validate_hook_patterns(cls, v):
        return [pattern.strip() for pattern in v if pattern.strip()]


class ProfileConfig(BaseModel):
    """Complete profile configuration with immutable identity and adaptive behavior."""
    
    # Profile metadata
    profile_id: str = Field(..., min_length=1, description="Unique profile identifier")
    name: str = Field(..., min_length=1, description="Profile display name")
    description: Optional[str] = Field(None, description="Profile description")
    
    # Core configuration sections
    identity: IdentityConfig = Field(..., description="Immutable identity configuration")
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig, description="Adaptive behavior configuration")
    
    # Versioning and metadata
    version: int = Field(default=1, ge=1, description="Profile version number")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Profile creation timestamp")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Configuration flags
    enabled: bool = Field(default=True, description="Whether profile is active")
    
    model_config = {
        "validate_assignment": True,
        "extra": "forbid",  # Prevent additional fields
    }
    
    @field_validator('profile_id')
    @classmethod
    def validate_profile_id(cls, v):
        """Validate profile ID format."""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Profile ID must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()
    
    @model_validator(mode='before')
    @classmethod
    def validate_timestamps(cls, values):
        """Ensure timestamps are consistent."""
        if isinstance(values, dict):
            created_at = values.get('created_at')
            last_updated = values.get('last_updated')
            
            if created_at and last_updated and last_updated < created_at:
                values['last_updated'] = created_at
        
        return values
    
    def can_modify_field(self, field_name: str) -> bool:
        """Check if a field can be automatically modified."""
        immutable_fields = {
            'profile_id', 'name', 'created_at', 'version',
            'identity.headline', 'identity.seniority', 
            'identity.primary_domains', 'identity.target_audience',
            'identity.positioning'
        }
        
        # Handle nested field paths
        if '.' in field_name:
            return field_name not in immutable_fields
        
        # Handle top-level fields
        if field_name in ['identity']:
            return False
        
        if field_name in ['behavior']:
            return True
            
        return field_name not in immutable_fields
    
    def increment_version(self) -> 'ProfileConfig':
        """Create a new version of the profile with incremented version number."""
        new_config = self.model_copy(deep=True)
        new_config.version += 1
        new_config.last_updated = datetime.utcnow()
        return new_config
    
    def to_yaml(self) -> str:
        """Convert profile to YAML string."""
        data = self.model_dump()
        # Convert datetime objects to ISO strings for YAML serialization
        data['created_at'] = self.created_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        
        # Convert enum to string value
        if 'identity' in data and 'seniority' in data['identity']:
            data['identity']['seniority'] = data['identity']['seniority'].value
        
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'ProfileConfig':
        """Create ProfileConfig from YAML string."""
        try:
            data = yaml.safe_load(yaml_content)
            if not data:
                raise ValueError("Empty YAML content")
            
            # Convert ISO strings back to datetime objects
            if 'created_at' in data and isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'last_updated' in data and isinstance(data['last_updated'], str):
                data['last_updated'] = datetime.fromisoformat(data['last_updated'])
            
            # Convert string seniority back to enum
            if 'identity' in data and 'seniority' in data['identity'] and isinstance(data['identity']['seniority'], str):
                data['identity']['seniority'] = SeniorityLevel(data['identity']['seniority'])
            
            return cls(**data)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse profile configuration: {e}")
    
    @classmethod
    def from_yaml_file(cls, file_path: Path) -> 'ProfileConfig':
        """Load ProfileConfig from YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return cls.from_yaml(content)
        except FileNotFoundError:
            raise ValueError(f"Profile file not found: {file_path}")
        except Exception as e:
            raise ValueError(f"Failed to load profile from {file_path}: {e}")
    
    def save_to_file(self, file_path: Path) -> None:
        """Save profile configuration to YAML file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.to_yaml())
        except Exception as e:
            raise ValueError(f"Failed to save profile to {file_path}: {e}")


class ProfileValidationError(Exception):
    """Custom exception for profile validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, errors: Optional[List[str]] = None):
        self.message = message
        self.field = field
        self.errors = errors or []
        super().__init__(self.message)

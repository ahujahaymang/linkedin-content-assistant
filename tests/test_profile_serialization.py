"""Test profile YAML serialization and deserialization."""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from src.linkedin_content_assistant.profiles.models import (
    ProfileConfig,
    IdentityConfig,
    BehaviorConfig,
    SeniorityLevel,
    PostingWindow,
    ProfileValidationError
)


class TestProfileSerialization:
    """Test YAML serialization and deserialization of profile models."""
    
    @pytest.fixture
    def sample_identity(self):
        """Create a sample identity configuration."""
        return IdentityConfig(
            headline="Senior Software Engineer | AI & Cloud Architecture",
            seniority=SeniorityLevel.SENIOR,
            primary_domains=["AI/ML", "Cloud Architecture", "Python"],
            target_audience="Software engineers and tech leaders",
            excluded_topics=["Politics", "Religion"],
            positioning="Technical thought leader in AI and cloud solutions"
        )
    
    @pytest.fixture
    def sample_behavior(self):
        """Create a sample behavior configuration."""
        return BehaviorConfig(
            active_topics=["AI", "Cloud", "Python"],
            hook_patterns=["Question hook", "Story hook"],
            posting_windows=[
                PostingWindow(start_hour=9, end_hour=11),
                PostingWindow(start_hour=14, end_hour=16)
            ],
            emoji_frequency="moderate",
            comment_depth="detailed",
            vocabulary_bias="professional",
            engagement_style="thoughtful"
        )
    
    @pytest.fixture
    def sample_profile(self, sample_identity, sample_behavior):
        """Create a sample profile configuration."""
        return ProfileConfig(
            profile_id="test-profile",
            name="Test Profile",
            description="A test profile for serialization",
            identity=sample_identity,
            behavior=sample_behavior,
            version=1,
            enabled=True
        )
    
    def test_profile_to_yaml(self, sample_profile):
        """Test converting profile to YAML string."""
        yaml_str = sample_profile.to_yaml()
        
        # Verify YAML contains key fields
        assert "profile_id: test-profile" in yaml_str
        assert "name: Test Profile" in yaml_str
        assert "headline: Senior Software Engineer" in yaml_str
        assert "seniority: senior" in yaml_str
        assert "primary_domains:" in yaml_str
        assert "AI/ML" in yaml_str
        assert "version: 1" in yaml_str
    
    def test_profile_from_yaml(self, sample_profile):
        """Test creating profile from YAML string."""
        # Convert to YAML and back
        yaml_str = sample_profile.to_yaml()
        restored_profile = ProfileConfig.from_yaml(yaml_str)
        
        # Verify all fields match
        assert restored_profile.profile_id == sample_profile.profile_id
        assert restored_profile.name == sample_profile.name
        assert restored_profile.description == sample_profile.description
        assert restored_profile.version == sample_profile.version
        assert restored_profile.enabled == sample_profile.enabled
        
        # Verify identity fields
        assert restored_profile.identity.headline == sample_profile.identity.headline
        assert restored_profile.identity.seniority == sample_profile.identity.seniority
        assert restored_profile.identity.primary_domains == sample_profile.identity.primary_domains
        assert restored_profile.identity.target_audience == sample_profile.identity.target_audience
        assert restored_profile.identity.excluded_topics == sample_profile.identity.excluded_topics
        assert restored_profile.identity.positioning == sample_profile.identity.positioning
        
        # Verify behavior fields
        assert restored_profile.behavior.active_topics == sample_profile.behavior.active_topics
        assert restored_profile.behavior.hook_patterns == sample_profile.behavior.hook_patterns
        assert restored_profile.behavior.emoji_frequency == sample_profile.behavior.emoji_frequency
        assert restored_profile.behavior.comment_depth == sample_profile.behavior.comment_depth
        assert restored_profile.behavior.vocabulary_bias == sample_profile.behavior.vocabulary_bias
        assert restored_profile.behavior.engagement_style == sample_profile.behavior.engagement_style
        
        # Verify posting windows
        assert len(restored_profile.behavior.posting_windows) == len(sample_profile.behavior.posting_windows)
        for orig_window, restored_window in zip(
            sample_profile.behavior.posting_windows,
            restored_profile.behavior.posting_windows
        ):
            assert restored_window.start_hour == orig_window.start_hour
            assert restored_window.end_hour == orig_window.end_hour
    
    def test_profile_file_operations(self, sample_profile):
        """Test saving and loading profile from file."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_profile.yaml"
            
            # Save to file
            sample_profile.save_to_file(file_path)
            assert file_path.exists()
            
            # Load from file
            loaded_profile = ProfileConfig.from_yaml_file(file_path)
            
            # Verify loaded profile matches original
            assert loaded_profile.profile_id == sample_profile.profile_id
            assert loaded_profile.name == sample_profile.name
            assert loaded_profile.identity.headline == sample_profile.identity.headline
            assert loaded_profile.behavior.active_topics == sample_profile.behavior.active_topics
    
    def test_datetime_serialization(self, sample_profile):
        """Test that datetime fields are properly serialized."""
        yaml_str = sample_profile.to_yaml()
        
        # Verify datetime fields are in ISO format
        assert "created_at:" in yaml_str
        assert "last_updated:" in yaml_str
        
        # Restore and verify datetime objects
        restored_profile = ProfileConfig.from_yaml(yaml_str)
        assert isinstance(restored_profile.created_at, datetime)
        assert isinstance(restored_profile.last_updated, datetime)
    
    def test_enum_serialization(self, sample_profile):
        """Test that enum fields are properly serialized."""
        yaml_str = sample_profile.to_yaml()
        
        # Verify enum is serialized as string value
        assert "seniority: senior" in yaml_str
        
        # Restore and verify enum object
        restored_profile = ProfileConfig.from_yaml(yaml_str)
        assert isinstance(restored_profile.identity.seniority, SeniorityLevel)
        assert restored_profile.identity.seniority == SeniorityLevel.SENIOR
    
    def test_invalid_yaml(self):
        """Test handling of invalid YAML."""
        invalid_yaml = "invalid: yaml: content: {"
        
        with pytest.raises(ValueError, match="Invalid YAML format"):
            ProfileConfig.from_yaml(invalid_yaml)
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields in YAML."""
        incomplete_yaml = """
profile_id: test
name: Test
"""
        
        with pytest.raises(ValueError, match="Failed to parse profile configuration"):
            ProfileConfig.from_yaml(incomplete_yaml)
    
    def test_file_not_found(self):
        """Test handling of non-existent file."""
        with pytest.raises(ValueError, match="Profile file not found"):
            ProfileConfig.from_yaml_file(Path("/nonexistent/path/profile.yaml"))


class TestIdentityConfig:
    """Test IdentityConfig model."""
    
    def test_valid_identity_config(self):
        """Test creating valid identity configuration."""
        identity = IdentityConfig(
            headline="Test Headline",
            seniority=SeniorityLevel.MID,
            primary_domains=["Domain1", "Domain2"],
            target_audience="Test Audience",
            excluded_topics=["Topic1"],
            positioning="Test Positioning"
        )
        
        assert identity.headline == "Test Headline"
        assert identity.seniority == SeniorityLevel.MID
        assert len(identity.primary_domains) == 2
        assert len(identity.excluded_topics) == 1
    
    def test_domain_validation(self):
        """Test primary domains validation."""
        # Test with empty domains after stripping
        identity = IdentityConfig(
            headline="Test",
            seniority=SeniorityLevel.MID,
            primary_domains=["  ", "Valid Domain", "  "],
            target_audience="Test",
            positioning="Test"
        )
        
        # Should only keep non-empty domains
        assert len(identity.primary_domains) == 1
        assert identity.primary_domains[0] == "Valid Domain"


class TestBehaviorConfig:
    """Test BehaviorConfig model."""
    
    def test_default_behavior_config(self):
        """Test creating behavior config with defaults."""
        behavior = BehaviorConfig()
        
        assert behavior.emoji_frequency == "moderate"
        assert behavior.comment_depth == "detailed"
        assert behavior.vocabulary_bias == "professional"
        assert behavior.engagement_style == "thoughtful"
        assert behavior.active_topics == []
        assert behavior.hook_patterns == []
        assert behavior.posting_windows == []
    
    def test_posting_window_validation(self):
        """Test posting window validation."""
        # Valid window
        window = PostingWindow(start_hour=9, end_hour=17)
        assert window.start_hour == 9
        assert window.end_hour == 17
        
        # Invalid window (end before start)
        with pytest.raises(ValueError, match="end_hour must be greater than start_hour"):
            PostingWindow(start_hour=17, end_hour=9)


class TestProfileConfig:
    """Test ProfileConfig model."""
    
    def test_profile_id_validation(self):
        """Test profile ID validation."""
        identity = IdentityConfig(
            headline="Test",
            seniority=SeniorityLevel.MID,
            primary_domains=["Test"],
            target_audience="Test",
            positioning="Test"
        )
        
        # Valid profile IDs
        valid_ids = ["test-profile", "test_profile", "test123", "TEST-PROFILE"]
        for profile_id in valid_ids:
            profile = ProfileConfig(
                profile_id=profile_id,
                name="Test",
                identity=identity
            )
            # Profile ID should be lowercased
            assert profile.profile_id == profile_id.lower()
        
        # Invalid profile ID (special characters)
        with pytest.raises(ValueError):
            ProfileConfig(
                profile_id="test@profile!",
                name="Test",
                identity=identity
            )
    
    def test_can_modify_field(self):
        """Test field modification permissions."""
        identity = IdentityConfig(
            headline="Test",
            seniority=SeniorityLevel.MID,
            primary_domains=["Test"],
            target_audience="Test",
            positioning="Test"
        )
        
        profile = ProfileConfig(
            profile_id="test",
            name="Test",
            identity=identity
        )
        
        # Immutable fields
        assert not profile.can_modify_field("profile_id")
        assert not profile.can_modify_field("name")
        assert not profile.can_modify_field("created_at")
        assert not profile.can_modify_field("version")
        assert not profile.can_modify_field("identity")
        assert not profile.can_modify_field("identity.headline")
        
        # Mutable fields
        assert profile.can_modify_field("behavior")
        assert profile.can_modify_field("behavior.active_topics")
        assert profile.can_modify_field("enabled")
        assert profile.can_modify_field("description")
    
    def test_increment_version(self):
        """Test version incrementing."""
        identity = IdentityConfig(
            headline="Test",
            seniority=SeniorityLevel.MID,
            primary_domains=["Test"],
            target_audience="Test",
            positioning="Test"
        )
        
        profile = ProfileConfig(
            profile_id="test",
            name="Test",
            identity=identity,
            version=1
        )
        
        new_profile = profile.increment_version()
        
        assert new_profile.version == 2
        assert new_profile.profile_id == profile.profile_id
        assert new_profile.last_updated > profile.last_updated

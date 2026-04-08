"""
Property-based tests for Profile Store using Hypothesis.

These tests validate the correctness properties defined in the design document
for profile data storage and management.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
from pydantic import ValidationError

from src.linkedin_content_assistant.profiles.models import (
    ProfileConfig,
    IdentityConfig,
    BehaviorConfig,
    SeniorityLevel,
    PostingWindow,
    ProfileValidationError
)
from src.linkedin_content_assistant.profiles.manager import ProfileManager


# ============================================================================
# Hypothesis Strategies for Generating Test Data
# ============================================================================

@st.composite
def posting_window_strategy(draw):
    """Generate valid PostingWindow instances."""
    start_hour = draw(st.integers(min_value=0, max_value=22))
    end_hour = draw(st.integers(min_value=start_hour + 1, max_value=23))
    return PostingWindow(start_hour=start_hour, end_hour=end_hour)


@st.composite
def identity_config_strategy(draw):
    """Generate valid IdentityConfig instances."""
    return IdentityConfig(
        headline=draw(st.text(min_size=1, max_size=220, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Pc', 'Pd'),
            whitelist_characters='|&@'
        ))),
        seniority=draw(st.sampled_from(SeniorityLevel)),
        primary_domains=draw(st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            min_size=1,
            max_size=5
        )),
        target_audience=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Pc')
        ))),
        excluded_topics=draw(st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            max_size=10
        )),
        positioning=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Pc')
        )))
    )


@st.composite
def behavior_config_strategy(draw):
    """Generate valid BehaviorConfig instances."""
    return BehaviorConfig(
        active_topics=draw(st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
            )),
            max_size=10
        )),
        hook_patterns=draw(st.lists(
            st.text(min_size=1, max_size=100, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Pc')
            )),
            max_size=10
        )),
        posting_windows=draw(st.lists(posting_window_strategy(), max_size=5)),
        emoji_frequency=draw(st.sampled_from(['none', 'low', 'moderate', 'high'])),
        comment_depth=draw(st.sampled_from(['brief', 'moderate', 'detailed'])),
        vocabulary_bias=draw(st.sampled_from(['casual', 'professional', 'technical', 'academic'])),
        engagement_style=draw(st.sampled_from(['reactive', 'thoughtful', 'proactive']))
    )


@st.composite
def profile_config_strategy(draw):
    """Generate valid ProfileConfig instances."""
    profile_id = draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-_')
    ))
    # Ensure profile_id starts with a letter
    if not profile_id[0].isalpha():
        profile_id = 'p' + profile_id
    
    return ProfileConfig(
        profile_id=profile_id,
        name=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')
        ))),
        description=draw(st.one_of(
            st.none(),
            st.text(max_size=500, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Pc')
            ))
        )),
        identity=draw(identity_config_strategy()),
        behavior=draw(behavior_config_strategy()),
        version=draw(st.integers(min_value=1, max_value=100)),
        enabled=draw(st.booleans())
    )


# ============================================================================
# Property 1: Profile Data Round-Trip Preservation
# **Validates: Requirements 1.1, 1.4**
# ============================================================================

@given(profile=profile_config_strategy())
@settings(max_examples=100, deadline=None)
def test_property_1_profile_data_round_trip_preservation(profile):
    """
    Feature: linkedin-content-assistant, Property 1: Profile Data Round-Trip Preservation
    
    For any valid ProfileConfig, serializing to YAML then deserializing should 
    produce an equivalent ProfileConfig with all fields preserved.
    
    **Validates: Requirements 1.1, 1.4**
    """
    # Serialize to YAML
    yaml_content = profile.to_yaml()
    
    # Deserialize from YAML
    restored_profile = ProfileConfig.from_yaml(yaml_content)
    
    # Verify all fields are preserved
    assert restored_profile.profile_id == profile.profile_id
    assert restored_profile.name == profile.name
    assert restored_profile.description == profile.description
    assert restored_profile.version == profile.version
    assert restored_profile.enabled == profile.enabled
    
    # Verify identity fields
    assert restored_profile.identity.headline == profile.identity.headline
    assert restored_profile.identity.seniority == profile.identity.seniority
    assert restored_profile.identity.primary_domains == profile.identity.primary_domains
    assert restored_profile.identity.target_audience == profile.identity.target_audience
    assert restored_profile.identity.excluded_topics == profile.identity.excluded_topics
    assert restored_profile.identity.positioning == profile.identity.positioning
    
    # Verify behavior fields
    assert restored_profile.behavior.active_topics == profile.behavior.active_topics
    assert restored_profile.behavior.hook_patterns == profile.behavior.hook_patterns
    assert restored_profile.behavior.emoji_frequency == profile.behavior.emoji_frequency
    assert restored_profile.behavior.comment_depth == profile.behavior.comment_depth
    assert restored_profile.behavior.vocabulary_bias == profile.behavior.vocabulary_bias
    assert restored_profile.behavior.engagement_style == profile.behavior.engagement_style
    
    # Verify posting windows
    assert len(restored_profile.behavior.posting_windows) == len(profile.behavior.posting_windows)
    for orig_window, restored_window in zip(
        profile.behavior.posting_windows,
        restored_profile.behavior.posting_windows
    ):
        assert restored_window.start_hour == orig_window.start_hour
        assert restored_window.end_hour == orig_window.end_hour
    
    # Verify timestamps are preserved (within reasonable tolerance for serialization)
    assert abs((restored_profile.created_at - profile.created_at).total_seconds()) < 1
    assert abs((restored_profile.last_updated - profile.last_updated).total_seconds()) < 1


# ============================================================================
# Property 2: Profile Data Validation Rejects Invalid Input
# **Validates: Requirements 1.2**
# ============================================================================

@given(
    field_to_invalidate=st.sampled_from(['headline', 'primary_domains', 'target_audience', 'positioning']),
    seniority=st.sampled_from(SeniorityLevel)
)
@settings(max_examples=100, deadline=None)
def test_property_2_profile_validation_rejects_invalid_input(field_to_invalidate, seniority):
    """
    Feature: linkedin-content-assistant, Property 2: Profile Data Validation Rejects Invalid Input
    
    For any profile data missing required fields (headline, seniority, primary_domains, 
    target_audience, positioning), the Profile_Store should reject storage and raise 
    a validation error.
    
    **Validates: Requirements 1.2**
    """
    # Create valid defaults
    valid_data = {
        'headline': 'Valid Headline',
        'seniority': seniority,
        'primary_domains': ['Domain 1', 'Domain 2'],
        'target_audience': 'Valid Audience',
        'positioning': 'Valid Positioning'
    }
    
    # Invalidate the selected field
    if field_to_invalidate == 'headline':
        valid_data['headline'] = ''
    elif field_to_invalidate == 'primary_domains':
        valid_data['primary_domains'] = []
    elif field_to_invalidate == 'target_audience':
        valid_data['target_audience'] = ''
    elif field_to_invalidate == 'positioning':
        valid_data['positioning'] = ''
    
    # Attempt to create profile with invalid data - should raise validation error
    with pytest.raises((ValueError, ValidationError, ProfileValidationError)):
        identity = IdentityConfig(**valid_data)
        
        profile = ProfileConfig(
            profile_id="test-profile",
            name="Test Profile",
            identity=identity
        )


@given(
    start_hour=st.integers(min_value=0, max_value=23),
    end_hour=st.integers(min_value=0, max_value=23)
)
@settings(max_examples=100, deadline=None)
def test_property_2_posting_window_validation(start_hour, end_hour):
    """
    Feature: linkedin-content-assistant, Property 2: Profile Data Validation Rejects Invalid Input
    
    For any posting window where end_hour <= start_hour, validation should reject it.
    
    **Validates: Requirements 1.2**
    """
    if end_hour <= start_hour:
        with pytest.raises(ValueError, match="end_hour must be greater than start_hour"):
            PostingWindow(start_hour=start_hour, end_hour=end_hour)
    else:
        # Valid window should be created successfully
        window = PostingWindow(start_hour=start_hour, end_hour=end_hour)
        assert window.start_hour == start_hour
        assert window.end_hour == end_hour


# ============================================================================
# Property 3: Profile Version Increment on Update
# **Validates: Requirements 1.3**
# ============================================================================

@given(profile=profile_config_strategy())
@settings(max_examples=100, deadline=None)
def test_property_3_profile_version_increment_on_update(profile):
    """
    Feature: linkedin-content-assistant, Property 3: Profile Version Increment on Update
    
    For any ProfileConfig, when behavior configuration is updated, the resulting 
    profile should have a version number exactly one greater than the original.
    
    **Validates: Requirements 1.3**
    """
    original_version = profile.version
    
    # Increment version
    updated_profile = profile.increment_version()
    
    # Verify version incremented by exactly 1
    assert updated_profile.version == original_version + 1
    
    # Verify last_updated timestamp was updated
    assert updated_profile.last_updated > profile.last_updated
    
    # Verify other fields remain unchanged
    assert updated_profile.profile_id == profile.profile_id
    assert updated_profile.name == profile.name
    assert updated_profile.identity.headline == profile.identity.headline


@given(profile=profile_config_strategy())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_3_profile_manager_update_increments_version(profile):
    """
    Feature: linkedin-content-assistant, Property 3: Profile Version Increment on Update
    
    For any ProfileConfig managed by ProfileManager, updating behavior should 
    increment the version number.
    
    **Validates: Requirements 1.3**
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create profile manager with temporary directory
        manager = ProfileManager(profiles_dir=str(Path(tmp_dir) / "profiles"))
        
        # Create profile
        manager.create_profile(profile)
        original_version = profile.version
        
        # Update behavior
        updates = {
            "behavior.active_topics": ["New Topic 1", "New Topic 2"]
        }
        
        updated_profile = manager.update_profile(
            profile.profile_id,
            updates,
            description="Test update"
        )
        
        # Verify version incremented
        assert updated_profile.version == original_version + 1
        
        # Verify update was applied
        assert "New Topic 1" in updated_profile.behavior.active_topics
        assert "New Topic 2" in updated_profile.behavior.active_topics


# ============================================================================
# Property 4: Multiple Profile Independence
# **Validates: Requirements 1.5**
# ============================================================================

@given(
    profile1=profile_config_strategy(),
    profile2=profile_config_strategy()
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_4_multiple_profile_independence(profile1, profile2):
    """
    Feature: linkedin-content-assistant, Property 4: Multiple Profile Independence
    
    For any two distinct profile IDs, storing and retrieving profiles should 
    maintain independence such that updates to one profile do not affect the 
    other profile's data.
    
    **Validates: Requirements 1.5**
    """
    # Ensure profiles have different IDs
    assume(profile1.profile_id != profile2.profile_id)
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create profile manager with temporary directory
        manager = ProfileManager(profiles_dir=str(Path(tmp_dir) / "profiles"))
        
        # Store both profiles
        manager.create_profile(profile1)
        manager.create_profile(profile2)
        
        # Retrieve both profiles
        retrieved_profile1 = manager.load_profile(profile1.profile_id)
        retrieved_profile2 = manager.load_profile(profile2.profile_id)
        
        # Verify profiles are independent
        assert retrieved_profile1.profile_id == profile1.profile_id
        assert retrieved_profile2.profile_id == profile2.profile_id
        assert retrieved_profile1.profile_id != retrieved_profile2.profile_id
        
        # Update profile1
        updates = {
            "behavior.active_topics": ["Updated Topic for Profile 1"]
        }
        updated_profile1 = manager.update_profile(
            profile1.profile_id,
            updates,
            description="Update profile 1"
        )
        
        # Retrieve profile2 again
        retrieved_profile2_after_update = manager.load_profile(profile2.profile_id)
        
        # Verify profile2 was not affected by profile1 update
        assert retrieved_profile2_after_update.behavior.active_topics == profile2.behavior.active_topics
        assert retrieved_profile2_after_update.version == profile2.version
        
        # Verify profile1 was updated
        assert "Updated Topic for Profile 1" in updated_profile1.behavior.active_topics
        assert updated_profile1.version == profile1.version + 1


@given(
    profiles=st.lists(profile_config_strategy(), min_size=2, max_size=5, unique_by=lambda p: p.profile_id)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_4_multiple_profile_storage_and_retrieval(profiles):
    """
    Feature: linkedin-content-assistant, Property 4: Multiple Profile Independence
    
    For any set of profiles with distinct IDs, all profiles should be stored 
    and retrieved independently without data corruption or cross-contamination.
    
    **Validates: Requirements 1.5**
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create profile manager with temporary directory
        manager = ProfileManager(profiles_dir=str(Path(tmp_dir) / "profiles"))
        
        # Store all profiles
        for profile in profiles:
            manager.create_profile(profile)
        
        # Verify all profiles can be listed
        profile_ids = manager.list_profiles()
        assert len(profile_ids) == len(profiles)
        
        # Retrieve and verify each profile
        for original_profile in profiles:
            retrieved_profile = manager.load_profile(original_profile.profile_id)
            
            # Verify profile data matches
            assert retrieved_profile.profile_id == original_profile.profile_id
            assert retrieved_profile.name == original_profile.name
            assert retrieved_profile.identity.headline == original_profile.identity.headline
            assert retrieved_profile.behavior.active_topics == original_profile.behavior.active_topics
            
            # Verify this profile is distinct from others
            for other_profile in profiles:
                if other_profile.profile_id != original_profile.profile_id:
                    assert retrieved_profile.profile_id != other_profile.profile_id
                    # Data should be independent
                    if retrieved_profile.name == other_profile.name:
                        # Even if names match, profile_ids should differ
                        assert retrieved_profile.profile_id != other_profile.profile_id


# ============================================================================
# Additional Property Tests for File Persistence
# ============================================================================

@given(profile=profile_config_strategy())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_profile_file_round_trip_preservation(profile):
    """
    Verify that saving to file and loading from file preserves all data.
    
    This extends Property 1 to include file I/O operations.
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "test_profile.yaml"
        
        # Save to file
        profile.save_to_file(file_path)
        assert file_path.exists()
        
        # Load from file
        loaded_profile = ProfileConfig.from_yaml_file(file_path)
        
        # Verify all fields preserved
        assert loaded_profile.profile_id == profile.profile_id
        assert loaded_profile.name == profile.name
        assert loaded_profile.identity.headline == profile.identity.headline
        assert loaded_profile.behavior.active_topics == profile.behavior.active_topics
        assert loaded_profile.version == profile.version


@given(profile=profile_config_strategy())
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_profile_manager_backup_creation(profile):
    """
    Verify that ProfileManager creates backups when updating profiles.
    
    This validates the backup mechanism for profile updates.
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = ProfileManager(profiles_dir=str(Path(tmp_dir) / "profiles"))
        
        # Create initial profile
        manager.create_profile(profile)
        
        # Update profile (should create backup)
        updates = {"behavior.active_topics": ["New Topic"]}
        manager.update_profile(profile.profile_id, updates, description="Test update")
        
        # Verify backup directory exists
        backup_dir = Path(tmp_dir) / "profiles" / "backups" / profile.profile_id
        assert backup_dir.exists()
        
        # Verify at least one backup file exists
        backup_files = list(backup_dir.glob("backup_*.yaml"))
        assert len(backup_files) > 0

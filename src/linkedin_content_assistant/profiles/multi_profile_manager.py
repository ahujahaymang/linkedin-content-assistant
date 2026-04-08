"""Multi-profile manager for handling multiple LinkedIn profiles with isolation."""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

from .manager import ProfileManager
from .models import ProfileConfig, ProfileValidationError

# Note: Memory store will be imported once the memory module is implemented
# from ..memory.store import MemoryStore, InMemoryStore

logger = logging.getLogger(__name__)


class ProfileIsolationError(Exception):
    """Exception raised when profile isolation is violated."""
    pass


class MultiProfileManager:
    """Manages multiple LinkedIn profiles with strict isolation."""
    
    def __init__(self, profiles_dir: str = "./profiles", max_concurrent_profiles: int = 3):
        """Initialize multi-profile manager.
        
        Args:
            profiles_dir: Directory containing profile configurations
            max_concurrent_profiles: Maximum number of profiles to process concurrently
        """
        self.profiles_dir = Path(profiles_dir)
        self.max_concurrent_profiles = max_concurrent_profiles
        
        # Profile managers - one per profile for isolation
        self._profile_managers: Dict[str, ProfileManager] = {}
        self._profile_locks: Dict[str, threading.RLock] = {}
        self._active_profiles: Set[str] = set()
        self._lock = threading.RLock()
        
        # Thread pool for concurrent profile operations
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent_profiles)
        
        # Initialize profile managers
        self._initialize_profile_managers()
    
    def _initialize_profile_managers(self) -> None:
        """Initialize profile managers for all discovered profiles."""
        with self._lock:
            # Discover existing profiles
            if self.profiles_dir.exists():
                active_dir = self.profiles_dir / "active"
                if active_dir.exists():
                    for profile_file in active_dir.glob("*.yaml"):
                        profile_id = profile_file.stem
                        self._ensure_profile_manager(profile_id)
    
    def _ensure_profile_manager(self, profile_id: str) -> ProfileManager:
        """Ensure a profile manager exists for the given profile ID."""
        if profile_id not in self._profile_managers:
            # Create isolated profile directory
            profile_dir = self.profiles_dir / "isolated" / profile_id
            profile_dir.mkdir(parents=True, exist_ok=True)
            
            # Create profile manager with isolated directory
            self._profile_managers[profile_id] = ProfileManager(str(profile_dir))
            self._profile_locks[profile_id] = threading.RLock()
            
            logger.info(f"Created isolated profile manager for {profile_id}")
        
        return self._profile_managers[profile_id]
    
    def _get_profile_lock(self, profile_id: str) -> threading.RLock:
        """Get the lock for a specific profile."""
        with self._lock:
            if profile_id not in self._profile_locks:
                self._profile_locks[profile_id] = threading.RLock()
            return self._profile_locks[profile_id]
    
    def list_profiles(self) -> List[str]:
        """List all available profile IDs."""
        with self._lock:
            all_profiles = set()
            
            # Get profiles from main directory
            main_manager = ProfileManager(str(self.profiles_dir))
            all_profiles.update(main_manager.list_profiles())
            
            # Get profiles from isolated directories
            isolated_dir = self.profiles_dir / "isolated"
            if isolated_dir.exists():
                for profile_dir in isolated_dir.iterdir():
                    if profile_dir.is_dir():
                        profile_manager = ProfileManager(str(profile_dir))
                        if profile_manager.list_profiles():
                            all_profiles.add(profile_dir.name)
            
            return sorted(list(all_profiles))
    
    def get_active_profiles(self) -> List[str]:
        """Get list of currently active profiles."""
        with self._lock:
            return list(self._active_profiles)
    
    def activate_profile(self, profile_id: str) -> None:
        """Activate a profile for processing."""
        with self._lock:
            if profile_id not in self._profile_managers:
                self._ensure_profile_manager(profile_id)
            
            self._active_profiles.add(profile_id)
            logger.info(f"Activated profile {profile_id}")
    
    def deactivate_profile(self, profile_id: str) -> None:
        """Deactivate a profile from processing."""
        with self._lock:
            self._active_profiles.discard(profile_id)
            logger.info(f"Deactivated profile {profile_id}")
    
    def get_profile(self, profile_id: str) -> Optional[ProfileConfig]:
        """Get profile configuration with isolation."""
        profile_lock = self._get_profile_lock(profile_id)
        with profile_lock:
            try:
                manager = self._ensure_profile_manager(profile_id)
                return manager.load_profile(profile_id)
            except ProfileValidationError:
                return None
    
    def update_profile(self, profile_id: str, updates: Dict[str, Any], 
                      description: str = "Profile update") -> Optional[ProfileConfig]:
        """Update profile with isolation."""
        profile_lock = self._get_profile_lock(profile_id)
        with profile_lock:
            try:
                manager = self._ensure_profile_manager(profile_id)
                return manager.update_profile(profile_id, updates, description)
            except ProfileValidationError as e:
                logger.error(f"Failed to update profile {profile_id}: {e}")
                return None
    
    def create_profile(self, profile: ProfileConfig) -> bool:
        """Create a new profile with isolation."""
        profile_lock = self._get_profile_lock(profile.profile_id)
        with profile_lock:
            try:
                manager = self._ensure_profile_manager(profile.profile_id)
                manager.create_profile(profile)
                return True
            except ProfileValidationError as e:
                logger.error(f"Failed to create profile {profile.profile_id}: {e}")
                return False
    
    def delete_profile(self, profile_id: str, create_backup: bool = True) -> bool:
        """Delete a profile with isolation."""
        profile_lock = self._get_profile_lock(profile_id)
        with profile_lock:
            try:
                # Deactivate first
                self.deactivate_profile(profile_id)
                
                manager = self._ensure_profile_manager(profile_id)
                manager.delete_profile(profile_id, create_backup)
                
                # Clean up manager
                with self._lock:
                    if profile_id in self._profile_managers:
                        del self._profile_managers[profile_id]
                    if profile_id in self._profile_locks:
                        del self._profile_locks[profile_id]
                
                return True
            except ProfileValidationError as e:
                logger.error(f"Failed to delete profile {profile_id}: {e}")
                return False
    
    def get_profile_memory_store(self, profile_id: str):
        """Get isolated memory store for a profile.
        
        Note: This method will be fully implemented once the memory module is available.
        For now, it creates the directory structure.
        """
        profile_lock = self._get_profile_lock(profile_id)
        with profile_lock:
            # Create profile-specific memory directory
            memory_dir = self.profiles_dir / "isolated" / profile_id / "memory"
            memory_dir.mkdir(parents=True, exist_ok=True)
            
            # Create persistence file path
            persistence_file = memory_dir / "events.json"
            
            # TODO: Return InMemoryStore once memory module is implemented
            # return InMemoryStore(str(persistence_file))
            return None
    
    def execute_with_profile(self, profile_id: str, operation: callable, *args, **kwargs) -> Any:
        """Execute an operation with profile isolation."""
        if profile_id not in self._active_profiles:
            raise ProfileIsolationError(f"Profile {profile_id} is not active")
        
        profile_lock = self._get_profile_lock(profile_id)
        with profile_lock:
            try:
                # Load profile context
                profile = self.get_profile(profile_id)
                if not profile:
                    raise ProfileIsolationError(f"Profile {profile_id} not found")
                
                # Get isolated memory store
                memory_store = self.get_profile_memory_store(profile_id)
                
                # Execute operation with profile context
                return operation(profile, memory_store, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error executing operation for profile {profile_id}: {e}")
                raise
    
    async def execute_concurrent_operations(self, operations: List[tuple]) -> Dict[str, Any]:
        """Execute operations concurrently across multiple profiles."""
        if len(operations) > self.max_concurrent_profiles:
            raise ProfileIsolationError(
                f"Cannot execute {len(operations)} operations concurrently. "
                f"Maximum allowed: {self.max_concurrent_profiles}"
            )
        
        # Validate all profiles are active
        for profile_id, _, _, _ in operations:
            if profile_id not in self._active_profiles:
                raise ProfileIsolationError(f"Profile {profile_id} is not active")
        
        # Execute operations concurrently using thread pool
        futures = []
        for profile_id, operation, args, kwargs in operations:
            future = self._executor.submit(
                self.execute_with_profile, 
                profile_id, 
                operation, 
                *args, 
                **kwargs
            )
            futures.append((profile_id, future))
        
        # Collect results
        results = {}
        for profile_id, future in futures:
            try:
                results[profile_id] = future.result()
            except Exception as e:
                results[profile_id] = {"error": str(e)}
                logger.error(f"Operation failed for profile {profile_id}: {e}")
        
        return results
    
    def get_profile_stats(self) -> Dict[str, Any]:
        """Get statistics about profile usage."""
        with self._lock:
            return {
                "total_profiles": len(self._profile_managers),
                "active_profiles": len(self._active_profiles),
                "max_concurrent": self.max_concurrent_profiles,
                "profile_list": list(self._profile_managers.keys()),
                "active_list": list(self._active_profiles)
            }
    
    def validate_profile_isolation(self, profile_id: str) -> Dict[str, bool]:
        """Validate that profile isolation is maintained."""
        results = {
            "has_isolated_directory": False,
            "has_isolated_memory": False,
            "has_profile_lock": False,
            "manager_exists": False
        }
        
        try:
            # Check isolated directory
            isolated_dir = self.profiles_dir / "isolated" / profile_id
            results["has_isolated_directory"] = isolated_dir.exists()
            
            # Check isolated memory
            memory_dir = isolated_dir / "memory"
            results["has_isolated_memory"] = memory_dir.exists()
            
            # Check profile lock
            results["has_profile_lock"] = profile_id in self._profile_locks
            
            # Check manager exists
            results["manager_exists"] = profile_id in self._profile_managers
            
        except Exception as e:
            logger.error(f"Error validating isolation for profile {profile_id}: {e}")
        
        return results
    
    def shutdown(self) -> None:
        """Shutdown the multi-profile manager."""
        logger.info("Shutting down multi-profile manager")
        
        # Deactivate all profiles
        with self._lock:
            for profile_id in list(self._active_profiles):
                self.deactivate_profile(profile_id)
        
        # Shutdown thread pool
        self._executor.shutdown(wait=True)
        
        logger.info("Multi-profile manager shutdown complete")

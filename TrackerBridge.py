"""
Tracker Bridge for Archipelago Integration

Provides a communication bridge between SSHDClient and external tracker applications.
Writes tracker state to a shared JSON file that trackers can read for autotracking.

This allows the standalone tracker (separate repository) to auto-update based on
Archipelago multiworld progress.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Set, Optional, Any
import logging

logger = logging.getLogger(__name__)


class TrackerBridge:
    """
    Bridge between SSHDClient and tracker applications.
    
    Exports tracker-relevant state to a shared JSON file that can be read
    by tracker GUIs for autotracking functionality.
    """
    
    def __init__(self, shared_dir: Optional[Path] = None):
        """
        Initialize the tracker bridge.
        
        Args:
            shared_dir: Directory for shared state file. 
                       Defaults to:
                       - Windows: C:\\Users\\<username>\\.sshd_ap_tracker
                       - Linux/macOS: ~/.sshd_ap_tracker
        """
        if shared_dir is None:
            shared_dir = Path.home() / ".sshd_ap_tracker"
        
        self.shared_dir = Path(shared_dir)
        
        # Create directory if it doesn't exist
        try:
            self.shared_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Tracker bridge directory: {self.shared_dir}")
        except Exception as e:
            logger.error(f"Failed to create tracker directory {self.shared_dir}: {e}")
        
        self.state_file = self.shared_dir / "tracker_state.json"
        self.last_write_time = 0.0
        self.write_interval = 0.5  # Write at most once per 0.5 seconds
        
        # Initialize empty state file
        if not self.state_file.exists():
            try:
                self._write_state({})
                logger.info(f"Created initial tracker state file: {self.state_file}")
            except Exception as e:
                logger.error(f"Failed to create initial state file: {e}")
    
    def update_tracker_state(
        self,
        checked_locations: Set[int],
        received_items: Dict[str, int],
        slot_name: str,
        seed_name: Optional[str] = None,
        location_names: Optional[Dict[int, str]] = None,
        item_names: Optional[Dict[int, str]] = None,
        slot_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update the shared tracker state file with current progress.
        
        Args:
            checked_locations: Set of location IDs that have been checked
            received_items: Dict mapping item names to quantities received
            slot_name: Player's slot/save name
            seed_name: Name of the seed/multiworld
            location_names: Mapping of location IDs to names
            item_names: Mapping of item IDs to names
            slot_data: Additional slot data from server
        """
        # Rate limit writes
        current_time = time.time()
        if current_time - self.last_write_time < self.write_interval:
            return
        
        # Convert location IDs to names if mapping provided
        checked_location_names = []
        if location_names:
            checked_location_names = [
                location_names.get(loc_id, f"Location_{loc_id}")
                for loc_id in checked_locations
            ]
        else:
            checked_location_names = [str(loc_id) for loc_id in checked_locations]
        
        state = {
            "version": 1,
            "slot_name": slot_name,
            "seed_name": seed_name,
            "last_update": current_time,
            "checked_locations": sorted(checked_location_names),
            "checked_location_ids": sorted(list(checked_locations)),
            "received_items": received_items,
            "slot_data": slot_data or {},
        }
        
        self._write_state(state)
        self.last_write_time = current_time
    
    def _write_state(self, state: dict) -> None:
        """Write state to the shared JSON file."""
        try:
            # Write to temp file first, then atomic rename
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Atomic replace
            temp_file.replace(self.state_file)
            logger.debug(f"Wrote tracker state to {self.state_file}")
            
        except Exception as e:
            logger.error(f"Failed to write tracker state to {self.state_file}: {e}")
            import traceback
            traceback.print_exc()
    
    def get_state_file_path(self) -> Path:
        """Get the path to the shared state file."""
        return self.state_file
    
    @staticmethod
    def read_tracker_state(shared_dir: Optional[Path] = None) -> Optional[dict]:
        """
        Read the current tracker state from the shared file.
        
        This is a static method that tracker applications can call to read state.
        
        Args:
            shared_dir: Directory containing the state file.
                       Defaults to:
                       - Windows: C:\\Users\\<username>\\.sshd_ap_tracker
                       - Linux/macOS: ~/.sshd_ap_tracker
        
        Returns:
            Dictionary containing tracker state, or None if file doesn't exist
        """
        if shared_dir is None:
            shared_dir = Path.home() / ".sshd_ap_tracker"
        
        state_file = Path(shared_dir) / "tracker_state.json"
        
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read tracker state: {e}")
            return None

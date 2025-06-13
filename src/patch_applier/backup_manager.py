"""
Backup Manager Component

This module provides comprehensive backup functionality for safe patch application.
"""

import os
import shutil
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .data_structures import BackupManifest, BackupEntry, PerforceStatus
from .config import BackupConfig
from .exceptions import BackupError


class BackupManager:
    """Comprehensive backup system for patch application safety."""
    
    def __init__(self, config: BackupConfig):
        """Initialize the backup manager with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def create_backup(self, files_to_backup: List[str], patch_id: str,
                     working_directory: str = ".") -> BackupManifest:
        """
        Create backups for a list of files before patch application.
        
        Args:
            files_to_backup: List of file paths to backup
            patch_id: Unique identifier for this patch
            working_directory: Base directory for file operations
            
        Returns:
            BackupManifest with backup information
        """
        if not self.config.enabled:
            self.logger.info("Backup disabled, skipping backup creation")
            return BackupManifest(
                patch_id=patch_id,
                backup_directory="",
                backup_timestamp=datetime.utcnow()
            )
        
        self.logger.info(f"Creating backup for patch {patch_id} with {len(files_to_backup)} files")
        
        # Create backup directory
        backup_dir = self._create_backup_directory(patch_id)
        
        # Initialize backup manifest
        manifest = BackupManifest(
            patch_id=patch_id,
            backup_directory=str(backup_dir),
            backup_timestamp=datetime.utcnow()
        )
        
        # Backup each file
        for file_path in files_to_backup:
            try:
                entry = self._backup_single_file(file_path, backup_dir, working_directory)
                if entry:
                    manifest.add_entry(entry)
            except Exception as e:
                self.logger.error(f"Failed to backup {file_path}: {e}")
                raise BackupError(f"Failed to backup {file_path}: {e}")
        
        # Save manifest to backup directory
        self._save_manifest(manifest)
        
        self.logger.info(f"Backup complete: {manifest.total_files} files, "
                        f"{manifest.total_size_bytes} bytes")
        
        return manifest
    
    def restore_backup(self, manifest: BackupManifest, 
                      working_directory: str = ".") -> List[str]:
        """
        Restore files from backup.
        
        Args:
            manifest: BackupManifest to restore from
            working_directory: Base directory for file operations
            
        Returns:
            List of successfully restored file paths
        """
        if not self.config.enabled:
            self.logger.info("Backup disabled, skipping restore")
            return []
        
        self.logger.info(f"Restoring backup for patch {manifest.patch_id}")
        
        restored_files = []
        
        for entry in manifest.entries:
            try:
                self._restore_single_file(entry, working_directory)
                restored_files.append(entry.original_path)
                self.logger.debug(f"Restored {entry.original_path}")
            except Exception as e:
                self.logger.error(f"Failed to restore {entry.original_path}: {e}")
                # Continue restoring other files
        
        self.logger.info(f"Restore complete: {len(restored_files)} files restored")
        return restored_files
    
    def cleanup_backup(self, manifest: BackupManifest) -> bool:
        """
        Clean up backup files.
        
        Args:
            manifest: BackupManifest to clean up
            
        Returns:
            True if cleanup was successful
        """
        if not self.config.auto_cleanup:
            self.logger.info("Auto cleanup disabled, keeping backup")
            return True
        
        try:
            backup_path = Path(manifest.backup_directory)
            if backup_path.exists():
                shutil.rmtree(backup_path)
                self.logger.info(f"Cleaned up backup directory: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cleanup backup: {e}")
            return False
    
    def _create_backup_directory(self, patch_id: str) -> Path:
        """Create backup directory for this patch."""
        base_dir = Path(self.config.backup_directory)
        
        if self.config.create_timestamp_dirs:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_dir = base_dir / f"{timestamp}_{patch_id}"
        else:
            backup_dir = base_dir / patch_id
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    def _backup_single_file(self, file_path: str, backup_dir: Path,
                           working_directory: str) -> Optional[BackupEntry]:
        """Backup a single file."""
        source_path = Path(working_directory) / file_path
        
        if not source_path.exists():
            self.logger.warning(f"Source file does not exist: {file_path}")
            return None
        
        # Create backup file path
        backup_file_path = backup_dir / file_path.replace('/', '_').replace('\\', '_')
        backup_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(source_path, backup_file_path)
        
        # Calculate checksum
        checksum = self._calculate_checksum(source_path)
        
        # Get file size
        file_size = source_path.stat().st_size
        
        return BackupEntry(
            original_path=file_path,
            backup_path=str(backup_file_path),
            file_size=file_size,
            checksum=checksum,
            backup_timestamp=datetime.utcnow(),
            perforce_status=None  # Will be set by Perforce manager if enabled
        )
    
    def _restore_single_file(self, entry: BackupEntry, working_directory: str):
        """Restore a single file from backup."""
        backup_path = Path(entry.backup_path)
        target_path = Path(working_directory) / entry.original_path
        
        if not backup_path.exists():
            raise BackupError(f"Backup file not found: {backup_path}")
        
        # Verify checksum if enabled
        if self.config.verify_checksums:
            current_checksum = self._calculate_checksum(backup_path)
            if current_checksum != entry.checksum:
                self.logger.warning(f"Checksum mismatch for {entry.original_path}")
        
        # Ensure target directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Restore file
        shutil.copy2(backup_path, target_path)
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _save_manifest(self, manifest: BackupManifest):
        """Save backup manifest to file."""
        manifest_path = Path(manifest.backup_directory) / "backup_manifest.json"
        
        import json
        with open(manifest_path, 'w') as f:
            json.dump(manifest.to_dict(), f, indent=2)
        
        self.logger.debug(f"Saved backup manifest: {manifest_path}") 
"""
Configuration management for Patch Applier component.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class PerforceConfig:
    """Configuration for Perforce integration."""
    enabled: bool = True
    p4_port: str = ""
    p4_user: str = ""
    p4_client: str = ""
    auto_checkout: bool = True
    auto_revert_on_failure: bool = True


@dataclass  
class BackupConfig:
    """Configuration for backup management."""
    enabled: bool = True
    backup_directory: str = ".patch_backups"
    create_timestamp_dirs: bool = True
    retain_backups: bool = True
    verify_checksums: bool = True


@dataclass
class ValidationConfig:
    """Configuration for patch validation."""
    check_file_existence: bool = True
    check_file_permissions: bool = True
    validate_syntax: bool = True
    detect_conflicts: bool = True
    min_confidence_for_auto_apply: float = 0.7


@dataclass
class SafetyConfig:
    """Configuration for safety mechanisms."""
    enable_rollback: bool = True
    automatic_rollback_on_failure: bool = True
    dry_run_mode: bool = False


@dataclass
class PatchApplierConfig:
    """Main configuration class for the Patch Applier."""
    
    perforce: PerforceConfig = field(default_factory=PerforceConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    
    working_directory: str = "."
    log_level: str = "INFO"
    
    @classmethod
    def create_default(cls) -> 'PatchApplierConfig':
        """Create a default configuration."""
        return cls() 
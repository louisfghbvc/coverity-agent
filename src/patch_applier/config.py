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
    p4_charset: str = ""
    p4_timeout: int = 30
    auto_checkout: bool = True
    auto_revert_on_failure: bool = True
    create_changelist: bool = True
    changelist_description_template: str = "Automated fix for Coverity defect {defect_id}: {defect_type}"
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass  
class BackupConfig:
    """Configuration for backup management."""
    enabled: bool = True
    backup_directory: str = ".patch_backups"
    create_timestamp_dirs: bool = True
    retain_backups: bool = True
    verify_checksums: bool = True
    max_backup_age_days: int = 30
    max_total_backups: int = 100
    compression_enabled: bool = False
    auto_cleanup: bool = True
    cleanup_on_success: bool = False


@dataclass
class ValidationConfig:
    """Configuration for patch validation."""
    check_file_existence: bool = True
    check_file_permissions: bool = True
    check_file_encoding: bool = True
    validate_syntax: bool = True
    check_line_endings: bool = True
    validate_patch_format: bool = True
    detect_conflicts: bool = True
    fuzzy_matching: bool = True
    fuzzy_threshold: float = 0.8
    max_files_per_patch: int = 10
    max_lines_per_file: int = 1000
    max_total_line_changes: int = 5000
    min_confidence_for_auto_apply: float = 0.7
    min_style_score_for_auto_apply: float = 0.6


@dataclass
class SafetyConfig:
    """Configuration for safety mechanisms."""
    enable_rollback: bool = True
    automatic_rollback_on_failure: bool = True
    rollback_timeout: int = 30
    dry_run_mode: bool = False
    require_clean_workspace: bool = False
    check_workspace_state: bool = True
    prevent_overwrite_uncommitted: bool = True
    require_confirmation: bool = False
    batch_size_limit: int = 50
    stop_on_first_error: bool = False
    max_consecutive_failures: int = 5


@dataclass
class PatchApplierConfig:
    """Main configuration class for the Patch Applier."""
    
    perforce: PerforceConfig = field(default_factory=PerforceConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    
    working_directory: str = "."
    temp_directory: str = ".patch_temp"
    log_level: str = "INFO"
    enable_progress_tracking: bool = True
    save_detailed_logs: bool = True
    parallel_processing: bool = False
    max_concurrent_patches: int = 1
    
    @classmethod
    def create_default(cls) -> 'PatchApplierConfig':
        """Create a default configuration."""
        return cls() 
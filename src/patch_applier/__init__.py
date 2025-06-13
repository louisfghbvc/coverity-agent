"""
Patch Applier Component

This module provides safe patch application functionality with comprehensive
validation, backup mechanisms, and Perforce integration for applying
generated patches to target codebases.
"""

from .patch_applier import PatchApplier
from .patch_validator import PatchValidator
from .backup_manager import BackupManager
from .perforce_manager import PerforceManager
from .data_structures import (
    PatchValidationResult,
    BackupManifest,
    PatchApplicationResult,
    PerforceWorkspaceState,
    AppliedChange,
    ApplicationStatus,
    ValidationSeverity,
    PerforceStatus,
    ValidationIssue,
    BackupEntry,
    PerforceFileInfo,
    FileModification
)
from .config import PatchApplierConfig
from .exceptions import (
    PatchApplierError,
    PatchValidationError,
    BackupError,
    PerforceError,
    PatchApplicationError
)

__all__ = [
    # Main classes
    'PatchApplier',
    'PatchValidator',
    'BackupManager', 
    'PerforceManager',
    
    # Data structures
    'PatchValidationResult',
    'BackupManifest',
    'PatchApplicationResult',
    'PerforceWorkspaceState',
    'AppliedChange',
    'ValidationIssue',
    'BackupEntry',
    'PerforceFileInfo',
    'FileModification',
    
    # Enums
    'ApplicationStatus',
    'ValidationSeverity',
    'PerforceStatus',
    
    # Configuration
    'PatchApplierConfig',
    
    # Exceptions
    'PatchApplierError',
    'PatchValidationError',
    'BackupError',
    'PerforceError',
    'PatchApplicationError'
] 
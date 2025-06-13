"""
Patch Applier Component

This module provides safe patch application functionality with comprehensive
validation, backup mechanisms, and Perforce integration for applying
generated patches to target codebases.
"""

from .patch_applier import PatchApplier
from .data_structures import (
    PatchValidationResult,
    BackupManifest,
    PatchApplicationResult,
    PerforceWorkspaceState,
    AppliedChange
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
    'PatchApplier',
    'PatchValidationResult',
    'BackupManifest',
    'PatchApplicationResult',
    'PerforceWorkspaceState',
    'AppliedChange',
    'PatchApplierConfig',
    'PatchApplierError',
    'PatchValidationError',
    'BackupError',
    'PerforceError',
    'PatchApplicationError'
] 
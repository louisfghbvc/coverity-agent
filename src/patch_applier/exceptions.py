"""
Patch Applier Exceptions

Exception classes for the patch applier component.
"""


class PatchApplierError(Exception):
    """Base exception for patch applier errors."""
    pass


class PatchValidationError(PatchApplierError):
    """Exception raised when patch validation fails."""
    pass


class BackupError(PatchApplierError):
    """Exception raised when backup operations fail."""
    pass


class PerforceError(PatchApplierError):
    """Exception raised when Perforce operations fail."""
    pass


class PatchApplicationError(PatchApplierError):
    """Exception raised when patch application fails."""
    pass


class FileAccessError(PatchApplierError):
    """Exception raised when file access operations fail."""
    pass


class WorkspaceStateError(PatchApplierError):
    """Exception raised when workspace state is invalid."""
    pass


class RollbackError(PatchApplierError):
    """Exception raised when rollback operations fail."""
    pass 
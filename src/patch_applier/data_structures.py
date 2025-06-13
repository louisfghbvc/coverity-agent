"""
Data structures for Patch Applier component.

This module defines the core data structures used for patch validation,
backup management, Perforce integration, and patch application results.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class PerforceStatus(Enum):
    """Perforce file status."""
    EDIT = "edit"
    ADD = "add"
    DELETE = "delete"
    INTEGRATE = "integrate"
    UNKNOWN = "unknown"
    NOT_IN_P4 = "not_in_p4"


class ApplicationStatus(Enum):
    """Status of patch application."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    
    severity: ValidationSeverity
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "details": self.details
        }


@dataclass
class PatchValidationResult:
    """Result of patch validation with detailed feedback."""
    
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    files_to_modify: List[str] = field(default_factory=list)
    files_missing: List[str] = field(default_factory=list)
    conflicts_detected: List[Dict[str, Any]] = field(default_factory=list)
    validation_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has any errors."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation has any warnings."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)
    
    @property
    def error_count(self) -> int:
        """Count of error-level validation issues."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level validation issues."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING)
    
    def add_issue(self, severity: ValidationSeverity, message: str, 
                 file_path: Optional[str] = None, line_number: Optional[int] = None,
                 details: Optional[Dict[str, Any]] = None):
        """Add a validation issue."""
        self.issues.append(ValidationIssue(
            severity=severity,
            message=message,
            file_path=file_path,
            line_number=line_number,
            details=details or {}
        ))
        
        # Update validation status if we have errors
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "issues": [issue.to_dict() for issue in self.issues],
            "files_to_modify": self.files_to_modify,
            "files_missing": self.files_missing,
            "conflicts_detected": self.conflicts_detected,
            "validation_timestamp": self.validation_timestamp.isoformat(),
            "error_count": self.error_count,
            "warning_count": self.warning_count
        }


@dataclass
class BackupEntry:
    """Represents a single file backup entry."""
    
    original_path: str
    backup_path: str
    file_size: int
    checksum: str
    backup_timestamp: datetime
    perforce_status: Optional[PerforceStatus] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "original_path": self.original_path,
            "backup_path": self.backup_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "backup_timestamp": self.backup_timestamp.isoformat(),
            "perforce_status": self.perforce_status.value if self.perforce_status else None
        }


@dataclass
class BackupManifest:
    """Comprehensive backup manifest for patch application."""
    
    patch_id: str
    backup_directory: str
    backup_timestamp: datetime
    entries: List[BackupEntry] = field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0
    perforce_workspace: Optional[str] = None
    
    def __post_init__(self):
        """Calculate derived fields."""
        self.total_files = len(self.entries)
        self.total_size_bytes = sum(entry.file_size for entry in self.entries)
    
    def add_entry(self, entry: BackupEntry):
        """Add a backup entry to the manifest."""
        self.entries.append(entry)
        self.total_files = len(self.entries)
        self.total_size_bytes = sum(entry.file_size for entry in self.entries)
    
    def get_entry_by_path(self, original_path: str) -> Optional[BackupEntry]:
        """Get backup entry by original file path."""
        for entry in self.entries:
            if entry.original_path == original_path:
                return entry
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "patch_id": self.patch_id,
            "backup_directory": self.backup_directory,
            "backup_timestamp": self.backup_timestamp.isoformat(),
            "entries": [entry.to_dict() for entry in self.entries],
            "total_files": self.total_files,
            "total_size_bytes": self.total_size_bytes,
            "perforce_workspace": self.perforce_workspace
        }


@dataclass
class PerforceFileInfo:
    """Information about a file in Perforce."""
    
    depot_path: str
    client_path: str
    status: PerforceStatus
    head_revision: Optional[str] = None
    have_revision: Optional[str] = None
    action: Optional[str] = None
    change: Optional[str] = None
    user: Optional[str] = None
    locked: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "depot_path": self.depot_path,
            "client_path": self.client_path,
            "status": self.status.value,
            "head_revision": self.head_revision,
            "have_revision": self.have_revision,
            "action": self.action,
            "change": self.change,
            "user": self.user,
            "locked": self.locked
        }


@dataclass
class PerforceWorkspaceState:
    """State of Perforce workspace for patch application."""
    
    workspace_name: str
    user: str
    root_directory: str
    files_info: List[PerforceFileInfo] = field(default_factory=list)
    has_pending_changes: bool = False
    default_changelist_description: str = ""
    validation_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def get_file_info(self, file_path: str) -> Optional[PerforceFileInfo]:
        """Get Perforce info for a specific file."""
        for file_info in self.files_info:
            if file_info.client_path == file_path or file_info.depot_path.endswith(file_path):
                return file_info
        return None
    
    def add_file_info(self, file_info: PerforceFileInfo):
        """Add file information to workspace state."""
        self.files_info.append(file_info)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "workspace_name": self.workspace_name,
            "user": self.user,
            "root_directory": self.root_directory,
            "files_info": [info.to_dict() for info in self.files_info],
            "has_pending_changes": self.has_pending_changes,
            "default_changelist_description": self.default_changelist_description,
            "validation_timestamp": self.validation_timestamp.isoformat()
        }


@dataclass
class FileModification:
    """Represents a single file modification during patch application."""
    
    file_path: str
    original_content: str
    modified_content: str
    lines_added: int
    lines_removed: int
    lines_changed: int
    modification_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_changes(self) -> int:
        """Total number of line changes."""
        return self.lines_added + self.lines_removed + self.lines_changed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file_path": self.file_path,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "lines_changed": self.lines_changed,
            "total_changes": self.total_changes,
            "modification_timestamp": self.modification_timestamp.isoformat()
        }


@dataclass
class AppliedChange:
    """Result of applying changes to target codebase."""
    
    # Original defect information
    defect_id: str
    file_path: str
    line_number: int
    
    # Applied fix information
    fix_candidate_index: int
    applied_content: str
    confidence_score: float
    
    # Application metadata
    application_timestamp: datetime = field(default_factory=datetime.utcnow)
    backup_manifest: Optional[BackupManifest] = None
    perforce_operations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Modification details
    modifications: List[FileModification] = field(default_factory=list)
    
    # Status tracking
    status: ApplicationStatus = ApplicationStatus.SUCCESS
    error_message: Optional[str] = None
    rollback_available: bool = True
    
    def add_modification(self, modification: FileModification):
        """Add a file modification to the applied change."""
        self.modifications.append(modification)
    
    def get_total_line_changes(self) -> int:
        """Get total line changes across all modified files."""
        return sum(mod.total_changes for mod in self.modifications)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "defect_id": self.defect_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "fix_candidate_index": self.fix_candidate_index,
            "confidence_score": self.confidence_score,
            "application_timestamp": self.application_timestamp.isoformat(),
            "backup_manifest": self.backup_manifest.to_dict() if self.backup_manifest else None,
            "perforce_operations": self.perforce_operations,
            "modifications": [mod.to_dict() for mod in self.modifications],
            "status": self.status.value,
            "error_message": self.error_message,
            "rollback_available": self.rollback_available,
            "total_line_changes": self.get_total_line_changes()
        }


@dataclass
class PatchApplicationResult:
    """Comprehensive result of patch application operation."""
    
    # Application metadata
    patch_id: str
    defect_analysis_result: Any  # DefectAnalysisResult from fix_generator
    application_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Results
    applied_changes: List[AppliedChange] = field(default_factory=list)
    validation_result: Optional[PatchValidationResult] = None
    workspace_state: Optional[PerforceWorkspaceState] = None
    
    # Status tracking
    overall_status: ApplicationStatus = ApplicationStatus.SUCCESS
    success_count: int = 0
    failure_count: int = 0
    
    # Performance metrics
    processing_time_seconds: float = 0.0
    total_files_modified: int = 0
    total_line_changes: int = 0
    
    # Error handling
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived metrics."""
        self.success_count = sum(1 for change in self.applied_changes 
                               if change.status == ApplicationStatus.SUCCESS)
        self.failure_count = len(self.applied_changes) - self.success_count
        self.total_files_modified = len(set(change.file_path for change in self.applied_changes))
        self.total_line_changes = sum(change.get_total_line_changes() for change in self.applied_changes)
        
        # Determine overall status
        if self.failure_count == 0:
            self.overall_status = ApplicationStatus.SUCCESS
        elif self.success_count > 0:
            self.overall_status = ApplicationStatus.PARTIAL
        else:
            self.overall_status = ApplicationStatus.FAILED
    
    def add_applied_change(self, change: AppliedChange):
        """Add an applied change to the result."""
        self.applied_changes.append(change)
        self.__post_init__()  # Recalculate metrics
    
    def add_error(self, error_message: str):
        """Add an error message."""
        self.errors.append(error_message)
    
    def add_warning(self, warning_message: str):
        """Add a warning message."""
        self.warnings.append(warning_message)
    
    @property
    def is_successful(self) -> bool:
        """Check if the patch application was successful."""
        return self.overall_status == ApplicationStatus.SUCCESS
    
    @property
    def has_failures(self) -> bool:
        """Check if there were any failures."""
        return self.failure_count > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the patch application results."""
        return {
            "patch_id": self.patch_id,
            "overall_status": self.overall_status.value,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_files_modified": self.total_files_modified,
            "total_line_changes": self.total_line_changes,
            "processing_time_seconds": self.processing_time_seconds,
            "has_errors": len(self.errors) > 0,
            "has_warnings": len(self.warnings) > 0,
            "application_timestamp": self.application_timestamp.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "patch_id": self.patch_id,
            "application_timestamp": self.application_timestamp.isoformat(),
            "applied_changes": [change.to_dict() for change in self.applied_changes],
            "validation_result": self.validation_result.to_dict() if self.validation_result else None,
            "workspace_state": self.workspace_state.to_dict() if self.workspace_state else None,
            "overall_status": self.overall_status.value,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "processing_time_seconds": self.processing_time_seconds,
            "total_files_modified": self.total_files_modified,
            "total_line_changes": self.total_line_changes,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self.get_summary()
        } 
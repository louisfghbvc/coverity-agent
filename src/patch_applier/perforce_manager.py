"""
Perforce Manager Component

This module provides basic Perforce integration for patch application,
including file checkout, workspace validation, and changelist management.
"""

import subprocess
import logging
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from .data_structures import (
    PerforceWorkspaceState, PerforceFileInfo, PerforceStatus
)
from .config import PerforceConfig
from .exceptions import PerforceError


class PerforceManager:
    """Basic Perforce integration for patch application."""
    
    def __init__(self, config: PerforceConfig):
        """Initialize the Perforce manager with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Cache for workspace-specific configurations
        self._workspace_configs = {}
        
        # Set Perforce environment variables
        if config.enabled:
            self._setup_perforce_environment()
    
    def validate_workspace(self) -> PerforceWorkspaceState:
        """
        Validate the current Perforce workspace state.
        
        Returns:
            PerforceWorkspaceState with workspace information
        """
        if not self.config.enabled:
            self.logger.info("Perforce disabled, skipping workspace validation")
            return PerforceWorkspaceState(
                workspace_name="disabled",
                user="disabled",
                root_directory=".",
                has_pending_changes=False
            )
        
        self.logger.info("Validating Perforce workspace")
        
        try:
            # Get workspace info
            workspace_info = self._run_p4_command(['info'])
            
            # Parse workspace information
            workspace_name = self._extract_field(workspace_info, 'Client name')
            user = self._extract_field(workspace_info, 'User name')
            root_directory = self._extract_field(workspace_info, 'Client root')
            
            # Check for pending changes
            pending_changes = self._run_p4_command(['opened'])
            has_pending = bool(pending_changes.strip())
            
            workspace_state = PerforceWorkspaceState(
                workspace_name=workspace_name or "unknown",
                user=user or "unknown",
                root_directory=root_directory or ".",
                has_pending_changes=has_pending
            )
            
            self.logger.info(f"Workspace validated: {workspace_name} ({user})")
            return workspace_state
            
        except Exception as e:
            self.logger.error(f"Failed to validate workspace: {e}")
            raise PerforceError(f"Workspace validation failed: {e}")
    
    def prepare_files_for_edit(self, file_paths: List[str], 
                              working_directory: str = ".") -> List[PerforceFileInfo]:
        """
        Prepare files for editing in Perforce (p4 edit).
        
        Args:
            file_paths: List of files to prepare for editing
            working_directory: Base directory for file operations
            
        Returns:
            List of PerforceFileInfo for prepared files
        """
        if not self.config.enabled:
            self.logger.info("Perforce disabled, skipping file preparation")
            return []
        
        if not self.config.auto_checkout:
            self.logger.info("Auto checkout disabled, skipping p4 edit")
            return []
        
        self.logger.info(f"Preparing {len(file_paths)} files for edit")
        
        file_infos = []
        
        for file_path in file_paths:
            try:
                file_info = self._prepare_single_file(file_path, working_directory)
                if file_info:
                    file_infos.append(file_info)
            except Exception as e:
                self.logger.error(f"Failed to prepare {file_path}: {e}")
                if self.config.auto_revert_on_failure:
                    self._revert_file(file_path)
                raise PerforceError(f"Failed to prepare {file_path}: {e}")
        
        self.logger.info(f"Prepared {len(file_infos)} files for edit")
        return file_infos
    
    def revert_files(self, file_paths: List[str]) -> List[str]:
        """
        Revert files in Perforce (p4 revert).
        
        Args:
            file_paths: List of files to revert
            
        Returns:
            List of successfully reverted files
        """
        if not self.config.enabled:
            self.logger.info("Perforce disabled, skipping revert")
            return []
        
        self.logger.info(f"Reverting {len(file_paths)} files")
        
        reverted_files = []
        
        for file_path in file_paths:
            try:
                self._revert_file(file_path)
                reverted_files.append(file_path)
            except Exception as e:
                self.logger.error(f"Failed to revert {file_path}: {e}")
                # Continue reverting other files
        
        self.logger.info(f"Reverted {len(reverted_files)} files")
        return reverted_files
    
    def create_changelist(self, description: str, files: List[str]) -> Optional[str]:
        """
        Create a new changelist with specified files.
        
        Args:
            description: Changelist description
            files: List of files to include
            
        Returns:
            Changelist number if successful, None otherwise
        """
        if not self.config.enabled or not self.config.create_changelist:
            self.logger.info("Changelist creation disabled")
            return None
        
        self.logger.info(f"Creating changelist with {len(files)} files")
        
        try:
            # Create changelist specification
            changelist_spec = self._create_changelist_spec(description, files)
            
            # Submit changelist spec to Perforce
            result = self._run_p4_command(['change', '-i'], input_data=changelist_spec)
            
            # Extract changelist number
            changelist_number = self._extract_changelist_number(result)
            
            self.logger.info(f"Created changelist: {changelist_number}")
            return changelist_number
            
        except Exception as e:
            self.logger.error(f"Failed to create changelist: {e}")
            return None
    
    def get_file_status(self, file_path: str, working_directory: str = ".") -> PerforceFileInfo:
        """
        Get Perforce status for a single file.
        
        Args:
            file_path: Path to the file
            working_directory: Base directory for file operations
            
        Returns:
            PerforceFileInfo with file status
        """
        if not self.config.enabled:
            return PerforceFileInfo(
                depot_path="",
                client_path=file_path,
                status=PerforceStatus.NOT_IN_P4
            )
        
        try:
            full_path = str(Path(working_directory) / file_path)
            
            # Get workspace-specific configuration for this file
            workspace_config = self._get_workspace_config_for_file(full_path)
            workspace_dir = self._find_workspace_for_file(full_path)
            
            # Check if file is in Perforce
            fstat_result = self._run_p4_command(
                ['fstat', full_path], 
                workspace_config=workspace_config,
                cwd=workspace_dir
            )
            
            if not fstat_result.strip():
                return PerforceFileInfo(
                    depot_path="",
                    client_path=file_path,
                    status=PerforceStatus.NOT_IN_P4
                )
            
            # Parse fstat output
            return self._parse_fstat_output(fstat_result, file_path)
            
        except Exception as e:
            self.logger.warning(f"Failed to get file status for {file_path}: {e}")
            return PerforceFileInfo(
                depot_path="",
                client_path=file_path,
                status=PerforceStatus.UNKNOWN
            )
    
    def _setup_perforce_environment(self):
        """Setup Perforce environment variables."""
        if self.config.p4_port:
            os.environ['P4PORT'] = self.config.p4_port
        if self.config.p4_user:
            os.environ['P4USER'] = self.config.p4_user
        if self.config.p4_client:
            os.environ['P4CLIENT'] = self.config.p4_client
        if self.config.p4_charset:
            os.environ['P4CHARSET'] = self.config.p4_charset
    
    def _find_workspace_for_file(self, file_path: str) -> Optional[str]:
        """
        Find the Perforce workspace directory that contains the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Path to workspace directory containing .p4config, or None
        """
        file_path = Path(file_path).resolve()
        current_dir = file_path.parent if file_path.is_file() else file_path
        
        # Look up the directory tree for .p4config
        while current_dir != current_dir.parent:
            p4config_path = current_dir / '.p4config'
            if p4config_path.exists():
                self.logger.debug(f"Found .p4config in {current_dir}")
                return str(current_dir)
            current_dir = current_dir.parent
        
        return None
    
    def _read_p4config(self, workspace_dir: str) -> Dict[str, str]:
        """
        Read .p4config file from workspace directory.
        
        Args:
            workspace_dir: Path to workspace directory
            
        Returns:
            Dictionary of Perforce environment variables
        """
        if workspace_dir in self._workspace_configs:
            return self._workspace_configs[workspace_dir]
        
        p4config_path = Path(workspace_dir) / '.p4config'
        config = {}
        
        try:
            with open(p4config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
            
            self.logger.debug(f"Loaded .p4config from {workspace_dir}: {list(config.keys())}")
            
            # Cache the configuration
            self._workspace_configs[workspace_dir] = config
            
        except Exception as e:
            self.logger.warning(f"Failed to read .p4config from {workspace_dir}: {e}")
        
        return config
    
    def _get_workspace_config_for_file(self, file_path: str) -> Dict[str, str]:
        """
        Get workspace-specific Perforce configuration for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary of Perforce environment variables for the workspace
        """
        workspace_dir = self._find_workspace_for_file(file_path)
        workspace_config = {}
        
        if workspace_dir:
            workspace_config = self._read_p4config(workspace_dir)
            self.logger.info(f"Using workspace config from {workspace_dir}: P4CLIENT={workspace_config.get('P4CLIENT', 'not set')}")
        
        # Merge with global configuration as fallback
        config = {
            'P4PORT': self.config.p4_port or '',
            'P4USER': self.config.p4_user or '',
            'P4CLIENT': self.config.p4_client or '',
            'P4CHARSET': self.config.p4_charset or ''
        }
        
        # Override with workspace-specific values
        config.update(workspace_config)
        
        # Remove empty values
        config = {k: v for k, v in config.items() if v}
        
        return config
    
    def _run_p4_command(self, args: List[str], input_data: str = None, 
                       workspace_config: Dict[str, str] = None, 
                       cwd: str = None) -> str:
        """
        Run a Perforce command and return output.
        
        Args:
            args: Perforce command arguments
            input_data: Input data for stdin
            workspace_config: Workspace-specific P4 environment variables
            cwd: Working directory to run command from
        """
        cmd = ['p4'] + args
        
        # Prepare environment with workspace-specific config
        env = os.environ.copy()
        if workspace_config:
            env.update(workspace_config)
        
        try:
            if input_data:
                result = subprocess.run(
                    cmd,
                    input=input_data,
                    text=True,
                    capture_output=True,
                    timeout=self.config.p4_timeout,
                    check=True,
                    env=env,
                    cwd=cwd
                )
            else:
                result = subprocess.run(
                    cmd,
                    text=True,
                    capture_output=True,
                    timeout=self.config.p4_timeout,
                    check=True,
                    env=env,
                    cwd=cwd
                )
            
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            raise PerforceError(f"Perforce command failed: {' '.join(cmd)}\n{e.stderr}")
        except subprocess.TimeoutExpired:
            raise PerforceError(f"Perforce command timed out: {' '.join(cmd)}")
    
    def _prepare_single_file(self, file_path: str, working_directory: str) -> Optional[PerforceFileInfo]:
        """Prepare a single file for editing."""
        full_path = str(Path(working_directory) / file_path)
        
        # Get current file status
        file_info = self.get_file_status(file_path, working_directory)
        
        if file_info.status == PerforceStatus.NOT_IN_P4:
            self.logger.warning(f"File not in Perforce: {file_path}")
            return None
        
        # Check out file for edit
        try:
            # Get workspace-specific configuration for this file
            workspace_config = self._get_workspace_config_for_file(full_path)
            workspace_dir = self._find_workspace_for_file(full_path)
            
            self._run_p4_command(
                ['edit', full_path], 
                workspace_config=workspace_config,
                cwd=workspace_dir
            )
            
            # Update status
            file_info.status = PerforceStatus.EDIT
            file_info.action = "edit"
            
            return file_info
            
        except PerforceError as e:
            self.logger.error(f"Failed to edit {file_path}: {e}")
            raise
    
    def _revert_file(self, file_path: str):
        """Revert a single file."""
        try:
            # Get workspace-specific configuration for this file
            workspace_config = self._get_workspace_config_for_file(file_path)
            workspace_dir = self._find_workspace_for_file(file_path)
            
            self._run_p4_command(
                ['revert', file_path], 
                workspace_config=workspace_config,
                cwd=workspace_dir
            )
            self.logger.debug(f"Reverted {file_path}")
        except PerforceError as e:
            self.logger.error(f"Failed to revert {file_path}: {e}")
            raise
    
    def _extract_field(self, p4_info: str, field_name: str) -> Optional[str]:
        """Extract a field value from p4 info output."""
        for line in p4_info.splitlines():
            if line.startswith(f"{field_name}: "):
                return line.split(": ", 1)[1]
        return None
    
    def _parse_fstat_output(self, fstat_output: str, file_path: str) -> PerforceFileInfo:
        """Parse p4 fstat output into PerforceFileInfo."""
        info = PerforceFileInfo(
            depot_path="",
            client_path=file_path,
            status=PerforceStatus.UNKNOWN
        )
        
        for line in fstat_output.splitlines():
            if line.startswith("... depotFile "):
                info.depot_path = line.split(" ", 2)[2]
            elif line.startswith("... clientFile "):
                info.client_path = line.split(" ", 2)[2]
            elif line.startswith("... headRev "):
                info.head_revision = line.split(" ", 2)[2]
            elif line.startswith("... haveRev "):
                info.have_revision = line.split(" ", 2)[2]
            elif line.startswith("... action "):
                action = line.split(" ", 2)[2]
                info.action = action
                if action == "edit":
                    info.status = PerforceStatus.EDIT
                elif action == "add":
                    info.status = PerforceStatus.ADD
                elif action == "delete":
                    info.status = PerforceStatus.DELETE
        
        return info
    
    def _create_changelist_spec(self, description: str, files: List[str]) -> str:
        """Create a changelist specification."""
        spec_lines = [
            "Change: new",
            f"Description:",
            f"\t{description}",
            "",
            "Files:"
        ]
        
        for file_path in files:
            spec_lines.append(f"\t{file_path}")
        
        return "\n".join(spec_lines)
    
    def _extract_changelist_number(self, change_output: str) -> Optional[str]:
        """Extract changelist number from p4 change output."""
        for line in change_output.splitlines():
            if line.startswith("Change ") and " created" in line:
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
        return None 
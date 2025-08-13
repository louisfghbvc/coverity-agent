# Patch Applier + Git Hook - Feature Plan

## Overview
Apply generated patches to the target codebase with comprehensive Git integration, providing safe patch application, rollback capabilities, and automated version control management.

## Requirements

### Functional Requirements
- **FR1**: Apply patches safely with validation and rollback
- **FR2**: Create Git commits with descriptive messages
- **FR3**: Generate comprehensive diffs for review
- **FR4**: Handle merge conflicts and resolution strategies
- **FR5**: Support batch patch application
- **FR6**: Integrate with Git hooks for automation
- **FR7**: Create branch management for fix isolation
- **FR8**: Generate pull request templates (optional)

### Non-Functional Requirements
- **NFR1**: Apply 100+ patches per hour safely
- **NFR2**: Zero data loss with comprehensive backup
- **NFR3**: Support large repositories (>100k files)
- **NFR4**: Minimal performance impact on Git operations

## Technical Design

### Core Components

#### 1. Patch Validator
```python
class PatchValidator:
    def validate_patch(self, patch: GeneratedPatch, target_repo: str) -> ValidationResult:
        """Validate patch before application"""
        
        # Check file existence and permissions
        file_checks = self._validate_target_files(patch.modified_files, target_repo)
        
        # Validate patch format
        format_checks = self._validate_patch_format(patch)
        
        # Check for conflicts with working directory
        conflict_checks = self._check_working_directory_conflicts(patch, target_repo)
        
        return ValidationResult(
            is_valid=all([file_checks, format_checks, conflict_checks]),
            validation_errors=self._collect_errors(),
            warnings=self._collect_warnings()
        )
```

#### 2. Git Manager
```python
class GitManager:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo = git.Repo(repo_path)
        
    def create_fix_branch(self, defect_id: str) -> str:
        """Create isolated branch for fix"""
        branch_name = f"fix/coverity-defect-{defect_id}"
        
        # Ensure clean working directory
        if self.repo.is_dirty():
            raise GitStateError("Working directory has uncommitted changes")
            
        # Create and checkout new branch
        fix_branch = self.repo.create_head(branch_name)
        fix_branch.checkout()
        
        return branch_name
    
    def commit_patch(self, patch: GeneratedPatch, message_template: str) -> str:
        """Commit applied patch with descriptive message"""
        
        # Stage modified files
        for file_path in patch.modified_files.keys():
            self.repo.index.add([file_path])
        
        # Generate commit message
        commit_message = self._generate_commit_message(patch, message_template)
        
        # Create commit
        commit = self.repo.index.commit(commit_message)
        
        return commit.hexsha
```

#### 3. Backup Manager
```python
class BackupManager:
    def __init__(self, backup_dir: str):
        self.backup_dir = backup_dir
        
    def create_backup(self, files: List[str], patch_id: str) -> str:
        """Create backup of files before modification"""
        
        backup_path = os.path.join(self.backup_dir, f"backup_{patch_id}")
        os.makedirs(backup_path, exist_ok=True)
        
        backup_manifest = []
        
        for file_path in files:
            if os.path.exists(file_path):
                backup_file = os.path.join(backup_path, 
                                         file_path.replace('/', '_'))
                shutil.copy2(file_path, backup_file)
                backup_manifest.append({
                    "original": file_path,
                    "backup": backup_file,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Save manifest
        manifest_path = os.path.join(backup_path, "manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(backup_manifest, f, indent=2)
            
        return backup_path
```

#### 4. Conflict Resolver
```python
class ConflictResolver:
    def __init__(self):
        self.resolution_strategies = {
            "auto_merge": self._auto_merge_strategy,
            "prefer_patch": self._prefer_patch_strategy,
            "prefer_original": self._prefer_original_strategy,
            "manual_review": self._manual_review_strategy
        }
    
    def resolve_conflicts(self, conflicts: List[Conflict], 
                         strategy: str = "auto_merge") -> ResolutionResult:
        """Resolve merge conflicts using specified strategy"""
        
        resolver = self.resolution_strategies.get(strategy, 
                                                self._manual_review_strategy)
        
        resolutions = []
        for conflict in conflicts:
            resolution = resolver(conflict)
            resolutions.append(resolution)
        
        return ResolutionResult(
            resolutions=resolutions,
            requires_manual_review=any(r.needs_review for r in resolutions),
            success_rate=len([r for r in resolutions if r.resolved]) / len(resolutions)
        )
```

## Implementation Plan

### Phase 1: Core Patch Application (Week 1)
- Basic patch application engine
- File backup and restore mechanisms
- Git integration foundation
- Safety validation framework

### Phase 2: Advanced Git Features (Week 2)
- Branch management automation
- Commit message generation
- Conflict detection and basic resolution
- Working directory state management

### Phase 3: Automation & Integration (Week 3)
- Git hooks integration
- Batch processing capabilities
- Pull request automation
- Advanced conflict resolution

### Phase 4: Production Features (Week 4)
- Comprehensive error handling
- Performance optimization
- Monitoring and logging
- Integration testing

## Configuration

```yaml
# patch_applier_config.yaml
patch_applier:
  git:
    auto_create_branches: true
    branch_prefix: "fix/coverity-defect"
    commit_message_template: |
      Fix Coverity defect: {defect_type}
      
      - Defect ID: {defect_id}
      - File: {primary_file}
      - Strategy: {fix_strategy}
      - Confidence: {confidence_score}
      
      Generated by Coverity Agent
    
  safety:
    enable_backups: true
    backup_retention_days: 30
    require_clean_working_dir: true
    validate_before_apply: true
    
  conflict_resolution:
    default_strategy: "auto_merge"
    manual_review_threshold: 0.7
    auto_resolve_simple_conflicts: true
    
  automation:
    enable_git_hooks: false
    auto_create_pr: false
    pr_template_path: ".github/pull_request_template.md"
```

## Success Metrics

- **Application Success Rate**: >95% successful patch application
- **Safety**: Zero data loss incidents
- **Performance**: <5 seconds average application time per patch
- **Git Integration**: 100% proper commit creation and branch management

## Integration Points

### Upstream Dependencies
- Fix Generator (generated patches)
- Git repository access
- File system permissions

### Downstream Consumers
- Verification system (applied changes)
- Git history and branch management
- Pull request systems (optional)

## Risk Mitigation

### Technical Risks
- **Data Loss**: Comprehensive backup system
- **Git Corruption**: Repository validation and recovery procedures
- **Merge Conflicts**: Multiple resolution strategies
- **Performance Issues**: Efficient file operations and Git usage

### Implementation Approach
- Extensive testing with disposable repositories
- Incremental feature rollout with safety validation
- Comprehensive backup and rollback mechanisms
- Conservative conflict resolution with manual review options 
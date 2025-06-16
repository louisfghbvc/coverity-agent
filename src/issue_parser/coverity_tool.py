"""
Coverity Report Tool - Core Analysis Tool

This module provides the core CoverityReportTool class for processing Coverity static 
code analysis reports, including querying issues, generating fix prompts, and 
summarizing issues.

Extracted from the original MCP server implementation and adapted for pipeline usage.
"""

import json
import os
import re
from typing import Dict, List, Optional, Any, Tuple

from .exceptions import CoverityError, ReportNotFoundError, InvalidReportError


class CoverityReportTool:
    """Tool for analyzing and fixing Coverity issues."""

    # Default paths to exclude from all queries
    DEFAULT_EXCLUDE_PATHS = ["DebugUtils/*"]

    def __init__(self, report_path: str = None):
        """Initialize the Coverity Report Tool.
        
        Args:
            report_path: Path to the Coverity report file
        """
        self.report_path = report_path or 'report.json'
        self._data = None
        
    def set_report_path(self, report_path: str) -> None:
        """Set a new path for the Coverity report file.
        
        Args:
            report_path: New path to the Coverity report file
        """
        self.report_path = report_path
        # Reset data to force reload from new path
        self._data = None
        
    def get_report_path(self) -> str:
        """Get the current path of the Coverity report file.
        
        Returns:
            The current report file path
        """
        return self.report_path

    def load_report(self) -> Dict[str, Any]:
        """Load the Coverity report from file.
        
        Returns:
            The loaded report data
            
        Raises:
            ReportNotFoundError: If the report file is not found
            InvalidReportError: If the report file is invalid
        """
        if not os.path.exists(self.report_path):
            raise ReportNotFoundError(f"Report file not found: {self.report_path}")
            
        try:
            with open(self.report_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not isinstance(data, dict):
                raise InvalidReportError("Report file is not a valid JSON object")
            
            if 'issues' not in data:
                raise InvalidReportError("Report file does not contain 'issues' field")
                
            self._data = data
            return data
        except json.JSONDecodeError:
            raise InvalidReportError("Report file is not valid JSON")
        except (OSError, IOError) as e:
            raise InvalidReportError(f"Error reading report file: {e}")
    
    def get_data(self) -> Dict[str, Any]:
        """Get the report data, loading it if not already loaded.
        
        Returns:
            The report data
            
        Raises:
            ReportNotFoundError: If the report file is not found
            InvalidReportError: If the report file is invalid
        """
        if self._data is None:
            self._data = self.load_report()
        return self._data
    
    def path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches an exclusion pattern.
        
        Args:
            path: The file path to check
            pattern: The exclusion pattern (supports glob-style wildcards)
            
        Returns:
            True if the path matches the pattern, False otherwise
        """
        # Handle directory wildcards (e.g., "DebugUtils/*")
        if pattern.endswith('/*'):
            # For directory patterns, check if the path contains the directory
            dir_name = pattern[:-2]  # Remove /*
            return f"/{dir_name}/" in path or path.startswith(f"{dir_name}/") or f"/{dir_name}" in path
        
        # Convert glob-style pattern to regex pattern for other cases
        # Escape special regex characters except * and ?
        regex_pattern = re.escape(pattern).replace('\\*', '.*').replace('\\?', '.')
        regex_pattern = f"^{regex_pattern}$"
        
        # Compile and match
        try:
            regex = re.compile(regex_pattern)
            return bool(regex.match(path))
        except re.error:
            # If there's an error in the regex, fall back to simple matching
            return path == pattern
    
    def query_issues_by_category(self, category: str, exclude_paths: List[str] = None) -> List[Dict[str, Any]]:
        """Query issues by category (case-insensitive match).
        
        Args:
            category: The category to filter issues by
            exclude_paths: List of path patterns to exclude (e.g. ["DebugUtils/*"])
                           If None, DEFAULT_EXCLUDE_PATHS will be used
            
        Returns:
            List of issues matching the category
        """
        data = self.get_data()
        issues = data.get('issues', [])
        
        # Filter by category and fixed status
        filtered_issues = [issue for issue in issues 
                if issue.get('checkerName', '').lower() == category.lower() 
                and not issue.get('fixed', False)]
        
        # Use default exclude paths if none provided
        if exclude_paths is None:
            exclude_paths = self.DEFAULT_EXCLUDE_PATHS
        elif len(exclude_paths) == 0:
            # Empty list means no exclusion
            return filtered_issues
        
        # Apply path exclusion
        result = []
        for issue in filtered_issues:
            file_path = issue.get('mainEventFilePathname', '')
            # Skip if file path matches any exclude pattern
            if not any(self.path_matches_pattern(file_path, pattern) for pattern in exclude_paths):
                result.append(issue)
        return result
    
    def auto_fix_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate auto-fix by marking the issue as fixed.
        
        Args:
            issue: The issue to fix
            
        Returns:
            The fixed issue
        """
        issue['fixed'] = True
        return issue
    
    def summarize_issues(self, exclude_paths: List[str] = None) -> Dict[str, int]:
        """Summarize issues by counting occurrences per category.
        
        Args:
            exclude_paths: List of path patterns to exclude (e.g. ["DebugUtils/*"])
                           If None, DEFAULT_EXCLUDE_PATHS will be used
            
        Returns:
            Dictionary mapping categories to counts
        """
        data = self.get_data()
        issues = data.get('issues', [])
        summary = {}
        
        # Use default exclude paths if none provided
        if exclude_paths is None:
            exclude_paths = self.DEFAULT_EXCLUDE_PATHS
        
        for issue in issues:
            # Skip fixed issues
            if issue.get('fixed', False):
                continue
            
            # Skip if file path matches any exclude pattern
            if exclude_paths and len(exclude_paths) > 0:
                file_path = issue.get('mainEventFilePathname', '')
                if any(self.path_matches_pattern(file_path, pattern) for pattern in exclude_paths):
                    continue
                
            checker_name = issue.get('checkerName', 'Unknown')
            if checker_name in summary:
                summary[checker_name] += 1
            else:
                summary[checker_name] = 1
        
        return summary
    
    def group_issues_by_location(self, issues: List[Dict[str, Any]]) -> Dict[Tuple[str, int, str], List[Dict[str, Any]]]:
        """Group issues by location (file, line, function).
        
        Args:
            issues: List of issues to group
            
        Returns:
            Dictionary mapping locations to lists of issues
        """
        grouped_issues = {}
        for issue in issues:
            key = (
                issue.get('mainEventFilePathname', ''),
                issue.get('mainEventLineNumber', 0),
                issue.get('functionDisplayName', '')
            )
            if key not in grouped_issues:
                grouped_issues[key] = []
            grouped_issues[key].append(issue)
        return grouped_issues
    
    def extract_event_descriptions(self, issue: Dict[str, Any]) -> List[str]:
        """Extract event descriptions from an issue.
        
        Args:
            issue: The issue to extract descriptions from
            
        Returns:
            List of event descriptions
        """
        event_descriptions = []
        if 'events' in issue and issue['events']:
            for event in issue['events']:
                if 'eventDescription' in event:
                    event_descriptions.append(event['eventDescription'])
        return event_descriptions
    
    def format_issue_for_query(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Format an issue for the query response.
        
        Args:
            issue: The issue to format
            
        Returns:
            Formatted issue for pipeline consumption
        """
        result = {
            "type": issue.get('checkerName', ''),
            "mainEventFilepath": issue.get('mainEventFilePathname', ''),
            "mainEventLineNumber": issue.get('mainEventLineNumber', 0),
            "functionDisplayName": issue.get('functionDisplayName', ''),
            "events": {
                "eventDescription": [],
                "subcategoryLongDescription": issue.get('subcategory', '')
            }
        }
        
        # Extract event descriptions
        if 'events' in issue and issue['events']:
            for event in issue['events']:
                if 'eventDescription' in event:
                    result['events']['eventDescription'].append(event['eventDescription'])
        
        return result
    
    def create_fix_prompt(self, issue: Dict[str, Any]) -> str:
        """Create a prompt for fixing an issue.
        
        Args:
            issue: The issue to create a prompt for
            
        Returns:
            Prompt for fixing the issue
        """
        event_descriptions = self.extract_event_descriptions(issue)
        
        return (
            "You are a senior software engineer with 20 years of experience in C/C++ programming. \n"
            "C++ version is C++17. \n"
            f"Help me to fix the coverity issue: {issue.get('checkerName', '')} \n"
            f"file is {issue.get('mainEventFilePathname', '')} \n"
            f"at line {issue.get('mainEventLineNumber', 0)} \n"
            f"in function {issue.get('functionDisplayName', '')}. \n"
            f"Reason: {issue.get('subcategory', '')}. \n"
            f"Details: {' '.join(event_descriptions)}. \n"
            "Don't make changes beyond the scope of that issue's function. \n"
            "You need to provide a patch to fix the issue. \n"
            "Describe why you made the changes you did. \n"
            "If there's an issue with the first change, don't modify the entire file. \n"
            "CRITICAL: PRESERVE ALL EXISTING COMMENTS - Do not remove any comments from the original code. \n"
            "Comments are essential for code understanding and must be kept in the fixed code. \n"
        )
    
    def create_multi_issue_prompt(self, location_issues: List[Dict[str, Any]], location: Tuple[str, int, str]) -> str:
        """Create a prompt for fixing multiple issues at the same location.
        
        Args:
            location_issues: List of issues at the same location
            location: Location tuple (file_path, line_number, function_name)
            
        Returns:
            Prompt for fixing multiple issues
        """
        file_path, line_number, function_name = location
        checker_names = set(issue.get('checkerName', '') for issue in location_issues)
        
        merged_prompt = (
            "You are a senior software engineer with 20 years of experience in C/C++ programming. \n"
            f"Help me to fix multiple coverity issues: {', '.join(checker_names)} \n"
            f"file is {file_path} \n"
            f"at line {line_number} \n"
            f"in function {function_name}. \n\n"
        )
        
        # Add details for each issue
        for i, issue in enumerate(location_issues, 1):
            event_descriptions = self.extract_event_descriptions(issue)
            
            merged_prompt += (
                f"Issue {i}: {issue.get('checkerName', '')} \n"
                f"Reason: {issue.get('subcategory', '')}. \n"
                f"Details: {' '.join(event_descriptions)}. \n\n"
            )
        
        merged_prompt += (
            "Don't make changes beyond the scope of that function. \n"
            "You need to provide a patch to fix all these issues at once. \n"
            "Describe why you made the changes you did. \n"
            "You describe the patch in detail, including the code changes and the rationale behind them. \n"
            "If there's an issue with the first change, don't modify the entire file. \n"
            "CRITICAL: PRESERVE ALL EXISTING COMMENTS - Do not remove any comments from the original code. \n"
            "Comments are essential for code understanding and must be kept in the fixed code. \n"
        )
        
        return merged_prompt 
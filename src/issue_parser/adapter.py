"""
Coverity Pipeline Adapter

This module provides the CoverityPipelineAdapter class that bridges the existing
CoverityReportTool with pipeline-compatible data structures. It converts the
tool's output to standardized ParsedDefect objects while preserving all
filtering and analysis capabilities.
"""

import time
from typing import Dict, List, Optional, Any

from .coverity_tool import CoverityReportTool
from .data_structures import ParsedDefect, ParsingStatistics
from .exceptions import CoverityError


class CoverityPipelineAdapter:
    """Adapter to integrate existing CoverityReportTool with the pipeline.
    
    This adapter wraps the proven CoverityReportTool and converts its output
    to pipeline-compatible ParsedDefect objects while maintaining all the
    original functionality including filtering, categorization, and path exclusion.
    """
    
    def __init__(self, report_path: str):
        """Initialize the pipeline adapter.
        
        Args:
            report_path: Path to the Coverity report file
            
        Raises:
            CoverityError: If there are issues with the report file
        """
        self.coverity_tool = CoverityReportTool(report_path)
        self._statistics = ParsingStatistics()
        
    def set_report_path(self, report_path: str) -> None:
        """Set a new path for the Coverity report file.
        
        Args:
            report_path: New path to the Coverity report file
        """
        self.coverity_tool.set_report_path(report_path)
        # Reset statistics for new report
        self._statistics = ParsingStatistics()
        
    def get_report_path(self) -> str:
        """Get the current path of the Coverity report file.
        
        Returns:
            The current report file path
        """
        return self.coverity_tool.get_report_path()
    
    def parse_all_issues(self, exclude_paths: Optional[List[str]] = None) -> List[ParsedDefect]:
        """Parse all issues from the report for pipeline processing.
        
        Args:
            exclude_paths: List of path patterns to exclude (e.g. ["DebugUtils/*"])
                          If None, uses CoverityReportTool.DEFAULT_EXCLUDE_PATHS
            
        Returns:
            List of ParsedDefect objects representing all non-fixed issues
            
        Raises:
            CoverityError: If there are issues loading or parsing the report
        """
        start_time = time.time()
        parsed_defects = []
        
        try:
            # Get raw data and reset statistics
            data = self.coverity_tool.get_data()
            raw_issues = data.get('issues', [])
            self._statistics = ParsingStatistics()
            self._statistics.total_issues_found = len(raw_issues)
            
            # Track categories found
            categories_seen = set()
            
            for issue in raw_issues:
                try:
                    # Skip already processed issues
                    if issue.get('fixed', False):
                        self._statistics.issues_skipped += 1
                        continue
                    
                    # Apply path exclusion using existing tool's logic
                    if exclude_paths is not None or self.coverity_tool.DEFAULT_EXCLUDE_PATHS:
                        file_path = issue.get('mainEventFilePathname', '')
                        exclude_list = exclude_paths if exclude_paths is not None else self.coverity_tool.DEFAULT_EXCLUDE_PATHS
                        
                        if exclude_list and any(self.coverity_tool.path_matches_pattern(file_path, pattern) for pattern in exclude_list):
                            self._statistics.issues_excluded += 1
                            continue
                    
                    # Convert to pipeline format using existing tool
                    formatted_issue = self.coverity_tool.format_issue_for_query(issue)
                    parsed_defect = ParsedDefect.from_coverity_tool_output(formatted_issue)
                    
                    # Validate the parsed defect
                    if not parsed_defect.validate():
                        self._statistics.parsing_errors += 1
                        continue
                    
                    parsed_defects.append(parsed_defect)
                    self._statistics.issues_processed += 1
                    
                    # Track category
                    category = parsed_defect.defect_type
                    if category:
                        categories_seen.add(category)
                        
                except Exception as e:
                    # Log parsing error but continue processing
                    self._statistics.parsing_errors += 1
                    continue
            
            # Update statistics
            self._statistics.categories_found = sorted(list(categories_seen))
            self._statistics.processing_time_seconds = time.time() - start_time
            
            return parsed_defects
            
        except Exception as e:
            raise CoverityError(f"Error parsing all issues: {e}")
    
    def parse_issues_by_category(self, category: str, exclude_paths: Optional[List[str]] = None) -> List[ParsedDefect]:
        """Parse issues of a specific category.
        
        Args:
            category: The category to filter issues by (case-insensitive)
            exclude_paths: List of path patterns to exclude (e.g. ["DebugUtils/*"])
                          If None, uses CoverityReportTool.DEFAULT_EXCLUDE_PATHS
            
        Returns:
            List of ParsedDefect objects for the specified category
            
        Raises:
            CoverityError: If there are issues loading or parsing the report
        """
        start_time = time.time()
        parsed_defects = []
        
        try:
            # Use existing tool's category filtering
            issues = self.coverity_tool.query_issues_by_category(category, exclude_paths)
            
            # Reset statistics for this operation
            self._statistics = ParsingStatistics()
            self._statistics.total_issues_found = len(issues)
            
            for issue in issues:
                try:
                    # Convert to pipeline format using existing tool
                    formatted_issue = self.coverity_tool.format_issue_for_query(issue)
                    parsed_defect = ParsedDefect.from_coverity_tool_output(formatted_issue)
                    
                    # Validate the parsed defect
                    if not parsed_defect.validate():
                        self._statistics.parsing_errors += 1
                        continue
                    
                    parsed_defects.append(parsed_defect)
                    self._statistics.issues_processed += 1
                    
                except Exception as e:
                    # Log parsing error but continue processing
                    self._statistics.parsing_errors += 1
                    continue
            
            # Update statistics
            if parsed_defects:
                self._statistics.categories_found = [category]
            self._statistics.processing_time_seconds = time.time() - start_time
            
            return parsed_defects
            
        except Exception as e:
            raise CoverityError(f"Error parsing issues by category '{category}': {e}")
    
    def get_parsing_statistics(self) -> Dict[str, Any]:
        """Get parsing statistics from the last operation.
        
        Returns:
            Dictionary with parsing statistics including counts, timing, and categories
        """
        return self._statistics.to_dict()
    
    def get_issue_summary(self, exclude_paths: Optional[List[str]] = None) -> Dict[str, int]:
        """Get a summary of issues by category using the existing tool.
        
        Args:
            exclude_paths: List of path patterns to exclude (e.g. ["DebugUtils/*"])
                          If None, uses CoverityReportTool.DEFAULT_EXCLUDE_PATHS
            
        Returns:
            Dictionary mapping category names to issue counts
            
        Raises:
            CoverityError: If there are issues loading the report
        """
        try:
            return self.coverity_tool.summarize_issues(exclude_paths)
        except Exception as e:
            raise CoverityError(f"Error getting issue summary: {e}")
    
    def group_parsed_defects_by_location(self, defects: List[ParsedDefect]) -> Dict[tuple, List[ParsedDefect]]:
        """Group ParsedDefect objects by location (file, line, function).
        
        Args:
            defects: List of ParsedDefect objects to group
            
        Returns:
            Dictionary mapping (file_path, line_number, function_name) tuples to lists of defects
        """
        grouped_defects = {}
        for defect in defects:
            key = (defect.file_path, defect.line_number, defect.function_name)
            if key not in grouped_defects:
                grouped_defects[key] = []
            grouped_defects[key].append(defect)
        return grouped_defects
    
    def validate_report(self) -> bool:
        """Validate the Coverity report can be loaded and processed.
        
        Returns:
            True if the report is valid and can be processed, False otherwise
        """
        try:
            # Try to load the report
            data = self.coverity_tool.get_data()
            
            # Check basic structure
            if not isinstance(data, dict):
                return False
            if 'issues' not in data:
                return False
            if not isinstance(data['issues'], list):
                return False
                
            # Try to process a sample issue if available
            issues = data['issues']
            if issues:
                sample_issue = issues[0]
                try:
                    formatted = self.coverity_tool.format_issue_for_query(sample_issue)
                    ParsedDefect.from_coverity_tool_output(formatted)
                    return True
                except Exception:
                    return False
            
            return True  # Empty report is valid
            
        except Exception:
            return False
    
    def get_available_categories(self, exclude_paths: Optional[List[str]] = None) -> List[str]:
        """Get list of all available defect categories in the report.
        
        Args:
            exclude_paths: List of path patterns to exclude (e.g. ["DebugUtils/*"])
                          If None, uses CoverityReportTool.DEFAULT_EXCLUDE_PATHS
            
        Returns:
            Sorted list of category names found in the report
            
        Raises:
            CoverityError: If there are issues loading the report
        """
        try:
            summary = self.get_issue_summary(exclude_paths)
            return sorted(summary.keys())
        except Exception as e:
            raise CoverityError(f"Error getting available categories: {e}")
    
    def create_batch_iterator(self, batch_size: int = 100, exclude_paths: Optional[List[str]] = None):
        """Create an iterator for processing large reports in batches.
        
        Args:
            batch_size: Number of issues to process per batch
            exclude_paths: List of path patterns to exclude
            
        Yields:
            List[ParsedDefect]: Batches of parsed defects
            
        Raises:
            CoverityError: If there are issues loading or parsing the report
        """
        try:
            # Get raw data
            data = self.coverity_tool.get_data()
            raw_issues = data.get('issues', [])
            
            current_batch = []
            for issue in raw_issues:
                try:
                    # Skip already processed issues
                    if issue.get('fixed', False):
                        continue
                    
                    # Apply path exclusion
                    if exclude_paths is not None or self.coverity_tool.DEFAULT_EXCLUDE_PATHS:
                        file_path = issue.get('mainEventFilePathname', '')
                        exclude_list = exclude_paths if exclude_paths is not None else self.coverity_tool.DEFAULT_EXCLUDE_PATHS
                        
                        if exclude_list and any(self.coverity_tool.path_matches_pattern(file_path, pattern) for pattern in exclude_list):
                            continue
                    
                    # Convert to pipeline format
                    formatted_issue = self.coverity_tool.format_issue_for_query(issue)
                    parsed_defect = ParsedDefect.from_coverity_tool_output(formatted_issue)
                    
                    if parsed_defect.validate():
                        current_batch.append(parsed_defect)
                        
                        # Yield batch when full
                        if len(current_batch) >= batch_size:
                            yield current_batch
                            current_batch = []
                            
                except Exception:
                    # Skip problematic issues
                    continue
            
            # Yield remaining items
            if current_batch:
                yield current_batch
                
        except Exception as e:
            raise CoverityError(f"Error creating batch iterator: {e}")
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"CoverityPipelineAdapter(report={self.get_report_path()})"
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"CoverityPipelineAdapter(report_path='{self.get_report_path()}')" 
"""
Data structures for LLM Fix Generator component.

This module defines the core data structures used for defect analysis,
fix generation, and NIM integration results.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class FixComplexity(Enum):
    """Classification of fix complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    HIGH_RISK = "high_risk"


class DefectSeverity(Enum):
    """Defect severity classification."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ConfidenceLevel(Enum):
    """Confidence levels for generated fixes."""
    VERY_HIGH = "very_high"  # >0.9
    HIGH = "high"           # 0.7-0.9
    MEDIUM = "medium"       # 0.5-0.7
    LOW = "low"            # 0.3-0.5
    VERY_LOW = "very_low"  # <0.3


@dataclass
class FixCandidate:
    """Represents a single fix candidate with metadata."""
    
    # Fix content and metadata
    fix_code: str
    explanation: str
    confidence_score: float
    complexity: FixComplexity
    risk_assessment: str
    
    # File modification details
    affected_files: List[str]
    line_ranges: List[Dict[str, int]]  # [{"start": n, "end": m}]
    
    # Additional metadata
    fix_strategy: str = ""
    estimated_effort: str = ""
    potential_side_effects: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate fix candidate data."""
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(f"Confidence score must be 0.0-1.0, got {self.confidence_score}")
        
        if not self.fix_code.strip():
            raise ValueError("Fix code cannot be empty")
        
        if not self.explanation.strip():
            raise ValueError("Fix explanation cannot be empty")
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level enum based on score."""
        if self.confidence_score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.confidence_score >= 0.7:
            return ConfidenceLevel.HIGH
        elif self.confidence_score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif self.confidence_score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "fix_code": self.fix_code,
            "explanation": self.explanation,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level.value,
            "complexity": self.complexity.value,
            "risk_assessment": self.risk_assessment,
            "affected_files": self.affected_files,
            "line_ranges": self.line_ranges,
            "fix_strategy": self.fix_strategy,
            "estimated_effort": self.estimated_effort,
            "potential_side_effects": self.potential_side_effects
        }


@dataclass
class NIMMetadata:
    """Metadata from NVIDIA NIM API calls."""
    
    model_used: str
    tokens_consumed: int
    generation_time: float
    api_endpoint: str
    request_id: Optional[str] = None
    
    # Cost tracking
    estimated_cost: Optional[float] = None
    
    # Performance metrics
    tokens_per_second: Optional[float] = field(init=False)
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.generation_time > 0:
            self.tokens_per_second = self.tokens_consumed / self.generation_time
        else:
            self.tokens_per_second = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model_used": self.model_used,
            "tokens_consumed": self.tokens_consumed,
            "generation_time": self.generation_time,
            "tokens_per_second": self.tokens_per_second,
            "api_endpoint": self.api_endpoint,
            "request_id": self.request_id,
            "estimated_cost": self.estimated_cost
        }


@dataclass
class DefectAnalysisResult:
    """
    Comprehensive result from LLM-based defect analysis and fix generation.
    
    This unified structure contains both classification results and generated fixes
    from a single NIM API call, optimizing performance and context preservation.
    """
    
    # Original defect information
    defect_id: str
    defect_type: str
    file_path: str
    line_number: int
    
    # Classification results (integrated into LLM analysis)
    defect_category: str
    severity_assessment: DefectSeverity
    fix_complexity: FixComplexity
    confidence_score: float
    
    # Fix generation results
    fix_candidates: List[FixCandidate]
    recommended_fix_index: int = 0  # Index of recommended fix in candidates list
    
    # Analysis metadata
    reasoning_trace: str = ""
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # NIM integration metadata
    nim_metadata: Optional[NIMMetadata] = None
    
    # Quality assurance
    style_consistency_score: float = 0.0
    safety_checks_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate analysis result data."""
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(f"Confidence score must be 0.0-1.0, got {self.confidence_score}")
        
        if not self.fix_candidates:
            raise ValueError("At least one fix candidate is required")
        
        if not (0 <= self.recommended_fix_index < len(self.fix_candidates)):
            raise ValueError(f"Invalid recommended fix index: {self.recommended_fix_index}")
        
        if not (0.0 <= self.style_consistency_score <= 1.0):
            raise ValueError(f"Style consistency score must be 0.0-1.0, got {self.style_consistency_score}")
    
    @property
    def recommended_fix(self) -> FixCandidate:
        """Get the recommended fix candidate."""
        return self.fix_candidates[self.recommended_fix_index]
    
    @property
    def high_confidence_fixes(self) -> List[FixCandidate]:
        """Get fix candidates with high confidence (>= 0.7)."""
        return [fix for fix in self.fix_candidates if fix.confidence_score >= 0.7]
    
    @property
    def is_ready_for_application(self) -> bool:
        """Check if the analysis result is ready for patch application."""
        return (
            self.safety_checks_passed and
            not self.validation_errors and
            self.recommended_fix.confidence_score >= 0.5 and
            self.style_consistency_score >= 0.6
        )
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get a summary of the analysis results."""
        return {
            "defect_id": self.defect_id,
            "defect_type": self.defect_type,
            "location": f"{self.file_path}:{self.line_number}",
            "category": self.defect_category,
            "severity": self.severity_assessment.value,
            "complexity": self.fix_complexity.value,
            "confidence": self.confidence_score,
            "num_candidates": len(self.fix_candidates),
            "recommended_confidence": self.recommended_fix.confidence_score,
            "style_consistency": self.style_consistency_score,
            "ready_for_application": self.is_ready_for_application,
            "analysis_timestamp": self.analysis_timestamp.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "defect_id": self.defect_id,
            "defect_type": self.defect_type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "defect_category": self.defect_category,
            "severity_assessment": self.severity_assessment.value,
            "fix_complexity": self.fix_complexity.value,
            "confidence_score": self.confidence_score,
            "fix_candidates": [fix.to_dict() for fix in self.fix_candidates],
            "recommended_fix_index": self.recommended_fix_index,
            "reasoning_trace": self.reasoning_trace,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "nim_metadata": self.nim_metadata.to_dict() if self.nim_metadata else None,
            "style_consistency_score": self.style_consistency_score,
            "safety_checks_passed": self.safety_checks_passed,
            "validation_errors": self.validation_errors,
            "analysis_summary": self.get_analysis_summary()
        }


@dataclass
class GenerationStatistics:
    """Statistics for tracking fix generation performance."""
    
    total_defects_processed: int = 0
    successful_generations: int = 0
    failed_generations: int = 0
    high_confidence_fixes: int = 0
    
    total_tokens_consumed: int = 0
    total_generation_time: float = 0.0
    total_estimated_cost: float = 0.0
    
    # Performance metrics
    average_generation_time: float = field(init=False, default=0.0)
    success_rate: float = field(init=False, default=0.0)
    average_confidence: float = field(init=False, default=0.0)
    
    def __post_init__(self):
        """Calculate derived metrics."""
        self.update_metrics()
    
    def update_metrics(self):
        """Update calculated metrics."""
        if self.total_defects_processed > 0:
            self.average_generation_time = self.total_generation_time / self.total_defects_processed
            self.success_rate = self.successful_generations / self.total_defects_processed
        else:
            self.average_generation_time = 0.0
            self.success_rate = 0.0
    
    def add_result(self, result: DefectAnalysisResult, success: bool = True):
        """Add a generation result to statistics."""
        self.total_defects_processed += 1
        
        if success:
            self.successful_generations += 1
            if result.recommended_fix.confidence_score >= 0.7:
                self.high_confidence_fixes += 1
        else:
            self.failed_generations += 1
        
        if result.nim_metadata:
            self.total_tokens_consumed += result.nim_metadata.tokens_consumed
            self.total_generation_time += result.nim_metadata.generation_time
            if result.nim_metadata.estimated_cost:
                self.total_estimated_cost += result.nim_metadata.estimated_cost
        
        self.update_metrics()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "total_defects_processed": self.total_defects_processed,
            "successful_generations": self.successful_generations,
            "failed_generations": self.failed_generations,
            "high_confidence_fixes": self.high_confidence_fixes,
            "success_rate": self.success_rate,
            "total_tokens_consumed": self.total_tokens_consumed,
            "total_generation_time": self.total_generation_time,
            "average_generation_time": self.average_generation_time,
            "total_estimated_cost": self.total_estimated_cost
        } 
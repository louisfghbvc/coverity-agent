"""
Pydantic Data Models for LLM Fix Generator with LangChain Integration.

This module defines type-safe Pydantic BaseModel classes for structured output,
automatic validation, JSON schema generation, and seamless LangChain integration.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from pydantic.types import PositiveFloat, PositiveInt
from typing import Annotated


# =============================================================================
# Supporting Enums
# =============================================================================

class DefectSeverity(str, Enum):
    """Defect severity classification levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FixComplexity(str, Enum):
    """Classification of fix complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERIMENTAL = "experimental"


class ConfidenceLevel(str, Enum):
    """Confidence levels for generated fixes and analysis."""
    VERY_LOW = "very_low"    # 0.0-0.3
    LOW = "low"              # 0.3-0.5
    MEDIUM = "medium"        # 0.5-0.7
    HIGH = "high"            # 0.7-0.9
    VERY_HIGH = "very_high"  # 0.9-1.0


class ProviderType(str, Enum):
    """LLM provider types for multi-provider support."""
    NVIDIA_NIM = "nvidia_nim"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class FixType(str, Enum):
    """Type of fix being applied."""
    CODE_FIX = "code_fix"
    SUPPRESSION = "suppression"
    REFACTOR = "refactor"
    CONFIGURATION = "configuration"


class StyleGuideType(str, Enum):
    """Supported code style guide types."""
    GOOGLE_CPP = "google_cpp"
    LLVM = "llvm"
    PEP8 = "pep8"
    BLACK = "black"
    GOOGLE_JAVA = "google_java"
    PRETTIER = "prettier"
    CUSTOM = "custom"


# =============================================================================
# Core Pydantic Models
# =============================================================================

class NIMMetadata(BaseModel):
    """
    NVIDIA NIM API call tracking and performance metrics.
    
    Tracks token usage, performance, and cost information for
    NVIDIA NIM API interactions with comprehensive validation.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    # Required fields
    model_used: Annotated[str, Field(min_length=1)] = Field(
        ..., 
        description="NVIDIA NIM model name used for generation"
    )
    tokens_consumed: PositiveInt = Field(
        ..., 
        description="Total tokens consumed in the API call"
    )
    generation_time: PositiveFloat = Field(
        ..., 
        description="Time taken for generation in seconds"
    )
    provider_used: ProviderType = Field(
        ..., 
        description="Provider type used for the request"
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the API request"
    )
    
    # Performance metrics
    input_tokens: PositiveInt = Field(
        default=0, 
        description="Tokens in the input prompt"
    )
    output_tokens: PositiveInt = Field(
        default=0, 
        description="Tokens in the generated output"
    )
    
    # Cost tracking
    api_cost: Optional[Decimal] = Field(
        default=None, 
        description="Estimated cost of the API call in USD",
        decimal_places=6
    )
    
    # Additional metadata
    api_endpoint: Optional[str] = Field(
        default=None, 
        description="API endpoint used for the request"
    )
    response_status: int = Field(
        default=200, 
        ge=100, 
        le=599, 
        description="HTTP response status code"
    )
    
    # Computed fields
    tokens_per_second: Optional[float] = Field(
        default=None, 
        description="Generation speed in tokens per second"
    )
    
    @model_validator(mode='after')
    def validate_and_calculate(self):
        """Validate tokens and calculate derived metrics."""
        # Auto-calculate output tokens if needed
        expected_output = self.tokens_consumed - self.input_tokens
        if self.output_tokens == 0:  # Auto-calculate if not provided
            object.__setattr__(self, 'output_tokens', expected_output)
        elif self.output_tokens != expected_output:
            raise ValueError(
                f"Token mismatch: input({self.input_tokens}) + "
                f"output({self.output_tokens}) != total({self.tokens_consumed})"
            )
        
        # Calculate tokens per second
        if self.generation_time > 0:
            tokens_per_sec = round(self.tokens_consumed / self.generation_time, 2)
            object.__setattr__(self, 'tokens_per_second', tokens_per_sec)
        else:
            object.__setattr__(self, 'tokens_per_second', 0.0)
            
        return self


class FixCandidate(BaseModel):
    """
    Individual fix candidate with comprehensive metadata and validation.
    
    Represents a single generated fix with confidence scoring,
    risk assessment, and detailed implementation information.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    # Required fields
    fix_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the fix candidate"
    )
    file_path: Annotated[str, Field(min_length=1)] = Field(
        ..., 
        description="Path to the file being modified"
    )
    original_code: Annotated[str, Field(min_length=1)] = Field(
        ..., 
        description="Original code snippet with the defect"
    )
    fixed_code: Annotated[str, Field(min_length=1)] = Field(
        ..., 
        description="Fixed code snippet"
    )
    explanation: Annotated[str, Field(min_length=10)] = Field(
        ..., 
        description="Detailed explanation of the fix"
    )
    
    # Confidence and risk assessment
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., 
        description="Confidence score for the fix (0.0-1.0)"
    )
    complexity: FixComplexity = Field(
        ..., 
        description="Complexity level of the fix"
    )
    estimated_risk: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0, 
        description="Estimated risk of applying the fix (0.0-1.0)"
    )
    
    # Implementation details
    line_start: PositiveInt = Field(
        ..., 
        description="Starting line number for the fix"
    )
    line_end: PositiveInt = Field(
        ..., 
        description="Ending line number for the fix"
    )
    fix_type: FixType = Field(
        default=FixType.CODE_FIX, 
        description="Type of fix being applied"
    )
    
    # Additional metadata
    fix_strategy: str = Field(
        default="", 
        description="Strategy used to generate the fix"
    )
    potential_side_effects: List[str] = Field(
        default_factory=list, 
        description="List of potential side effects"
    )
    testing_recommendations: List[str] = Field(
        default_factory=list,
        description="Recommended testing approaches"
    )
    
    # Performance impact
    performance_impact: str = Field(
        default="minimal", 
        description="Expected performance impact"
    )
    
    @field_validator('line_end')
    @classmethod
    def validate_line_range(cls, v, info):
        """Ensure line_end >= line_start."""
        if info.data and 'line_start' in info.data and v < info.data['line_start']:
            raise ValueError("line_end must be >= line_start")
        return v
    
    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v):
        """Validate file path format."""
        try:
            Path(v)  # Basic path validation
            return v
        except Exception:
            raise ValueError(f"Invalid file path format: {v}")
    
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
    
    @property
    def lines_affected(self) -> int:
        """Calculate number of lines affected by the fix."""
        return self.line_end - self.line_start + 1


class StyleAnalysisResult(BaseModel):
    """
    Style consistency analysis results with structured recommendations.
    
    Provides comprehensive style analysis including detected patterns,
    violations, and actionable recommendations for code consistency.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    # Style detection results
    detected_style: Dict[str, Any] = Field(
        ..., 
        description="Detected style patterns in the code"
    )
    consistency_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., 
        description="Overall style consistency score (0.0-1.0)"
    )
    language_detected: Annotated[str, Field(min_length=1)] = Field(
        ..., 
        description="Programming language detected"
    )
    
    # Style guide information
    style_guide_used: Optional[StyleGuideType] = Field(
        default=None, 
        description="Style guide used for analysis"
    )
    
    # Violations and recommendations
    style_violations: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="List of style violations found"
    )
    recommendations: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Style improvement recommendations"
    )
    
    # Analysis metadata
    analysis_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the style analysis was performed"
    )
    lines_analyzed: PositiveInt = Field(
        default=0, 
        description="Number of lines analyzed"
    )
    
    @field_validator('detected_style')
    @classmethod
    def validate_detected_style(cls, v):
        """Validate detected style structure."""
        required_keys = ['indentation_type', 'indentation_width', 'brace_style']
        for key in required_keys:
            if key not in v:
                raise ValueError(f"Missing required style key: {key}")
        return v
    
    @property
    def has_violations(self) -> bool:
        """Check if any style violations were found."""
        return len(self.style_violations) > 0
    
    @property
    def violation_count(self) -> int:
        """Get total number of violations."""
        return len(self.style_violations)


class DefectAnalysisResult(BaseModel):
    """
    Comprehensive defect analysis result with integrated classification and fixes.
    
    Main result structure that combines defect classification, fix generation,
    and style analysis in a single type-safe, validated model for LangChain integration.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    # Original defect information
    defect_id: Annotated[str, Field(min_length=1)] = Field(
        ..., 
        description="Unique identifier for the defect"
    )
    defect_type: Annotated[str, Field(min_length=1)] = Field(
        ..., 
        description="Type/category of the defect"
    )
    file_path: Annotated[str, Field(min_length=1)] = Field(
        ..., 
        description="Path to the file containing the defect"
    )
    line_number: PositiveInt = Field(
        ..., 
        description="Line number where the defect occurs"
    )
    
    # Analysis results
    severity: DefectSeverity = Field(
        ..., 
        description="Assessed severity of the defect"
    )
    confidence_level: ConfidenceLevel = Field(
        ..., 
        description="Confidence level of the analysis"
    )
    
    # Fix generation results
    fix_candidates: List[FixCandidate] = Field(
        ..., 
        min_length=1, 
        description="List of generated fix candidates"
    )
    recommended_fix_index: int = Field(
        default=0, 
        ge=0, 
        description="Index of the recommended fix candidate"
    )
    
    # Metadata and tracking
    metadata: NIMMetadata = Field(
        ..., 
        description="NVIDIA NIM API call metadata"
    )
    generation_statistics: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional generation statistics"
    )
    
    # Quality assurance
    style_analysis: Optional[StyleAnalysisResult] = Field(
        default=None, 
        description="Style consistency analysis results"
    )
    safety_checks_passed: bool = Field(
        default=True, 
        description="Whether safety validation passed"
    )
    validation_errors: List[str] = Field(
        default_factory=list, 
        description="List of validation errors"
    )
    
    # Analysis context
    reasoning_trace: str = Field(
        default="", 
        description="Detailed reasoning for the analysis"
    )
    analysis_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the analysis was performed"
    )
    
    # False positive detection
    is_false_positive: bool = Field(
        default=False, 
        description="Whether the defect is likely a false positive"
    )
    false_positive_reason: str = Field(
        default="", 
        description="Reason for false positive classification"
    )
    
    @field_validator('recommended_fix_index')
    @classmethod
    def validate_recommended_fix_index(cls, v, info):
        """Ensure recommended fix index is valid."""
        if info.data and 'fix_candidates' in info.data:
            fix_count = len(info.data['fix_candidates'])
            if v >= fix_count:
                raise ValueError(
                    f"Recommended fix index {v} >= fix count {fix_count}"
                )
        return v
    
    @model_validator(mode='after')
    def validate_consistency(self):
        """Perform cross-field validation."""
        # Ensure file_path consistency across fix candidates
        file_path = self.file_path
        fix_candidates = self.fix_candidates
        
        for i, fix in enumerate(fix_candidates):
            if fix.file_path != file_path:
                raise ValueError(
                    f"Fix candidate {i} file path mismatch: "
                    f"expected {file_path}, got {fix.file_path}"
                )
        
        return self
    
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
            len(self.validation_errors) == 0 and
            self.recommended_fix.confidence_score >= 0.5 and
            not self.is_false_positive and
            (self.style_analysis is None or self.style_analysis.consistency_score >= 0.6)
        )
    
    @property
    def overall_confidence_score(self) -> float:
        """Calculate overall confidence score."""
        if not self.fix_candidates:
            return 0.0
        
        # If only one fix candidate, return its confidence score
        if len(self.fix_candidates) == 1:
            return round(self.recommended_fix.confidence_score, 3)
        
        # Weight recommended fix more heavily when multiple candidates
        recommended_weight = 0.6
        other_weight = 0.4 / (len(self.fix_candidates) - 1)
        
        score = self.recommended_fix.confidence_score * recommended_weight
        
        for i, fix in enumerate(self.fix_candidates):
            if i != self.recommended_fix_index:
                score += fix.confidence_score * other_weight
        
        return round(score, 3)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the analysis."""
        return {
            "defect_id": self.defect_id,
            "defect_type": self.defect_type,
            "location": f"{self.file_path}:{self.line_number}",
            "severity": self.severity.value,
            "confidence_level": self.confidence_level.value,
            "is_false_positive": self.is_false_positive,
            "num_fix_candidates": len(self.fix_candidates),
            "recommended_fix_confidence": self.recommended_fix.confidence_score,
            "overall_confidence": self.overall_confidence_score,
            "high_confidence_fixes": len(self.high_confidence_fixes),
            "ready_for_application": self.is_ready_for_application,
            "safety_checks_passed": self.safety_checks_passed,
            "validation_errors_count": len(self.validation_errors),
            "style_consistency": self.style_analysis.consistency_score if self.style_analysis else None,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "provider_used": self.metadata.provider_used.value,
            "model_used": self.metadata.model_used,
            "tokens_consumed": self.metadata.tokens_consumed,
            "generation_time": self.metadata.generation_time
        }


# =============================================================================
# Additional Supporting Models
# =============================================================================

class GenerationStatistics(BaseModel):
    """
    Statistics for tracking fix generation performance across multiple defects.
    
    Provides comprehensive metrics for monitoring LLM performance,
    cost tracking, and quality assessment.
    """
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )
    
    # Counters
    total_defects_processed: int = Field(
        default=0, 
        ge=0, 
        description="Total number of defects processed"
    )
    successful_generations: int = Field(
        default=0, 
        ge=0, 
        description="Number of successful fix generations"
    )
    failed_generations: int = Field(
        default=0, 
        ge=0, 
        description="Number of failed generations"
    )
    high_confidence_fixes: int = Field(
        default=0, 
        ge=0, 
        description="Number of high-confidence fixes (>= 0.7)"
    )
    
    # Resource usage
    total_tokens_consumed: int = Field(
        default=0, 
        ge=0, 
        description="Total tokens consumed across all requests"
    )
    total_generation_time: float = Field(
        default=0.0, 
        ge=0.0, 
        description="Total time spent on generation"
    )
    total_estimated_cost: Decimal = Field(
        default=Decimal('0.00'), 
        ge=0, 
        description="Total estimated cost in USD"
    )
    
    # Performance metrics (computed)
    success_rate: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Success rate (successful/total)"
    )
    average_generation_time: float = Field(
        default=0.0, 
        ge=0.0, 
        description="Average generation time per defect"
    )
    average_confidence: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Average confidence score"
    )
    
    def update_metrics(self) -> None:
        """Update computed metrics based on current counters."""
        if self.total_defects_processed > 0:
            self.success_rate = self.successful_generations / self.total_defects_processed
            self.average_generation_time = self.total_generation_time / self.total_defects_processed
        else:
            self.success_rate = 0.0
            self.average_generation_time = 0.0
    
    def add_result(self, result: DefectAnalysisResult, success: bool = True) -> None:
        """Add a generation result to the statistics."""
        self.total_defects_processed += 1
        
        if success:
            self.successful_generations += 1
            if result.recommended_fix.confidence_score >= 0.7:
                self.high_confidence_fixes += 1
        else:
            self.failed_generations += 1
        
        # Add resource usage
        self.total_tokens_consumed += result.metadata.tokens_consumed
        self.total_generation_time += result.metadata.generation_time
        if result.metadata.api_cost:
            self.total_estimated_cost += result.metadata.api_cost
        
        # Update computed metrics
        self.update_metrics()


# =============================================================================
# JSON Schema Generation Utilities
# =============================================================================

def get_defect_analysis_schema() -> Dict[str, Any]:
    """
    Get JSON schema for DefectAnalysisResult for LLM prompt generation.
    
    Returns:
        JSON schema dictionary compatible with LangChain PydanticOutputParser
    """
    return DefectAnalysisResult.model_json_schema()


def get_style_analysis_schema() -> Dict[str, Any]:
    """
    Get JSON schema for StyleAnalysisResult for LLM prompt generation.
    
    Returns:
        JSON schema dictionary compatible with LangChain PydanticOutputParser
    """
    return StyleAnalysisResult.model_json_schema()


def get_fix_candidate_schema() -> Dict[str, Any]:
    """
    Get JSON schema for FixCandidate for LLM prompt generation.
    
    Returns:
        JSON schema dictionary compatible with LangChain PydanticOutputParser
    """
    return FixCandidate.model_json_schema()


# =============================================================================
# Validation Utilities
# =============================================================================

def validate_confidence_score(score: float) -> ConfidenceLevel:
    """Convert confidence score to confidence level enum."""
    if score >= 0.9:
        return ConfidenceLevel.VERY_HIGH
    elif score >= 0.7:
        return ConfidenceLevel.HIGH
    elif score >= 0.5:
        return ConfidenceLevel.MEDIUM
    elif score >= 0.3:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.VERY_LOW


def create_sample_defect_analysis() -> DefectAnalysisResult:
    """
    Create a sample DefectAnalysisResult for testing and documentation.
    
    Returns:
        Sample DefectAnalysisResult with realistic data
    """
    metadata = NIMMetadata(
        model_used="nvidia/llama-3.3-nemotron-super-49b-v1",
        tokens_consumed=1500,
        generation_time=2.5,
        provider_used=ProviderType.NVIDIA_NIM,
        input_tokens=800,
        output_tokens=700,
        api_cost=Decimal('0.045')
    )
    
    fix_candidate = FixCandidate(
        file_path="/path/to/source.cpp",
        original_code="char* ptr = nullptr;\n*ptr = 'x';",
        fixed_code="char* ptr = nullptr;\nif (ptr != nullptr) {\n    *ptr = 'x';\n}",
        explanation="Added null pointer check before dereferencing",
        confidence_score=0.85,
        complexity=FixComplexity.SIMPLE,
        line_start=42,
        line_end=43,
        estimated_risk=0.1
    )
    
    return DefectAnalysisResult(
        defect_id="DEFECT_001",
        defect_type="NULL_POINTER_DEREFERENCE",
        file_path="/path/to/source.cpp",
        line_number=43,
        severity=DefectSeverity.HIGH,
        confidence_level=ConfidenceLevel.HIGH,
        fix_candidates=[fix_candidate],
        metadata=metadata
    )


# Export all models and utilities
__all__ = [
    # Enums
    'DefectSeverity',
    'FixComplexity', 
    'ConfidenceLevel',
    'ProviderType',
    'FixType',
    'StyleGuideType',
    # Core Models
    'DefectAnalysisResult',
    'FixCandidate',
    'NIMMetadata',
    'StyleAnalysisResult',
    'GenerationStatistics',
    # Utilities
    'get_defect_analysis_schema',
    'get_style_analysis_schema',
    'get_fix_candidate_schema',
    'validate_confidence_score',
    'create_sample_defect_analysis'
] 
"""
API request and response schemas.
Defines Pydantic models for API validation.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class OverloadRequestSchema(BaseModel):
    """Schema for overload situation request."""
    description: str = Field(
        ...,
        description="Natural language description of the overload situation",
        min_length=10,
        example="Zone A dispatch is overloaded, need forklift help"
    )


class WorkerResponseSchema(BaseModel):
    """Schema for worker information response."""
    worker_id: str
    name: str
    primary_skill: str
    transferable_skills: List[str]
    current_zone: str
    shift: str
    load_status: str
    available: bool


class RecommendationResponseSchema(BaseModel):
    """Schema for shift recommendation response."""
    worker_id: str
    worker_name: str
    from_zone: str
    to_zone: str
    skill_match: str
    match_type: str
    reasoning: str
    confidence_score: float
    load_impact: Dict[str, Any]


class OverloadResponseSchema(BaseModel):
    """Schema for overload request response."""
    success: bool
    recommendation: Optional[RecommendationResponseSchema] = None
    all_candidates: Optional[List[Dict[str, Any]]] = None
    reasoning: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ShiftConfirmationSchema(BaseModel):
    """Schema for confirming a shift change."""
    worker_id: str = Field(..., description="Worker ID to move")
    from_zone: str = Field(..., description="Source zone")
    to_zone: str = Field(..., description="Target zone")
    confirmed_by: Optional[str] = Field(None, description="Manager name")


class ShiftConfirmationResponseSchema(BaseModel):
    """Schema for shift confirmation response."""
    success: bool
    message: str
    updated_worker: Optional[WorkerResponseSchema] = None
    zone_statistics: Optional[Dict[str, Any]] = None


class ZoneStatisticsSchema(BaseModel):
    """Schema for zone statistics."""
    zone: str
    total_workers: int
    available_workers: int
    average_load: float
    high_load_count: int


class HealthCheckSchema(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    components: Dict[str, str]
    timestamp: str

# Made with Bob

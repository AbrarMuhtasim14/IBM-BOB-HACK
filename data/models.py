"""
Data models for SmartShift application.
Defines Pydantic models for worker data validation and type safety.
"""
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator


class Zone(str, Enum):
    """Warehouse zones."""
    ZONE_A = "Zone A"
    ZONE_B = "Zone B"
    ZONE_C = "Zone C"
    ZONE_D = "Zone D"


class Shift(str, Enum):
    """Work shift timings."""
    MORNING = "Morning"
    AFTERNOON = "Afternoon"
    NIGHT = "Night"


class LoadStatus(str, Enum):
    """Worker load status."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class Worker(BaseModel):
    """Worker profile model."""
    worker_id: str = Field(..., description="Unique worker identifier")
    name: str = Field(..., description="Worker full name")
    primary_skill: str = Field(..., description="Primary job skill")
    transferable_skills: List[str] = Field(
        default_factory=list,
        description="List of transferable skills"
    )
    current_zone: Zone = Field(..., description="Current assigned zone")
    shift: Shift = Field(..., description="Work shift timing")
    load_status: LoadStatus = Field(..., description="Current workload status")
    available: bool = Field(default=True, description="Availability for reassignment")
    
    @validator('transferable_skills', pre=True)
    def parse_transferable_skills(cls, v):
        """Parse transferable skills from string or list."""
        if isinstance(v, str):
            # Split by semicolon and strip whitespace
            return [skill.strip() for skill in v.split(';') if skill.strip()]
        return v
    
    def get_all_skills(self) -> List[str]:
        """Get all skills (primary + transferable)."""
        return [self.primary_skill] + self.transferable_skills
    
    def has_skill(self, skill: str) -> bool:
        """Check if worker has a specific skill (case-insensitive)."""
        skill_lower = skill.lower()
        all_skills = [s.lower() for s in self.get_all_skills()]
        return skill_lower in all_skills
    
    def get_load_percentage(self) -> int:
        """Get approximate load percentage based on status."""
        load_map = {
            LoadStatus.LOW: 30,
            LoadStatus.MEDIUM: 60,
            LoadStatus.HIGH: 90
        }
        return load_map.get(self.load_status, 50)
    
    class Config:
        use_enum_values = True


class OverloadRequest(BaseModel):
    """Request model for overload situation."""
    description: str = Field(
        ...,
        description="Natural language description of overload situation",
        min_length=10
    )
    zone: Optional[Zone] = Field(None, description="Overloaded zone (optional)")
    required_skill: Optional[str] = Field(None, description="Required skill (optional)")


class ShiftRecommendation(BaseModel):
    """Shift recommendation model."""
    worker_id: str
    worker_name: str
    from_zone: Zone
    to_zone: Zone
    skill_match: str
    match_type: str = Field(
        ...,
        description="Type of match: 'primary' or 'transferable'"
    )
    reasoning: str = Field(..., description="AI-generated reasoning for recommendation")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)"
    )
    load_impact: dict = Field(
        default_factory=dict,
        description="Load impact on zones"
    )


class ShiftPlan(BaseModel):
    """Updated shift plan after worker reassignment."""
    recommendations: List[ShiftRecommendation]
    total_workers_affected: int
    zones_rebalanced: List[Zone]
    estimated_improvement: str
    timestamp: str

# Made with Bob

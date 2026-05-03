"""
Custom tools for CrewAI agents.
Provides tools for searching workers and analyzing zone capacity.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class SearchWorkersTool(BaseModel):
    """Tool for searching workers by skill."""
    
    name: str = "search_workers"
    description: str = (
        "Search for workers with specific skills. "
        "Input should be a skill name (e.g., 'forklift operator'). "
        "Returns a list of matching workers with their details."
    )
    
    retriever: Any = Field(default=None, exclude=True)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, skill: str, exclude_zone: Optional[str] = None) -> str:
        """Execute the search."""
        try:
            from data.models import Zone
            
            exclude_zone_enum = None
            if exclude_zone:
                try:
                    exclude_zone_enum = Zone(exclude_zone)
                except ValueError:
                    pass
            
            workers = self.retriever.search_by_skill(
                skill_query=skill,
                exclude_zone=exclude_zone_enum,
                top_k=5
            )
            
            if not workers:
                return f"No workers found with skill: {skill}"
            
            # Format results
            result = f"Found {len(workers)} workers with '{skill}' skill:\n\n"
            for i, worker in enumerate(workers, 1):
                result += f"{i}. {worker['name']} (ID: {worker['worker_id']})\n"
                result += f"   - Primary Skill: {worker['primary_skill']}\n"
                result += f"   - Match Type: {worker['match_type']}\n"
                result += f"   - Current Zone: {worker['current_zone']}\n"
                result += f"   - Shift: {worker['shift']}\n"
                result += f"   - Load Status: {worker['load_status']}\n"
                result += f"   - Match Score: {worker['match_score']}\n\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in search_workers tool: {e}")
            return f"Error searching for workers: {str(e)}"


class GetWorkerDetailsTool(BaseModel):
    """Tool for getting detailed information about a specific worker."""
    
    name: str = "get_worker_details"
    description: str = (
        "Get detailed information about a specific worker by ID. "
        "Input should be a worker ID (e.g., 'W001')."
    )
    
    data_loader: Any = Field(default=None, exclude=True)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, worker_id: str) -> str:
        """Get worker details."""
        try:
            worker = self.data_loader.get_worker_by_id(worker_id)
            
            if not worker:
                return f"Worker not found: {worker_id}"
            
            result = f"Worker Details for {worker.name} ({worker.worker_id}):\n"
            result += f"- Primary Skill: {worker.primary_skill}\n"
            result += f"- Transferable Skills: {', '.join(worker.transferable_skills)}\n"
            result += f"- Current Zone: {worker.current_zone.value}\n"
            result += f"- Shift: {worker.shift.value}\n"
            result += f"- Load Status: {worker.load_status.value} ({worker.get_load_percentage()}%)\n"
            result += f"- Available: {'Yes' if worker.available else 'No'}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in get_worker_details tool: {e}")
            return f"Error getting worker details: {str(e)}"


class CheckZoneCapacityTool(BaseModel):
    """Tool for checking zone capacity and availability."""
    
    name: str = "check_zone_capacity"
    description: str = (
        "Check the capacity and worker availability in a specific zone. "
        "Input should be a zone name (e.g., 'Zone A', 'Zone B')."
    )
    
    retriever: Any = Field(default=None, exclude=True)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, zone: str) -> str:
        """Check zone capacity."""
        try:
            from data.models import Zone
            
            zone_enum = Zone(zone)
            capacity = self.retriever.get_zone_capacity(zone_enum)
            
            result = f"Zone Capacity for {zone}:\n"
            result += f"- Total Workers: {capacity['total_workers']}\n"
            result += f"- Available Workers: {capacity['available_workers']}\n"
            result += f"- Low Load Workers: {capacity['low_load_workers']}\n"
            result += f"- Can Spare Worker: {'Yes' if capacity['can_spare_worker'] else 'No'}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in check_zone_capacity tool: {e}")
            return f"Error checking zone capacity: {str(e)}"


class CalculateLoadImpactTool(BaseModel):
    """Tool for calculating load impact of moving a worker."""
    
    name: str = "calculate_load_impact"
    description: str = (
        "Calculate the impact on zone loads if a worker is moved. "
        "Input should be worker_id, from_zone, to_zone (comma-separated)."
    )
    
    data_loader: Any = Field(default=None, exclude=True)
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, input_str: str) -> str:
        """Calculate load impact."""
        try:
            parts = [p.strip() for p in input_str.split(',')]
            if len(parts) != 3:
                return "Invalid input. Expected: worker_id, from_zone, to_zone"
            
            worker_id, from_zone, to_zone = parts
            
            worker = self.data_loader.get_worker_by_id(worker_id)
            if not worker:
                return f"Worker not found: {worker_id}"
            
            from data.models import Zone
            from_zone_enum = Zone(from_zone)
            to_zone_enum = Zone(to_zone)
            
            # Get zone statistics
            from_zone_workers = self.data_loader.get_workers_by_zone(from_zone_enum)
            to_zone_workers = self.data_loader.get_workers_by_zone(to_zone_enum)
            
            # Calculate current loads
            from_zone_load = sum(w.get_load_percentage() for w in from_zone_workers) / len(from_zone_workers) if from_zone_workers else 0
            to_zone_load = sum(w.get_load_percentage() for w in to_zone_workers) / len(to_zone_workers) if to_zone_workers else 0
            
            # Calculate new loads after move
            worker_load = worker.get_load_percentage()
            new_from_load = (from_zone_load * len(from_zone_workers) - worker_load) / max(len(from_zone_workers) - 1, 1)
            new_to_load = (to_zone_load * len(to_zone_workers) + worker_load) / (len(to_zone_workers) + 1)
            
            result = f"Load Impact Analysis:\n"
            result += f"\n{from_zone}:\n"
            result += f"  Current Load: {from_zone_load:.1f}%\n"
            result += f"  After Move: {new_from_load:.1f}%\n"
            result += f"  Change: {new_from_load - from_zone_load:+.1f}%\n"
            result += f"\n{to_zone}:\n"
            result += f"  Current Load: {to_zone_load:.1f}%\n"
            result += f"  After Move: {new_to_load:.1f}%\n"
            result += f"  Change: {new_to_load - to_zone_load:+.1f}%\n"
            result += f"\nOverall Balance Improvement: {abs(new_from_load - new_to_load) < abs(from_zone_load - to_zone_load)}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in calculate_load_impact tool: {e}")
            return f"Error calculating load impact: {str(e)}"

# Made with Bob

"""
Shift Planner Agent for selecting the best worker and explaining the decision.
Uses CrewAI to make intelligent shift recommendations.
"""
from crewai import Agent, Task
from typing import List, Dict, Any, Optional
import logging

from agents.tools import CalculateLoadImpactTool, CheckZoneCapacityTool
from data.models import ShiftRecommendation

logger = logging.getLogger(__name__)


def create_shift_planner_agent(llm, tools: List[Any]) -> Agent:
    """
    Create the Shift Planner Agent.
    
    Args:
        llm: Language model instance
        tools: List of tools for the agent
        
    Returns:
        Configured Agent instance
    """
    agent = Agent(
        role="Workforce Optimization Strategist",
        goal="Select the best worker to shift and provide clear reasoning for the decision",
        backstory=(
            "You are an experienced workforce manager who excels at balancing workload "
            "across zones while minimizing disruption. You consider multiple factors: "
            "skill match quality, current zone capacity, worker load, and overall impact. "
            "You always provide clear, actionable recommendations with detailed reasoning "
            "that managers can understand and trust."
        ),
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    return agent


def create_shift_planning_task(
    agent: Agent,
    candidates: List[Dict[str, Any]],
    target_zone: str,
    skill_requirement: str
) -> Task:
    """
    Create a task for the Shift Planner Agent.
    
    Args:
        agent: Shift Planner Agent instance
        candidates: List of candidate workers
        target_zone: Zone that needs help
        skill_requirement: Required skill
        
    Returns:
        Configured Task instance
    """
    candidates_text = "\n".join([
        f"- {c['name']} ({c['worker_id']}): {c['primary_skill']}, "
        f"Zone {c['current_zone']}, {c['load_status']} load, "
        f"Match: {c['match_type']} ({c['match_score']})"
        for c in candidates[:5]
    ])
    
    task = Task(
        description=(
            f"Analyze these worker candidates and select the BEST ONE to move to {target_zone} "
            f"for {skill_requirement} work:\n\n"
            f"{candidates_text}\n\n"
            f"For each candidate, check:\n"
            f"1. Their source zone capacity (can it spare them?)\n"
            f"2. The load impact of moving them\n"
            f"3. Their skill match quality\n\n"
            f"Select the single best candidate and provide:\n"
            f"- Worker ID and name\n"
            f"- Clear reasoning (2-3 sentences)\n"
            f"- Expected load impact on both zones\n"
            f"- Confidence level (High/Medium/Low)"
        ),
        expected_output=(
            "A single recommendation with:\n"
            "- Selected worker: [ID] [Name]\n"
            "- From: [Source Zone]\n"
            "- To: [Target Zone]\n"
            "- Skill match: [primary/transferable]\n"
            "- Reasoning: [Clear explanation]\n"
            "- Load impact: [Specific percentages]\n"
            "- Confidence: [High/Medium/Low]"
        ),
        agent=agent
    )
    
    return task


class ShiftPlannerService:
    """Service for shift planning operations."""
    
    def __init__(self, data_loader):
        """
        Initialize the shift planner service.
        
        Args:
            data_loader: WorkerDataLoader instance
        """
        self.data_loader = data_loader
        logger.info("ShiftPlannerService initialized")
    
    def create_recommendation(
        self,
        worker: Dict[str, Any],
        target_zone: str,
        skill_requirement: str,
        reasoning: str,
        confidence: float = 0.8
    ) -> ShiftRecommendation:
        """
        Create a shift recommendation object.
        
        Args:
            worker: Selected worker dictionary
            target_zone: Target zone
            skill_requirement: Required skill
            reasoning: Explanation for the recommendation
            confidence: Confidence score (0-1)
            
        Returns:
            ShiftRecommendation object
        """
        from data.models import Zone
        
        # Calculate load impact
        load_impact = self._calculate_load_impact(
            worker['worker_id'],
            worker['current_zone'],
            target_zone
        )
        
        recommendation = ShiftRecommendation(
            worker_id=worker['worker_id'],
            worker_name=worker['name'],
            from_zone=Zone(worker['current_zone']),
            to_zone=Zone(target_zone),
            skill_match=skill_requirement,
            match_type=worker.get('match_type', 'transferable'),
            reasoning=reasoning,
            confidence_score=confidence,
            load_impact=load_impact
        )
        
        return recommendation
    
    def _calculate_load_impact(
        self,
        worker_id: str,
        from_zone: str,
        to_zone: str
    ) -> Dict[str, float]:
        """
        Calculate the load impact of moving a worker.
        
        Args:
            worker_id: Worker ID
            from_zone: Source zone
            to_zone: Target zone
            
        Returns:
            Dictionary with load impact data
        """
        from data.models import Zone
        
        worker = self.data_loader.get_worker_by_id(worker_id)
        if not worker:
            return {}
        
        from_zone_enum = Zone(from_zone)
        to_zone_enum = Zone(to_zone)
        
        # Get zone workers
        from_zone_workers = self.data_loader.get_workers_by_zone(from_zone_enum)
        to_zone_workers = self.data_loader.get_workers_by_zone(to_zone_enum)
        
        # Calculate current loads
        from_zone_load = (
            sum(w.get_load_percentage() for w in from_zone_workers) / len(from_zone_workers)
            if from_zone_workers else 0
        )
        to_zone_load = (
            sum(w.get_load_percentage() for w in to_zone_workers) / len(to_zone_workers)
            if to_zone_workers else 0
        )
        
        # Calculate new loads after move
        worker_load = worker.get_load_percentage()
        new_from_load = (
            (from_zone_load * len(from_zone_workers) - worker_load) / max(len(from_zone_workers) - 1, 1)
        )
        new_to_load = (
            (to_zone_load * len(to_zone_workers) + worker_load) / (len(to_zone_workers) + 1)
        )
        
        return {
            'from_zone': from_zone,
            'from_zone_current_load': round(from_zone_load, 1),
            'from_zone_new_load': round(new_from_load, 1),
            'from_zone_change': round(new_from_load - from_zone_load, 1),
            'to_zone': to_zone,
            'to_zone_current_load': round(to_zone_load, 1),
            'to_zone_new_load': round(new_to_load, 1),
            'to_zone_change': round(new_to_load - to_zone_load, 1),
            'balance_improved': abs(new_from_load - new_to_load) < abs(from_zone_load - to_zone_load)
        }
    
    def select_best_candidate(
        self,
        candidates: List[Dict[str, Any]],
        target_zone: str
    ) -> Optional[Dict[str, Any]]:
        """
        Select the best candidate from the list.
        
        Args:
            candidates: List of candidate workers
            target_zone: Target zone (used for zone capacity analysis)
            
        Returns:
            Best candidate or None
        """
        if not candidates:
            return None
        
        from data.models import Zone
        
        # Score each candidate
        scored_candidates = []
        for candidate in candidates:
            score = 0.0
            
            # Match score (35%)
            score += candidate.get('match_score', 0.5) * 0.35
            
            # Load status (30%) - prefer low load
            load_map = {'Low': 1.0, 'Medium': 0.6, 'High': 0.2}
            score += load_map.get(candidate.get('load_status', 'Medium'), 0.5) * 0.3
            
            # Match type (20%) - prefer primary
            match_type_map = {'primary': 1.0, 'transferable': 0.8}
            score += match_type_map.get(candidate.get('match_type', 'transferable'), 0.7) * 0.2
            
            # Zone capacity (15%) - can source zone spare them?
            try:
                source_zone = Zone(candidate.get('current_zone'))
                source_workers = self.data_loader.get_workers_by_zone(source_zone)
                available_count = sum(1 for w in source_workers if w.available and w.load_status.value == 'Low')
                
                # Higher score if source zone has more available low-load workers
                if len(source_workers) > 0:
                    capacity_ratio = available_count / len(source_workers)
                    score += capacity_ratio * 0.15
                else:
                    score += 0.05  # Default if no workers
            except Exception as e:
                logger.warning(f"Could not calculate zone capacity for {candidate.get('name')}: {e}")
                score += 0.05  # Default score
            
            candidate['selection_score'] = round(score, 3)
            scored_candidates.append(candidate)
        
        # Return highest scoring candidate
        best = max(scored_candidates, key=lambda x: x['selection_score'])
        logger.info(f"Selected best candidate: {best['name']} (score: {best['selection_score']}) for {target_zone}")
        
        return best

# Made with Bob

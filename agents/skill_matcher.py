"""
Skill Matcher Agent for finding workers with matching skills.
Uses CrewAI to intelligently search for suitable workers.
"""
from crewai import Agent, Task
from typing import List, Dict, Any
import logging

from agents.tools import SearchWorkersTool, GetWorkerDetailsTool, CheckZoneCapacityTool

logger = logging.getLogger(__name__)


def create_skill_matcher_agent(llm, tools: List[Any]) -> Agent:
    """
    Create the Skill Matcher Agent.
    
    Args:
        llm: Language model instance
        tools: List of tools for the agent
        
    Returns:
        Configured Agent instance
    """
    agent = Agent(
        role="Skill Search Specialist",
        goal="Find workers with matching or transferable skills for the required position",
        backstory=(
            "You are an expert at understanding skill relationships and worker capabilities. "
            "You excel at finding workers whose primary or transferable skills match the requirements. "
            "You consider not just exact matches but also related skills that could fulfill the need. "
            "You always prioritize workers who are available and have lower workload."
        ),
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    return agent


def create_skill_matching_task(
    agent: Agent,
    skill_requirement: str,
    exclude_zone: str,
    shift: str = None
) -> Task:
    """
    Create a task for the Skill Matcher Agent.
    
    Args:
        agent: Skill Matcher Agent instance
        skill_requirement: Required skill
        exclude_zone: Zone to exclude from search
        shift: Required shift (optional)
        
    Returns:
        Configured Task instance
    """
    shift_context = f" during the {shift} shift" if shift else ""
    
    task = Task(
        description=(
            f"Find the best workers who have '{skill_requirement}' skill{shift_context}. "
            f"Do NOT include workers from {exclude_zone}. "
            f"Search for workers with this skill and analyze their suitability. "
            f"Consider:\n"
            f"1. Workers with '{skill_requirement}' as primary skill (best match)\n"
            f"2. Workers with '{skill_requirement}' as transferable skill (good match)\n"
            f"3. Workers with related skills (acceptable match)\n"
            f"4. Worker availability and current workload\n"
            f"5. Zone capacity - can the source zone spare this worker?\n\n"
            f"Return the top 3-5 candidates with their details and match quality."
        ),
        expected_output=(
            "A ranked list of 3-5 worker candidates with:\n"
            "- Worker ID and name\n"
            "- Match type (primary/transferable/related)\n"
            "- Current zone and shift\n"
            "- Load status\n"
            "- Brief explanation of why they're suitable"
        ),
        agent=agent
    )
    
    return task


class SkillMatcherService:
    """Service for skill matching operations."""
    
    def __init__(self, retriever, data_loader):
        """
        Initialize the skill matcher service.
        
        Args:
            retriever: WorkerRetriever instance
            data_loader: WorkerDataLoader instance
        """
        self.retriever = retriever
        self.data_loader = data_loader
        logger.info("SkillMatcherService initialized")
    
    def find_candidates(
        self,
        skill: str,
        exclude_zone: str = None,
        shift: str = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find worker candidates matching the skill requirement.
        
        Args:
            skill: Required skill
            exclude_zone: Zone to exclude
            shift: Required shift
            top_k: Number of candidates to return
            
        Returns:
            List of candidate workers
        """
        from data.models import Zone, Shift as ShiftEnum
        
        exclude_zone_enum = None
        if exclude_zone:
            try:
                exclude_zone_enum = Zone(exclude_zone)
            except ValueError:
                logger.warning(f"Invalid zone: {exclude_zone}")
        
        shift_enum = None
        if shift:
            try:
                shift_enum = ShiftEnum(shift)
            except ValueError:
                logger.warning(f"Invalid shift: {shift}")
        
        candidates = self.retriever.search_by_skill(
            skill_query=skill,
            exclude_zone=exclude_zone_enum,
            required_shift=shift_enum,
            only_available=True,
            top_k=top_k
        )
        
        logger.info(f"Found {len(candidates)} candidates for skill: {skill}")
        return candidates
    
    def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        criteria: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank candidates based on multiple criteria.
        
        Args:
            candidates: List of candidate workers
            criteria: Weighting for different criteria
            
        Returns:
            Ranked list of candidates
        """
        if not criteria:
            criteria = {
                'match_score': 0.4,
                'load_status': 0.3,
                'match_type': 0.3
            }
        
        for candidate in candidates:
            score = 0.0
            
            # Match score contribution
            score += candidate.get('match_score', 0.5) * criteria['match_score']
            
            # Load status contribution (lower is better)
            load_map = {'Low': 1.0, 'Medium': 0.6, 'High': 0.2}
            load_score = load_map.get(candidate.get('load_status', 'Medium'), 0.5)
            score += load_score * criteria['load_status']
            
            # Match type contribution
            match_type_map = {'primary': 1.0, 'transferable': 0.8}
            match_type_score = match_type_map.get(candidate.get('match_type', 'transferable'), 0.7)
            score += match_type_score * criteria['match_type']
            
            candidate['ranking_score'] = round(score, 3)
        
        # Sort by ranking score
        ranked = sorted(candidates, key=lambda x: x['ranking_score'], reverse=True)
        
        return ranked

# Made with Bob

"""
CrewAI setup and orchestration for SmartShift agents.
Configures the crew with IBM Granite LLM and coordinates agent workflow.
"""
from crewai import Crew, Process
from typing import Dict, Any, List
import logging

from agents.skill_matcher import (
    create_skill_matcher_agent,
    create_skill_matching_task,
    SkillMatcherService
)
from agents.shift_planner import (
    create_shift_planner_agent,
    create_shift_planning_task,
    ShiftPlannerService
)
from agents.tools import (
    SearchWorkersTool,
    GetWorkerDetailsTool,
    CheckZoneCapacityTool,
    CalculateLoadImpactTool
)
from config.settings import get_settings

logger = logging.getLogger(__name__)


class SmartShiftCrew:
    """Manages the CrewAI workflow for SmartShift."""

    def __init__(self, retriever, data_loader, embedder):
        """
        Initialize the SmartShift crew.

        Args:
            retriever: WorkerRetriever instance
            data_loader: WorkerDataLoader instance
            embedder: SkillEmbedder instance
        """
        self.retriever = retriever        # stored for diagnostics
        self.data_loader = data_loader
        self.embedder = embedder          # stored for diagnostics
        self.settings = get_settings()

        # Initialize services
        self.skill_matcher_service = SkillMatcherService(retriever, data_loader)
        self.shift_planner_service = ShiftPlannerService(data_loader)

        # Initialize LLM
        self.llm = self._initialize_llm()

        # Initialize tools
        self.tools = self._initialize_tools()

        logger.info("SmartShiftCrew initialized")

    def _initialize_llm(self):
        """Initialize IBM Granite LLM via watsonx.ai."""
        if not self.settings.validate_watsonx_credentials():
            logger.warning(
                "watsonx.ai credentials not configured. Using fallback logic."
            )
            return None

        try:
            from langchain_ibm import WatsonxLLM
            llm = WatsonxLLM(
                model_id=self.settings.llm_model,
                url=self.settings.watsonx_url,
                apikey=self.settings.watsonx_api_key,
                project_id=self.settings.watsonx_project_id,
                params={
                    "max_new_tokens": self.settings.llm_max_tokens,
                    "temperature": self.settings.llm_temperature,
                    "top_p": 0.9,
                    "top_k": 50
                }
            )
            logger.info(f"Initialized watsonx LLM: {self.settings.llm_model}")
            return llm
        except Exception as e:
            logger.error(f"Error initializing watsonx LLM: {e}")
            return None

    def _initialize_tools(self) -> List[Any]:
        """Initialize tools for agents."""
        tools = [
            SearchWorkersTool(retriever=self.retriever),
            GetWorkerDetailsTool(data_loader=self.data_loader),
            CheckZoneCapacityTool(retriever=self.retriever),
            CalculateLoadImpactTool(data_loader=self.data_loader)
        ]
        logger.info(f"Initialized {len(tools)} tools for agents")
        return tools

    def process_overload_request(
        self,
        description: str,
        parsed_query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process an overload request using rule-based fallback logic.

        Args:
            description: Original overload description
            parsed_query: Parsed query information

        Returns:
            Dictionary with recommendations and reasoning
        """
        logger.info(f"Processing overload request (fallback): {description}")

        try:
            target_zone = parsed_query.get('zone')
            skill_requirement = parsed_query.get('skill')
            shift = parsed_query.get('shift')

            if not target_zone or not skill_requirement:
                return {
                    'success': False,
                    'error': 'Could not parse zone or skill from description'
                }

            # Step 1: Find candidates
            candidates = self.skill_matcher_service.find_candidates(
                skill=skill_requirement,
                exclude_zone=target_zone,
                shift=shift,
                top_k=5
            )

            if not candidates:
                return {
                    'success': False,
                    'error': (
                        f'No available workers found with '
                        f'{skill_requirement} skill'
                    )
                }

            # Step 2: Rank candidates
            ranked_candidates = self.skill_matcher_service.rank_candidates(
                candidates
            )

            # Step 3: Select best candidate
            best_candidate = self.shift_planner_service.select_best_candidate(
                ranked_candidates,
                target_zone
            )

            if not best_candidate:
                return {
                    'success': False,
                    'error': 'Could not select a suitable candidate'
                }

            # Step 4: Generate reasoning
            reasoning = self._generate_reasoning(
                best_candidate,
                target_zone,
                skill_requirement,
                ranked_candidates
            )

            # Step 5: Create recommendation
            recommendation = self.shift_planner_service.create_recommendation(
                worker=best_candidate,
                target_zone=target_zone,
                skill_requirement=skill_requirement,
                reasoning=reasoning,
                confidence=best_candidate.get('selection_score', 0.8)
            )

            return {
                'success': True,
                'recommendation': recommendation.dict(),
                'all_candidates': ranked_candidates[:3],
                'reasoning': reasoning
            }

        except Exception as e:
            logger.error(f"Error processing overload request: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_reasoning(
        self,
        selected_worker: Dict[str, Any],
        target_zone: str,
        skill: str,
        all_candidates: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable reasoning for the recommendation."""
        match_type = selected_worker.get('match_type', 'transferable')
        load_status = selected_worker.get('load_status', 'Medium')
        from_zone = selected_worker.get('current_zone')

        reasoning = (
            f"Recommend moving {selected_worker['name']} "
            f"from {from_zone} to {target_zone}. "
        )

        if match_type == 'primary':
            reasoning += (
                f"{skill.capitalize()} is their primary skill, "
                f"ensuring high performance. "
            )
        else:
            reasoning += (
                f"They have {skill} as a transferable skill, "
                f"making them well-suited for this role. "
            )

        if load_status == 'Low':
            reasoning += (
                f"{from_zone} is currently at low load "
                f"and can spare this worker. "
            )
        elif load_status == 'Medium':
            reasoning += (
                f"{from_zone} has moderate load but can "
                f"accommodate this temporary shift. "
            )

        if len(all_candidates) > 1:
            reasoning += (
                f"Selected over {len(all_candidates) - 1} other candidates "
                f"due to optimal skill match and zone capacity."
            )

        return reasoning

    def run_with_crewai(
        self,
        description: str,
        parsed_query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run the full CrewAI workflow (when LLM is available).

        Args:
            description: Overload description
            parsed_query: Parsed query

        Returns:
            Crew execution results
        """
        if not self.llm:
            logger.warning("LLM not available, using fallback logic")
            return self.process_overload_request(description, parsed_query)

        try:
            from agents.skill_matcher import create_skill_matcher_agent
            from agents.shift_planner import create_shift_planner_agent

            skill_matcher = create_skill_matcher_agent(self.llm, self.tools)
            shift_planner = create_shift_planner_agent(self.llm, self.tools)

            candidates = self.skill_matcher_service.find_candidates(
                skill=parsed_query.get('skill'),
                exclude_zone=parsed_query.get('zone'),
                shift=parsed_query.get('shift'),
                top_k=5
            )

            if not candidates:
                return {
                    'success': False,
                    'error': 'No candidates found'
                }

            skill_task = create_skill_matching_task(
                skill_matcher,
                parsed_query.get('skill'),
                parsed_query.get('zone'),
                parsed_query.get('shift')
            )

            planning_task = create_shift_planning_task(
                shift_planner,
                candidates,
                parsed_query.get('zone'),
                parsed_query.get('skill')
            )

            crew = Crew(
                agents=[skill_matcher, shift_planner],
                tasks=[skill_task, planning_task],
                process=Process.sequential,
                verbose=True
            )

            result = crew.kickoff()

            # Still build a proper recommendation from candidates
            ranked = self.skill_matcher_service.rank_candidates(candidates)
            best = self.shift_planner_service.select_best_candidate(
                ranked, parsed_query.get('zone')
            )
            reasoning = str(result)  # Use LLM output as reasoning

            recommendation = self.shift_planner_service.create_recommendation(
                worker=best,
                target_zone=parsed_query.get('zone'),
                skill_requirement=parsed_query.get('skill'),
                reasoning=reasoning,
                confidence=best.get('selection_score', 0.85)
            )

            return {
                'success': True,
                'recommendation': recommendation.dict(),
                'all_candidates': ranked[:3],
                'reasoning': reasoning
            }

        except Exception as e:
            logger.error(f"Error running CrewAI workflow: {e}")
            return self.process_overload_request(description, parsed_query)


def create_smartshift_crew(
    retriever, data_loader, embedder
) -> SmartShiftCrew:
    """
    Factory function to create SmartShift crew.

    Args:
        retriever: WorkerRetriever instance
        data_loader: WorkerDataLoader instance
        embedder: SkillEmbedder instance

    Returns:
        SmartShiftCrew instance
    """
    return SmartShiftCrew(retriever, data_loader, embedder)

# Made with Bob
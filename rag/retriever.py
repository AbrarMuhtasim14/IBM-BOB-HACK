"""
Retrieval module for finding relevant workers based on skill queries.
Implements semantic search with filtering capabilities.
"""
from typing import List, Dict, Any, Optional
import logging

from data.models import Worker, Zone, Shift, LoadStatus
from embeddings.skill_embedder import SkillEmbedder
from rag.vector_store import WorkerVectorStore

logger = logging.getLogger(__name__)


class WorkerRetriever:
    """Retrieves relevant workers based on skill requirements."""
    
    def __init__(
        self,
        vector_store: WorkerVectorStore,
        embedder: SkillEmbedder
    ):
        """
        Initialize the retriever.
        
        Args:
            vector_store: Vector store instance
            embedder: Skill embedder instance
        """
        self.vector_store = vector_store
        self.embedder = embedder
        logger.info("WorkerRetriever initialized")
    
    def search_by_skill(
        self,
        skill_query: str,
        exclude_zone: Optional[Zone] = None,
        required_shift: Optional[Shift] = None,
        only_available: bool = True,
        max_load: Optional[LoadStatus] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for workers with matching skills.
        
        Args:
            skill_query: Skill to search for (e.g., "forklift operator")
            exclude_zone: Zone to exclude from results
            required_shift: Required shift timing
            only_available: Only return available workers
            max_load: Maximum acceptable load status
            top_k: Number of results to return
            
        Returns:
            List of worker dictionaries with match scores
        """
        logger.info(f"Searching for workers with skill: {skill_query}")
        
        # Generate embedding for the skill query
        skill_embedding = self.embedder.embed_text(skill_query)
        
        # Build filters
        filters = {}
        if only_available:
            filters["available"] = True  # Use boolean, not string
        if required_shift:
            filters["shift"] = required_shift.value
        
        # Search in vector store
        results = self.vector_store.search_by_skill(
            skill_embedding=skill_embedding,
            n_results=top_k * 2,  # Get more results for filtering
            filters=filters if filters else None
        )
        
        # Process and filter results
        workers = []
        if results and results.get('ids'):
            for i, worker_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i] if 'distances' in results else 0
                
                # Apply zone filter
                if exclude_zone and metadata['current_zone'] == exclude_zone.value:
                    continue
                
                # Apply load filter
                if max_load:
                    worker_load = LoadStatus(metadata['load_status'])
                    if worker_load == LoadStatus.HIGH and max_load != LoadStatus.HIGH:
                        continue
                
                # Calculate match score (convert distance to similarity)
                match_score = 1 - (distance / 2)  # Normalize to 0-1
                
                worker_data = {
                    'worker_id': worker_id,
                    'name': metadata['name'],
                    'primary_skill': metadata['primary_skill'],
                    'transferable_skills': metadata['transferable_skills'].split(';'),
                    'current_zone': metadata['current_zone'],
                    'shift': metadata['shift'],
                    'load_status': metadata['load_status'],
                    'available': metadata['available'],  # Already boolean
                    'match_score': round(match_score, 3),
                    'match_type': self._determine_match_type(
                        skill_query,
                        metadata['primary_skill'],
                        metadata['transferable_skills']
                    )
                }
                
                workers.append(worker_data)
                
                if len(workers) >= top_k:
                    break
        
        logger.info(f"Found {len(workers)} matching workers")
        return workers
    
    def _determine_match_type(
        self,
        query_skill: str,
        primary_skill: str,
        transferable_skills: str
    ) -> str:
        """
        Determine if match is primary or transferable skill.
        
        Args:
            query_skill: Queried skill
            primary_skill: Worker's primary skill
            transferable_skills: Worker's transferable skills (semicolon-separated)
            
        Returns:
            'primary' or 'transferable'
        """
        query_lower = query_skill.lower()
        primary_lower = primary_skill.lower()
        
        # Check for primary skill match
        if query_lower in primary_lower or primary_lower in query_lower:
            return 'primary'
        
        # Check for transferable skill match
        transferable_list = [s.strip().lower() for s in transferable_skills.split(';')]
        for skill in transferable_list:
            if query_lower in skill or skill in query_lower:
                return 'transferable'
        
        # Default to transferable if semantic match
        return 'transferable'
    
    def get_available_workers_by_zone(
        self,
        zone: Zone,
        only_low_load: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all available workers in a specific zone.
        
        Args:
            zone: Zone to search
            only_low_load: Only return workers with low load
            
        Returns:
            List of worker dictionaries
        """
        filters = {
            "current_zone": zone.value,
            "available": True  # Use boolean, not string
        }
        
        if only_low_load:
            filters["load_status"] = LoadStatus.LOW.value
        
        # Use a broader query that will match skills_text content
        # Search for common skill terms that appear in worker profiles
        results = self.vector_store.search_by_text(
            query_text="",  # Empty string to match all when filtered
            n_results=100,
            filters=filters
        )
        
        workers = []
        if results and results.get('ids'):
            for i, worker_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                
                worker_data = {
                    'worker_id': worker_id,
                    'name': metadata['name'],
                    'primary_skill': metadata['primary_skill'],
                    'transferable_skills': metadata['transferable_skills'].split(';'),
                    'current_zone': metadata['current_zone'],
                    'shift': metadata['shift'],
                    'load_status': metadata['load_status'],
                    'available': metadata['available']  # Already boolean
                }
                
                workers.append(worker_data)
        
        return workers
    
    def find_best_match(
        self,
        skill_query: str,
        exclude_zone: Optional[Zone] = None,
        required_shift: Optional[Shift] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find the single best matching worker.
        
        Args:
            skill_query: Skill to search for
            exclude_zone: Zone to exclude
            required_shift: Required shift
            
        Returns:
            Best matching worker or None
        """
        workers = self.search_by_skill(
            skill_query=skill_query,
            exclude_zone=exclude_zone,
            required_shift=required_shift,
            only_available=True,
            top_k=1
        )
        
        return workers[0] if workers else None
    
    def get_zone_capacity(self, zone: Zone) -> Dict[str, Any]:
        """
        Get capacity information for a zone.
        
        Args:
            zone: Zone to analyze
            
        Returns:
            Dictionary with zone capacity info
        """
        all_workers = self.get_available_workers_by_zone(zone, only_low_load=False)
        low_load_workers = self.get_available_workers_by_zone(zone, only_low_load=True)
        
        return {
            'zone': zone.value,
            'total_workers': len(all_workers),
            'available_workers': len([w for w in all_workers if w['available']]),
            'low_load_workers': len(low_load_workers),
            'can_spare_worker': len(low_load_workers) > 0
        }

# Made with Bob

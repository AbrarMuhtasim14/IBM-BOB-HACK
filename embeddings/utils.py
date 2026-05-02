"""
Utility functions for embeddings module.
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def normalize_skill_name(skill: str) -> str:
    """
    Normalize skill name for consistent matching.
    
    Args:
        skill: Raw skill name
        
    Returns:
        Normalized skill name
    """
    return skill.strip().lower()


def extract_unique_skills(workers_data: List[Dict[str, Any]]) -> List[str]:
    """
    Extract unique skills from worker data.
    
    Args:
        workers_data: List of worker profile dictionaries
        
    Returns:
        List of unique skill names
    """
    skills = set()
    
    for worker in workers_data:
        if "all_skills" in worker:
            for skill in worker["all_skills"]:
                skills.add(normalize_skill_name(skill))
    
    return sorted(list(skills))


def create_skill_embedding_map(
    skills: List[str],
    embeddings: List[List[float]]
) -> Dict[str, List[float]]:
    """
    Create a mapping from skill names to their embeddings.
    
    Args:
        skills: List of skill names
        embeddings: List of embedding vectors
        
    Returns:
        Dictionary mapping skill names to embeddings
    """
    if len(skills) != len(embeddings):
        raise ValueError("Number of skills must match number of embeddings")
    
    return {skill: embedding for skill, embedding in zip(skills, embeddings)}


def batch_list(items: List[Any], batch_size: int) -> List[List[Any]]:
    """
    Split a list into batches.
    
    Args:
        items: List to batch
        batch_size: Size of each batch
        
    Returns:
        List of batches
    """
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

# Made with Bob

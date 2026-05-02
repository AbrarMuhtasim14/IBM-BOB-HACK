"""
Skill embedding module using sentence-transformers.
Generates vector embeddings for worker skills to enable semantic search.
"""
from typing import List, Dict, Any
import logging
from sentence_transformers import SentenceTransformer
import numpy as np

from data.models import Worker

logger = logging.getLogger(__name__)


class SkillEmbedder:
    """Generates embeddings for worker skills using sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the skill embedder.
        
        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model_name = model_name
        self._model = None
        logger.info(f"Initializing SkillEmbedder with model: {model_name}")
    
    def _load_model(self) -> SentenceTransformer:
        """Lazy load the sentence-transformers model."""
        if self._model is None:
            logger.info(f"Loading sentence-transformers model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        model = self._load_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        return embeddings.tolist()
    
    def embed_skills(self, skills: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of skills.
        
        Args:
            skills: List of skill names
            
        Returns:
            List of embedding vectors
        """
        return self.embed_texts(skills)
    
    def embed_worker_profile(self, worker: Worker) -> Dict[str, Any]:
        """
        Generate embeddings for a worker's complete skill profile.
        
        Args:
            worker: Worker object
            
        Returns:
            Dictionary containing worker info and embeddings
        """
        # Combine all skills into a single text for comprehensive embedding
        all_skills = worker.get_all_skills()
        skills_text = ", ".join(all_skills)
        
        # Also create individual skill embeddings
        individual_embeddings = self.embed_skills(all_skills)
        
        # Create a combined profile embedding
        profile_text = f"{worker.primary_skill}. Additional skills: {', '.join(worker.transferable_skills)}"
        profile_embedding = self.embed_text(profile_text)
        
        return {
            "worker_id": worker.worker_id,
            "name": worker.name,
            "primary_skill": worker.primary_skill,
            "transferable_skills": worker.transferable_skills,
            "all_skills": all_skills,
            "skills_text": skills_text,
            "profile_embedding": profile_embedding,
            "individual_skill_embeddings": individual_embeddings,
            "current_zone": worker.current_zone.value,
            "shift": worker.shift.value,
            "load_status": worker.load_status.value,
            "available": worker.available
        }
    
    def embed_worker_profiles(self, workers: List[Worker]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for multiple worker profiles.
        
        Args:
            workers: List of Worker objects
            
        Returns:
            List of dictionaries containing worker info and embeddings
        """
        logger.info(f"Generating embeddings for {len(workers)} workers")
        profiles = []
        
        for worker in workers:
            try:
                profile = self.embed_worker_profile(worker)
                profiles.append(profile)
            except Exception as e:
                logger.error(f"Error embedding worker {worker.worker_id}: {e}")
                continue
        
        logger.info(f"Successfully generated embeddings for {len(profiles)} workers")
        return profiles
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Cosine similarity
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        
        # Normalize to 0-1 range
        return float((similarity + 1) / 2)
    
    def find_similar_skills(
        self,
        query_skill: str,
        skill_embeddings: Dict[str, List[float]],
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find skills most similar to a query skill.
        
        Args:
            query_skill: Skill to search for
            skill_embeddings: Dictionary mapping skill names to embeddings
            top_k: Number of top results to return
            
        Returns:
            List of (skill_name, similarity_score) tuples
        """
        query_embedding = self.embed_text(query_skill)
        
        similarities = []
        for skill_name, skill_embedding in skill_embeddings.items():
            similarity = self.compute_similarity(query_embedding, skill_embedding)
            similarities.append((skill_name, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]


# Global embedder instance
_embedder_instance = None


def get_embedder(model_name: str = "all-MiniLM-L6-v2") -> SkillEmbedder:
    """Get or create the global embedder instance."""
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = SkillEmbedder(model_name)
    return _embedder_instance

# Made with Bob

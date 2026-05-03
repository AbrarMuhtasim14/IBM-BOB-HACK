"""
Simple embedder fallback when sentence-transformers is not available.
Uses basic text hashing for embeddings.
"""
from typing import List, Dict, Any
import logging
import hashlib
import numpy as np

from data.models import Worker

logger = logging.getLogger(__name__)


class SimpleEmbedder:
    """Simple embedder using text hashing when sentence-transformers unavailable."""
    
    def __init__(self, model_name: str = "simple-hash"):
        """Initialize the simple embedder."""
        self.model_name = model_name
        self.embedding_dim = 384  # Match all-MiniLM-L6-v2 dimension
        logger.info(f"Using SimpleEmbedder (fallback mode)")
    
    def _text_to_embedding(self, text: str) -> List[float]:
        """Convert text to a simple hash-based embedding."""
        # Create a deterministic embedding from text
        text_lower = text.lower().strip()
        
        # Use multiple hash functions to create embedding
        embedding = []
        for i in range(self.embedding_dim // 32):
            hash_input = f"{text_lower}_{i}".encode('utf-8')
            hash_obj = hashlib.sha256(hash_input)
            hash_bytes = hash_obj.digest()
            
            # Convert bytes to floats
            for j in range(0, len(hash_bytes), 4):
                if len(embedding) >= self.embedding_dim:
                    break
                chunk = hash_bytes[j:j+4]
                value = int.from_bytes(chunk, 'big') / (2**32)
                embedding.append(value)
        
        # Normalize
        embedding = np.array(embedding[:self.embedding_dim])
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.tolist()
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text string."""
        return self._text_to_embedding(text)
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self._text_to_embedding(text) for text in texts]
    
    def embed_skills(self, skills: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of skills."""
        return self.embed_texts(skills)
    
    def embed_worker_profile(self, worker: Worker) -> Dict[str, Any]:
        """Generate embeddings for a worker's complete skill profile."""
        all_skills = worker.get_all_skills()
        skills_text = ", ".join(all_skills)
        
        individual_embeddings = self.embed_skills(all_skills)
        
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
        """Generate embeddings for multiple worker profiles."""
        logger.info(f"Generating simple embeddings for {len(workers)} workers")
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
        """Compute cosine similarity between two embeddings."""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return float((similarity + 1) / 2)
    
    def find_similar_skills(
        self,
        query_skill: str,
        skill_embeddings: Dict[str, List[float]],
        top_k: int = 5
    ) -> List[tuple]:
        """Find skills most similar to a query skill."""
        query_embedding = self.embed_text(query_skill)
        
        similarities = []
        for skill_name, skill_embedding in skill_embeddings.items():
            similarity = self.compute_similarity(query_embedding, skill_embedding)
            similarities.append((skill_name, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

# Made with Bob

"""
FAISS vector store for worker skill embeddings.
Manages the vector database for semantic skill search.
"""
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import pickle
import numpy as np
import faiss

from data.models import Worker

logger = logging.getLogger(__name__)


class WorkerVectorStore:
    """Manages FAISS vector store for worker skills."""
    
    def __init__(
        self,
        persist_directory: str = "./faiss_db",
        collection_name: str = "worker_skills"
    ):
        """
        Initialize the vector store.
        
        Args:
            persist_directory: Directory to persist FAISS data
            collection_name: Name of the collection
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.index_file = self.persist_directory / f"{collection_name}.index"
        self.metadata_file = self.persist_directory / f"{collection_name}_metadata.pkl"
        
        self._index = None
        self._metadata = []
        self._id_to_idx = {}
        
        logger.info(f"Initializing WorkerVectorStore at {persist_directory}")
        
        # Load existing index if available
        self._load_index()
    
    def _load_index(self) -> None:
        """Load existing FAISS index and metadata from disk."""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                self._index = faiss.read_index(str(self.index_file))
                with open(self.metadata_file, 'rb') as f:
                    data = pickle.load(f)
                    self._metadata = data['metadata']
                    self._id_to_idx = data['id_to_idx']
                logger.info(f"Loaded existing index with {len(self._metadata)} workers")
            except Exception as e:
                logger.error(f"Error loading index: {e}")
                self._index = None
                self._metadata = []
                self._id_to_idx = {}
    
    def _save_index(self) -> None:
        """Save FAISS index and metadata to disk."""
        if self._index is None:
            return
        
        try:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self._index, str(self.index_file))
            with open(self.metadata_file, 'wb') as f:
                pickle.dump({
                    'metadata': self._metadata,
                    'id_to_idx': self._id_to_idx
                }, f)
            logger.info(f"Saved index with {len(self._metadata)} workers")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    def index_workers(self, worker_profiles: List[Dict[str, Any]]) -> None:
        """
        Index worker profiles in the vector store.
        
        Args:
            worker_profiles: List of worker profile dictionaries with embeddings
        """
        if not worker_profiles:
            logger.warning("No worker profiles to index")
            return
        
        # Extract embeddings and metadata
        embeddings = []
        metadata = []
        
        for profile in worker_profiles:
            embeddings.append(profile["profile_embedding"])
            
            # Store metadata
            # Convert transferable_skills list to semicolon-separated string for consistency
            transferable_skills_str = ';'.join(profile["transferable_skills"]) if isinstance(profile["transferable_skills"], list) else profile["transferable_skills"]
            
            meta = {
                "id": profile["worker_id"],
                "name": profile["name"],
                "primary_skill": profile["primary_skill"],
                "current_zone": profile["current_zone"],
                "shift": profile["shift"],
                "load_status": profile["load_status"],
                "available": profile["available"],  # Store as boolean
                "transferable_skills": transferable_skills_str,  # Store as string
                "skills_text": profile["skills_text"]
            }
            metadata.append(meta)
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)
        dimension = embeddings_array.shape[1]
        
        # Create FAISS index (using L2 distance)
        self._index = faiss.IndexFlatL2(dimension)
        self._index.add(embeddings_array)
        
        # Store metadata and ID mapping
        self._metadata = metadata
        self._id_to_idx = {meta["id"]: idx for idx, meta in enumerate(metadata)}
        
        # Save to disk
        self._save_index()
        
        logger.info(f"Indexed {len(worker_profiles)} workers in FAISS vector store")
    
    def search_by_skill(
        self,
        skill_embedding: List[float],
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for workers by skill embedding.
        
        Args:
            skill_embedding: Embedding vector for the skill query
            n_results: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            Dictionary containing search results
        """
        if self._index is None or len(self._metadata) == 0:
            logger.warning("Index is empty")
            return {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}
        
        # Convert query to numpy array
        query_vector = np.array([skill_embedding], dtype=np.float32)
        
        # Search in FAISS
        distances, indices = self._index.search(query_vector, min(n_results * 2, len(self._metadata)))
        
        # Filter results based on metadata filters
        filtered_results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            meta = self._metadata[idx]
            
            # Apply filters
            if filters:
                match = True
                for key, value in filters.items():
                    if value is not None and meta.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            filtered_results.append({
                "id": meta["id"],
                "distance": float(dist),
                "metadata": meta,
                "document": meta["skills_text"]
            })
            
            if len(filtered_results) >= n_results:
                break
        
        # Format results to match ChromaDB structure
        return {
            "ids": [[r["id"] for r in filtered_results]],
            "distances": [[r["distance"] for r in filtered_results]],
            "metadatas": [[r["metadata"] for r in filtered_results]],
            "documents": [[r["document"] for r in filtered_results]]
        }
    
    def search_by_text(
        self,
        query_text: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for workers by text query.
        Note: This requires an embedding model to convert text to vector.
        For now, we'll do a simple text match in metadata.
        
        Args:
            query_text: Text query (e.g., "forklift operator")
            n_results: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            Dictionary containing search results
        """
        if self._index is None or len(self._metadata) == 0:
            logger.warning("Index is empty")
            return {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}
        
        # Simple text matching in skills_text
        query_lower = query_text.lower()
        results = []
        
        for idx, meta in enumerate(self._metadata):
            # Check if query matches skills text (empty query matches all)
            if not query_text or query_lower in meta["skills_text"].lower():
                # Apply filters
                if filters:
                    match = True
                    for key, value in filters.items():
                        if value is not None and meta.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue
                
                results.append({
                    "id": meta["id"],
                    "distance": 0.0,  # Text match, no distance
                    "metadata": meta,
                    "document": meta["skills_text"]
                })
                
                if len(results) >= n_results:
                    break
        
        # Format results
        return {
            "ids": [[r["id"] for r in results]],
            "distances": [[r["distance"] for r in results]],
            "metadatas": [[r["metadata"] for r in results]],
            "documents": [[r["document"] for r in results]]
        }
    
    def get_worker_by_id(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific worker by ID.
        
        Args:
            worker_id: Worker ID
            
        Returns:
            Worker data or None if not found
        """
        idx = self._id_to_idx.get(worker_id)
        if idx is not None and idx < len(self._metadata):
            meta = self._metadata[idx]
            return {
                'id': meta["id"],
                'metadata': meta,
                'document': meta["skills_text"]
            }
        return None
    
    def update_worker_metadata(
        self,
        worker_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update worker metadata in the vector store.
        
        Args:
            worker_id: Worker ID
            metadata: New metadata
            
        Returns:
            True if successful, False otherwise
        """
        idx = self._id_to_idx.get(worker_id)
        if idx is not None and idx < len(self._metadata):
            # Update metadata
            self._metadata[idx].update(metadata)
            self._save_index()
            logger.info(f"Updated metadata for worker {worker_id}")
            return True
        
        logger.error(f"Worker {worker_id} not found")
        return False
    
    def delete_all(self) -> None:
        """Delete all data from the collection."""
        try:
            self._index = None
            self._metadata = []
            self._id_to_idx = {}
            
            if self.index_file.exists():
                self.index_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            
            logger.info(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        return {
            "collection_name": self.collection_name,
            "total_workers": len(self._metadata),
            "persist_directory": str(self.persist_directory)
        }


# Global vector store instance
_vector_store_instance = None


def get_vector_store(
    persist_directory: str = "./faiss_db",
    collection_name: str = "worker_skills"
) -> WorkerVectorStore:
    """Get or create the global vector store instance."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = WorkerVectorStore(persist_directory, collection_name)
    return _vector_store_instance

# Made with Bob

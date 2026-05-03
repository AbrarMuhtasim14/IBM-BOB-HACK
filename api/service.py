"""
Business logic service layer for SmartShift API.
Handles the core application logic and coordinates between components.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from data.models import Worker, Zone
from data.loader import WorkerDataLoader
from rag.query_builder import QueryBuilder
from agents.crew_setup import SmartShiftCrew

logger = logging.getLogger(__name__)


class SmartShiftService:
    """Main service class for SmartShift operations."""

    def __init__(
        self,
        data_loader: WorkerDataLoader,
        crew: SmartShiftCrew,
        query_builder: QueryBuilder
    ):
        """
        Initialize the service.

        Args:
            data_loader: Worker data loader instance
            crew: SmartShift crew instance
            query_builder: Query builder instance
        """
        self.data_loader = data_loader
        self.crew = crew
        self.query_builder = query_builder
        logger.info("SmartShiftService initialized")

    def get_all_workers(self) -> List[Dict[str, Any]]:
        """Get all workers."""
        workers = self.data_loader.get_workers()
        return [self._worker_to_dict(w) for w in workers]

    def get_worker_by_id(
        self, worker_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific worker by ID."""
        worker = self.data_loader.get_worker_by_id(worker_id)
        return self._worker_to_dict(worker) if worker else None

    def get_zone_statistics(self) -> Dict[str, Any]:
        """Get statistics for all zones."""
        return self.data_loader.get_zone_statistics()

    def _build_diagnostics(self, execution_path: str) -> Dict[str, Any]:
        """
        Build diagnostics dictionary showing what components were used.

        Args:
            execution_path: 'crewai' or 'fallback'

        Returns:
            Dictionary with diagnostic information
        """
        # Vector store stats
        try:
            vs_stats = (
                self.crew.retriever.vector_store.get_collection_stats()
            )
            vs_backend = vs_stats.get("backend", "faiss")
            vs_workers = vs_stats.get("total_workers", 0)
        except Exception:
            vs_backend = "unknown"
            vs_workers = 0

        # Embedding model name
        try:
            embedding_model = getattr(
                self.crew.embedder, "model_name", "unknown"
            )
        except Exception:
            embedding_model = "unknown"

        # LLM model name
        try:
            if self.crew.llm:
                llm_model = getattr(
                    self.crew.llm, "model_id",
                    self.crew.settings.llm_model
                )
            else:
                llm_model = "not configured"
        except Exception:
            llm_model = "unknown"

        return {
            "llm_used": bool(self.crew.llm),
            "llm_model": llm_model,
            "execution_path": execution_path,
            "vector_store_used": True,
            "vector_store_backend": vs_backend,
            "vector_store_workers_indexed": vs_workers,
            "embedding_model": embedding_model,
            "watsonx_configured": (
                self.crew.settings.validate_watsonx_credentials()
            ),
        }

    def process_overload_request(
        self, description: str
    ) -> Dict[str, Any]:
        """
        Process an overload situation and generate recommendations.

        Args:
            description: Natural language description of overload

        Returns:
            Dictionary with recommendation or error
        """
        logger.info(f"Processing overload request: {description}")

        try:
            # Step 1: Parse the description
            parsed_query = self.query_builder.parse_overload_description(
                description
            )

            # Step 2: Validate the query
            is_valid, error_msg = self.query_builder.validate_query(
                parsed_query
            )
            if not is_valid:
                return {
                    'success': False,
                    'error': error_msg,
                    'parsed_query': parsed_query
                }

            # Step 3: Decide execution path
            # Use CrewAI + LLM if configured, otherwise fallback
            if self.crew.llm:
                execution_path = "crewai"
                logger.info("Using CrewAI + watsonx LLM path")
                result = self.crew.run_with_crewai(
                    description, parsed_query
                )
            else:
                execution_path = "fallback"
                logger.info("Using rule-based fallback path (no LLM)")
                result = self.crew.process_overload_request(
                    description, parsed_query
                )

            # Step 4: Add diagnostics to result
            result['diagnostics'] = self._build_diagnostics(execution_path)

            # Step 5: Add timestamp and parsed query
            result['timestamp'] = datetime.utcnow().isoformat()
            result['parsed_query'] = parsed_query

            return result

        except Exception as e:
            logger.error(f"Error processing overload request: {e}")
            return {
                'success': False,
                'error': f"Internal error: {str(e)}",
                'timestamp': datetime.utcnow().isoformat()
            }

    def confirm_shift_change(
        self,
        worker_id: str,
        from_zone: str,
        to_zone: str,
        confirmed_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Confirm and execute a shift change.

        Args:
            worker_id: Worker ID
            from_zone: Source zone
            to_zone: Target zone
            confirmed_by: Manager name (optional)

        Returns:
            Dictionary with confirmation result
        """
        logger.info(
            f"Confirming shift change: {worker_id} "
            f"from {from_zone} to {to_zone}"
        )

        try:
            worker = self.data_loader.get_worker_by_id(worker_id)
            if not worker:
                return {
                    'success': False,
                    'message': f"Worker not found: {worker_id}"
                }

            if worker.current_zone.value != from_zone:
                return {
                    'success': False,
                    'message': (
                        f"Worker is not in {from_zone}. "
                        f"Current zone: {worker.current_zone.value}"
                    )
                }

            try:
                new_zone = Zone(to_zone)
            except ValueError:
                return {
                    'success': False,
                    'message': f"Invalid zone: {to_zone}"
                }

            success = self.data_loader.update_worker_zone(
                worker_id, new_zone
            )

            if success:
                updated_worker = self.data_loader.get_worker_by_id(
                    worker_id
                )
                zone_stats = self.data_loader.get_zone_statistics()

                message = (
                    f"Successfully moved {worker.name} "
                    f"from {from_zone} to {to_zone}"
                )
                if confirmed_by:
                    message += f" (confirmed by {confirmed_by})"

                return {
                    'success': True,
                    'message': message,
                    'updated_worker': self._worker_to_dict(updated_worker),
                    'zone_statistics': zone_stats
                }
            else:
                return {
                    'success': False,
                    'message': "Failed to update worker zone"
                }

        except Exception as e:
            logger.error(f"Error confirming shift change: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}"
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        components = {
            'data_loader': 'healthy',
            'vector_store': 'healthy',
            'embedder': 'healthy',
            'crew': 'healthy'
        }

        # Check workers loaded
        try:
            workers = self.data_loader.get_workers()
            if not workers:
                components['data_loader'] = 'no data'
        except Exception:
            components['data_loader'] = 'error'

        # Check vector store
        try:
            stats = self.crew.retriever.vector_store.get_collection_stats()
            if stats.get('total_workers', 0) == 0:
                components['vector_store'] = 'empty'
        except Exception:
            components['vector_store'] = 'error'

        # Check LLM
        if not self.crew.llm:
            components['crew'] = 'llm not configured (using fallback)'

        overall_status = 'healthy' if all(
            v == 'healthy' for v in components.values()
        ) else 'degraded'

        return {
            'status': overall_status,
            'version': '1.0.0',
            'components': components,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _worker_to_dict(self, worker: Worker) -> Dict[str, Any]:
        """Convert Worker model to dictionary."""
        return {
            'worker_id': worker.worker_id,
            'name': worker.name,
            'primary_skill': worker.primary_skill,
            'transferable_skills': worker.transferable_skills,
            'current_zone': worker.current_zone.value,
            'shift': worker.shift.value,
            'load_status': worker.load_status.value,
            'available': worker.available,
            'load_percentage': worker.get_load_percentage()
        }

# Made with Bob
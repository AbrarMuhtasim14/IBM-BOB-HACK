"""
Data loading utilities for SmartShift application.
Handles CSV loading, validation, and worker data management.
"""
import pandas as pd
from pathlib import Path
from typing import List, Optional
import logging
from data.models import Worker, Zone, Shift, LoadStatus

logger = logging.getLogger(__name__)


class WorkerDataLoader:
    """Loads and manages worker data from CSV."""

    def __init__(self, csv_path: Path):
        """Initialize loader with CSV file path."""
        self.csv_path = csv_path
        self._workers: List[Worker] = []

    def load_workers(self) -> List[Worker]:
        """Load workers from CSV file."""
        try:
            if not self.csv_path.exists():
                raise FileNotFoundError(f"Worker CSV not found: {self.csv_path}")

            # Try multiple encodings in order
            df = None
            encodings = ['utf-8-sig', 'utf-8', 'utf-16', 'latin-1', 'cp1252']

            for encoding in encodings:
                try:
                    df = pd.read_csv(self.csv_path, encoding=encoding)
                    logger.info(
                        f"Loaded {len(df)} workers from {self.csv_path} "
                        f"using encoding: {encoding}"
                    )
                    break
                except (UnicodeDecodeError, Exception) as enc_err:
                    logger.debug(f"Encoding {encoding} failed: {enc_err}")
                    continue

            if df is None:
                raise ValueError(
                    "Could not read CSV with any known encoding. "
                    "Please recreate the file using scripts/create_workers_csv.py"
                )

            # Validate required columns
            required_columns = [
                'worker_id', 'name', 'primary_skill', 'transferable_skills',
                'current_zone', 'shift', 'load_status', 'available'
            ]
            missing_cols = [c for c in required_columns if c not in df.columns]
            if missing_cols:
                raise ValueError(f"CSV missing required columns: {missing_cols}")

            # Convert to Worker models
            workers = []
            for _, row in df.iterrows():
                try:
                    # Convert 'Yes'/'No' to boolean
                    available_raw = str(row['available']).strip().lower()
                    available = available_raw in ('yes', 'true', '1')

                    worker = Worker(
                        worker_id=str(row['worker_id']).strip(),
                        name=str(row['name']).strip(),
                        primary_skill=str(row['primary_skill']).strip(),
                        transferable_skills=str(row['transferable_skills']).strip(),
                        current_zone=str(row['current_zone']).strip(),
                        shift=str(row['shift']).strip(),
                        load_status=str(row['load_status']).strip(),
                        available=available
                    )
                    workers.append(worker)
                except Exception as e:
                    logger.error(
                        f"Error parsing worker "
                        f"{row.get('worker_id', 'unknown')}: {e}"
                    )
                    continue

            self._workers = workers
            logger.info(f"Successfully parsed {len(workers)} workers")
            return workers

        except Exception as e:
            logger.error(f"Error loading workers: {e}")
            raise

    def get_workers(self) -> List[Worker]:
        """Get loaded workers."""
        if not self._workers:
            self.load_workers()
        return self._workers

    def get_worker_by_id(self, worker_id: str) -> Optional[Worker]:
        """Get worker by ID."""
        workers = self.get_workers()
        for worker in workers:
            if worker.worker_id == worker_id:
                return worker
        return None

    def get_workers_by_zone(self, zone: Zone) -> List[Worker]:
        """Get all workers in a specific zone."""
        workers = self.get_workers()
        return [w for w in workers if w.current_zone == zone]

    def get_workers_by_shift(self, shift: Shift) -> List[Worker]:
        """Get all workers in a specific shift."""
        workers = self.get_workers()
        return [w for w in workers if w.shift == shift]

    def get_available_workers(
        self, exclude_zone: Optional[Zone] = None
    ) -> List[Worker]:
        """Get available workers, optionally excluding a zone."""
        workers = self.get_workers()
        available = [w for w in workers if w.available]

        if exclude_zone:
            available = [w for w in available if w.current_zone != exclude_zone]

        return available

    def get_workers_by_skill(self, skill: str) -> List[Worker]:
        """Get workers with a specific skill (primary or transferable)."""
        workers = self.get_workers()
        return [w for w in workers if w.has_skill(skill)]

    def get_zone_statistics(self) -> dict:
        """Get statistics for each zone."""
        workers = self.get_workers()
        stats = {}

        for zone in Zone:
            zone_workers = [w for w in workers if w.current_zone == zone]
            if zone_workers:
                avg_load = (
                    sum(w.get_load_percentage() for w in zone_workers)
                    / len(zone_workers)
                )
                stats[zone.value] = {
                    'total_workers': len(zone_workers),
                    'available': len([w for w in zone_workers if w.available]),
                    'average_load': round(avg_load, 1),
                    'high_load_count': len(
                        [w for w in zone_workers
                         if w.load_status == LoadStatus.HIGH]
                    )
                }

        return stats

    def update_worker_zone(self, worker_id: str, new_zone: Zone) -> bool:
        """Update worker's zone assignment."""
        worker = self.get_worker_by_id(worker_id)
        if worker:
            worker.current_zone = new_zone
            logger.info(f"Updated {worker_id} zone to {new_zone}")
            return True
        return False

    def update_worker_availability(
        self, worker_id: str, available: bool
    ) -> bool:
        """Update worker's availability status."""
        worker = self.get_worker_by_id(worker_id)
        if worker:
            worker.available = available
            logger.info(f"Updated {worker_id} availability to {available}")
            return True
        return False


def load_workers_from_csv(csv_path: Path) -> List[Worker]:
    """Convenience function to load workers from CSV."""
    loader = WorkerDataLoader(csv_path)
    return loader.load_workers()

# Made with Bob
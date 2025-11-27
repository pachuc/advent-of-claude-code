"""Progress tracking abstraction for the Advent of Code solver.

This module provides thread-safe progress tracking that can be used by both
the CLI (which just prints) and the web interface (which buffers for polling).
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Callable
from threading import Lock


class SolverStage(Enum):
    """Stages the solver goes through when solving a puzzle."""
    INITIALIZING = "initializing"
    TRANSLATION = "translation"
    PLANNING = "planning"
    CRITIQUE = "critique"
    REVISION = "revision"
    CODING = "coding"
    TESTING = "testing"
    SOLVING = "solving"  # One-shot mode: combined solve stage
    SUBMITTING = "submitting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressUpdate:
    """Immutable snapshot of solver progress."""
    stage: SolverStage
    part: int
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    attempt: int = 1
    answer: Optional[str] = None
    error: Optional[str] = None
    is_complete: bool = False


class ProgressTracker:
    """Thread-safe progress storage for polling.

    Used by the web interface to buffer progress updates that can be
    retrieved via polling.
    """

    def __init__(self):
        self._updates: List[ProgressUpdate] = []
        self._lock = Lock()

    def report(self, update: ProgressUpdate) -> None:
        """Record a progress update.

        Args:
            update: The progress update to record
        """
        with self._lock:
            self._updates.append(update)

    def get_latest(self) -> Optional[ProgressUpdate]:
        """Get the most recent progress update.

        Returns:
            The latest ProgressUpdate, or None if no updates yet
        """
        with self._lock:
            return self._updates[-1] if self._updates else None

    def get_updates_since(self, cursor: int) -> tuple[List[ProgressUpdate], int]:
        """Get all updates since a cursor position.

        Args:
            cursor: The index to start from (0 for all updates)

        Returns:
            Tuple of (list of new updates, new cursor position)
        """
        with self._lock:
            new_updates = self._updates[cursor:]
            return new_updates, len(self._updates)

    def get_all_updates(self) -> List[ProgressUpdate]:
        """Get all recorded updates.

        Returns:
            List of all ProgressUpdate objects
        """
        with self._lock:
            return list(self._updates)

    def clear(self) -> None:
        """Clear all recorded updates."""
        with self._lock:
            self._updates.clear()


def create_progress_callback(tracker: ProgressTracker, part: int) -> Callable[[str, str], None]:
    """Create a progress callback function for use with AdventSolver.

    Args:
        tracker: The ProgressTracker to record updates to
        part: The puzzle part number (1 or 2)

    Returns:
        A callback function that takes (stage, message) and records to tracker
    """
    def callback(stage: str, message: str, attempt: int = 1, answer: str = None, error: str = None):
        try:
            solver_stage = SolverStage(stage)
        except ValueError:
            solver_stage = SolverStage.INITIALIZING

        update = ProgressUpdate(
            stage=solver_stage,
            part=part,
            message=message,
            attempt=attempt,
            answer=answer,
            error=error,
            is_complete=(solver_stage in [SolverStage.COMPLETED, SolverStage.FAILED])
        )
        tracker.report(update)

    return callback

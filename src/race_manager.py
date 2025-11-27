"""Race state management and background solver execution.

This module manages the "Race Against Claude" game state, tracking both
the user's progress and Claude's solver progress through background threads.
"""

import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock

from src.progress import ProgressTracker, ProgressUpdate, SolverStage, create_progress_callback
from src.aoc_client import AdventOfCodeClient
from src.main import setup_workspace
from src.solvers import SolverFactory


WORKSPACE_BASE = "/app/agent_workspace"


@dataclass
class ParticipantState:
    """Tracks a single participant's (user or Claude) progress on a part."""
    status: str = "pending"  # pending | running | completed | failed
    answer: Optional[str] = None
    finish_time: Optional[float] = None  # seconds since race start
    stage: Optional[str] = None  # Current stage (for Claude)
    attempt: int = 1  # Current attempt number


@dataclass
class PartState:
    """Tracks the state of a single part (1 or 2)."""
    claude: ParticipantState = field(default_factory=ParticipantState)
    user: ParticipantState = field(default_factory=ParticipantState)
    correct_answer: Optional[str] = None  # Set after first successful submission
    winner: Optional[str] = None  # "user" | "claude" | None


class RaceManager:
    """Manages the race state and background solver execution.

    This is a singleton-like class that manages a single race at a time.
    The race state is stored in memory and can be polled by the API.
    """

    def __init__(self):
        self._lock = Lock()
        self._reset_state()

    def _reset_state(self):
        """Reset all state to initial values."""
        self.status = "idle"  # idle | racing | finished
        self.year: Optional[int] = None
        self.day: Optional[int] = None
        self.aoc_session: Optional[str] = None
        self.start_time: Optional[float] = None

        self.part1 = PartState()
        self.part2 = PartState()

        self.puzzle_part1: Optional[str] = None
        self.puzzle_part2: Optional[str] = None
        self.puzzle_title: Optional[str] = None
        self.input_url: Optional[str] = None

        # Practice mode flag - True when racing on already-completed puzzles
        self.is_practice_mode: bool = False

        # Solver strategy (default or one-shot)
        self.strategy: str = "default"

        self.progress_tracker = ProgressTracker()
        self._solver_thread: Optional[threading.Thread] = None
        self._stop_requested = False

    def reset(self):
        """Reset the race to idle state."""
        with self._lock:
            self._stop_requested = True
            # Wait briefly for thread to stop
            if self._solver_thread and self._solver_thread.is_alive():
                self._solver_thread.join(timeout=1.0)
            self._reset_state()

    def get_elapsed_seconds(self) -> float:
        """Get elapsed time since race start."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def start_race(self, year: int, day: int, aoc_session: str, strategy: str = "default") -> Dict[str, Any]:
        """Start a new race.

        Args:
            year: Puzzle year
            day: Puzzle day (1-25)
            aoc_session: AOC session token
            strategy: Solver strategy ("default", "one-shot", "fast")

        Returns:
            Dict with puzzle content and race info

        Raises:
            ValueError: If a race is already in progress or session is invalid
        """
        with self._lock:
            if self.status == "racing":
                raise ValueError("A race is already in progress. Reset first.")

            self._reset_state()

            # Validate session and fetch puzzle
            try:
                client = AdventOfCodeClient(session_token=aoc_session)
                puzzle_data = client.get_puzzle_for_display(year, day, 1)
            except Exception as e:
                raise ValueError(f"Failed to fetch puzzle: {e}")

            # Check completion status and get known answers for practice mode
            try:
                completion = client.get_completion_status(year, day)
                self.is_practice_mode = completion['part1_complete']

                # Pre-populate correct answers if known (enables local validation)
                if completion['part1_answer']:
                    self.part1.correct_answer = completion['part1_answer']
                if completion['part2_answer']:
                    self.part2.correct_answer = completion['part2_answer']

                # Fetch Part 2 puzzle immediately if already completed
                if completion['part2_complete'] and completion['available_parts'] >= 2:
                    try:
                        puzzle2_data = client.get_puzzle_for_display(year, day, 2)
                        self.puzzle_part2 = puzzle2_data["markdown"]
                    except:
                        pass  # Part 2 puzzle fetch failed, will try again later
            except Exception:
                # If completion check fails, proceed without practice mode
                self.is_practice_mode = False

            # Initialize state
            self.year = year
            self.day = day
            self.aoc_session = aoc_session
            self.status = "racing"
            self.start_time = time.time()

            self.puzzle_part1 = puzzle_data["markdown"]
            self.puzzle_title = puzzle_data["title"]
            self.input_url = client.get_input_url(year, day)

            self.part1.claude.status = "running"
            self.part1.user.status = "pending"
            self.strategy = strategy

            # Start solver in background thread
            self._stop_requested = False
            self._solver_thread = threading.Thread(
                target=self._run_solver,
                args=(year, day, aoc_session, self.is_practice_mode, strategy),
                daemon=True
            )
            self._solver_thread.start()

            return {
                "success": True,
                "puzzle_part1": self.puzzle_part1,
                "puzzle_title": self.puzzle_title,
                "input_url": self.input_url
            }

    def _run_solver(self, year: int, day: int, aoc_session: str, practice_mode: bool = False, strategy: str = "default"):
        """Run the solver in a background thread.

        Args:
            year: Puzzle year
            day: Puzzle day
            aoc_session: AOC session token
            practice_mode: If True, skip AoC submission (for already-completed puzzles)
            strategy: Solver strategy ("default", "one-shot", "fast")
        """
        try:
            client = AdventOfCodeClient(session_token=aoc_session)

            # Solve Part 1
            self._solve_part(client, year, day, 1, practice_mode, strategy)

            if self._stop_requested:
                return

            # If Part 1 succeeded, fetch Part 2 puzzle and solve it
            if self.part1.claude.status == "completed":
                try:
                    puzzle2_data = client.get_puzzle_for_display(year, day, 2)
                    with self._lock:
                        self.puzzle_part2 = puzzle2_data["markdown"]
                        self.part2.claude.status = "running"

                    self._solve_part(client, year, day, 2, practice_mode, strategy)
                except ValueError as e:
                    # Part 2 not available yet
                    with self._lock:
                        self.part2.claude.status = "pending"

            # Mark race as finished if both parts done or Claude failed
            with self._lock:
                if (self.part1.claude.status in ["completed", "failed"] and
                    self.part2.claude.status in ["completed", "failed", "pending"]):
                    self._check_race_finished()

        except Exception as e:
            with self._lock:
                # Mark current part as failed
                if self.part1.claude.status == "running":
                    self.part1.claude.status = "failed"
                elif self.part2.claude.status == "running":
                    self.part2.claude.status = "failed"
                self.progress_tracker.report(ProgressUpdate(
                    stage=SolverStage.FAILED,
                    part=1 if self.part1.claude.status == "failed" else 2,
                    message=f"Solver error: {e}",
                    error=str(e)
                ))

    def _solve_part(self, client: AdventOfCodeClient, year: int, day: int, part: int, practice_mode: bool = False, strategy: str = "default"):
        """Solve a single part of the puzzle.

        Args:
            client: AOC client instance
            year: Puzzle year
            day: Puzzle day
            part: Part number (1 or 2)
            practice_mode: If True, skip AoC submission (for already-completed puzzles)
            strategy: Solver strategy ("default", "one-shot", "fast")
        """
        if self._stop_requested:
            return

        part_state = self.part1 if part == 1 else self.part2

        # Create progress callback that updates race state
        def on_progress(stage: str, message: str, attempt: int = 1, answer: str = None, error: str = None):
            with self._lock:
                part_state.claude.stage = stage
                part_state.claude.attempt = attempt
                if answer:
                    part_state.claude.answer = answer

            # Also record to progress tracker for polling
            try:
                solver_stage = SolverStage(stage)
            except ValueError:
                solver_stage = SolverStage.INITIALIZING

            self.progress_tracker.report(ProgressUpdate(
                stage=solver_stage,
                part=part,
                message=message,
                attempt=attempt,
                answer=answer,
                error=error,
                is_complete=(solver_stage in [SolverStage.COMPLETED, SolverStage.FAILED])
            ))

        # Setup workspace
        workspace_path = setup_workspace(client, year, day, part, WORKSPACE_BASE)

        # Only skip submission if we have the correct answer for THIS part
        # (handles partial completion: Part 1 done, Part 2 not done)
        skip_submission_for_part = part_state.correct_answer is not None

        # Run solver using factory
        solver = SolverFactory.create(
            strategy,
            workspace_path=str(workspace_path),
            part=part,
            client=client,
            year=year,
            day=day,
            progress_callback=on_progress,
            skip_submission=skip_submission_for_part,
            correct_answer=part_state.correct_answer
        )

        success = solver.solve()

        with self._lock:
            elapsed = self.get_elapsed_seconds()
            if success:
                # Read the answer
                answer_file = Path(workspace_path) / "answer.txt"
                answer = answer_file.read_text().strip() if answer_file.exists() else None

                # If we skipped submission, verify against known correct answer
                if skip_submission_for_part and part_state.correct_answer is not None and answer:
                    answer_normalized = answer.strip().lower()
                    correct_normalized = part_state.correct_answer.strip().lower()
                    if answer_normalized != correct_normalized:
                        # Answer doesn't match known correct answer - mark as failed
                        part_state.claude.status = "failed"
                        part_state.claude.answer = answer
                        part_state.claude.finish_time = elapsed
                        self.progress_tracker.report(ProgressUpdate(
                            stage=SolverStage.FAILED,
                            part=part,
                            message=f"Answer '{answer}' doesn't match correct answer (practice mode)",
                            answer=answer,
                            error="Answer mismatch"
                        ))
                        return  # Don't mark as winner

                part_state.claude.status = "completed"
                part_state.claude.answer = answer
                part_state.claude.finish_time = elapsed

                # Set correct answer if user hasn't submitted yet
                if part_state.correct_answer is None:
                    part_state.correct_answer = answer

                # Check if Claude won this part
                if part_state.winner is None:
                    part_state.winner = "claude"
            else:
                part_state.claude.status = "failed"
                part_state.claude.finish_time = elapsed

    def submit_user_answer(self, part: int, answer: str) -> Dict[str, Any]:
        """Submit the user's answer for a part.

        Args:
            part: Part number (1 or 2)
            answer: User's answer

        Returns:
            Dict with submission result
        """
        with self._lock:
            if self.status != "racing":
                return {"success": False, "message": "No race in progress"}

            part_state = self.part1 if part == 1 else self.part2
            answer = answer.strip()

            # Check if user already completed this part
            if part_state.user.status == "completed":
                return {"success": False, "message": "You already completed this part"}

            # Check if correct answer is known (Claude already solved it or practice mode)
            if part_state.correct_answer is not None:
                # Compare locally - normalize both for comparison
                user_answer_normalized = answer.strip().lower()
                correct_answer_normalized = part_state.correct_answer.strip().lower()
                is_correct = (user_answer_normalized == correct_answer_normalized)
                if is_correct:
                    part_state.user.status = "completed"
                    part_state.user.answer = answer
                    part_state.user.finish_time = self.get_elapsed_seconds()

                    # Check if user won this part
                    if part_state.winner is None:
                        part_state.winner = "user"

                    # If Part 1, try to fetch Part 2 puzzle
                    if part == 1 and self.puzzle_part2 is None:
                        try:
                            client = AdventOfCodeClient(session_token=self.aoc_session)
                            puzzle2_data = client.get_puzzle_for_display(self.year, self.day, 2)
                            self.puzzle_part2 = puzzle2_data["markdown"]
                        except:
                            pass  # Part 2 not available yet

                    self._check_race_finished()
                    return {"success": True, "correct": True, "message": "Correct!"}
                else:
                    return {"success": True, "correct": False, "message": "That's not the right answer."}
            else:
                # Submit to AoC
                try:
                    client = AdventOfCodeClient(session_token=self.aoc_session)
                    result = client.submit_answer(self.year, self.day, part, answer)

                    message = result.get("message", "")
                    is_correct = "That's the right answer" in message or "You got the answer" in message

                    # Check if puzzle was already completed (Claude submitted first)
                    already_completed = (
                        "already complete" in message.lower() or
                        "not the right level" in message.lower() or
                        "did you already complete it" in message.lower()
                    )
                    if already_completed:
                        # Claude must have finished - check locally against Claude's answer
                        if part_state.claude.answer:
                            user_normalized = answer.strip().lower()
                            claude_normalized = part_state.claude.answer.strip().lower()
                            if user_normalized == claude_normalized:
                                part_state.user.status = "completed"
                                part_state.user.answer = answer
                                part_state.user.finish_time = self.get_elapsed_seconds()
                                if part_state.winner is None:
                                    part_state.winner = "user"

                                # If Part 1, try to fetch Part 2 puzzle
                                if part == 1 and self.puzzle_part2 is None:
                                    try:
                                        puzzle2_data = client.get_puzzle_for_display(self.year, self.day, 2)
                                        self.puzzle_part2 = puzzle2_data["markdown"]
                                    except:
                                        pass  # Part 2 not available yet

                                self._check_race_finished()
                                return {"success": True, "correct": True, "message": "Correct!"}
                            else:
                                return {"success": True, "correct": False, "message": "That's not the right answer."}
                        else:
                            return {"success": True, "correct": False, "message": "Puzzle already completed. Unable to verify your answer."}

                    msg_lower = message.lower()

                    # Check for wrong answer FIRST (may contain "please wait" after multiple wrong guesses)
                    is_wrong = "not the right answer" in msg_lower or "that's not it" in msg_lower

                    # Check for hints
                    hint = None
                    if "too high" in msg_lower:
                        hint = "too high"
                    elif "too low" in msg_lower:
                        hint = "too low"

                    # Check for rate limiting (only if not a wrong answer response)
                    # AoC says "You gave an answer too recently" with a countdown
                    if not is_wrong and not is_correct:
                        rate_limited = (
                            "too recently" in msg_lower or
                            "gave an answer" in msg_lower or
                            "you have to wait" in msg_lower or
                            "left to wait" in msg_lower
                        )
                        if rate_limited:
                            return {
                                "success": True,
                                "correct": False,
                                "message": "Rate limited by AoC. Please wait before trying again.",
                                "rate_limited": True
                            }

                    if is_correct:
                        part_state.user.status = "completed"
                        part_state.user.answer = answer
                        part_state.user.finish_time = self.get_elapsed_seconds()
                        part_state.correct_answer = answer

                        # User won this part
                        if part_state.winner is None:
                            part_state.winner = "user"

                        # If Part 1, try to fetch Part 2 puzzle
                        if part == 1 and self.puzzle_part2 is None:
                            try:
                                puzzle2_data = client.get_puzzle_for_display(self.year, self.day, 2)
                                self.puzzle_part2 = puzzle2_data["markdown"]
                            except:
                                pass

                        self._check_race_finished()
                        return {"success": True, "correct": True, "message": "Correct!"}
                    else:
                        # Build a clean wrong answer message
                        if hint:
                            wrong_msg = f"Wrong answer (your answer is {hint})"
                        else:
                            wrong_msg = "That's not the right answer."

                        # Check if there's a wait time mentioned
                        if "please wait" in msg_lower or "before trying again" in msg_lower:
                            wrong_msg += " Wait before trying again."

                        return {
                            "success": True,
                            "correct": False,
                            "message": wrong_msg,
                            "hint": hint
                        }

                except Exception as e:
                    return {"success": False, "message": f"Error submitting answer: {e}"}

    def _check_race_finished(self):
        """Check if the race is finished and update status."""
        # Race is finished when both participants have completed both parts
        # or when one has completed both and the other has had a chance

        user_done = (
            self.part1.user.status == "completed" and
            self.part2.user.status == "completed"
        )
        claude_done = (
            self.part1.claude.status in ["completed", "failed"] and
            self.part2.claude.status in ["completed", "failed"]
        )

        # For now, keep racing until user decides to finish or both complete
        # The frontend will show results when appropriate

    def get_status(self) -> Dict[str, Any]:
        """Get the current race status for polling.

        Returns:
            Dict with full race state
        """
        with self._lock:
            # Get latest progress update
            latest = self.progress_tracker.get_latest()
            latest_stage = latest.stage.value if latest else None
            latest_message = latest.message if latest else None

            return {
                "status": self.status,
                "strategy": self.strategy,
                "elapsed_seconds": self.get_elapsed_seconds(),
                "year": self.year,
                "day": self.day,
                "puzzle_title": self.puzzle_title,
                "puzzle_part1": self.puzzle_part1,
                "puzzle_part2": self.puzzle_part2,
                "input_url": self.input_url,
                "part1": {
                    "claude": {
                        "status": self.part1.claude.status,
                        "stage": self.part1.claude.stage,
                        "attempt": self.part1.claude.attempt,
                        "answer": self.part1.claude.answer,
                        "finish_time": self.part1.claude.finish_time
                    },
                    "user": {
                        "status": self.part1.user.status,
                        "answer": self.part1.user.answer,
                        "finish_time": self.part1.user.finish_time
                    },
                    "winner": self.part1.winner
                },
                "part2": {
                    "claude": {
                        "status": self.part2.claude.status,
                        "stage": self.part2.claude.stage,
                        "attempt": self.part2.claude.attempt,
                        "answer": self.part2.claude.answer,
                        "finish_time": self.part2.claude.finish_time
                    },
                    "user": {
                        "status": self.part2.user.status,
                        "answer": self.part2.user.answer,
                        "finish_time": self.part2.user.finish_time
                    },
                    "winner": self.part2.winner
                },
                "latest_stage": latest_stage,
                "latest_message": latest_message
            }

    def get_progress_updates(self, cursor: int = 0) -> Dict[str, Any]:
        """Get progress updates since a cursor position.

        Args:
            cursor: Position to start from (0 for all)

        Returns:
            Dict with updates and new cursor
        """
        updates, new_cursor = self.progress_tracker.get_updates_since(cursor)
        return {
            "updates": [
                {
                    "stage": u.stage.value,
                    "part": u.part,
                    "message": u.message,
                    "timestamp": u.timestamp.isoformat(),
                    "attempt": u.attempt,
                    "answer": u.answer,
                    "error": u.error,
                    "is_complete": u.is_complete
                }
                for u in updates
            ],
            "cursor": new_cursor
        }


# Global race manager instance
race_manager = RaceManager()

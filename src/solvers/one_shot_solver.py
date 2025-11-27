from .base_solver import BaseSolver
from src.agents import OneShotAgent, SubmissionAgent


class OneShotSolver(BaseSolver):
    """Fast solver that uses a single OneShotAgent pass.

    This strategy skips the translation/planning/critique phases
    and goes directly to solving and submission.

    The OneShotAgent reads the puzzle directly, writes a solution,
    tests it internally against examples, and produces an answer.

    Retries only happen after submission failures, when the agent
    can read submission_issues.md for feedback (e.g., "too high", "too low").
    """

    def __init__(self, **kwargs):
        """Initialize OneShotSolver with OneShotAgent and SubmissionAgent."""
        super().__init__(**kwargs)
        self.one_shot_agent = OneShotAgent(self.workspace_path, self.part)
        self.submission_agent = SubmissionAgent(self.workspace_path, self.part)

    @property
    def strategy_name(self) -> str:
        return "one-shot"

    def resolve_with_submission_feedback(self):
        """Re-run one-shot agent after submission was rejected.

        Called when a solution is submitted but rejected by AoC.
        The OneShotAgent reads submission_issues.md for guidance
        (e.g., "answer too high", "answer too low").
        """
        self._report("solving", "Re-solving based on submission feedback...")
        result = self.one_shot_agent.run_agent(feedback=True)

        try:
            success = self.parse_test_result(result)
            if success:
                answer = self._read_answer()
                self._report("solving", f"New solution found: {answer}", answer=answer)
            else:
                self._report("solving", "Re-solve attempt did not produce a solution")
        except ValueError as e:
            self._report("solving", f"Error parsing result: {e}", error=str(e))

    def solve(self) -> bool:
        """Execute the one-shot solving strategy.

        Pipeline:
        1. One-shot solve (single attempt - no retries without feedback)
        2. Submission loop (retries with submission feedback if rejected)

        Returns:
            True if solution was found and submitted successfully, False otherwise
        """
        # Phase 1: One-shot solving (single attempt)
        self._report("solving", "Running one-shot solver...")

        try:
            result = self.one_shot_agent.run_agent()
            success = self.parse_test_result(result)
        except ValueError as e:
            self._report("failed", f"Error parsing solver result: {e}", error=str(e))
            return False

        if not success:
            self._report("failed", "One-shot solver could not find a solution")
            return False

        # Success - answer should be in answer.txt
        answer = self._read_answer()
        self._report("solving", f"Solution found: {answer}", answer=answer)

        # Phase 2: Submission loop (handles retries with submission feedback)
        return self._run_submission_loop(
            self.submission_agent,
            resolve_callback=self.resolve_with_submission_feedback
        )

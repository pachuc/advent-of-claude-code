from abc import ABC, abstractmethod
from typing import Optional, Callable
from pathlib import Path


class BaseSolver(ABC):
    """Abstract base class for all puzzle solvers.

    Defines the contract that all solver implementations must follow,
    enabling interchangeable solver strategies.
    """

    def __init__(
        self,
        workspace_path: str = "./agent_workspace",
        part: int = 1,
        client: Optional['AdventOfCodeClient'] = None,
        year: Optional[int] = None,
        day: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
        skip_submission: bool = False,
        correct_answer: Optional[str] = None
    ):
        """Initialize the solver.

        Args:
            workspace_path: Path to the workspace directory where agents will run
            part: Part number (1 or 2) of the puzzle being solved
            client: AdventOfCodeClient instance for submissions (optional)
            year: Year of the puzzle (required if client provided)
            day: Day of the puzzle (required if client provided)
            progress_callback: Optional callback function for progress reporting.
                              Signature: callback(stage: str, message: str, attempt: int = 1,
                                                  answer: str = None, error: str = None)
            skip_submission: If True, skip AoC submission even if client is provided.
            correct_answer: Known correct answer for local verification (practice mode).
        """
        self.workspace_path = workspace_path
        self.part = part
        self.client = client
        self.year = year
        self.day = day
        self.progress_callback = progress_callback
        self.skip_submission = skip_submission
        self.correct_answer = correct_answer

    @abstractmethod
    def solve(self) -> bool:
        """Execute the solving strategy.

        Returns:
            True if solution was found and submitted successfully
            (or tests passed if no client provided).
            False otherwise.
        """
        pass

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Return the human-readable name of this strategy."""
        pass

    def _report(self, stage: str, message: str, attempt: int = 1,
                answer: str = None, error: str = None):
        """Report progress via callback if one is registered.

        This also prints to stdout for CLI visibility.
        """
        print(f"[{stage.upper()}] {message}")
        if self.progress_callback:
            self.progress_callback(stage, message, attempt, answer, error)

    def parse_test_result(self, result: str) -> bool:
        """Parse agent result for Success/Failure.

        Args:
            result: The output from an agent that ends with Success/Failure

        Returns:
            True if success, False if failure

        Raises:
            ValueError: If the result doesn't end with Success or Failure
        """
        result_lines = result.strip().splitlines()
        last_line = result_lines[-1] if result_lines else ""
        last_line = last_line.lower()
        if last_line == "success":
            return True
        elif last_line == "failure":
            return False
        else:
            raise ValueError("Agent response must end with either 'Success' or 'Failure'.")

    def parse_submission_result(self, result: str) -> bool:
        """Parse submission agent result to determine if submission was successful.

        Args:
            result: The output from SubmissionAgent.run_agent()

        Returns:
            True if submission was accepted, False if rejected

        Raises:
            ValueError: If the agent output doesn't end with 'Success' or 'Failure'
        """
        return self.parse_test_result(result)

    def _read_answer(self) -> Optional[str]:
        """Read answer from answer.txt in workspace.

        Returns:
            The answer string, or None if file doesn't exist
        """
        answer_file = Path(self.workspace_path) / "answer.txt"
        return answer_file.read_text().strip() if answer_file.exists() else None

    def _verify_answer_locally(self, answer: str) -> tuple[bool, Optional[str]]:
        """Verify answer against known correct answer.

        Args:
            answer: The answer to verify

        Returns:
            Tuple of (is_correct, hint) where hint may be "too high", "too low", or None
        """
        if not self.correct_answer:
            return True, None  # No correct answer to check against

        # Normalize for comparison
        answer_normalized = answer.strip().lower()
        correct_normalized = self.correct_answer.strip().lower()

        if answer_normalized == correct_normalized:
            return True, None

        # Try to provide a hint for numeric answers
        hint = None
        try:
            answer_num = int(answer.strip())
            correct_num = int(self.correct_answer.strip())
            if answer_num > correct_num:
                hint = "too high"
            else:
                hint = "too low"
        except ValueError:
            # Not numeric, no hint available
            pass

        return False, hint

    def _write_local_submission_issues(self, answer: str, hint: Optional[str]):
        """Write submission_issues.md for local verification failure.

        Does NOT reveal the correct answer - only provides hints like AoC does.
        """
        issues_file = Path(self.workspace_path) / "submission_issues.md"

        hint_text = ""
        if hint:
            hint_text = f"\n\n**Hint**: Your answer is **{hint}**."

        content = f"""# Submission Result (Local Verification)

**Status**: Incorrect

**Your Answer**: {answer}

**Message**: That's not the right answer.{hint_text}

## Suggestions

- Double-check your solution logic
- Verify edge cases are handled correctly
- Make sure you're reading the problem correctly
- Check for off-by-one errors
- Ensure your solution works for the full input, not just examples
"""
        issues_file.write_text(content)

    def _run_submission_loop(self, submission_agent, resolve_callback: Callable = None) -> bool:
        """Run the submission loop with retries.

        Args:
            submission_agent: The SubmissionAgent instance to use
            resolve_callback: Optional callback to resolve submission failures.
                             Called when submission fails and retries remain.

        Returns:
            True if submission succeeded, False otherwise
        """
        max_submission_attempts = 3

        # Practice mode with local verification
        if self.skip_submission and self.correct_answer:
            for attempt in range(max_submission_attempts):
                self._report("submitting",
                            f"Verifying answer locally (attempt {attempt + 1}/{max_submission_attempts})...",
                            attempt=attempt + 1)

                answer = self._read_answer()
                if not answer:
                    self._report("failed", "Error: answer.txt not found", error="answer.txt not found")
                    return False

                self._report("submitting", f"Checking answer for Part {self.part}: {answer}",
                            attempt=attempt + 1, answer=answer)

                is_correct, hint = self._verify_answer_locally(answer)

                if is_correct:
                    self._report("completed", f"Part {self.part} solved correctly! (practice mode)", answer=answer)
                    return True
                else:
                    hint_msg = f" (hint: {hint})" if hint else ""
                    self._report("submitting",
                                f"Answer incorrect{hint_msg} (attempt {attempt + 1}/{max_submission_attempts})",
                                attempt=attempt + 1, answer=answer)

                    # Write feedback for the solver to read
                    self._write_local_submission_issues(answer, hint)

                    if attempt < max_submission_attempts - 1:
                        if resolve_callback:
                            resolve_callback()
                    else:
                        self._report("failed",
                                    f"Part {self.part} failed after {max_submission_attempts} attempts (practice mode)",
                                    error="Max attempts reached")
                        return False

            return False
        elif self.skip_submission and not self.correct_answer:
            raise ValueError("Cannot skip submission without a correct answer for local verification.")

        # Normal submission to AoC
        for attempt in range(max_submission_attempts):
            self._report("submitting", f"Submitting answer (attempt {attempt + 1}/{max_submission_attempts})...",
                        attempt=attempt + 1)

            # Read answer
            answer_file = Path(self.workspace_path) / "answer.txt"
            if not answer_file.exists():
                self._report("failed", "Error: answer.txt not found", error="answer.txt not found")
                return False

            answer = answer_file.read_text().strip()
            self._report("submitting", f"Submitting answer for Part {self.part}: {answer}",
                        attempt=attempt + 1, answer=answer)

            # Submit answer
            result = self.client.submit_answer(self.year, self.day, self.part, answer)

            # Save submission result for agent analysis
            result_file = Path(self.workspace_path) / "submission_result.md"
            result_content = f"""# Submission Result

**Status Code**: {result['status_code']}

**Response Message**:
{result['message']}

**Raw HTML** (for reference):
```html
{result['raw_html']}
```
"""
            result_file.write_text(result_content)

            # Analyze submission with SubmissionAgent
            self._report("submitting", "Analyzing submission result...", attempt=attempt + 1)
            analysis_result = submission_agent.run_agent()

            # Parse result
            try:
                submission_success = self.parse_submission_result(analysis_result)
            except ValueError as e:
                self._report("failed", f"Error parsing submission result: {e}", error=str(e))
                return False

            if submission_success:
                self._report("completed", f"Part {self.part} solved correctly!", answer=answer)
                return True
            else:
                self._report("submitting",
                            f"Submission rejected (attempt {attempt + 1}/{max_submission_attempts})",
                            attempt=attempt + 1, answer=answer)

                if attempt < max_submission_attempts - 1:
                    # Still have retries left - call resolve callback if provided
                    if resolve_callback:
                        resolve_callback()
                else:
                    self._report("failed",
                                f"Part {self.part} failed after {max_submission_attempts} attempts",
                                error="Max submission attempts reached")
                    return False

        return False

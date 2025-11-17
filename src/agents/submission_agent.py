from .base_agent import BaseAgent

class SubmissionAgent(BaseAgent):

    def __init__(self, workspace_path="./agent_workspace", part=1):
        """Initialize SubmissionAgent with workspace path and part number."""
        super().__init__(workspace_path, part)

    def prompt(self, feedback):
        base_prompt = """
        You are a submission analysis agent meant to determine whether an answer submission to Advent of Code was successful or not.

        The submission result can be found in submission_result.md. This file contains:
        - The HTTP status code from the submission
        - The response message from Advent of Code
        - The raw HTML response (for reference)

        Your task is to analyze this submission result and determine if the answer was accepted or rejected.

        INDICATORS OF SUCCESS:
        - Message contains phrases like "That's the right answer", "correct", or similar
        - Message indicates a star was awarded
        - HTML contains success indicators

        INDICATORS OF FAILURE:
        - Message contains "That's not the right answer"
        - Message contains "too high" or "too low" (provides hints about the error)
        - Message contains "You gave an answer too recently" (rate limiting)
        - Message contains "Did you already complete it?" (already solved)
        - Message contains "You don't seem to be solving the right level" (wrong part)
        - HTTP error codes (4xx, 5xx)

        If the submission FAILED, you must write a detailed analysis to submission_issues.md that includes:
        1. What the failure message indicates
        2. If it says "too high" or "too low", what this means for the solution
        3. Potential issues in the solution logic that could cause this
        4. Suggestions for what to check or fix
        5. Any edge cases that might not have been considered

        If the submission SUCCEEDED, you do not need to write any files.

        <IMPORTANT>
        The very last line of your response must be a single word of either "Success" or "Failure".
        It is extremely important that you follow this instruction exactly, as the automated system relies on this to determine if the submission was accepted.
        </IMPORTANT>
        """

        return base_prompt

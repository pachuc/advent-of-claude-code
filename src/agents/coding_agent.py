from .base_agent import BaseAgent
import subprocess

class CodingAgent(BaseAgent):

    def __init__(self, workspace_path="./agent_workspace", part=1):
        """Initialize CodingAgent with workspace path and part number."""
        super().__init__(workspace_path, part)

    def prompt(self, feedback, submission_feedback=False):
        coding_prompt = """
        You are a coding agent meant to develop a solution to a given problem.
        The problem can be found in problem.md.
        The input to the problem can be found in input.md.
        A plan on how to tackle the problem can be found in implementation_plan.md.
        A plan on how to test and verify the solution can be found in test_plan.md.

        Using this information, create a solution to solve the problem. Make sure you test your solution as directed and itterate on your code as neccessary.
        The code should be written in python, and should be written to solution.py.
        Remember we are just solving this specific problem, we do not need to make production grade code. Keep it simple and to the point.
        Write a summary of what you implemented, the files you created, and how the testing process went into implementation_summary.md.
        """

        if self.part == 2:
            coding_prompt += """

        IMPORTANT - PART 2 CONTEXT:
        You are implementing a solution for Part 2 of a multi-part puzzle. You have
        access to Part 1 artifacts:

        - part_1_solution.py: The working code that solved Part 1
        - part_1_answer.txt: The answer computed for Part 1 (may be needed as input)
        - part_1_problem.md: Full context of Part 1's problem
        - part_1_puzzle.md: Original Part 1 puzzle with examples

        STRONGLY CONSIDER:
        - Can you adapt or extend part_1_solution.py rather than rewriting from scratch?
        - Does your Part 2 solution need to use the Part 1 answer as a starting value?
        - Can you reuse helper functions, parsing logic, or data structures from Part 1?
        - Review part_1_solution.py to understand the approach - it may save significant time

        You can read these files for reference and copy/adapt code as needed. Focus on
        what's different in Part 2 rather than duplicating Part 1 logic unnecessarily.
        """

        if feedback:
            if submission_feedback:
                coding_prompt = coding_prompt + """

            <SUBMISSION_FEEDBACK>
            Your solution passed all local tests, but the submission to Advent of Code was rejected.
            Feedback from the submission analysis can be found in submission_issues.md.

            This typically means:
            - Your solution works for test cases but not for the full input
            - There may be edge cases you're not handling correctly
            - Your answer might be slightly off (too high, too low, wrong format)
            - You may have misunderstood part of the problem statement

            Review the submission feedback carefully. The Advent of Code response often provides
            hints like "too high" or "too low" which can guide you to the issue.

            Your original implementation summary can be found in implementation_summary.md
            Your original solution can be found in solution.py

            Based on the submission feedback, adjust your solution and ensure it handles all edge cases.
            Update implementation_summary.md with what you changed and why.
            </SUBMISSION_FEEDBACK>
            """
            else:
                coding_prompt = coding_prompt + """

            <UPDATE>
            This is actually your 2nd time implementing this.
            Your first implementation was found insufficient by the testing agent.
            Feedback from the testing agent can be found in testing_issues.md.
            Your original implementation summary can be found in implementation_summary.md
            Your original solution can be found in solution.py
            Based on the feedback provided by the testing agent, itterate further and solve the problem.
            </UPDATE>
            """

        return coding_prompt

    def run_agent(self, feedback=False, submission_feedback=False):
        """Run the coding agent with optional feedback flags.

        Args:
            feedback: If True, agent will read testing_issues.md for test feedback
            submission_feedback: If True, agent will read submission_issues.md for submission feedback

        Returns:
            The stdout from the Claude Code CLI
        """
        result = subprocess.run(
            ["claude", "-p", self.prompt(feedback, submission_feedback), "--dangerously-skip-permissions"],
            cwd=self.workspace_path,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"Claude Code threw an error: {result.stderr}")
        return result.stdout

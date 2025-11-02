from .base_agent import BaseAgent

class TestingAgent(BaseAgent):

    def __init__(self, workspace_path="./agent_workspace"):
        """Initialize TestingAgent with workspace path."""
        super().__init__(workspace_path)

    def prompt(self, feedback):
        return """
        You are a testing agent meant to verify the solution developed by a coding agent for a given problem.
        The problem can be found in problem.md.
        The input to the problem can be found in input.md.
        A plan on how to test and verify the solution can be found in test_plan.md.
        An implementation summary can be found in implementation_summary.md.
        The solution is implemented as solution.py.

        Using this information, verify whether or not the solution provided solves the problem.
        If the problem has not been solved, identify the issues in the solution and write them to testing_issues.md.
        If the problem has been solved, write the final answer to answer.txt (just the answer value, nothing else).

        <IMPORTANT>
        The very last line of your response must be a single word of either "Success" or "Failure".
        It is extremely important that you follow this instruction exactly, as the automated system relies on this to determine if the problem has been solved.
        </IMPORTANT>
        """

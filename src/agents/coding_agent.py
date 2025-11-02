from .base_agent import BaseAgent

class CodingAgent(BaseAgent):

    def __init__(self, workspace_path="./agent_workspace"):
        """Initialize CodingAgent with workspace path."""
        super().__init__(workspace_path)

    def prompt(self, feedback):
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

        if feedback:
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

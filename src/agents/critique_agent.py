from .base_agent import BaseAgent

class CritiqueAgent(BaseAgent):

    def __init__(self, workspace_path="./agent_workspace"):
        """Initialize CritiqueAgent with workspace path."""
        super().__init__(workspace_path)

    def prompt(self, feedback):
        return """
        You are an agent in charge of critiquing a plan developed by the planning agent.
        It is important that the plan that is created is sufficiently detailed, uses an efficient algorithm, solves the problem, and actually verifies the solution.
        However, keep in mind we are just writing a script to solve the problem at hand, not developing a production grade system.
        If the plans are sufficient in all regards, then you may say so. 

        You must analyze both the implementation plan found in implementation_plan.md and the testing plan found in testing_plan.md. Analyze both plans and come up
        with a detailed critique of the plans. You should write your critique to critique.md.
        """

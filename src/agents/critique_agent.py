from .base_agent import BaseAgent

class CritiqueAgent(BaseAgent):

    def __init__(self, workspace_path="./agent_workspace", part=1):
        """Initialize CritiqueAgent with workspace path and part number."""
        super().__init__(workspace_path, part)

    def prompt(self, feedback):
        base_prompt = """
        You are an agent in charge of critiquing a plan developed by the planning agent.
        It is important that the plan that is created is sufficiently detailed, uses an efficient algorithm, solves the problem, and actually verifies the solution.
        However, keep in mind we are just writing a script to solve the problem at hand, not developing a production grade system.
        If the plans are sufficient in all regards, then you may say so.

        You must analyze both the implementation plan found in implementation_plan.md and the testing plan found in testing_plan.md. Analyze both plans and come up
        with a detailed critique of the plans. You should write your critique to critique.md.
        """

        if self.part == 2:
            part2_context = """

        IMPORTANT - PART 2 CONTEXT:
        You are critiquing a plan for Part 2 of a multi-part puzzle. Part 1 has already
        been solved. Available context:

        - part_1_solution.py: The working code from Part 1
        - part_1_answer.txt: The Part 1 answer
        - part_1_problem.md: Part 1 problem description

        When critiquing, consider:
        - Does the plan appropriately leverage Part 1's solution/approach?
        - If Part 2 is similar to Part 1, does the plan suggest reusing logic efficiently?
        - Does the plan correctly use the Part 1 answer if needed?
        - Is the plan reinventing the wheel when it could adapt Part 1 code?
        """
            return base_prompt + part2_context

        return base_prompt

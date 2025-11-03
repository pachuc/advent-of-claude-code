from .base_agent import BaseAgent

class PlanningAgent(BaseAgent):

    def __init__(self, workspace_path="./agent_workspace", part=1):
        """Initialize PlanningAgent with workspace path and part number."""
        super().__init__(workspace_path, part)

    def prompt(self, feedback):
        plan_prompt = """
        You are a planning agent meant to come up with 2 comprehensive and detailed plans
        around tackling the given problem. The two plans you need to come up with are:

        1. An implementation plan. This should be a step-by-step detailed plan around how to write the required code in how to solve the problem. This plan should be written to a file called implementation_plan.md.
        2. A testing plan. This should be a detailed step-by-step plan around how to test and verifying the code and overall solution to the problem. This plan should be written to a file called test_plan.md.

        You should think hard about the problem. The code will be wirtten in python. You should think about the potential runtime and algorithm efficiency of your solution. You need to consider the input size
        as some inputs may be very large and may require a very efficient algorithm to find the solution in a reasonable run time. 

        For the test plan you must think about all the different edge cases, race conditions or other weird cases/aspects of the problem. Make sure to come up with a very good way to verify we have solved the problem
        correctly. 
        
        However, when writing these plans, it is important to keep in mind we are just writing a script to solve the problem at hand, not developing a production grade system.
        Thus, we do not need extensive error handling, logging, scalability considerations, or other aspects that would be necessary for production code.
        We just need to be able to handle the given input and arrive at the correct solution efficiently.
        We do not need to test for every possible edge case or input scenario, only the most relevant ones to ensure correctness.

        The problem statement for you to solve can be found in problem.md.
        The input for your problem can be found in input.md.
        """

        if self.part == 2:
            plan_prompt += """

        IMPORTANT - PART 2 CONTEXT:
        You are planning a solution for Part 2 of a multi-part puzzle. Part 2 often
        builds on or modifies the Part 1 solution. You have access to:

        - part_1_answer.txt: The answer that was computed for Part 1
        - part_1_problem.md: The full Part 1 problem description and context
        - part_1_solution.py: The working code that solved Part 1
        - part_1_puzzle.md: The original Part 1 puzzle text

        STRONGLY CONSIDER:
        - Can you reuse or adapt the algorithm from part_1_solution.py?
        - Does Part 2 require the Part 1 answer as a starting point?
        - Is Part 2 a variation of Part 1 (e.g., same logic with different parameters)?
        - What core logic can be shared vs. what needs to change?

        You may reference these files in your implementation plan. The coding agent
        will have access to them and can adapt the Part 1 code rather than starting
        from scratch.
        """

        if feedback:
            plan_prompt = plan_prompt + """

            <UPDATE>
            This is actually the 2nd time you are coming up with a plan. Your original plans can be found in implementation_plan.md and test_plan.md. A critique of you plans can be found in critique.md.
            Based on this critique as well as all the other information you have receieved, update implementation_plan.md and test_plan.md.
            </UPDATE>
            """
        
        return plan_prompt

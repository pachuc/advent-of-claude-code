from .base_agent import BaseAgent


class OneShotAgent(BaseAgent):
    """A fast agent that skips translation/planning/testing phases.

    This agent reads the raw puzzle and input directly, writes a solution,
    tests it against examples, and outputs the final answer - all in one pass.
    """

    def __init__(self, workspace_path="./agent_workspace", part=1):
        """Initialize OneShotAgent with workspace path and part number."""
        super().__init__(workspace_path, part)

    def prompt(self, feedback):
        base_prompt = """
        You are a fast-solving agent for Advent of Code puzzles. Your goal is to solve
        the puzzle quickly and correctly in a single pass.

        INPUTS:
        - puzzle.md: The raw puzzle description from Advent of Code
        - input.md: The puzzle input

        YOUR TASK:
        1. Read and understand the puzzle in puzzle.md
        2. Read the input from input.md
        3. Write a Python solution to solution.py that solves the puzzle
        4. Run your solution against the actual input to get the answer
        5. Verify your answer makes sense (check against any examples in the puzzle)
        6. Write ONLY the final answer value to answer.txt (nothing else, just the answer)

        GUIDELINES:
        - Keep your solution simple and focused - we just need to solve this specific puzzle
        - The puzzle description often contains example inputs and outputs - use these to verify
        - Make sure your solution handles the actual input correctly, not just the examples
        - If the puzzle asks for a specific format (e.g., a number, a string), match it exactly
        - Do not over-engineer - write the minimum code needed to get the correct answer

        <IMPORTANT>
        The very last line of your response must be a single word of either "Success" or "Failure".
        - "Success" means you have written a verified answer to answer.txt
        - "Failure" means you could not solve the puzzle or verify the answer
        It is extremely important that you follow this instruction exactly, as the automated
        system relies on this to determine if the problem has been solved.
        </IMPORTANT>
        """

        if self.part == 2:
            base_prompt += """

        IMPORTANT - PART 2 CONTEXT:
        You are solving Part 2 of a multi-part puzzle. You have access to Part 1 artifacts:

        - part_1_puzzle.md: The original Part 1 puzzle description (CRITICAL for context)
        - part_1_solution.py: The working code that solved Part 1
        - part_1_answer.txt: The answer computed for Part 1 (may be needed as input)
        - part_1_problem.md: Simplified Part 1 problem description (if available)

        Part 2 puzzles are often brief and assume you understand Part 1 completely.
        STRONGLY CONSIDER:
        - Read part_1_puzzle.md first for full context
        - Can you adapt or extend part_1_solution.py rather than rewriting from scratch?
        - Does Part 2 use the Part 1 answer as input?
        - What specifically changed from Part 1 to Part 2?
        """

        if feedback:
            base_prompt += """

        <FEEDBACK>
        This is a retry attempt. Your previous solution was submitted but rejected.
        Check submission_issues.md for details on what went wrong.

        Common issues:
        - Answer too high or too low (off-by-one errors, edge cases)
        - Wrong format (integer vs string, extra whitespace)
        - Misunderstood the problem (re-read the puzzle carefully)
        - Works for examples but not full input (scale issues, overflow)

        Your previous solution is in solution.py - analyze what might be wrong.
        </FEEDBACK>
        """

        return base_prompt

from src.agents import TranslationAgent, PlanningAgent, CritiqueAgent, CodingAgent, TestingAgent, SubmissionAgent
from src.aoc_client import AdventOfCodeClient
from pathlib import Path
import shutil
import time
import click
import sys


class AdventSolver():

    def __init__(self, workspace_path="./agent_workspace", part=1, client=None, year=None, day=None,
                 progress_callback=None, skip_submission=False):
        """Initialize AdventSolver with workspace path and part number.

        Args:
            workspace_path: Path to the workspace directory where agents will run
            part: Part number (1 or 2) of the puzzle being solved
            client: AdventOfCodeClient instance for submissions (optional)
            year: Year of the puzzle (required if client provided)
            day: Day of the puzzle (required if client provided)
            progress_callback: Optional callback function for progress reporting.
                              Signature: callback(stage: str, message: str, attempt: int = 1,
                                                  answer: str = None, error: str = None)
                              If not provided, only print statements are used (default CLI behavior).
            skip_submission: If True, skip AoC submission even if client is provided.
                            Used for practice mode on already-completed puzzles.
        """
        self.workspace_path = workspace_path
        self.part = part
        self.client = client
        self.year = year
        self.day = day
        self.progress_callback = progress_callback
        self.skip_submission = skip_submission
        self.translation_agent = TranslationAgent(workspace_path, part)
        self.planning_agent = PlanningAgent(workspace_path, part)
        self.critique_agent = CritiqueAgent(workspace_path, part)
        self.coding_agent = CodingAgent(workspace_path, part)
        self.testing_agent = TestingAgent(workspace_path, part)
        self.submission_agent = SubmissionAgent(workspace_path, part)

    def _report(self, stage: str, message: str, attempt: int = 1, answer: str = None, error: str = None):
        """Report progress via callback if one is registered.

        This is a no-op if no callback was provided, preserving CLI behavior.
        """
        if self.progress_callback:
            self.progress_callback(stage, message, attempt, answer, error)

    def parse_test_result(self, result):
        result_lines = result.strip().splitlines()
        last_line = result_lines[-1] if result_lines else ""
        last_line = last_line.lower()
        if last_line == "success":
            return True
        elif last_line == "failure":
            return False
        else:
            raise ValueError("Testing agent response must be either 'Success' or 'Failure'.")

    def parse_submission_result(self, result):
        """Parse submission agent result to determine if submission was successful.

        Args:
            result: The output from SubmissionAgent.run_agent()

        Returns:
            True if submission was accepted, False if rejected

        Raises:
            ValueError: If the agent output doesn't end with 'Success' or 'Failure'
        """
        result_lines = result.strip().splitlines()
        last_line = result_lines[-1] if result_lines else ""
        last_line = last_line.lower()
        if last_line == "success":
            return True
        elif last_line == "failure":
            return False
        else:
            raise ValueError("Submission agent response must be either 'Success' or 'Failure'.")

    def _run_planning_phase(self):
        """Run the planning phase: translation, planning, critique, and plan revision.

        This phase prepares the implementation and test plans before coding begins.
        """
        self._report("translation", "Translating problem description...")
        print("Translating problem description...")
        self.translation_agent.run_agent()

        self._report("planning", "Creating implementation plan...")
        print("Planning solution...")
        self.planning_agent.run_agent()

        self._report("critique", "Reviewing and critiquing plan...")
        print("Critiquing plan...")
        self.critique_agent.run_agent()

        self._report("revision", "Revising plan based on critique...")
        print("Planning revised solution...")
        self.planning_agent.run_agent(feedback=True)

    def _run_testing_loop(self):
        """Run the testing/coding feedback loop until tests pass.

        Returns:
            True when tests pass successfully
        """
        test_attempt = 0
        while True:
            test_attempt += 1
            self._report("testing", f"Running tests (attempt {test_attempt})...", attempt=test_attempt)
            print("Testing solution...")
            results = self.testing_agent.run_agent()
            parsed_result = self.parse_test_result(results)
            if parsed_result:
                print("Local tests passed!")
                return True
            else:
                self._report("coding", f"Adjusting code based on test feedback (attempt {test_attempt})...", attempt=test_attempt)
                print("Adjusting code based on test feedback...")
                self.coding_agent.run_agent(feedback=True)

    def solve(self):
        # Phase 1: Planning
        self._run_planning_phase()

        # Phase 2: Implementation
        self._report("coding", "Writing initial solution...")
        print("Coding solution...")
        self.coding_agent.run_agent()

        # Phase 3: Testing loop (runs until tests pass)
        self._run_testing_loop()

        # Phase 4: Submission loop (if client is provided and not in skip mode, submit and verify)
        if self.client and not self.skip_submission:
            max_submission_attempts = 3
            for attempt in range(max_submission_attempts):
                self._report("submitting", f"Submitting answer (attempt {attempt + 1}/{max_submission_attempts})...", attempt=attempt + 1)
                print(f"\n{'='*60}")
                print(f"  Submission Attempt {attempt + 1}/{max_submission_attempts}")
                print(f"{'='*60}\n")

                # Read answer
                answer_file = Path(self.workspace_path) / "answer.txt"
                if not answer_file.exists():
                    self._report("failed", "Error: answer.txt not found", error="answer.txt not found")
                    print("\n✗ Error: answer.txt not found")
                    print("  The testing agent should have created this file.")
                    return False

                answer = answer_file.read_text().strip()
                print(f"Submitting Answer for Part {self.part}: {answer}\n")

                # Submit answer
                result = self.client.submit_answer(self.year, self.day, self.part, answer)
                print(f"Status: {result['status_code']}")
                print(f"Response:\n{result['message']}\n")

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
                print("Analyzing submission result...")
                analysis_result = self.submission_agent.run_agent()

                # Parse result
                try:
                    submission_success = self.parse_submission_result(analysis_result)
                except ValueError as e:
                    self._report("failed", f"Error parsing submission result: {e}", error=str(e))
                    print(f"✗ Error: {e}")
                    return False

                if submission_success:
                    self._report("completed", f"Part {self.part} solved correctly!", answer=answer)
                    print(f"🎉 Part {self.part} solved correctly!")
                    return True
                else:
                    print(f"✗ Submission attempt {attempt + 1} failed")

                    if attempt < max_submission_attempts - 1:
                        # Still have retries left - adjust code based on submission feedback
                        self.resolve_with_submission_feedback()
                    else:
                        self._report("failed", f"Part {self.part} failed after {max_submission_attempts} attempts", error="Max submission attempts reached")
                        print(f"\n✗ Part {self.part} failed after {max_submission_attempts} submission attempts")
                        return False

            return False
        else:
            # No client provided or skip_submission mode - just return success after tests pass
            # Read the answer for reporting
            answer_file = Path(self.workspace_path) / "answer.txt"
            answer = answer_file.read_text().strip() if answer_file.exists() else None
            if self.skip_submission:
                self._report("completed", "Solution verified locally (practice mode)", answer=answer)
                print("Solution verified locally (practice mode - skipping AoC submission)!")
            else:
                self._report("completed", "Problem solved locally (no submission client)", answer=answer)
                print("Problem has been solved locally (no submission client provided)!")
            return True

    def resolve_with_submission_feedback(self):
        """Re-run coding and testing loop with submission feedback.

        Called when a solution passes local tests but fails submission.
        The CodingAgent will read submission_issues.md for guidance.
        """
        self._report("coding", "Adjusting code based on submission feedback...")
        print("Adjusting code based on submission feedback...")
        self.coding_agent.run_agent(feedback=True, submission_feedback=True)

        # Re-test the updated solution using the standard testing loop
        self._run_testing_loop()


def setup_workspace(client, year, day, part, workspace_base):
    """Set up workspace for a puzzle part.

    Creates workspace directory, fetches puzzle and input files, and copies
    Part 1 artifacts if solving Part 2.

    Args:
        client: AdventOfCodeClient instance
        year: The year of the puzzle
        day: The day of the puzzle
        part: The part number (1 or 2)
        workspace_base: Base workspace directory

    Returns:
        Path object for the workspace directory
    """
    # Create workspace directory
    workspace_path = Path(workspace_base) / str(year) / f"day_{day}" / f"part_{part}"
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"Workspace: {workspace_path}\n")

    # Fetch puzzle and input
    print(f"Fetching puzzle part {part}...")
    puzzle_file = client.save_puzzle_to_file(year, day, part, workspace_base)
    print(f"  ✓ Puzzle saved to {puzzle_file}")

    print(f"Fetching input...")
    input_file = client.save_input_to_file(year, day, part, workspace_base)
    print(f"  ✓ Input saved to {input_file}")

    # If Part 2, copy Part 1 artifacts for context
    if part == 2:
        print(f"\nCopying Part 1 artifacts for context...")
        part1_workspace = workspace_path.parent / "part_1"

        if not part1_workspace.exists():
            print(f"  ⚠ Warning: Part 1 workspace not found at {part1_workspace}")
        else:
            # Files to copy: (source_name, destination_name)
            files_to_copy = [
                ("answer.txt", "part_1_answer.txt"),
                ("problem.md", "part_1_problem.md"),
                ("solution.py", "part_1_solution.py"),
                ("puzzle.md", "part_1_puzzle.md"),
            ]

            for source_name, dest_name in files_to_copy:
                source_file = part1_workspace / source_name
                dest_file = workspace_path / dest_name

                if source_file.exists():
                    try:
                        shutil.copy2(source_file, dest_file)
                        print(f"  ✓ Copied {source_name} → {dest_name}")
                    except Exception as e:
                        print(f"  ⚠ Warning: Failed to copy {source_name}: {e}")
                else:
                    print(f"  ⚠ Warning: Part 1 file not found: {source_name}")

    print()  # Empty line after setup
    return workspace_path


def solve_part(client, year, day, part, workspace_base):
    """Solve a single part of a puzzle.

    Args:
        client: AdventOfCodeClient instance
        year: The year of the puzzle
        day: The day of the puzzle
        part: The part number (1 or 2)
        workspace_base: Base workspace directory

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"  Part {part}")
    print(f"{'='*60}\n")

    # Set up workspace (create dirs, fetch files, copy Part 1 artifacts if needed)
    workspace_path = setup_workspace(client, year, day, part, workspace_base)

    # Run solver - it handles testing, submission, and retries internally
    print("=== Starting Solver ===\n")
    solver = AdventSolver(
        workspace_path=str(workspace_path),
        part=part,
        client=client,
        year=year,
        day=day
    )
    success = solver.solve()

    if not success:
        print(f"\n✗ Failed to solve part {part}")
        return False

    return True


def solve_single_day(client, year, day, workspace_base):
    """Solve both parts of a single day.

    Args:
        client: AdventOfCodeClient instance
        year: The year of the puzzle
        day: The day of the puzzle
        workspace_base: Base workspace directory

    Returns:
        dict with keys: 'day', 'status', 'part1_result', 'part2_result', 'error'
    """
    result = {
        'day': day,
        'status': 'unknown',
        'part1_result': None,
        'part2_result': None,
        'error': None
    }

    try:
        print(f"\n{'='*60}")
        print(f"  Advent of Code {year} Day {day}")
        print(f"{'='*60}\n")

        # Check completion status
        print("Checking puzzle completion status...")
        status = client.get_completion_status(year, day)
        print(f"  Part 1: {'✓ Complete' if status['part1_complete'] else '○ Incomplete'}")
        print(f"  Part 2: {'✓ Complete' if status['part2_complete'] else '○ Incomplete' if status['available_parts'] >= 2 else '🔒 Locked'}")
        print(f"  Available parts: {status['available_parts']}\n")

        # Check if both parts are already complete
        if status['part1_complete'] and status['part2_complete']:
            print("🎉 Both parts already complete!")
            print(f"  Part 1 answer: {status['part1_answer']}")
            print(f"  Part 2 answer: {status['part2_answer']}")
            result['status'] = 'already_complete'
            result['part1_result'] = 'complete'
            result['part2_result'] = 'complete'
            return result

        # Solve Part 1 if not complete
        if not status['part1_complete']:
            success = solve_part(client, year, day, 1, workspace_base)
            if not success:
                result['status'] = 'failed'
                result['part1_result'] = 'failed'
                result['error'] = 'Part 1 failed'
                return result
            result['part1_result'] = 'solved'

            # Re-check status after part 1 to see if part 2 is now available
            print("\nRechecking puzzle status...")
            status = client.get_completion_status(year, day)
        else:
            print("Part 1 already complete, skipping to Part 2...\n")
            if status['part1_answer']:
                print(f"  Part 1 answer: {status['part1_answer']}")
            result['part1_result'] = 'complete'

        # Solve Part 2 if available and not complete
        if status['available_parts'] >= 2:
            if not status['part2_complete']:
                success = solve_part(client, year, day, 2, workspace_base)
                if not success:
                    result['status'] = 'partial'
                    result['part2_result'] = 'failed'
                    result['error'] = 'Part 2 failed'
                    return result
                result['part2_result'] = 'solved'
            else:
                print("Part 2 already complete!")
                if status['part2_answer']:
                    print(f"  Part 2 answer: {status['part2_answer']}")
                result['part2_result'] = 'complete'
        else:
            print("Part 2 not yet available (Part 1 must be completed first)")
            result['part2_result'] = 'not_available'

        result['status'] = 'success'
        return result

    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        print(f"\n✗ Error on day {day}: {e}")
        import traceback
        traceback.print_exc()
        return result


def solve_all_days(client, year, start_time):
    """Solve all 25 days of Advent of Code for a given year.

    Args:
        client: AdventOfCodeClient instance
        year: The year to solve
        start_time: Start time for performance tracking
    """
    print(f"\n{'='*70}")
    print(f"  Solving All Days - Advent of Code {year}")
    print(f"{'='*70}\n")

    workspace_base = "/app/agent_workspace"
    results = []

    # Solve each day
    for day in range(1, 26):
        day_result = solve_single_day(client, year, day, workspace_base)
        results.append(day_result)

        # Print day summary
        print(f"\n--- Day {day} Summary ---")
        print(f"Status: {day_result['status']}")
        if day_result['error']:
            print(f"Error: {day_result['error']}")
        print()

    # Print overall summary
    end_time = time.perf_counter()
    print(f"\n{'='*70}")
    print(f"  FINAL SUMMARY - Advent of Code {year}")
    print(f"{'='*70}\n")

    # Categorize results
    already_complete = [r for r in results if r['status'] == 'already_complete']
    success = [r for r in results if r['status'] == 'success']
    partial = [r for r in results if r['status'] == 'partial']
    failed = [r for r in results if r['status'] == 'failed']
    errors = [r for r in results if r['status'] == 'error']

    print(f"✓ Already Complete:     {len(already_complete)} days")
    print(f"🎉 Successfully Solved:  {len(success)} days")
    print(f"⚠ Partially Solved:     {len(partial)} days (Part 1 only)")
    print(f"✗ Failed:               {len(failed)} days")
    print(f"💥 Errors:               {len(errors)} days")
    print()

    # Show details for non-complete days
    if success:
        print("Successfully solved:")
        for r in success:
            print(f"  Day {r['day']}: Part 1 {r['part1_result']}, Part 2 {r['part2_result']}")
        print()

    if partial:
        print("Partially solved (Part 1 only):")
        for r in partial:
            print(f"  Day {r['day']}: {r['error']}")
        print()

    if failed:
        print("Failed days:")
        for r in failed:
            print(f"  Day {r['day']}: {r['error']}")
        print()

    if errors:
        print("Days with errors:")
        for r in errors:
            print(f"  Day {r['day']}: {r['error']}")
        print()

    total_stars = sum(
        (1 if r['part1_result'] in ['solved', 'complete'] else 0) +
        (1 if r['part2_result'] in ['solved', 'complete'] else 0)
        for r in results
    )
    print(f"⭐ Total stars: {total_stars} / 50")
    print(f"⏱ Total runtime: {end_time - start_time:.2f} seconds")
    print(f"{'='*70}\n")

    sys.exit(0)


@click.command()
@click.option('--year', required=True, type=int, help='Year of the puzzle (e.g., 2024)')
@click.option('--day', type=int, help='Day of the puzzle (1-25)')
@click.option('--all-days', is_flag=True, help='Solve all 25 days')
def main(year, day, all_days):
    """Solve Advent of Code puzzles automatically."""
    start_time = time.perf_counter()

    # Validate parameters
    if not day and not all_days:
        print("Error: Must provide either --day or --all-days")
        sys.exit(1)

    if day and all_days:
        print("Error: Cannot specify both --day and --all-days")
        sys.exit(1)

    try:
        # Initialize AOC client
        client = AdventOfCodeClient()

        # Handle all-days mode
        if all_days:
            solve_all_days(client, year, start_time)
            return

        # Single day mode
        print(f"\n{'='*60}")
        print(f"  Advent of Code {year} Day {day}")
        print(f"{'='*60}\n")

        workspace_base = "/app/agent_workspace"

        # Check completion status
        print("Checking puzzle completion status...")
        status = client.get_completion_status(year, day)
        print(f"  Part 1: {'✓ Complete' if status['part1_complete'] else '○ Incomplete'}")
        print(f"  Part 2: {'✓ Complete' if status['part2_complete'] else '○ Incomplete' if status['available_parts'] >= 2 else '🔒 Locked'}")
        print(f"  Available parts: {status['available_parts']}\n")

        # Check if both parts are already complete
        if status['part1_complete'] and status['part2_complete']:
            print("🎉 Both parts already complete!")
            print(f"  Part 1 answer: {status['part1_answer']}")
            print(f"  Part 2 answer: {status['part2_answer']}")
            end_time = time.perf_counter()
            print(f"\n=== Total runtime: {end_time - start_time:.2f} seconds ===")
            sys.exit(0)

        # Solve Part 1 if not complete
        if not status['part1_complete']:
            success = solve_part(client, year, day, 1, workspace_base)
            if not success:
                sys.exit(1)

            # Re-check status after part 1 to see if part 2 is now available
            print("\nRechecking puzzle status...")
            status = client.get_completion_status(year, day)
        else:
            print("Part 1 already complete, skipping to Part 2...\n")
            if status['part1_answer']:
                print(f"  Part 1 answer: {status['part1_answer']}")

        # Solve Part 2 if available and not complete
        if status['available_parts'] >= 2:
            if not status['part2_complete']:
                success = solve_part(client, year, day, 2, workspace_base)
                if not success:
                    sys.exit(1)
            else:
                print("Part 2 already complete!")
                if status['part2_answer']:
                    print(f"  Part 2 answer: {status['part2_answer']}")
        else:
            print("Part 2 not yet available (Part 1 must be completed first)")

        end_time = time.perf_counter()
        print(f"\n{'='*60}")
        print(f"  Total runtime: {end_time - start_time:.2f} seconds")
        print(f"{'='*60}")
        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

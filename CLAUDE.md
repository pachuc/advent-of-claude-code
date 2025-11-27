# Advent of Claude Code - Development Reference

> **Last Updated**: 2025-11-26
> **Maintainer Notes**: Keep this document updated when making architectural changes or discovering new AoC behavior patterns.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
   - [Multi-Agent System](#multi-agent-system)
   - [Workflow](#workflow)
4. [File Structure](#file-structure)
5. [Advent of Code Client](#advent-of-code-client)
6. [Development Workflow](#development-workflow)
7. [Container Management](#container-management)
8. [Key Implementation Details](#key-implementation-details)
9. [Advent of Code API Notes](#advent-of-code-api-notes)
10. [Common Issues & Solutions](#common-issues--solutions)
11. [Architecture Decisions](#architecture-decisions)
12. [Future Improvements](#future-improvements)
13. [References](#references)

---

## Project Overview

This project uses AI agents powered by Claude Code to automatically solve Advent of Code puzzles. The system fetches puzzles, plans solutions, writes code, tests it, and submits answers - handling both Part 1 and Part 2 automatically.

**Key Features:**
- Fully automated solving pipeline (no human in the loop)
- Multi-agent architecture with specialized roles
- Automatic submission with retry logic
- Handles both Part 1 and Part 2 sequentially
- Built-in testing and feedback loops
- **Race Mode**: Web interface to race against Claude on AoC puzzles

## Quick Start

```bash
# 1. Clone and navigate to repo
cd advent-of-claude-code

# 2. Extract your AOC session cookie (see COOKIE_EXTRACTION.md for detailed guide)
# Quick method: Open browser console at adventofcode.com and run:
# document.cookie.split('; ').find(c => c.startsWith('session=')).split('=')[1]

# 3. Create .env file with credentials
cp .env.example .env
# Edit .env and add your AOC_SESSION value

# 4. Build the container
make build

# 5. Solve a specific day
make solve YEAR=2015 DAY=1

# 6. Or solve all 25 days
make solve YEAR=2015

# 7. Or race against Claude (web interface)
make web
# Open http://localhost:8000 in your browser
```

For detailed cookie extraction instructions, see [COOKIE_EXTRACTION.md](COOKIE_EXTRACTION.md).

### Quick Reference

**Common Commands:**
```bash
make build               # Build container
make solve YEAR=Y DAY=D  # Solve specific day (CLI mode)
make solve YEAR=Y        # Solve all 25 days (CLI mode)
make web                 # Start race mode web server (http://localhost:8000)
make debug               # Interactive shell
make clean               # Remove container
```

**Key Files & Locations:**
```
Host                                Container
./workspace/                    →   /app/agent_workspace/
~/.claude/                      →   /root/.claude/
./.env                          →   (passed as env vars)
```

**Workspace Structure:**
```
workspace/YEAR/day_DAY/part_PART/
├── puzzle.md              (input from AoC)
├── input.md               (input from AoC)
├── problem.md             (TranslationAgent)
├── implementation_plan.md (PlanningAgent)
├── test_plan.md           (PlanningAgent)
├── critique.md            (CritiqueAgent)
├── solution.py            (CodingAgent)
├── answer.txt             (TestingAgent - on success)
└── *_issues.md            (various agents - on failure)
```

## Architecture

### Multi-Agent System

The solver uses a pipeline of specialized agents, each with a specific role:

1. **TranslationAgent** (`src/agents/translation_agent.py`)
   - Converts the puzzle markdown into a structured problem description
   - Creates `problem.md` with clear problem statement

2. **PlanningAgent** (`src/agents/planning_agent.py`)
   - Reads the problem and creates an implementation plan
   - Creates `implementation_plan.md` and `test_plan.md`
   - Can be run with feedback to revise plans (reads `critique.md` and updates both plan files)

3. **CritiqueAgent** (`src/agents/critique_agent.py`)
   - Reviews the initial plan and provides critical feedback
   - Creates `critique.md` with suggestions for improvement

4. **CodingAgent** (`src/agents/coding_agent.py`)
   - Implements the solution based on the plan
   - Creates `solution.py`
   - Can be run with feedback to fix bugs

5. **TestingAgent** (`src/agents/testing_agent.py`)
   - Tests the solution against examples and real input
   - **MUST** end response with exactly "Success" or "Failure" on the last line (case-insensitive)
   - On success: creates `answer.txt` with the final answer (just the value, nothing else)
   - On failure: creates `testing_issues.md` with issues found

6. **SubmissionAgent** (`src/agents/submission_agent.py`)
   - Analyzes the result of submitting an answer to Advent of Code
   - Reads `submission_result.md` containing the HTTP response from AoC
   - **MUST** end response with exactly "Success" or "Failure" on the last line (case-insensitive)
   - On success: No additional files created
   - On failure: creates `submission_issues.md` with detailed analysis and suggestions

All agents inherit from `BaseAgent` (`src/agents/base_agent.py`) which provides:
- Workspace management (workspace_path and part number tracking)
- Claude Code CLI integration via subprocess
- Abstract `prompt(feedback)` method that must be implemented
- `run_agent(feedback=False)` method that executes the Claude Code CLI
- Automatic error handling for CLI failures

**BaseAgent Implementation:**
```python
class BaseAgent(ABC):
    def __init__(self, workspace_path, part):
        self.workspace_path = workspace_path
        self.part = part

    @abstractmethod
    def prompt(self, feedback):
        """Each agent implements its own prompt template"""
        pass

    def run_agent(self, feedback=False):
        """Runs claude CLI with the agent's prompt in the workspace"""
        subprocess.run(
            ["claude", "-p", self.prompt(feedback), "--dangerously-skip-permissions"],
            cwd=self.workspace_path,
            capture_output=True,
            text=True
        )
```

**Note:** CodingAgent overrides `run_agent()` to accept an additional `submission_feedback` parameter.

### Workflow

The `AdventSolver` class orchestrates the entire solving process, from planning through submission:

```
1. Check completion status (both parts)
   ↓
2. For each incomplete part → AdventSolver.solve():
   ↓
   ┌─────────────────────────────────────────────────┐
   │  3. Translation Agent → Creates problem.md      │
   │     ↓                                            │
   │  4. Planning Agent → Creates plans              │
   │     ↓                                            │
   │  5. Critique Agent → Reviews plans              │
   │     ↓                                            │
   │  6. Planning Agent (feedback) → Updates plans   │
   │     ↓                                            │
   │  7. Coding Agent → Creates solution.py          │
   │     ↓                                            │
   │  8. Testing Loop (INFINITE retry):              │
   │     → Testing Agent tests solution              │
   │     → If fail: Coding Agent adjusts → retest    │
   │     → If pass: continue to submission           │
   │     ↓                                            │
   │  9. Submission Loop (max 3 attempts):           │
   │     → Submit answer to Advent of Code           │
   │     → Submission Agent analyzes result          │
   │     → If success: DONE                          │
   │     → If fail AND retries left:                 │
   │       • Coding Agent (submission feedback)      │
   │       • Re-run testing loop (step 8)            │
   │       • Retry submission                        │
   │     → If fail AND no retries: FAIL              │
   └─────────────────────────────────────────────────┘
   ↓
3. If Part 1 complete: Re-check status to unlock Part 2
   ↓
4. If Part 2 available: goto step 2
```

## File Structure

### Repository Layout

```
advent-of-claude-code/
├── src/
│   ├── main.py              # CLI entry point, orchestrates the workflow
│   ├── aoc_client.py        # Advent of Code API client
│   ├── api.py               # FastAPI web server (race mode)
│   ├── race_manager.py      # Race state management & background solver
│   ├── progress.py          # Progress tracking abstraction
│   └── agents/
│       ├── __init__.py           # Dynamic agent exports
│       ├── base_agent.py         # Base class for all agents
│       ├── translation_agent.py  # Simplifies puzzle description
│       ├── planning_agent.py     # Creates implementation & test plans
│       ├── critique_agent.py     # Reviews and critiques plans
│       ├── coding_agent.py       # Implements the solution
│       ├── testing_agent.py      # Tests and verifies solution
│       ├── submission_agent.py   # Analyzes submission results
│       └── simple_agent.py       # Example/test agent (not used in pipeline)
├── static/                  # Web frontend assets (race mode)
│   ├── index.html           # Single-page app
│   ├── style.css            # AoC-inspired dark theme
│   └── app.js               # Frontend application logic
├── workspace/               # Generated workspace (mounted volume)
│   └── <year>/
│       └── day_<day>/
│           ├── part_1/
│           │   ├── puzzle.md                  # Raw puzzle from AoC
│           │   ├── input.md                   # Puzzle input
│           │   ├── problem.md                 # Simplified problem (TranslationAgent)
│           │   ├── implementation_plan.md     # Implementation plan (PlanningAgent)
│           │   ├── test_plan.md               # Testing plan (PlanningAgent)
│           │   ├── critique.md                # Plan critique (CritiqueAgent)
│           │   ├── solution.py                # Python solution (CodingAgent)
│           │   ├── implementation_summary.md  # Implementation notes (CodingAgent)
│           │   ├── testing_issues.md          # Issues found (TestingAgent, only if tests failed)
│           │   ├── answer.txt                 # Final answer (TestingAgent, only if tests success)
│           │   ├── submission_result.md       # AoC submission response (created before SubmissionAgent)
│           │   └── submission_issues.md       # Submission failure analysis (SubmissionAgent, only if submission failed)
│           └── part_2/
│               ├── (same structure as part_1)
│               ├── part_1_puzzle.md           # Copied from Part 1 (for context)
│               ├── part_1_problem.md          # Copied from Part 1 (for context)
│               ├── part_1_solution.py         # Copied from Part 1 (for reuse)
│               └── part_1_answer.txt          # Copied from Part 1 (may be needed)
├── .env                     # AOC_SESSION env var (git-ignored)
├── .env.example             # Template for environment variables
├── .gitignore               # Git ignore rules (workspace/, .env, etc.)
├── Containerfile            # Podman/Docker container definition
├── Makefile                 # Build, run, solve, debug, web commands
├── requirements.txt         # Python dependencies
├── README.md                # Project overview and high-level description
├── CLAUDE.md                # This file - comprehensive development reference
├── COOKIE_EXTRACTION.md     # Detailed guide for extracting AOC session cookie
└── flow_chart.png           # Visual diagram of the agent workflow
```

### Workspace Organization

**Important**: The workspace uses a nested structure:
```
/workspace/<year>/day_<day>/part_<part>/
```

Each part gets its own isolated workspace with:
- Its own puzzle description
- Its own copy of the input (input is the same for both parts, but duplicated)
- Its own agent artifacts (plan, critique, solution, etc.)

This isolation prevents part 1 and part 2 from interfering with each other.

## Advent of Code Client

### Key Methods

#### `get_completion_status(year, day) -> dict`
Fetches the puzzle page and determines completion status.

**Returns:**
```python
{
    "part1_complete": bool,      # True if part 1 solved
    "part2_complete": bool,      # True if part 2 solved
    "part1_answer": str | None,  # Answer if completed
    "part2_answer": str | None,  # Answer if completed
    "available_parts": int       # 1 or 2
}
```

**Detection Logic:**
- Counts `<article>` elements (1 = only part 1, 2 = part 2 unlocked)
- Looks for text: "Your puzzle answer was" (indicates completion)
- Looks for text: "Both parts of this puzzle are complete!" (both done)
- Extracts answers from `<code>` tags in paragraphs

#### `get_puzzle(year, day, part) -> str`
Fetches puzzle description as markdown.
- Part 1: First `<article>` element
- Part 2: Second `<article>` element (if unlocked)

#### `get_input(year, day) -> str`
Fetches puzzle input (same for both parts).

#### `submit_answer(year, day, part, answer) -> dict`
Submits an answer and returns the response.

**Returns:**
```python
{
    "status_code": int,
    "message": str,       # Parsed from response
    "raw_html": str
}
```

Check for "right answer" in message to determine success.

#### `save_puzzle_to_file(year, day, part, output_dir)`
Saves puzzle to: `{output_dir}/{year}/day_{day}/part_{part}/puzzle.md`

#### `save_input_to_file(year, day, part, output_dir)`
Saves input to: `{output_dir}/{year}/day_{day}/part_{part}/input.md`

### Authentication

The client requires your AOC session cookie to make authenticated requests.

**Quick Setup:**
1. Copy the example environment file: `cp .env.example .env`
2. Follow the detailed extraction guide in [COOKIE_EXTRACTION.md](COOKIE_EXTRACTION.md)
3. Add your session value to `.env`: `AOC_SESSION=<your_cookie_value>`

**Security Notes:**
- Session tokens are valid for ~30 days
- The `.env` file is git-ignored (never commit it)
- Tokens can be revoked from your AoC account settings

## Development Workflow

### Initial Setup

```bash
# Clone and navigate to repo
cd advent-of-claude-code

# Create .env file from template
cp .env.example .env

# Edit .env and add your AOC_SESSION value
# See COOKIE_EXTRACTION.md for detailed extraction instructions

# Build the container
make build
```

**Environment Variables:**
- `AOC_SESSION` (required): Your Advent of Code session cookie
- `IS_SANDBOX` (auto-set): Set to `1` by Makefile to indicate container environment
- `PYTHONUNBUFFERED` (auto-set): Set to `1` for real-time output in container

**Note:** Claude API credentials are mounted from `~/.claude/.credentials.json`, not stored in `.env`.

### Solving Puzzles

**Available Make Commands:**

```bash
# Build the container image
make build

# Solve a specific day (handles both parts automatically)
make solve YEAR=2015 DAY=1

# Solve all 25 days for a year
make solve YEAR=2015

# Start interactive debug shell in container
make debug

# Clean up container and image
make clean
```

**Solve Behavior:**
The script automatically:
- Checks which parts are already complete
- Skips completed parts (shows cached answers)
- Solves incomplete parts in order (Part 1 → Part 2)
- Re-checks status after Part 1 to unlock Part 2
- Provides comprehensive summary when using `--all-days`

### Debugging

```bash
# Start an interactive shell in the container
make debug

# Inside the container:
python src/main.py --year 2015 --day 1

# Or test individual components:
python -c "from src.aoc_client import AdventOfCodeClient; c = AdventOfCodeClient(); print(c.get_completion_status(2015, 1))"
```

### Viewing Results

```bash
# Check workspace for generated files
ls -la workspace/2015/day_1/part_1/

# View the solution
cat workspace/2015/day_1/part_1/solution.py

# View the answer
cat workspace/2015/day_1/part_1/answer.txt
```

### Command Line Interface

The main script (`src/main.py`) accepts the following options:

```bash
python src/main.py --year YEAR [--day DAY | --all-days]
```

**Required:**
- `--year YEAR` - Year of the puzzle (e.g., 2015, 2024)

**Mutually Exclusive (must provide one):**
- `--day DAY` - Solve a specific day (1-25)
- `--all-days` - Solve all 25 days sequentially

**Examples:**
```bash
# Solve a single day
python src/main.py --year 2015 --day 1

# Solve all 25 days
python src/main.py --year 2015 --all-days
```

**`--all-days` Behavior:**
- Solves days 1-25 sequentially
- Continues to next day even if current day fails
- Tracks results: already_complete, success, partial (Part 1 only), failed, error
- Prints comprehensive summary at the end with star count (out of 50)
- Shows runtime statistics

**Workspace Location:**
- Container: `/app/agent_workspace` (hardcoded in main.py)
- Host: `./workspace` (mounted volume)

## Container Management

### Container Image Details

**Base Image:** `python:3.11-slim`

**Installed Dependencies:**
- Python packages (from `requirements.txt`)
- Node.js and npm (required for Claude Code CLI)
- Claude Code CLI (`@anthropic-ai/claude-code`)

**Working Directory:** `/app`

**Agent Workspace:** `/app/agent_workspace` (mounted from host `./workspace`)

The Containerfile sets up a complete environment with all required dependencies and tools pre-installed.

### Credentials Mounting

The container mounts your local `~/.claude` directory:
```bash
-v $HOME/.claude:/root/.claude:z
```

**Benefits:**
- No need to rebuild when credentials change
- Credentials never baked into container image
- Always uses latest Claude Code settings

**Files mounted:**
- `~/.claude/.credentials.json` - API credentials
- `~/.claude/settings.local.json` - Claude Code settings
- Any other Claude config files

### Workspace Mounting

```bash
-v $(pwd)/workspace:/app/agent_workspace:z
```

The `workspace/` directory is mounted so:
- Solutions persist after container exits
- You can inspect/modify files from host
- Multiple runs accumulate in the same workspace

## Key Implementation Details

### Solver Architecture

The `AdventSolver` class (`src/main.py`) is the core orchestrator:

**Initialization:**
- Takes workspace path, part number, and optional AoC client/year/day
- Creates all specialized agents (Translation, Planning, Critique, Coding, Testing, Submission)
- If client is provided, handles full workflow including submission
- If no client, runs in "local mode" (testing only, no submission)

**Internal Organization:**
The solver organizes the workflow into logical phases using helper methods:
- `_run_planning_phase()` - Handles translation → planning → critique → plan revision
- `_run_testing_loop()` - Handles the testing/coding feedback loop (reusable)
- `solve()` - Orchestrates all phases: planning → coding → testing → submission
- `resolve_with_submission_feedback()` - Adjusts code based on submission failure, re-tests

**Multi-Part Handling:**
1. **Check status before starting** - avoids redundant work
2. **Skip completed parts** - prints cached answers
3. **Auto-unlock part 2** - re-checks status after part 1 submission
4. **Isolated workspaces** - each part has its own directory
5. **Part 1 context for Part 2** - copies artifacts for reuse (see below)

### Part 2 Context System

When solving Part 2, the system automatically copies Part 1 artifacts to provide context:

**Copied Files:**
- `part_1_puzzle.md` - Original Part 1 puzzle text
- `part_1_problem.md` - Simplified Part 1 problem description
- `part_1_solution.py` - Working Part 1 code (can be adapted/reused)
- `part_1_answer.txt` - Part 1 answer (may be needed as input)

**Agent Awareness:**
All agents (Translation, Planning, Critique, Coding, Testing) receive special prompts when `part == 2` that:
- Alert them to the availability of Part 1 artifacts
- Encourage code reuse and adaptation over rewriting
- Suggest checking if Part 2 builds on Part 1's algorithm
- Remind them that Part 2 descriptions are often brief and assume Part 1 context

This dramatically improves solving efficiency and success rate for Part 2 puzzles.

### Error Handling

- If part 1 fails: exits, doesn't attempt part 2
- If part 2 fails: exits, but part 1 remains complete
- If tests fail: enters **infinite** feedback loop with CodingAgent (no retry limit)
- If submission fails: enters submission retry loop (max 3 attempts)
  - SubmissionAgent analyzes the failure
  - On retry: CodingAgent reads `submission_issues.md` and adjusts solution
  - Solution is re-tested before next submission attempt
  - After 3 failed submissions: gives up and exits

### Agent Communication

Agents communicate via files in the workspace:
- Each agent reads specific input files
- Each agent writes specific output files
- `AdventSolver` orchestrates all agents and passes workspace path to each
- Agents use BaseAgent utilities to read/write files
- Solver manages the feedback loops:
  - Testing feedback: `testing_issues.md` → CodingAgent
  - Submission feedback: `submission_issues.md` → CodingAgent (with `submission_feedback=True`)
  - Plan critique: `critique.md` → PlanningAgent (with `feedback=True`)

### Testing Loop

The testing/coding feedback loop is encapsulated in `AdventSolver._run_testing_loop()`:

```python
# Simplified - actual implementation in _run_testing_loop()
while True:
    result = testing_agent.run_agent()
    if parse_test_result(result):  # "Success"
        return True
    else:  # "Failure"
        coding_agent.run_agent(feedback=True)
```

**Important Details:**
- **No retry limit** - loop continues indefinitely until success
- Testing agent must return exactly "Success" or "Failure" as the last line (case-insensitive)
- `parse_test_result()` raises `ValueError` if last line is neither "success" nor "failure"
- On failure, CodingAgent reads `testing_issues.md` and updates `solution.py`
- Reused by both initial solve and submission feedback loops

### Submission Loop (Integrated into Solver)

After tests pass, `AdventSolver.solve()` automatically enters the submission loop:

```python
# Inside AdventSolver.solve(), after testing loop passes:
if self.client:  # Only if client was provided
    for attempt in range(max_submission_attempts):  # max = 3
        # Submit answer to Advent of Code
        result = self.client.submit_answer(self.year, self.day, self.part, answer)

        # Save result to submission_result.md
        write_submission_result(result)

        # Analyze with SubmissionAgent
        analysis = self.submission_agent.run_agent()

        if self.parse_submission_result(analysis):  # "Success"
            return True
        else:  # "Failure"
            if attempt < max_attempts - 1:
                # Adjust code based on submission feedback
                self.resolve_with_submission_feedback()
            else:
                return False  # Give up after 3 attempts
else:
    # No client - just return success after tests pass
    return True
```

**Important Details:**
- **Hard limit of 3 attempts** - prevents infinite submission spam
- SubmissionAgent analyzes AoC response (status code, message, HTML)
- On failure, creates `submission_issues.md` with detailed analysis
- CodingAgent receives submission feedback via `submission_feedback=True` parameter
- Solution is re-tested after adjustments before next submission attempt
- Common failure modes detected: "too high", "too low", rate limiting, wrong format

## Advent of Code API Notes

### HTML Structure Patterns

**Unsolved puzzle:**
- 1 `<article>` element
- Contains puzzle description
- Form with answer input field

**Part 1 complete:**
- 2 `<article>` elements
- First contains part 1 description
- Paragraph: "Your puzzle answer was `<code>232</code>`."
- Paragraph: "The first half of this puzzle is complete! It provides one gold star: *"
- Second `<article>` contains part 2 description
- Form with answer input field

**Both parts complete:**
- 2 `<article>` elements
- Two "Your puzzle answer was" paragraphs
- Paragraph: "Both parts of this puzzle are complete! They provide two gold stars: **"
- No answer input form

### Rate Limiting

Advent of Code has rate limits:
- Be respectful with API calls
- Don't spam submissions
- The script naturally rate-limits by solving sequentially

### Session Cookie

- Valid for ~30 days
- Must be renewed when expired
- Tied to your AoC account
- Can be revoked from AoC settings

## Common Issues & Solutions

### "Session token not found"
- Check `.env` file exists
- Verify `AOC_SESSION` is set correctly
- Cookie may have expired - get a fresh one

### "ModuleNotFoundError"
- Run inside container: `make solve` or `make debug`
- Don't run `python src/main.py` directly on host

### "Puzzle not unlocked yet"
- Part 2 requires Part 1 completion
- Check status: script will show "🔒 Locked"

### Agent fails repeatedly
- Check workspace files for error messages
- Review `implementation_plan.md` and `critique.md`
- Try running in debug mode to see agent outputs

### Container mount issues (SELinux)
- The `:z` flag in volume mounts handles SELinux labeling
- If issues persist, check SELinux status: `getenforce`

## Future Improvements

### Potential Enhancements

1. **Parallel Processing**
   - Solve multiple days concurrently
   - Requires careful rate limiting

2. **Resume from Checkpoint**
   - If agent fails, resume from last step
   - Don't restart entire pipeline

3. **Better Error Recovery**
   - Save agent conversation history
   - Allow manual intervention
   - Retry failed submissions

4. **Performance Optimization**
   - Cache common patterns/solutions
   - Learn from previous days
   - Template common algorithms

5. **Testing Improvements**
   - Extract all examples from puzzle
   - Run comprehensive test suite
   - Benchmark performance

6. **Statistics & Analytics**
   - Track solve times
   - Success rates per agent
   - Common failure patterns

7. **Interactive Mode**
   - Prompt for confirmation before submission
   - Allow human hints to agents
   - Manual plan editing

## Architecture Decisions

### Why Separate Workspaces for Each Part?

**Pros:**
- Clean isolation prevents cross-contamination
- Part 2 can completely rethink approach
- Easy to compare both solutions
- Clearer debugging (no mixed artifacts)

**Cons:**
- Duplicates input file
- More disk space
- Can't easily share code between parts

**Decision**: Isolation is worth the duplication. Part 2 often requires significant changes.

### Why File-Based Agent Communication?

**Pros:**
- Simple, debuggable
- Can inspect intermediate steps
- Easy to resume/retry
- Language-agnostic

**Cons:**
- More I/O overhead
- Requires workspace management
- Not suitable for large data

**Decision**: Simplicity and debuggability outweigh performance concerns for this use case.

### Why Multiple Agents Instead of One?

**Pros:**
- Specialized prompts for each task
- Better prompt engineering
- Modular, testable components
- Can swap/improve individual agents

**Cons:**
- More complex orchestration
- Context loss between agents
- More API calls

**Decision**: Specialization produces better results than a monolithic agent.

## References

- [Advent of Code](https://adventofcode.com/)
- [Claude Code Documentation](https://docs.claude.com/claude-code)
- [Podman Documentation](https://docs.podman.io/)
- [advent-of-code-data](https://github.com/wimglenn/advent-of-code-data) - Python library that inspired completion detection logic

---

## Additional Resources

### Project Files

- **README.md**: High-level project overview and goals
- **COOKIE_EXTRACTION.md**: Comprehensive guide for extracting your AOC session cookie
- **flow_chart.png**: Visual diagram of the agent workflow pipeline
- **.env.example**: Template for setting up environment variables
- **.gitignore**: Ensures sensitive files (`.env`, `workspace/`) are not committed

### Development Notes

**Simple Agent (`src/agents/simple_agent.py`):**
This is a minimal test agent that can be used as a template for creating new agents. It's not part of the main solving pipeline but serves as an example of the BaseAgent interface.

**Agent Exports (`src/agents/__init__.py`):**
Uses dynamic imports to automatically export all agent classes from the agents package, making imports cleaner in the main module.

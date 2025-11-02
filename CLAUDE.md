# Advent of Claude Code - Development Reference

## Project Overview

This project uses AI agents powered by Claude Code to automatically solve Advent of Code puzzles. The system fetches puzzles, plans solutions, writes code, tests it, and submits answers - handling both Part 1 and Part 2 automatically.

## Architecture

### Multi-Agent System

The solver uses a pipeline of specialized agents, each with a specific role:

1. **TranslationAgent** (`src/agents/translation_agent.py`)
   - Converts the puzzle markdown into a structured problem description
   - Creates `problem.md` with clear problem statement

2. **PlanningAgent** (`src/agents/planning_agent.py`)
   - Reads the problem and creates an implementation plan
   - Creates `implementation_plan.md`
   - Can be run with feedback to revise plans

3. **CritiqueAgent** (`src/agents/critique_agent.py`)
   - Reviews the initial plan and provides critical feedback
   - Creates `critique.md` with suggestions for improvement

4. **CodingAgent** (`src/agents/coding_agent.py`)
   - Implements the solution based on the plan
   - Creates `solution.py`
   - Can be run with feedback to fix bugs

5. **TestingAgent** (`src/agents/testing_agent.py`)
   - Tests the solution against examples and real input
   - Creates `test_plan.md`
   - Returns "Success" or "Failure"
   - Creates `answer.txt` with the final answer

All agents inherit from `BaseAgent` (`src/agents/base_agent.py`) which provides:
- Workspace management
- File reading/writing utilities
- Claude Code CLI integration
- System prompt construction

### Workflow

```
1. Check completion status (both parts)
   ↓
2. For each incomplete part:
   ↓
3. Translation Agent → Creates problem.md
   ↓
4. Planning Agent → Creates implementation_plan.md
   ↓
5. Critique Agent → Creates critique.md
   ↓
6. Planning Agent (with feedback) → Updates plan
   ↓
7. Coding Agent → Creates solution.py
   ↓
8. Testing Agent → Tests solution
   ↓
9. If tests fail: Coding Agent (with feedback) → goto step 8
   ↓
10. If tests pass: Submit answer
   ↓
11. If Part 1 complete: Re-check status to unlock Part 2
   ↓
12. If Part 2 available: goto step 2
```

## File Structure

### Repository Layout

```
advent-of-claude-code/
├── src/
│   ├── main.py              # Entry point, orchestrates the workflow
│   ├── aoc_client.py        # Advent of Code API client
│   └── agents/
│       ├── __init__.py
│       ├── base_agent.py
│       ├── translation_agent.py
│       ├── planning_agent.py
│       ├── critique_agent.py
│       ├── coding_agent.py
│       └── testing_agent.py
├── workspace/               # Generated workspace (mounted volume)
│   └── <year>/
│       └── day_<day>/
│           ├── part_1/
│           │   ├── puzzle.md
│           │   ├── input.md
│           │   ├── problem.md
│           │   ├── implementation_plan.md
│           │   ├── critique.md
│           │   ├── solution.py
│           │   ├── test_plan.md
│           │   ├── implementation_summary.md
│           │   └── answer.txt
│           └── part_2/
│               └── (same structure)
├── .env                     # AOC_SESSION and CLAUDE_API_KEY
├── Containerfile            # Podman/Docker container definition
├── Makefile                 # Build, run, solve commands
├── requirements.txt         # Python dependencies
└── CLAUDE.md               # This file
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

Requires AOC session cookie from browser:
1. Log in to adventofcode.com
2. Open browser dev tools → Application/Storage → Cookies
3. Copy the `session` cookie value
4. Add to `.env`: `AOC_SESSION=<cookie_value>`

## Development Workflow

### Initial Setup

```bash
# Clone and navigate to repo
cd advent-of-claude-code

# Create .env file with credentials
cat > .env << EOF
AOC_SESSION=your_aoc_session_cookie_here
CLAUDE_API_KEY=your_claude_api_key_here
EOF

# Build the container
make build
```

### Solving Puzzles

```bash
# Solve a specific day (handles both parts automatically)
make solve YEAR=2015 DAY=1

# The script will:
# - Check which parts are complete
# - Skip completed parts
# - Solve incomplete parts
# - Automatically proceed from part 1 to part 2
```

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

## Container Management

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

### Multi-Part Handling

The main script (`src/main.py`) handles both parts intelligently:

1. **Check status before starting** - avoids redundant work
2. **Skip completed parts** - prints cached answers
3. **Auto-unlock part 2** - re-checks status after part 1 submission
4. **Isolated workspaces** - each part has its own directory

### Error Handling

- If part 1 fails: exits, doesn't attempt part 2
- If part 2 fails: exits, but part 1 remains complete
- If tests fail: enters feedback loop with CodingAgent (up to retry limit)
- If submission fails: error message displayed

### Agent Communication

Agents communicate via files in the workspace:
- Each agent reads specific input files
- Each agent writes specific output files
- Main orchestrator passes workspace path to agents
- Agents use BaseAgent utilities to read/write files

### Testing Loop

```python
while True:
    result = testing_agent.run_agent()
    if parse_test_result(result):  # "Success"
        return True
    else:  # "Failure"
        coding_agent.run_agent(feedback=True)
```

The testing agent must return exactly "Success" or "Failure" as the last line.

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

**Last Updated**: 2025-10-28
**Maintainer Notes**: Keep this document updated when making architectural changes or discovering new AoC behavior patterns.

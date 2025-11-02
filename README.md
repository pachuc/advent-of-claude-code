# Advent of Claude Code

## Overview

The idea is to fully automate solving advent of code problems via claude code. There should be no human in the loop.
We will construct a series of agents that will be run in a deterministic flow chart to produce the desired result
from the raw input/puzzle given by Advent of Code.

Stretch goal is to automate even the reterival of the text and entering of the input.

## Agents

1. Translation Agent: This agent will transform the whimsical problem description provided by Advent of Code into a formal problem definition.
2. Planning Agent: This agent will be in charge of developing a comprehensive plan, including a test plan, from the problem definition.
3. Planning Critique Agent: This agent will be in charge of critiquing the plan.
4. Coding Agent: This agent takes the plan and writes a python script to solve it.
5. Testing Agent: This agent tests the solution according to the test plan.


# Pacman Capture the Flag — Complete Guide

> Based on the UC Berkeley AI Projects framework (v1.002), adapted for the honors section.

---

## Table of Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [File Structure](#file-structure)
4. [Running a Game](#running-a-game)
5. [Command-Line Options](#command-line-options)
6. [Game Rules & Mechanics](#game-rules--mechanics)
7. [Writing Your Agent (`myTeam.py`)](#writing-your-agent-myteampy)
8. [CaptureAgent API Reference](#captureagent-api-reference)
9. [GameState API Reference](#gamestate-api-reference)
10. [Utility Classes (`util.py`)](#utility-classes-utilpy)
11. [Distance Calculator](#distance-calculator)
12. [Available Layouts](#available-layouts)
13. [Baseline Team Reference](#baseline-team-reference)
14. [Timing Constraints](#timing-constraints)
15. [Debugging Tips](#debugging-tips)

---

## Overview

This is a two-team, adversarial Pacman game. Red and blue teams each control **2 agents** on a symmetric maze. The left half belongs to red, the right half to blue.

- Agents on their **own side** are **ghosts** (defenders).
- Agents that **cross the center line** become **Pacmen** (attackers).
- Goal: eat the **opponent's food** and return it to your side before time runs out.
- The team that returns the most food — or leaves fewer than 2 food dots on the opponent's side — wins.

---

## Requirements

| Requirement | Version |
|-------------|---------|
| **Python**  | **3.x** (Python 2 is not supported — `importlib.machinery` and `print()` calls require Python 3) |
| `tkinter`   | Required for the GUI display (usually bundled with Python) |

No external packages (`pip install`) are needed. Everything runs from the standard library.

To check your Python version:
```bash
python3 --version
```

---

## File Structure

```
project-files-honors/
├── capture.py              # Main game runner and GameState definition
├── captureAgents.py        # CaptureAgent base class (your agents extend this)
├── myTeam.py               # YOUR FILE — implement your agents here
├── baselineTeam.py         # Provided reference team (OffensiveReflexAgent + DefensiveReflexAgent)
├── game.py                 # Core game engine (Agent, Directions, Actions, Grid, etc.)
├── util.py                 # Data structures (Stack, Queue, PriorityQueue, Counter, etc.)
├── distanceCalculator.py   # Maze distance precomputation (BFS-based)
├── layout.py               # Layout file parser
├── captureGraphicsDisplay.py  # GUI display
├── textDisplay.py          # Text/null display modes
├── graphicsDisplay.py      # General graphics utilities
├── graphicsUtils.py        # Low-level Tk drawing utilities
├── keyboardAgents.py       # Human keyboard-controlled agents
├── ghostAgents.py          # Simple ghost agent implementations
├── pacmanAgents.py         # Simple Pacman agent implementations
├── mazeGenerator.py        # Random maze generator
├── autograder.py           # Automated grading framework
├── distanceCalculator.py   # Shortest-path precomputation
└── layouts/                # Pre-built map files (.lay)
    ├── defaultCapture.lay
    ├── mediumCapture.lay
    ├── tinyCapture.lay
    └── ... (12 layouts total)
```

---

## Running a Game

All commands are run from inside the `project-files-honors/` directory.

### Default game (two baseline teams, GUI)
```bash
python3 capture.py
```

### Your team (blue) vs. baseline (red)
```bash
python3 capture.py -r baselineTeam -b myTeam
```

### Your team vs. itself
```bash
python3 capture.py -r myTeam -b myTeam
```

### Two-player interactive (you control agent 0)
```bash
python3 capture.py --keys0
```
- **P1 keys:** `a` / `s` / `d` / `w`
- **P2 keys:** `l` / `;` / `,` / `p`

### No graphics (quiet mode, faster)
```bash
python3 capture.py -r myTeam -b baselineTeam -q
```

### Run multiple games and report win rate
```bash
python3 capture.py -r myTeam -b baselineTeam -n 10 -q
```

### Use a specific layout
```bash
python3 capture.py -l mediumCapture
```

### Random layout
```bash
python3 capture.py -l RANDOM
# or with a fixed seed
python3 capture.py -l RANDOM42
```

### Replay a recorded game
```bash
python3 capture.py --replay replay-0
```

---

## Command-Line Options

| Flag | Long form | Description | Default |
|------|-----------|-------------|---------|
| `-r` | `--red` | Red team module (filename without `.py`) | `baselineTeam` |
| `-b` | `--blue` | Blue team module | `baselineTeam` |
| `--red-name` | | Display name for red team | `Red` |
| `--blue-name` | | Display name for blue team | `Blue` |
| `--redOpts` | | Extra args passed to red `createTeam` (e.g. `first=ClassName`) | `""` |
| `--blueOpts` | | Extra args passed to blue `createTeam` | `""` |
| `--keys0` | | Make agent 0 (first red) a keyboard agent | off |
| `--keys1` | | Make agent 1 (second red) a keyboard agent | off |
| `--keys2` | | Make agent 2 (first blue) a keyboard agent | off |
| `--keys3` | | Make agent 3 (second blue) a keyboard agent | off |
| `-l` | `--layout` | Layout file name or `RANDOM[seed]` | `defaultCapture` |
| `-t` | `--textgraphics` | Display as ASCII text | off |
| `-q` | `--quiet` | No graphics, minimal output | off |
| `-Q` | `--super-quiet` | No graphics, suppress agent output too | off |
| `-z` | `--zoom` | Zoom factor for GUI | `1` |
| `-i` | `--time` | Move limit per game | `1200` |
| `-n` | `--numGames` | Number of games to play | `1` |
| `-f` | `--fixRandomSeed` | Fix seed to `'cs188'` for reproducibility | off |
| `--record` | | Save game to `replay-N` file | off |
| `--replay` | | Replay a saved game file | — |
| `-x` | `--numTraining` | Number of silent training episodes | `0` |
| `-c` | `--catchExceptions` | Catch exceptions and enforce time limits | off |

---

## Game Rules & Mechanics

### Map structure
- The map is divided vertically. Red team starts on the **left half**, blue on the **right half**.
- There are **60 total food dots** split evenly across both halves.
- Power **capsules** (`o` in layout files) make the opposing team scared for **40 moves**.

### Winning conditions (checked in order)
1. A team **returns ≥ 28 food dots** (60 total ÷ 2 − 2 minimum remaining) → that team wins immediately.
2. After **1200 moves** (default), the team with the **higher score wins**. Ties are possible.

### Scoring
- Score is tracked as: `red_returned − blue_returned`.
- Positive score = Red winning; negative = Blue winning.
- Food is only scored when the Pacman **crosses back to its own side** while carrying dots.
- If a Pacman is eaten while carrying food, those dots are **dropped back** in place (near where the Pacman died).

### Observation (partial visibility)
- Agents can **see exactly** any agent within **Manhattan distance ≤ 5**.
- Agents beyond sight range return `None` for their position.
- `getAgentDistances()` returns noisy distance estimates to all agents (with ±6 noise range).

### Death & respawn
- When a Pacman is caught by a non-scared ghost, it respawns at its starting position and drops all carried food.
- When a Pacman eats a scared ghost, the ghost respawns at its starting position.

### Timing
| Phase | Limit |
|-------|-------|
| `registerInitialState` | 15 seconds |
| Each `chooseAction` call | 1 second warning, 3 second hard timeout |
| Per-agent total game time | 900 seconds |
| Max warnings before forfeit | 2 |

---

## Writing Your Agent (`myTeam.py`)

This is the only file you should edit. It must export a `createTeam` function.

### Minimal skeleton

```python
from captureAgents import CaptureAgent
import random
from game import Directions

def createTeam(firstIndex, secondIndex, isRed,
               first='MyAgent', second='MyAgent'):
    """
    Returns a list of two agents for this team.

    firstIndex / secondIndex : integer agent indices assigned by the game
    isRed                    : True if this team is red
    first / second           : class names to instantiate (can be overridden
                               from the command line via --redOpts first=ClassName)
    """
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


class MyAgent(CaptureAgent):

    def registerInitialState(self, gameState):
        """
        Called once at game start. Runs for at most 15 seconds.
        Always call the parent implementation first.
        """
        CaptureAgent.registerInitialState(self, gameState)
        # Custom setup — store your start position, precompute paths, etc.
        self.start = gameState.getAgentPosition(self.index)

    def chooseAction(self, gameState):
        """
        Called every turn. Must return a legal action within ~1 second.
        Legal actions: Directions.NORTH, SOUTH, EAST, WEST, STOP
        """
        actions = gameState.getLegalActions(self.index)
        return random.choice(actions)
```

### Two-agent team with different roles

```python
def createTeam(firstIndex, secondIndex, isRed,
               first='Attacker', second='Defender'):
    return [Attacker(firstIndex), Defender(secondIndex)]

class Attacker(CaptureAgent):
    def chooseAction(self, gameState):
        # go eat opponent food
        ...

class Defender(CaptureAgent):
    def chooseAction(self, gameState):
        # protect own food
        ...
```

---

## CaptureAgent API Reference

Defined in `captureAgents.py`. Subclass this for all your agents.

### Constructor

```python
CaptureAgent(index, timeForComputing=0.1)
```

### Instance variables (available after `registerInitialState`)

| Variable | Type | Description |
|----------|------|-------------|
| `self.index` | `int` | This agent's index in the game |
| `self.red` | `bool` | `True` if on the red team |
| `self.agentsOnTeam` | `list[int]` | Indices of your teammates |
| `self.distancer` | `Distancer` | Maze distance calculator |
| `self.observationHistory` | `list[GameState]` | All game states seen so far |
| `self.display` | display object | Access to graphics (for `debugDraw`) |

### Methods to override

#### `registerInitialState(self, gameState)`
Called once at the start. Call `CaptureAgent.registerInitialState(self, gameState)` first to initialize `self.distancer` and `self.red`.

#### `chooseAction(self, gameState) → str`
**The main method to implement.** Return one of:
- `Directions.NORTH`
- `Directions.SOUTH`
- `Directions.EAST`
- `Directions.WEST`
- `Directions.STOP`

### Convenience methods

```python
# Food
self.getFood(gameState)                 # Grid of opponent's food (you eat this)
self.getFoodYouAreDefending(gameState)  # Grid of your own food (you protect this)

# Capsules
self.getCapsules(gameState)                 # List of opponent's capsule positions
self.getCapsulesYouAreDefending(gameState)  # List of your capsule positions

# Teams
self.getTeam(gameState)       # List of your agent indices
self.getOpponents(gameState)  # List of opponent agent indices

# Score (positive = your team is winning)
self.getScore(gameState)

# Distances (maze distance via BFS, falls back to Manhattan if not precomputed)
self.getMazeDistance(pos1, pos2)   # pos is a tuple (x, y)

# History
self.getPreviousObservation()    # GameState from last turn (or None)
self.getCurrentObservation()     # GameState from this turn

# Debug drawing (GUI only)
self.debugDraw(cells, color, clear=False)
# cells: (x,y) or list of (x,y); color: [r, g, b] floats 0-1
self.debugClear()
```

---

## GameState API Reference

The `gameState` object passed to `chooseAction` and `registerInitialState`.

### Agent state

```python
gameState.getLegalActions(agentIndex)
# Returns list of legal action strings for the given agent

gameState.getAgentState(index)
# Returns AgentState object with:
#   .isPacman         → bool, True if agent is on opponent's side
#   .getPosition()    → (x, y) tuple or None if not observable
#   .numCarrying      → int, food dots currently being carried
#   .numReturned      → int, food dots successfully returned this game
#   .scaredTimer      → int, turns remaining scared (0 = not scared)
#   .configuration.direction → current facing direction

gameState.getAgentPosition(index)
# (x, y) tuple if visible, None otherwise

gameState.getNumAgents()
# Total number of agents (4 in standard game)

gameState.getInitialAgentPosition(agentIndex)
# (x, y) spawn position for an agent
```

### Food and map

```python
gameState.getRedFood()   # Grid object; m[x][y] = True if red food at (x,y)
gameState.getBlueFood()  # Grid object for blue food

gameState.getRedCapsules()   # List of (x, y) tuples
gameState.getBlueCapsules()

gameState.getWalls()       # Grid object; m[x][y] = True if wall
gameState.hasFood(x, y)    # bool
gameState.hasWall(x, y)    # bool

# Grid objects have:
#   .asList()       → list of (x, y) positions where value is True
#   .count()        → number of True cells
#   m[x][y]         → direct access
```

### Scores and teams

```python
gameState.getScore()                # int, positive = red winning
gameState.isOver()                  # bool
gameState.isOnRedTeam(agentIndex)   # bool
gameState.getRedTeamIndices()       # e.g. [0, 2]
gameState.getBlueTeamIndices()      # e.g. [1, 3]
gameState.getAgentDistances()       # List of noisy distances to each agent
```

### State transitions (for lookahead / simulation)

```python
successor = gameState.generateSuccessor(agentIndex, action)
# Returns a new GameState after the agent takes the action.
# Use this for minimax, expectimax, MCTS, etc.
```

---

## Utility Classes (`util.py`)

### Data structures

```python
from util import Stack, Queue, PriorityQueue, PriorityQueueWithFunction

s = Stack()
s.push(item)
s.pop()
s.isEmpty()

q = Queue()
q.push(item)
q.pop()
q.isEmpty()

pq = PriorityQueue()
pq.push(item, priority)   # lower priority = higher precedence
pq.pop()
pq.isEmpty()

pqf = PriorityQueueWithFunction(fn)  # fn(item) -> priority
pqf.push(item)
pqf.pop()
```

### Counter (weighted dictionary)

```python
from util import Counter

c = Counter()
c['key'] += 1          # defaults to 0 for unseen keys
c.totalCount()         # sum of all values
c.argMax()             # key with highest value
c.normalize()          # scale values to sum to 1.0
c.incrementAll(keys, count)
c1 * c2                # dot product
c1 + c2                # element-wise addition
c1 - c2                # element-wise subtraction
```

### Distance and sampling

```python
from util import manhattanDistance, nearestPoint, flipCoin

manhattanDistance((x1,y1), (x2,y2))  # |x1-x2| + |y1-y2|
nearestPoint((x, y))                  # rounds to nearest integer grid point
flipCoin(p)                           # True with probability p
```

---

## Distance Calculator

Precomputes all-pairs BFS distances across the maze. Initialized automatically by `CaptureAgent.registerInitialState`.

```python
# After registerInitialState runs:
self.distancer.getMazeDistances()           # precompute (called for you)
self.distancer.getDistance(pos1, pos2)      # returns exact maze distance

# Convenience wrapper on CaptureAgent:
self.getMazeDistance(pos1, pos2)
```

To skip precomputation and use Manhattan distance instead, remove the `self.distancer.getMazeDistances()` call in `registerInitialState`.

---

## Available Layouts

All layout files are in `layouts/`. Pass the name without `.lay` to `-l`.

| Layout | Description |
|--------|-------------|
| `defaultCapture` | Standard 32×16 symmetric maze |
| `tinyCapture` | Very small map, good for quick testing |
| `mediumCapture` | Medium-sized open map |
| `fastCapture` | Narrow corridors, fast games |
| `officeCapture` | Office-style grid |
| `bloxCapture` | Block-based layout |
| `alleyCapture` | Long alleys |
| `crowdedCapture` | Dense food, crowded |
| `distantCapture` | Teams start far apart |
| `jumboCapture` | Large map |
| `strategicCapture` | Strategically interesting choke points |
| `testCapture` | Minimal test map |

### Layout file format

```
%  = wall
   = empty space (walkable)
.  = food dot
o  = power capsule (scared timer)
1  = red agent 1 start
2  = red agent 2 start  (note: agent numbers differ — see indices)
3  = blue agent 1 start
4  = blue agent 2 start
```

---

## Baseline Team Reference

`baselineTeam.py` provides two agent classes you can study or inherit from.

### `OffensiveReflexAgent`
- Moves toward the nearest food dot on the opponent's side.
- Features: `successorScore` (number of remaining food, negated), `distanceToFood`.
- Weights: `successorScore=100`, `distanceToFood=-1`.

### `DefensiveReflexAgent`
- Stays on its own side and chases invaders.
- Features: `onDefense` (1 if ghost, 0 if Pacman), `numInvaders`, `invaderDistance`, `stop`, `reverse`.
- Weights: `numInvaders=-1000`, `onDefense=100`, `invaderDistance=-10`, `stop=-100`, `reverse=-2`.

### `ReflexCaptureAgent` (base class for both)

Key methods:

```python
def getSuccessor(self, gameState, action):
    """Returns successor GameState, advancing one full grid step."""

def evaluate(self, gameState, action):
    """Returns features * weights (dot product)."""

def getFeatures(self, gameState, action):
    """Returns a Counter of feature_name -> value."""

def getWeights(self, gameState, action):
    """Returns a dict or Counter of feature_name -> weight."""
```

---

## Timing Constraints

Your `registerInitialState` can run for up to **15 seconds** — use this for maze distance precomputation, policy initialization, or learning.

Your `chooseAction` must complete in under **1 second** (soft limit). After **3 seconds** the agent is disqualified for that move and a random action is chosen. After **2 timing violations**, the team forfeits.

```python
def chooseAction(self, gameState):
    # If you're doing lookahead (minimax/MCTS), bound your search depth
    # to ensure you return within the time limit.
    import time
    start = time.time()
    # ... search ...
    if time.time() - start > 0.9:
        break  # stop early
    return best_action
```

---

## Debugging Tips

### Draw on the display

```python
def chooseAction(self, gameState):
    # Highlight food positions in green
    foodList = self.getFood(gameState).asList()
    self.debugDraw(foodList, [0, 1, 0])

    # Highlight a single cell in red
    self.debugDraw((5, 3), [1, 0, 0], clear=True)
```

### Print agent info

```python
def chooseAction(self, gameState):
    myState = gameState.getAgentState(self.index)
    myPos   = myState.getPosition()
    print(f"Agent {self.index} at {myPos}, carrying {myState.numCarrying} food")
    print(f"Score: {self.getScore(gameState)}")
```

### Run without graphics for speed

```bash
python3 capture.py -r myTeam -b baselineTeam -q -n 20
```

### Fix the random seed for reproducibility

```bash
python3 capture.py -r myTeam -b baselineTeam -f
```

### Record and replay

```bash
# Record
python3 capture.py -r myTeam -b baselineTeam --record

# Replay (file named replay-0)
python3 capture.py --replay replay-0
```

# Hybrid Capture Agent: Architecture & Training Pipeline

This document explains the inner workings of our Pacman CTF agent (`myTeam.py`) and the offline parameter training system we developed to optimize it.

## 1. Agent Architecture (`myTeam.py`)

Our agent (`HybridCaptureAgent`) is a state-of-the-art hybrid system that combines **heuristic planning** (A* search) with **probabilistic belief tracking** and **dynamic role assignment**. It does not use deep learning at runtime; instead, it uses a finely-tuned set of numerical coefficients (stored in the `PARAMS` dictionary) to evaluate game states and actions.

### Core Components

1. **Shared Memory (`self.shared`)**
   Since agents are instantiated independently, we use a shared class-level dictionary to persist memory across turns and between teammates. This allows both of our agents to share their radar observations, coordinate who is attacking/defending, and prevent duplicate calculations (like dead-end depth mapping).

2. **Probabilistic Belief Tracking (`ParticleFilter`)**
   Enemies are often hidden in the fog of war. We maintain a probability distribution of where each enemy is likely to be:
   - Every turn, we update the belief distribution based on whether the enemy was visible, noisy distance readings, and valid maze transitions.
   - If an enemy eats food or a capsule, we snap the belief to that exact location.
   - This belief state drives risk assessment: we avoid moving into spaces with a high probability of holding an enemy ghost.

3. **Dynamic Role Assignment (`assignRoles`)**
   Agents are not strictly "Offense" or "Defense". Roles switch dynamically based on the game state (score, time left, invaders present).
   - **Attack**: Pushes into enemy territory to eat food.
   - **Retreat**: Triggered when carrying too much food, time is running low, or a threat is too close. The agent routes back to the nearest safe border.
   - **Intercept/Patrol (Defense)**: Triggered when an enemy invader is detected in our territory. The closest agent is assigned to intercept them using a pressure-based heuristic.

4. **Action Evaluation & A* Search (`scoreActions` & `weightedAStar`)**
   Rather than evaluating every possible future path (which takes too long), we use a weighted A* search to find a path to a specific high-value target (like a safe border or a cluster of food).
   - Once a path is found, the *immediate next action* is scored.
   - The action's score is penalized by factors such as `positionRisk` (how close it gets us to danger) and `dead_end_depth` (avoiding getting trapped).
   - **Tactical Search**: If an enemy is within 5 tiles, we run a short minimax-style lookahead to evaluate how the enemy could respond, helping us juke out of tight spots.

---

## 2. The Training Pipeline

Because `myTeam.py` relies heavily on heuristics, its performance depends entirely on its numerical coefficients (e.g., *How much should we penalize walking into a dead end?* or *How much risk is acceptable when carrying 5 food?*). 

To avoid guessing these numbers, we built an **offline data collection and optimization pipeline**.

### Centralized `PARAMS` Dictionary
All magic numbers in `myTeam.py` have been extracted into a single dictionary called `PARAMS`. This dictionary controls everything from A* heuristic weights to food scoring multipliers.

### Step 1: Data Collection (`collect_data.py`)
To train the agent, we need data. When you run `collect_data.py`:
1. It plays dozens of headless (no-UI) games against a baseline opponent.
2. It sets a special environment variable `PACMAN_LOG=1`.
3. `myTeam.py` detects this variable and triggers its `_logTurnData` method.
4. Every single turn, the agent logs its **State Features** (e.g., `carrying`, `homeDist`, `positionRisk`) and the **Action** it chose into a JSONL file.
5. After the games finish, `collect_data.py` looks into the *future* of those logs to label each turn with outcomes (e.g., *Did the agent die within 10 turns?* *How much score was gained?*). It outputs a flattened file: `training_data.csv`.

### Step 2: Weight Optimization (`train_weights.py`)
Instead of heavy neural networks, we use **Ridge Regression** to find the optimal `PARAMS` values.
1. The script loads `training_data.csv`.
2. It splits the data by the agent's mode (e.g., `attack`, `retreat`).
3. It performs a linear regression mapping the **State Features** to the **Future Outcomes** (e.g., *score delta* or *death*).
   *Example: The regression might discover that when `positionRisk` is high, `died_within_k` spikes heavily.*
4. The script extracts the learned weights from the regression and uses them to **automatically adjust the `PARAMS` dictionary** (e.g., making the `attack_risk_penalty` harsher).
5. It rewrites `myTeam.py` with the newly updated `PARAMS`.

### The Training Loop Workflow
To continuously improve the agent:
1. Run `python3 collect_data.py --games 50 --opponent baselineTeam` to generate a dataset.
2. Run `python3 train_weights.py` to calculate new optimal parameters and inject them into `myTeam.py`.
3. Run a benchmark tournament to see if the win rate improved!

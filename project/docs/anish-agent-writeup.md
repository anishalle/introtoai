# Anish Capture-the-Flag Agent Writeup

This document describes the current `myTeam.py` agent in this repository in implementation-level detail. It is meant to be a durable engineering writeup rather than a short contest summary.

The current agent is a shared-memory, dynamic-role, risk-aware weighted-A* capture team with shallow local adversarial search. It is tuned for the exact engine in this repository, not for a generic Berkeley contest description copied from the web.

## 1. Engine Model and Contest Assumptions

The agent is built for the rules implemented by this local `capture.py`, not for older contest mirrors.

### 1.1 Scoring model

- Food is not permanently scored when first eaten.
- Food is carried as `numCarrying`.
- Points are awarded when the agent returns home and increments `numReturned`.
- Carried food can be dropped if the agent dies.
- End-of-game messaging uses `state.data.score` and `numReturned`, not a pure “eat immediately for points” model.

Relevant engine code:

- `timeleft` decrements once per action: `capture.py:122`
- game length is total actions, not rounds: `capture.py:375-388`
- winner is determined by score / returned food status: `capture.py:391-414`

### 1.2 Move budget

- The engine uses `game.length` as total plies across all four agents.
- `150` moves per agent means `600` total actions.
- The correct command-line setting for a real contest-length game is `-i 600`.

### 1.3 Timing model

- `15s` startup per agent in `registerInitialState`
- `1s` move warning threshold
- `3s` hard move timeout
- third time warning loses the game

Relevant engine code:

- startup: `capture.py:435-436`
- warning: `capture.py:438-439`
- timeout: `capture.py:441-442`
- max warnings: `capture.py:444-445`

### 1.4 Observability model in this repo

- Enemies are visible only when the engine returns an actual position.
- The local code path does not expose the classic noisy-distance contest model in a way that materially drives action selection here.
- The implemented belief tracker therefore uses side constraints, visibility exclusion, and event anchoring rather than a full distance-probability sonar update.

### 1.5 Practical implication

This environment rewards low-variance food banking, fast visible-threat reaction, and cheap decision-making. It punishes over-planning, deep global adversarial search, and policy logic that assumes longer games than `150` moves per agent.

## 2. High-Level Architecture

The current team has five major layers:

1. Shared map analysis at startup
2. Shared opponent belief tracking during play
3. Dynamic role assignment each turn
4. Weighted A* planning to a macro target
5. Shallow tactical adversarial tie-breaking when enemies are close and visible

At a high level, each turn does:

1. Update shared state
2. Assign a mode: `attack`, `retreat`, `intercept`, or `patrol`
3. Choose a target for that mode
4. Plan a path to the target with weighted A*
5. Score legal actions against the plan and the current situation
6. If a local fight is happening, rescore top actions with a shallow adversarial reply model
7. Pick the best-scoring action, breaking remaining ties deterministically

## 3. Shared Team Memory

`TEAM_MEMORY` is keyed by:

- side color (`self.red`)
- sorted team indices
- layout wall hash

This avoids belief/state leakage across different teams or layouts and lets both agents read and write the same team context.

### 3.1 Shared fields

| Field | Meaning |
| --- | --- |
| `width`, `height` | layout dimensions |
| `neighbors` | precomputed legal grid neighbors per cell |
| `legal_positions` | all non-wall cells |
| `home_positions` | cells on our side |
| `enemy_positions` | cells on enemy side |
| `home_border` | valid return boundary cells |
| `home_distance` | maze distance from each cell to its best return border |
| `best_border` | nearest return border cell for each position |
| `patrol_points` | top defensive border positions |
| `dead_end_depth` | dead-end / corridor depth score per cell |
| `beliefs` | current belief distribution for each opponent |
| `enemy_pacman` | previous observed pacman/ghost state of each enemy |
| `recent_events` | missing defended food/capsule events with TTL |
| `agent_goals` | last chosen target for each teammate |
| `agent_goal_kinds` | target category for each teammate |
| `agent_modes` | current role for each teammate |
| `agent_paths` | current plan for each teammate |
| `agent_slots` | startup slot assignment |
| `agent_starts` | initial starting positions |
| `updates` | turn/update counter |
| `last_food_defending` | defended food from previous turn |
| `last_capsules_defending` | defended capsules from previous turn |
| `contest_length` | initial `timeleft` seen at startup |

## 4. Startup Map Analysis

The agent spends startup time precomputing geometry that should never be recomputed every move.

### 4.1 Border cells

The agent computes all legal home-border cells that have a legal enemy-adjacent partner cell. Those are the only meaningful “return home” crossing points.

### 4.2 Home distances

For every legal cell, the agent stores:

- nearest return border cell
- maze distance to that border cell

This is used everywhere:

- retreat thresholds
- offensive tempo scoring
- defensive interception
- late-game banking decisions

### 4.3 Patrol points

The agent ranks home-border cells by average maze distance to defended food and defended capsules, then keeps the best few as patrol candidates. This keeps defense centered on high-value frontier access points rather than wandering the whole border uniformly.

### 4.4 Dead-end depth

The agent computes corridor/dead-end depth by peeling degree-1 cells inward. This produces a cheap static trap metric for:

- offensive food filtering
- path penalties
- retreat path evaluation

## 5. Belief Tracking

The belief tracker is intentionally lightweight and deterministic enough to fit the move budget.

### 5.1 Visible update

If an enemy is visible:

- collapse that enemy’s belief distribution to a point mass at the visible position

### 5.2 Transition update

If an enemy moved last turn and is not currently visible:

- propagate each probability mass equally over `{stay} U legal neighbors`

This is a simple mobility model with no learned opponent policy.

### 5.3 Side filtering

Beliefs are filtered by the enemy’s current pacman/ghost status:

- enemy pacman belief support is limited to our side
- enemy ghost belief support is limited to their side

### 5.4 Visibility exclusion

Any believed location within `5` Manhattan distance of a teammate is removed, because if the enemy were there, we would expect to see it.

### 5.5 Carry-home reset heuristic

If the enemy was previously a pacman and is now a ghost, the belief resets to the enemy’s initial position. In practice this is a cheap proxy for “invader got home or died and is no longer an invading pacman.”

### 5.6 Event anchoring

When defended food disappears:

- add a `food` event with TTL `8`

When a defended capsule disappears:

- add a `capsule` event with TTL `12`

For pacman beliefs:

- exact event position gets `+4.0`
- neighboring positions get `+1.0`

This is what lets defense move with purpose even when invaders are not visible.

### 5.7 Fallback belief

If filtering and anchoring wipe out all mass:

- seed a uniform belief over legal side-consistent positions outside teammate sight range

## 6. Dynamic Role Assignment

The agent does not have a fixed “offense agent” and “defense agent.” It reassigns roles every turn.

### 6.1 Modes

- `attack`
- `retreat`
- `intercept`
- `patrol`

### 6.2 Threat target

Before assigning roles, the team finds a `primaryThreatTarget`:

- closest visible invader to home by `home_distance`
- otherwise the strongest inferred invader belief if confidence is at least `0.2`
- otherwise the highest-TTL recent event

This feeds the “closest defender goes now” rule.

### 6.3 Defender count policy

`needDefenders` is set as follows:

- if invaders exist: `1`
- if multiple invaders or we are ahead late: `2`
- else if recent defensive events and not opening: `1`
- else if late phase and up by at least `2` and not in a scared-offense window: `1`
- else if up by at least `5` with `<= 35` own moves left: `2`

Then it is relaxed:

- opening phase with no threat: `0`
- when behind by at least `2` and no threat: `0`
- if enemy scared window is at least `8`, score < `6`, and no invaders: `0`

### 6.4 Closest-defender commitment

If a threat target exists and defenders are needed:

- the closest/lowest-priority defender by `defensePriority` is forcibly included

This is one of the most important improvements over the earlier `anish` version.

### 6.5 Defense priority formula

For an agent:

`priority = 4 * numCarrying + 12 * isPacman + homeDist + targetDist - slotBonus`

where:

- `slotBonus = 2` if the agent is slot `1`, else `0`
- `targetDist` is distance to visible invader, else threat target, else nearest recent event

Lower priority is better for becoming the defender.

### 6.6 Opening and late-phase scheduling

- opening phase begins while `ownMovesLeft >= totalOwnMoves - 28`
- late phase begins while `ownMovesLeft <= max(25, 0.25 * totalOwnMoves)`

This is intentionally short-horizon. For a `150`-move-per-agent game, the opening is only the first `28` own moves, not half the game.

## 7. Retreat Logic

The retreat system is designed for carry-home scoring and short games.

### 7.1 Hard retreat triggers

Immediate retreat if:

- `ownMovesLeft <= homeDist + 2`
- `foodLeft <= 2`

### 7.2 Carry threshold

Base threshold:

- `5` in opening phase
- `4` otherwise

Threshold adjustments:

- `-1` if `ownMovesLeft <= 60`
- `-1` if `ownMovesLeft <= 35`
- `-1` if score `>= 4`
- `+1` if score `<= -4` and enemy scared window `< 6`
- `-1` if `homeDist >= 7`
- `-2` if visible threat distance `<= 5`
- `+1` if enemy scared window `>= 8` and no visible threat
- final threshold is clamped to at least `2`

Retreat if:

- `carrying >= threshold`
- `carrying >= 5`
- `carrying >= 3 and homeDist >= 7`
- visible threat distance `<= 4`
- `carrying >= 1 and ownMovesLeft <= homeDist + 6`
- `carrying >= 2 and ownMovesLeft <= 2 * homeDist + 2`
- `carrying >= 2 and homeDist >= 6 and visibleThreatDist <= 6`

This policy is much more aggressive about banking small gains than the longer-horizon versions of the agent were.

## 8. Target Selection

The agent picks a macro target first, then plans to it.

### 8.1 Retreat target

Among border cells, choose the one minimizing:

`distance(myPos, border) + 2.0 * positionRisk(border)`

### 8.2 Intercept target

Candidate generation:

- visible invader position
- visible invader exit border
- top inferred invader belief position
- inferred invader exit border
- recent event positions as fallback

Candidate scoring:

- `score = distance + pressure`
- `pressure = -6` for visible target
- `pressure = -4` for belief target
- `pressure = -2` for exit target
- if we are scared and the target is visible: add `4`

Lowest score wins.

### 8.3 Patrol target

Primary patrol rule:

- choose frontier defended food near the lane assigned to this agent
- frontier means closest to the border direction, then closest to current agent position

Fallback patrol rule:

- choose among precomputed patrol points using:
`distance - borderPressure + teammateCrowdingPenalty`

### 8.4 Attack target

This is the most tuned subsystem.

#### Lane split

Each agent gets a preferred upper or lower lane based on startup Y ordering. If there are at least `3` foods in the preferred lane, the agent restricts target candidates to that lane.

#### Capsule logic

Capsules are considered only when:

- capsule distance `<= 4`, or
- visible ghost threat distance `<= 5`

Capsule value:

`18 - 2.2 * distance - 3.0 * positionRisk(capsule)`

Adjustments:

- `+10` if visible threat distance `<= 5`
- `-6` if teammate goal is within maze distance `2`

#### Opening frontier food rule

During opening phase, if there are candidate foods with:

- `home_distance <= 4`
- `dead_end_depth <= 2`

then choose the food minimizing:

`distance + 0.6 * home_distance`

This is a deliberate “grab shallow, bank early, build tempo” rule.

#### General food value formula

For each candidate pellet:

- `distance = mazeDistance(myPos, pellet)`
- `homeDist = home_distance[pellet]`
- `depth = dead_end_depth[pellet]`
- `tripCost = distance + homeDist`

Components:

- `riskPenalty = 5.0 * positionRisk(pellet)`
- `depthPenalty = 1.2 * depth` if scared window `< 4`, else `0.4 * depth`
- `lanePenalty = 4.5` in opening or `2.0` later if the food is off-lane while enough on-lane food exists
- `shallowBonus = max(0, 5 - homeDist)`
- `tempoBonus = max(0, 12 - tripCost)` in opening, else `max(0, 9 - tripCost)`

Tempo penalties:

- `+12.0` if `tripCost > ownMovesLeft - 4`
- `+3.0` if `homeDist >= 8` and scared window `< 6`
- `+6.0` if a visible ghost can race to a deep pellet roughly as fast or faster and `depth >= 2`

Overall food value:

`value = shallowBonus + 1.5 * tempoBonus - 1.8 * distance - 0.9 * homeDist - riskPenalty - depthPenalty - lanePenalty - tempoPenalty`

Additional adjustments:

- `-0.6 * carrying * homeDist` if carrying food
- `-4` if visible threat distance `<= 4`
- `-8` if visible threat distance `<= 6` and depth `>= 2`
- `-5` if teammate goal is within maze distance `3`
- `+0.5` if this agent is slot `0`

The target with highest value wins.

## 9. Weighted A* Planner

The planner is intentionally bounded.

### 9.1 Search budget

- maximum `300` expansions

### 9.2 Heuristic

- standard maze distance to the closest goal
- heuristic weight `1.15`

### 9.3 Transition cost

`stepCost = 1.0 + pathCellPenalty(nextPos, mode)`

### 9.4 Path cell penalty

For `attack` and `retreat`:

- `+4.5 * positionRisk(pos)`
- `+0.2 * dead_end_depth` if on enemy side
- extra `+0.25 * dead_end_depth` in `retreat` mode

For `intercept` and `patrol`:

- `+1.5 * positionRisk(pos)`

Coordination penalty:

- `+2.5` if the next cell equals the teammate’s current goal

## 10. Immediate Action Scoring

The planner gives a path, but the agent still scores every legal action before choosing.

Base terms for every action:

- `+18.0 * gameScore(successor)`
- `-distance(nextPos, target)` if a target exists
- `+4.0` if action matches the first planned A* step
- `-6.0` for `STOP`
- `-1.5` for reverse

### 10.1 Attack mode action terms

- `+14.0` per food eaten this move
- `+18.0` per food returned this move
- `-10.0 * positionRisk(nextPos)`
- `-0.7 * dead_end_depth(nextPos)` on enemy side
- `-0.7 * currentCarrying * home_distance(nextPos)` if carrying
- `+1.5` in opening phase if action stays in preferred lane

### 10.2 Retreat mode action terms

- `-2.5 * home_distance(nextPos)`
- `-12.0 * positionRisk(nextPos)`
- `+24.0` per food returned this move

### 10.3 Intercept / patrol action terms

- `-3.0 * distance(nextPos, closestInvader)` if an invader target exists
- `+4.0` if we stay a ghost on defense
- `-10.0` if we become a pacman while trying to defend
- `-10.0` extra if we are scared and step into immediate contact range with an invader

## 11. Tactical Search

This is not the global controller. It is a local tie-breaker.

### 11.1 When it activates

Only in modes:

- `attack`
- `retreat`
- `intercept`

and only if a visible enemy is within maze distance `5`.

### 11.2 Candidate set

- only the top `4` actions from the immediate scoring layer are rescored

### 11.3 Adversarial model

For the closest visible enemy:

1. simulate our candidate action
2. enumerate all enemy replies
3. evaluate each reply state
4. take the minimum reply value
5. blend:

`rescored = 0.7 * baseScore + 0.3 * minEnemyReplyValue`

### 11.4 Tactical state value

Base:

- `+20.0 * score`
- `-7.0 * positionRisk(myPos)`

If in `attack` or `retreat`:

- `-1.5 * home_distance(myPos) * max(1, numCarrying)`

If in defense:

- `-2.5 * distance(myPos, closestInvader)` if an invader exists

If a target exists:

- `-0.4 * distance(myPos, target)`

This is intentionally shallow and cheap.

## 12. Risk Model

The current risk model heavily trusts visible ghosts and only lightly trusts invisible ones.

### 12.1 Visible ghost contributions

For each visible enemy ghost:

- `+3.5` if distance `<= 1`
- `+2.0` if distance `<= 2`
- `+0.8` if distance `<= 4`

### 12.2 Invisible ghost contributions

For each invisible enemy ghost:

- use only the top belief position
- ignore it entirely if peak belief probability `< 0.2`
- contribute:
  - `+2.0 * p` if distance `<= 1`
  - `+1.0 * p` if distance `<= 2`
  - `+0.4 * p` if distance `<= 4`

This was a critical short-horizon fix. Earlier variants were too afraid of diffuse invisible-ghost beliefs and therefore played too cautiously on offense.

## 13. Short-Horizon Design Decisions

The current version is optimized for `150` moves per agent. That pushed several strategic choices:

- early offense matters more than in long games
- shallow, bankable food is much more valuable than deep food clusters
- carrying `2` to `4` food is often enough reason to bank
- broad, speculative defense is often a mistake
- capsules should be opportunistic, not a standing macro-objective
- local fights matter, but only in small windows

The resulting style is:

- short opening with dual tempo pressure
- strong lane split to avoid teammate duplication
- one fast defender when a home threat appears
- low-variance retreat thresholds
- no heavyweight global minimax, MCTS, RL rollout, or planner loop in the per-turn critical path

## 14. Public-Agent Audit and What We Borrowed

The biggest practical lessons came from the strongest short-horizon public teams.

### 14.1 From `uripont`

Useful ideas:

- closest defender commits immediately to home threats
- lane splitting is important
- nearest safe food is often better than global food-value elegance
- capsules should be opportunistic

What we used:

- explicit primary threat target
- visible-threat-first logic
- stronger frontier defense
- simpler opening offense

### 14.2 From `LuChenyang3842`

Useful ideas:

- safe-vs-danger food classification
- bank early under a carry-home model
- A* is enough if target choice is good

What we used:

- stronger shallow-food preference
- earlier banking thresholds
- less emphasis on large food-cluster plans

### 14.3 From `vincent916735`

Useful ideas:

- tunnel / corridor awareness matters
- dead-end handling is more important than fancy search

What we used:

- dead-end depth penalties in target choice and path planning

### 14.4 What we deliberately did not copy as the global controller

- deep global minimax
- heavy per-turn MCTS
- PDDL/planner-first control loops
- approximate-Q as the main decision layer

Those approaches are too expensive or too brittle for the local `1s` warning budget and `150`-move-per-agent horizon.

## 15. Exact Behavioral Parameters

This section lists the main numeric knobs in one place.

### 15.1 Event TTLs

- missing defended food TTL: `8`
- missing defended capsule TTL: `12`

### 15.2 Belief anchoring

- exact event bonus: `+4.0`
- event-neighbor bonus: `+1.0`
- minimum invisible-belief confidence used in risk/threat logic: `0.2`

### 15.3 Role timing

- opening phase length: last `28` own moves from the start
- late phase threshold: `max(25, 25% of own total moves)`
- force two defenders if score `>= 5` and `ownMovesLeft <= 35`
- convert slot `1` from `attack` to `patrol` if score `>= 5`, `ownMovesLeft <= 30`, and no invaders

### 15.4 Retreat thresholds

- base carrying threshold: `5` opening, `4` otherwise
- threshold clamp minimum: `2`

### 15.5 Capsule scoring

- base capsule constant: `18`
- capsule distance coefficient: `-2.2`
- capsule risk coefficient: `-3.0`
- visible-threat capsule bonus: `+10`
- teammate overlap capsule penalty: `-6`

### 15.6 Food scoring

- food risk coefficient: `-5.0`
- food depth coefficient: `-1.2` or `-0.4` while enemies are scared
- opening off-lane penalty: `-4.5`
- later off-lane penalty: `-2.0`
- tempo coefficient: `+1.5`
- distance coefficient: `-1.8`
- home-distance coefficient: `-0.9`
- carrying/home penalty: `-0.6 * carrying * homeDist`
- visible-threat penalty: `-4`
- visible-threat deep-food penalty: `-8`
- teammate overlap food penalty: `-5`
- slot-0 tie bonus: `+0.5`

### 15.7 Weighted A*

- expansion cap: `300`
- heuristic weight: `1.15`
- attack/retreat risk multiplier: `4.5`
- defense risk multiplier: `1.5`
- enemy-side dead-end penalty: `0.2`
- extra retreat dead-end penalty: `0.25`
- teammate-goal occupancy penalty: `2.5`

### 15.8 Action scoring

- score multiplier: `18.0`
- planned action bonus: `4.0`
- stop penalty: `-6.0`
- reverse penalty: `-1.5`
- food eaten bonus: `+14.0`
- food returned bonus in attack: `+18.0`
- position risk penalty in attack: `-10.0`
- dead-end penalty in attack: `-0.7`
- carrying-home-distance penalty in attack: `-0.7 * carrying * homeDist`
- preferred-lane opening bonus: `+1.5`
- retreat home-distance coefficient: `-2.5`
- retreat risk coefficient: `-12.0`
- retreat return bonus: `+24.0`
- defense invader chase coefficient: `-3.0`
- defense “stay ghost” bonus: `+4.0`
- defense “accidentally become pacman” penalty: `-10.0`

### 15.9 Tactical search

- activation radius: `5`
- top candidates rescored: `4`
- blend weights: `0.7` base score, `0.3` worst enemy reply

## 16. Current Benchmark Summary

The current version was evaluated on:

- layouts: `defaultCapture`, `strategicCapture`, `fastCapture`
- both color assignments
- seeds `0` and `1`
- `length=600`, which equals `150` moves per agent

### 16.1 Overall ranking in this repo’s engine

1. `anish` — `126-10-8`, win% `0.903`
2. `master` — `83-43-18`, win% `0.639`
3. `LuChenyang3842` — `11-13-0`
4. `uripont` — `10-12-2`
5. `kkkkkaran` — `8-13-3`
6. `vincent916735` — `6-16-2`
7. `ngacho` — `2-17-5`
8. `abhinavcreed13` — `3-19-2`
9. `apattichis` — `2-19-3`
10. `lzheng1026` — `0-20-4`
11. `DarioVajda` — `0-21-3`
12. `martbojinov` — `0-24-0`
13. `jaredjxyz` — `0-24-0`

### 16.2 Key head-to-heads

- vs `master`: `10-1-1`
- vs `uripont`: `7-3-2`
- vs `LuChenyang3842`: `9-3-0`
- vs `vincent916735`: `10-1-1`
- vs `abhinavcreed13`: `10-1-1`

The remaining closest public opponent is `uripont`, but the current version is now positive in that matchup in this exact contest setting.

## 17. Why This Version Won More Consistently

The decisive changes relative to the earlier `anish` variant were:

- stop overvaluing diffuse hidden-defender beliefs
- simplify opening offense toward shallow, bankable food
- commit the closest agent to defense immediately on real home threats
- patrol frontier food, not arbitrary border points
- shorten the opening phase for a `150`-move-per-agent contest
- make retreat thresholds much more conservative about protecting carried food

In short: less theory, more tempo.

## 18. Remaining Weaknesses and Future Work

The current agent is strong, but not perfect.

### 18.1 Weakest remaining matchup

`uripont` is still the closest public opponent. The current margin is positive, but not dominant.

### 18.2 Known architectural limits

- beliefs are still a simple heuristic tracker, not a full exact-inference model
- tactical search only reasons about one visible enemy at a time
- no learned opponent modeling
- no route-level teammate joint optimization beyond lane split and goal overlap penalties

### 18.3 Best future upgrades

If more work is needed, the next high-value upgrades are:

- better interception of likely invader return routes
- more explicit modeling of defender coverage over border entries
- route-level “safe return corridor” caching
- light map-type specialization for open vs tunnel-heavy boards
- opponent-specific adaptation after repeated matches

## 19. How to Run It

### 19.1 Against master in GUI

`anish` as red:

```bash
python3 capture.py -r myTeam.py -b /tmp/introtoai-master-agent/project/myTeam.py -l strategicCapture -i 600 -f -c
```

`anish` as blue:

```bash
python3 capture.py -r /tmp/introtoai-master-agent/project/myTeam.py -b myTeam.py -l strategicCapture -i 600 -f -c
```

### 19.2 Full short-horizon public benchmark

```bash
python3 tests/rank_public_agents.py --layouts defaultCapture,strategicCapture,fastCapture --seeds 0,1 --length 600
```

## 20. Bottom Line

The current agent is not “the most theoretically sophisticated” team in the repo set. It is the best-engineered team for this exact environment:

- carry-home scoring
- hidden enemies
- `150` moves per agent
- strict `1s` warning budget

That is why the final design is a hybrid heuristic-search controller with shared memory and shallow tactical lookahead rather than a heavier single-paradigm system.
